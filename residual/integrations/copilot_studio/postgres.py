"""PostgreSQL persistence for horizontally scaled Copilot Studio services.

Mission bodies and evidence stay application-encrypted through CryptoProvider.
PostgreSQL provides shared transactional ownership, idempotency, row fencing, and
SKIP LOCKED worker claims across gateway/worker instances.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from typing import Any, Callable

from ...core import ContractError, canonical, identifier, strict_json
from ...crypto.provider import CryptoProvider
from ...factory.models import ExecutionPlan
from .backend import QueuedMissionWork
from .gateway import MissionBinding, MissionRequest
from .store import MissionRecord

_PREFIX_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_TERMINAL = frozenset({"completed", "failed", "cancelled", "rejected", "lease_expired"})
_ACTIVE = frozenset({"running", "cancellation_requested"})


def _psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - environment/package dependent
        raise ContractError(
            "PostgreSQL support requires the optional enterprise dependency"
        ) from exc
    return psycopg, dict_row


def _prefix(value: str) -> str:
    if not isinstance(value, str) or not _PREFIX_RE.fullmatch(value):
        raise ContractError("PostgreSQL table prefix must be a safe lowercase identifier")
    return value


class PostgresMissionStore:
    """Shared MissionStore for gateway ownership/idempotency."""

    def __init__(self, dsn: str, *, table_prefix: str = "residual_copilot"):
        if not isinstance(dsn, str) or not dsn.strip():
            raise ContractError("PostgreSQL DSN is required")
        self.dsn = dsn.strip()
        self.prefix = _prefix(table_prefix)
        self.table = f"{self.prefix}_ownership"
        self._init_schema()

    def _connect(self):
        psycopg, dict_row = _psycopg()
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    mission_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    department TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    UNIQUE (tenant_id, object_id, request_id)
                )
            """)
            db.commit()

    @staticmethod
    def _record(row) -> MissionRecord | None:
        if row is None:
            return None
        return MissionRecord(
            tenant_id=row["tenant_id"], object_id=row["object_id"],
            department=row["department"], request_id=row["request_id"],
            request_hash=row["request_hash"], mission_id=row["mission_id"],
            template_id=row["template_id"],
        )

    def get_by_request(self, tenant_id: str, object_id: str,
                       request_id: str) -> MissionRecord | None:
        with self._connect() as db:
            row = db.execute(
                f"""SELECT * FROM {self.table}
                    WHERE tenant_id=%s AND object_id=%s AND request_id=%s""",
                (tenant_id, object_id, request_id),
            ).fetchone()
        return self._record(row)

    def get_by_mission(self, mission_id: str) -> MissionRecord | None:
        with self._connect() as db:
            row = db.execute(
                f"SELECT * FROM {self.table} WHERE mission_id=%s", (mission_id,)
            ).fetchone()
        return self._record(row)

    def claim(self, record: MissionRecord) -> tuple[MissionRecord, bool]:
        if not isinstance(record, MissionRecord):
            raise ContractError("mission store requires a MissionRecord")
        with self._connect() as db:
            inserted = db.execute(
                f"""INSERT INTO {self.table}(
                        mission_id,tenant_id,object_id,department,request_id,
                        request_hash,template_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                    RETURNING *""",
                (
                    record.mission_id, record.tenant_id, record.object_id,
                    record.department, record.request_id, record.request_hash,
                    record.template_id,
                ),
            ).fetchone()
            if inserted is not None:
                db.commit()
                return self._record(inserted), True

            prior = db.execute(
                f"""SELECT * FROM {self.table}
                    WHERE tenant_id=%s AND object_id=%s AND request_id=%s""",
                (record.tenant_id, record.object_id, record.request_id),
            ).fetchone()
            if prior is None:
                prior = db.execute(
                    f"SELECT * FROM {self.table} WHERE mission_id=%s",
                    (record.mission_id,),
                ).fetchone()
            db.commit()
        existing = self._record(prior)
        if existing is None:
            raise ContractError("mission ownership conflict could not be resolved")
        if existing != record:
            if (
                existing.tenant_id == record.tenant_id
                and existing.object_id == record.object_id
                and existing.request_id == record.request_id
            ):
                raise ContractError("mission idempotency record conflict")
            raise ContractError("mission id collision")
        return existing, False


class PostgresEncryptedMissionQueueBackend:
    """Horizontally shared encrypted MissionBackend with fenced worker leases."""

    def __init__(
        self, dsn: str, crypto: CryptoProvider, *,
        table_prefix: str = "residual_copilot",
        clock: Callable[[], float] = time.time,
    ):
        if not isinstance(dsn, str) or not dsn.strip():
            raise ContractError("PostgreSQL DSN is required")
        if not isinstance(crypto, CryptoProvider):
            raise ContractError("PostgreSQL mission queue requires a CryptoProvider")
        if not callable(clock):
            raise ContractError("mission queue clock must be callable")
        self.dsn = dsn.strip()
        self.crypto = crypto
        self.prefix = _prefix(table_prefix)
        self.missions = f"{self.prefix}_missions"
        self.evidence_table = f"{self.prefix}_evidence"
        self._clock = clock
        self._init_schema()

    def _connect(self):
        psycopg, dict_row = _psycopg()
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def _init_schema(self):
        with self._connect() as db:
            db.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.missions} (
                    mission_id TEXT PRIMARY KEY,
                    binding_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    encrypted_payload BYTEA NOT NULL,
                    state TEXT NOT NULL,
                    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
                    lease_id TEXT,
                    lease_owner TEXT,
                    lease_generation INTEGER NOT NULL DEFAULT 0,
                    lease_expires_at DOUBLE PRECISION,
                    created_at DOUBLE PRECISION NOT NULL,
                    updated_at DOUBLE PRECISION NOT NULL
                )
            """)
            db.execute(
                f"CREATE INDEX IF NOT EXISTS {self.prefix}_mission_state_idx "
                f"ON {self.missions}(state, created_at)"
            )
            db.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.evidence_table} (
                    mission_id TEXT NOT NULL REFERENCES {self.missions}(mission_id),
                    sequence INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    encrypted_payload BYTEA NOT NULL,
                    created_at DOUBLE PRECISION NOT NULL,
                    PRIMARY KEY (mission_id, sequence)
                )
            """)
            db.commit()

    def ping(self) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 AS ok").fetchone()["ok"] == 1

    def _aad(self, mission_id: str, kind: str) -> bytes:
        return f"residual.copilot.{kind}.v1:{mission_id}".encode()

    def _encrypt(self, mission_id: str, kind: str, value: Any) -> bytes:
        return self.crypto.encrypt(
            canonical(value).encode("utf-8"), aad=self._aad(mission_id, kind)
        )

    def _decrypt(self, mission_id: str, kind: str, blob: bytes) -> Any:
        try:
            return strict_json(
                self.crypto.decrypt(
                    bytes(blob), aad=self._aad(mission_id, kind)
                ).decode("utf-8")
            )
        except ContractError:
            raise
        except Exception as exc:
            raise ContractError("encrypted PostgreSQL mission payload is invalid") from exc

    @staticmethod
    def _binding_dict(binding: MissionBinding) -> dict[str, Any]:
        return {
            "mission_id": binding.mission_id, "tenant_id": binding.tenant_id,
            "subject_id": binding.subject_id, "object_id": binding.object_id,
            "department": binding.department, "request_id": binding.request_id,
            "request_hash": binding.request_hash, "template_id": binding.template_id,
            "plan_hash": binding.plan_hash, "capabilities": list(binding.capabilities),
        }

    @staticmethod
    def _binding_from(data: dict[str, Any]) -> MissionBinding:
        return MissionBinding(
            mission_id=data["mission_id"], tenant_id=data["tenant_id"],
            subject_id=data["subject_id"], object_id=data["object_id"],
            department=data["department"], request_id=data["request_id"],
            request_hash=data["request_hash"], template_id=data["template_id"],
            plan_hash=data["plan_hash"], capabilities=tuple(data["capabilities"]),
        )

    def _mission_payload(self, binding, request, plan):
        return {
            "schema_version": "residual.copilot.queued-mission.v1",
            "binding": self._binding_dict(binding),
            "request": request.payload(), "plan": plan.to_dict(),
        }

    def _validate_submission(self, binding, request, plan):
        if binding.request_hash != request.request_hash:
            raise ContractError("mission binding/request hash mismatch")
        if binding.plan_hash != plan.graph_hash:
            raise ContractError("mission binding/plan hash mismatch")
        if binding.template_id != request.template_id:
            raise ContractError("mission binding/template mismatch")

    def _append_evidence(self, db, mission_id: str, kind: str,
                         payload: dict[str, Any]) -> None:
        identifier(kind)
        seq = db.execute(
            f"SELECT COALESCE(MAX(sequence),0)+1 AS seq "
            f"FROM {self.evidence_table} WHERE mission_id=%s",
            (mission_id,),
        ).fetchone()["seq"]
        db.execute(
            f"""INSERT INTO {self.evidence_table}
                (mission_id,sequence,kind,encrypted_payload,created_at)
                VALUES (%s,%s,%s,%s,%s)""",
            (
                mission_id, seq, kind,
                self._encrypt(mission_id, f"evidence:{seq}", payload),
                float(self._clock()),
            ),
        )

    @staticmethod
    def _row_status(row):
        return {
            "mission_id": row["mission_id"], "state": row["state"],
            "template_id": row["template_id"], "approval_required": False,
            "binding_hash": row["binding_hash"], "plan_hash": row["plan_hash"],
            "cancel_requested": bool(row["cancel_requested"]),
        }

    def submit(self, binding: MissionBinding, request: MissionRequest,
               plan: ExecutionPlan) -> dict[str, Any]:
        self._validate_submission(binding, request, plan)
        now = float(self._clock())
        encrypted = self._encrypt(
            binding.mission_id, "mission",
            self._mission_payload(binding, request, plan),
        )
        with self._connect() as db:
            row = db.execute(
                f"""INSERT INTO {self.missions}(
                    mission_id,binding_hash,request_hash,plan_hash,template_id,
                    encrypted_payload,state,created_at,updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s,'queued',%s,%s)
                ON CONFLICT DO NOTHING RETURNING *""",
                (
                    binding.mission_id, binding.binding_hash, request.request_hash,
                    plan.graph_hash, binding.template_id, encrypted, now, now,
                ),
            ).fetchone()
            if row is None:
                row = db.execute(
                    f"SELECT * FROM {self.missions} WHERE mission_id=%s FOR UPDATE",
                    (binding.mission_id,),
                ).fetchone()
                if row is None or (
                    row["binding_hash"] != binding.binding_hash
                    or row["request_hash"] != request.request_hash
                    or row["plan_hash"] != plan.graph_hash
                    or row["template_id"] != binding.template_id
                ):
                    raise ContractError("mission id collision or non-idempotent resubmission")
                db.commit()
                return self._row_status(row)

            self._append_evidence(
                db, binding.mission_id, "mission_binding",
                {
                    "binding_hash": binding.binding_hash,
                    "request_hash": binding.request_hash,
                    "plan_hash": binding.plan_hash,
                    "template_id": binding.template_id,
                },
            )
            db.commit()
            return self._row_status(row)

    def status(self, mission_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                f"SELECT * FROM {self.missions} WHERE mission_id=%s", (mission_id,)
            ).fetchone()
        if row is None:
            raise ContractError("unknown mission")
        return self._row_status(row)

    def evidence(self, mission_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as db:
            exists = db.execute(
                f"SELECT 1 AS ok FROM {self.missions} WHERE mission_id=%s",
                (mission_id,),
            ).fetchone()
            rows = db.execute(
                f"""SELECT sequence,kind,encrypted_payload FROM {self.evidence_table}
                    WHERE mission_id=%s ORDER BY sequence""",
                (mission_id,),
            ).fetchall()
        if exists is None:
            raise ContractError("unknown mission")
        out = []
        for row in rows:
            payload = self._decrypt(
                mission_id, f"evidence:{row['sequence']}", row["encrypted_payload"]
            )
            if not isinstance(payload, dict):
                raise ContractError("mission evidence payload must be an object")
            out.append({**payload, "kind": row["kind"]})
        return tuple(out)

    def cancel(self, mission_id: str) -> dict[str, Any]:
        now = float(self._clock())
        with self._connect() as db:
            row = db.execute(
                f"SELECT * FROM {self.missions} WHERE mission_id=%s FOR UPDATE",
                (mission_id,),
            ).fetchone()
            if row is None:
                raise ContractError("unknown mission")
            if row["state"] in _TERMINAL:
                db.commit()
                return self._row_status(row)
            state = "cancelled" if row["state"] == "queued" else "cancellation_requested"
            db.execute(
                f"""UPDATE {self.missions}
                    SET cancel_requested=TRUE,state=%s,updated_at=%s
                    WHERE mission_id=%s""",
                (state, now, mission_id),
            )
            self._append_evidence(
                db, mission_id, "cancellation_requested", {"state": state}
            )
            row = db.execute(
                f"SELECT * FROM {self.missions} WHERE mission_id=%s",
                (mission_id,),
            ).fetchone()
            db.commit()
            return self._row_status(row)

    def claim_next(self, worker_id: str, *, lease_seconds: float = 60.0,
                   template_ids: frozenset[str] | None = None) -> QueuedMissionWork | None:
        identifier(worker_id)
        if type(lease_seconds) not in (int, float) or not 1 <= lease_seconds <= 3600:
            raise ContractError("lease_seconds is out of bounds")
        ordered = None
        if template_ids is not None:
            if not isinstance(template_ids, frozenset) or not template_ids:
                raise ContractError("template_ids must be a non-empty frozenset")
            for tid in template_ids:
                identifier(tid)
            ordered = tuple(sorted(template_ids))
        now = float(self._clock())
        with self._connect() as db:
            if ordered is None:
                row = db.execute(
                    f"""SELECT * FROM {self.missions}
                        WHERE state='queued' AND cancel_requested=FALSE
                        ORDER BY created_at,mission_id
                        FOR UPDATE SKIP LOCKED LIMIT 1"""
                ).fetchone()
            else:
                row = db.execute(
                    f"""SELECT * FROM {self.missions}
                        WHERE state='queued' AND cancel_requested=FALSE
                          AND template_id = ANY(%s)
                        ORDER BY created_at,mission_id
                        FOR UPDATE SKIP LOCKED LIMIT 1""",
                    (list(ordered),),
                ).fetchone()
            if row is None:
                db.commit()
                return None

            mission_id = row["mission_id"]
            payload = self._decrypt(mission_id, "mission", row["encrypted_payload"])
            if not isinstance(payload, dict):
                raise ContractError("decrypted mission payload must be an object")
            binding = self._binding_from(payload["binding"])
            request = MissionRequest.from_dict(payload["request"])
            plan = ExecutionPlan.from_dict(payload["plan"])
            if (
                binding.mission_id != mission_id
                or binding.binding_hash != row["binding_hash"]
                or binding.request_hash != row["request_hash"]
                or binding.plan_hash != row["plan_hash"]
                or binding.template_id != row["template_id"]
                or binding.plan_hash != plan.graph_hash
                or binding.request_hash != request.request_hash
            ):
                raise ContractError("decrypted mission binding failed integrity checks")

            lease_id = secrets.token_hex(16)
            generation = int(row["lease_generation"]) + 1
            expires = now + float(lease_seconds)
            db.execute(
                f"""UPDATE {self.missions}
                    SET state='running',lease_id=%s,lease_owner=%s,
                        lease_generation=%s,lease_expires_at=%s,updated_at=%s
                    WHERE mission_id=%s""",
                (lease_id, worker_id, generation, expires, now, mission_id),
            )
            self._append_evidence(
                db, mission_id, "mission_claimed",
                {"worker_id": worker_id, "lease_generation": generation},
            )
            db.commit()
        return QueuedMissionWork(
            binding=binding, request=request, plan=plan, lease_id=lease_id,
            lease_generation=generation, lease_expires_at=expires,
        )

    def _active_row(self, db, mission_id: str, lease_id: str):
        row = db.execute(
            f"SELECT * FROM {self.missions} WHERE mission_id=%s FOR UPDATE",
            (mission_id,),
        ).fetchone()
        if row is None:
            raise ContractError("unknown mission")
        if row["state"] not in _ACTIVE or row["lease_id"] != lease_id:
            raise ContractError("stale or inactive mission lease")
        return row

    def heartbeat(self, mission_id: str, lease_id: str, *,
                  lease_seconds: float = 60.0) -> dict[str, Any]:
        if type(lease_seconds) not in (int, float) or not 1 <= lease_seconds <= 3600:
            raise ContractError("lease_seconds is out of bounds")
        now = float(self._clock())
        with self._connect() as db:
            row = self._active_row(db, mission_id, lease_id)
            if row["lease_expires_at"] is not None and now > row["lease_expires_at"]:
                raise ContractError("mission lease expired")
            expires = now + float(lease_seconds)
            db.execute(
                f"UPDATE {self.missions} SET lease_expires_at=%s,updated_at=%s "
                f"WHERE mission_id=%s",
                (expires, now, mission_id),
            )
            updated = db.execute(
                f"SELECT * FROM {self.missions} WHERE mission_id=%s", (mission_id,)
            ).fetchone()
            db.commit()
            return self._row_status(updated)

    def cancellation_requested(self, mission_id: str, lease_id: str) -> bool:
        with self._connect() as db:
            row = self._active_row(db, mission_id, lease_id)
            value = bool(row["cancel_requested"])
            db.commit()
            return value

    def complete(self, mission_id: str, lease_id: str, *,
                 evidence: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        return self._terminalize(mission_id, lease_id, "completed",
                                 "mission_completed", evidence)

    def fail(self, mission_id: str, lease_id: str, *, error_code: str,
             evidence: tuple[dict[str, Any], ...] = ()) -> dict[str, Any]:
        identifier(error_code)
        return self._terminalize(
            mission_id, lease_id, "failed", "mission_failed",
            ({"error_code": error_code},) + tuple(evidence),
        )

    def acknowledge_cancel(self, mission_id: str, lease_id: str, *,
                           evidence: tuple[dict[str, Any], ...] = ()) -> dict[str, Any]:
        return self._terminalize(
            mission_id, lease_id, "cancelled", "mission_cancelled",
            evidence, require_cancel=True,
        )

    def _terminalize(self, mission_id: str, lease_id: str, state: str,
                     kind: str, evidence: tuple[dict[str, Any], ...], *,
                     require_cancel: bool = False) -> dict[str, Any]:
        if state not in _TERMINAL:
            raise ContractError("invalid terminal mission state")
        if (
            not isinstance(evidence, tuple) or len(evidence) > 64
            or any(not isinstance(item, dict) for item in evidence)
        ):
            raise ContractError("mission evidence must be at most 64 objects")
        for item in evidence:
            if len(canonical(item).encode("utf-8")) > 64 * 1024:
                raise ContractError("mission evidence item exceeds 64 KB")
        now = float(self._clock())
        with self._connect() as db:
            row = self._active_row(db, mission_id, lease_id)
            if row["lease_expires_at"] is not None and now > row["lease_expires_at"]:
                raise ContractError("mission lease expired")
            if require_cancel and not row["cancel_requested"]:
                raise ContractError("mission cancellation was not requested")
            if state == "completed" and row["cancel_requested"]:
                raise ContractError("cancelled mission cannot be completed")
            for item in evidence:
                self._append_evidence(db, mission_id, "worker_evidence", item)
            self._append_evidence(db, mission_id, kind, {"state": state})
            db.execute(
                f"""UPDATE {self.missions}
                    SET state=%s,lease_id=NULL,lease_owner=NULL,
                        lease_expires_at=NULL,updated_at=%s
                    WHERE mission_id=%s""",
                (state, now, mission_id),
            )
            updated = db.execute(
                f"SELECT * FROM {self.missions} WHERE mission_id=%s", (mission_id,)
            ).fetchone()
            db.commit()
            return self._row_status(updated)

    def sweep_expired(self) -> tuple[str, ...]:
        now = float(self._clock())
        expired = []
        with self._connect() as db:
            rows = db.execute(
                f"""SELECT * FROM {self.missions}
                    WHERE state IN ('running','cancellation_requested')
                      AND lease_expires_at IS NOT NULL AND lease_expires_at < %s
                    ORDER BY mission_id FOR UPDATE SKIP LOCKED""",
                (now,),
            ).fetchall()
            for row in rows:
                mission_id = row["mission_id"]
                self._append_evidence(
                    db, mission_id, "mission_lease_expired",
                    {"state": "lease_expired"},
                )
                db.execute(
                    f"""UPDATE {self.missions}
                        SET state='lease_expired',lease_id=NULL,lease_owner=NULL,
                            lease_expires_at=NULL,updated_at=%s
                        WHERE mission_id=%s""",
                    (now, mission_id),
                )
                expired.append(mission_id)
            db.commit()
        return tuple(expired)
