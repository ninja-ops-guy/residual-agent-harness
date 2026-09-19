"""Encrypted durable mission queue behind the Copilot authorization gateway.

This backend is the admission/execution handoff. The HTTP-facing process can
persist an already-authorized MissionBinding + ExecutionPlan, while trusted
Factory workers claim work through leases. Mission content is encrypted through
RESIDUAL's CryptoProvider; production deployments must inject a KMS/HSM-backed
provider.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ...core import ContractError, canonical, identifier, strict_json
from ...crypto.provider import CryptoProvider
from ...factory.models import ExecutionPlan
from .gateway import MissionBinding, MissionRequest

_TERMINAL = frozenset({"completed", "failed", "cancelled", "rejected", "lease_expired"})
_ACTIVE = frozenset({"running", "cancellation_requested"})


@dataclass(frozen=True)
class QueuedMissionWork:
    binding: MissionBinding
    request: MissionRequest
    plan: ExecutionPlan
    lease_id: str
    lease_generation: int
    lease_expires_at: float

    def __post_init__(self):
        if not isinstance(self.binding, MissionBinding):
            raise ContractError("queued work requires MissionBinding")
        if not isinstance(self.request, MissionRequest):
            raise ContractError("queued work requires MissionRequest")
        if not isinstance(self.plan, ExecutionPlan):
            raise ContractError("queued work requires ExecutionPlan")
        if not isinstance(self.lease_id, str) or not self.lease_id:
            raise ContractError("queued work lease_id is required")
        if type(self.lease_generation) is not int or self.lease_generation < 1:
            raise ContractError("queued work lease generation is invalid")


class EncryptedMissionQueueBackend:
    """Durable encrypted MissionBackend plus trusted worker lease operations."""

    def __init__(
        self,
        path: str | Path,
        crypto: CryptoProvider,
        *,
        clock: Callable[[], float] = time.time,
    ):
        if not isinstance(crypto, CryptoProvider):
            raise ContractError("production mission queue requires a CryptoProvider")
        if not callable(clock):
            raise ContractError("mission queue clock must be callable")
        self.path = Path(path).absolute()
        self.crypto = crypto
        self._clock = clock
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._protect_parent()
        self._protect_file()
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    binding_hash TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    encrypted_payload BLOB NOT NULL,
                    state TEXT NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    lease_id TEXT,
                    lease_owner TEXT,
                    lease_generation INTEGER NOT NULL DEFAULT 0,
                    lease_expires_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS missions_state_idx
                    ON missions(state, created_at);
                CREATE TABLE IF NOT EXISTS evidence (
                    mission_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    encrypted_payload BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (mission_id, sequence),
                    FOREIGN KEY (mission_id) REFERENCES missions(mission_id)
                );
                """
            )

    def _protect_parent(self) -> None:
        if os.name != "posix":
            return
        parent = self.path.parent
        if parent.resolve(strict=False) != parent:
            raise ContractError("mission queue directory must not traverse symlinks")
        info = parent.stat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
        ):
            raise ContractError(
                "mission queue directory must be private and owned by the service"
            )

    def _protect_file(self) -> None:
        if os.name != "posix":
            return
        if self.path.resolve(strict=False) != self.path:
            raise ContractError("mission queue path must not traverse symlinks")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
            ):
                raise ContractError(
                    "mission queue must be a private regular file owned by the service"
                )
        finally:
            os.close(fd)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _aad(self, mission_id: str, kind: str) -> bytes:
        return f"residual.copilot.{kind}.v1:{mission_id}".encode("utf-8")

    def _encrypt(self, mission_id: str, kind: str, value: Any) -> bytes:
        return self.crypto.encrypt(
            canonical(value).encode("utf-8"),
            aad=self._aad(mission_id, kind),
        )

    def _decrypt(self, mission_id: str, kind: str, blob: bytes) -> Any:
        try:
            plain = self.crypto.decrypt(blob, aad=self._aad(mission_id, kind))
            return strict_json(plain.decode("utf-8"))
        except ContractError:
            raise
        except Exception as exc:
            raise ContractError("mission queue encrypted payload is invalid") from exc

    @staticmethod
    def _binding_dict(binding: MissionBinding) -> dict[str, Any]:
        return {
            "mission_id": binding.mission_id,
            "tenant_id": binding.tenant_id,
            "subject_id": binding.subject_id,
            "object_id": binding.object_id,
            "department": binding.department,
            "request_id": binding.request_id,
            "request_hash": binding.request_hash,
            "template_id": binding.template_id,
            "plan_hash": binding.plan_hash,
            "capabilities": list(binding.capabilities),
        }

    @staticmethod
    def _binding_from(data: dict[str, Any]) -> MissionBinding:
        return MissionBinding(
            mission_id=data["mission_id"],
            tenant_id=data["tenant_id"],
            subject_id=data["subject_id"],
            object_id=data["object_id"],
            department=data["department"],
            request_id=data["request_id"],
            request_hash=data["request_hash"],
            template_id=data["template_id"],
            plan_hash=data["plan_hash"],
            capabilities=tuple(data["capabilities"]),
        )

    def _mission_payload(
        self,
        binding: MissionBinding,
        request: MissionRequest,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        return {
            "schema_version": "residual.copilot.queued-mission.v1",
            "binding": self._binding_dict(binding),
            "request": request.payload(),
            "plan": plan.to_dict(),
        }

    def _validate_submission(
        self,
        binding: MissionBinding,
        request: MissionRequest,
        plan: ExecutionPlan,
    ) -> None:
        if binding.request_hash != request.request_hash:
            raise ContractError("mission binding/request hash mismatch")
        if binding.plan_hash != plan.graph_hash:
            raise ContractError("mission binding/plan hash mismatch")
        if binding.template_id != request.template_id:
            raise ContractError("mission binding/template mismatch")

    def _append_evidence(
        self,
        db: sqlite3.Connection,
        mission_id: str,
        kind: str,
        payload: dict[str, Any],
    ) -> None:
        identifier(kind)
        row = db.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM evidence WHERE mission_id=?",
            (mission_id,),
        ).fetchone()
        sequence = int(row[0])
        db.execute(
            """
            INSERT INTO evidence(mission_id, sequence, kind, encrypted_payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                mission_id,
                sequence,
                kind,
                self._encrypt(mission_id, f"evidence:{sequence}", payload),
                float(self._clock()),
            ),
        )

    def _row_status(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "mission_id": row["mission_id"],
            "state": row["state"],
            "template_id": row["template_id"],
            "approval_required": False,
            "binding_hash": row["binding_hash"],
            "plan_hash": row["plan_hash"],
            "cancel_requested": bool(row["cancel_requested"]),
        }

    # MissionBackend -----------------------------------------------------

    def submit(
        self,
        binding: MissionBinding,
        request: MissionRequest,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        self._validate_submission(binding, request, plan)
        payload = self._mission_payload(binding, request, plan)
        encrypted = self._encrypt(binding.mission_id, "mission", payload)
        now = float(self._clock())
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute(
                    "SELECT * FROM missions WHERE mission_id=?",
                    (binding.mission_id,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["binding_hash"] != binding.binding_hash
                        or existing["request_hash"] != request.request_hash
                        or existing["plan_hash"] != plan.graph_hash
                        or existing["template_id"] != binding.template_id
                    ):
                        raise ContractError("mission id collision or non-idempotent resubmission")
                    db.execute("COMMIT")
                    return self._row_status(existing)
                db.execute(
                    """
                    INSERT INTO missions(
                        mission_id, binding_hash, request_hash, plan_hash,
                        template_id, encrypted_payload, state,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)
                    """,
                    (
                        binding.mission_id,
                        binding.binding_hash,
                        request.request_hash,
                        plan.graph_hash,
                        binding.template_id,
                        encrypted,
                        now,
                        now,
                    ),
                )
                self._append_evidence(
                    db,
                    binding.mission_id,
                    "mission_binding",
                    {
                        "binding_hash": binding.binding_hash,
                        "request_hash": binding.request_hash,
                        "plan_hash": binding.plan_hash,
                        "template_id": binding.template_id,
                    },
                )
                row = db.execute(
                    "SELECT * FROM missions WHERE mission_id=?",
                    (binding.mission_id,),
                ).fetchone()
                db.execute("COMMIT")
                return self._row_status(row)
            except BaseException:
                try:
                    db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def status(self, mission_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
        if row is None:
            raise ContractError("unknown mission")
        return self._row_status(row)

    def evidence(self, mission_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as db:
            exists = db.execute(
                "SELECT 1 FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone()
            rows = db.execute(
                """
                SELECT sequence, kind, encrypted_payload
                FROM evidence WHERE mission_id=? ORDER BY sequence
                """,
                (mission_id,),
            ).fetchall()
        if exists is None:
            raise ContractError("unknown mission")
        result = []
        for row in rows:
            payload = self._decrypt(
                mission_id, f"evidence:{row['sequence']}", row["encrypted_payload"]
            )
            if not isinstance(payload, dict):
                raise ContractError("mission evidence payload must be an object")
            result.append({**payload, "kind": row["kind"]})
        return tuple(result)

    def cancel(self, mission_id: str) -> dict[str, Any]:
        now = float(self._clock())
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
                ).fetchone()
                if row is None:
                    raise ContractError("unknown mission")
                if row["state"] in _TERMINAL:
                    db.execute("COMMIT")
                    return self._row_status(row)
                if row["state"] == "queued":
                    state = "cancelled"
                else:
                    state = "cancellation_requested"
                db.execute(
                    """
                    UPDATE missions SET cancel_requested=1, state=?, updated_at=?
                    WHERE mission_id=?
                    """,
                    (state, now, mission_id),
                )
                self._append_evidence(
                    db, mission_id, "cancellation_requested", {"state": state}
                )
                row = db.execute(
                    "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
                ).fetchone()
                db.execute("COMMIT")
                return self._row_status(row)
            except BaseException:
                try:
                    db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    # Trusted worker surface --------------------------------------------

    def claim_next(
        self,
        worker_id: str,
        *,
        lease_seconds: float = 60.0,
    ) -> QueuedMissionWork | None:
        identifier(worker_id)
        if type(lease_seconds) not in (int, float) or not 1 <= lease_seconds <= 3600:
            raise ContractError("lease_seconds is out of bounds")
        now = float(self._clock())
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    """
                    SELECT * FROM missions
                    WHERE state='queued' AND cancel_requested=0
                    ORDER BY created_at, mission_id
                    LIMIT 1
                    """
                ).fetchone()
                if row is None:
                    db.execute("COMMIT")
                    return None
                lease_id = secrets.token_hex(16)
                generation = int(row["lease_generation"]) + 1
                expires = now + float(lease_seconds)
                cursor = db.execute(
                    """
                    UPDATE missions
                    SET state='running', lease_id=?, lease_owner=?,
                        lease_generation=?, lease_expires_at=?, updated_at=?
                    WHERE mission_id=? AND state='queued' AND cancel_requested=0
                    """,
                    (
                        lease_id, worker_id, generation, expires, now,
                        row["mission_id"],
                    ),
                )
                if cursor.rowcount != 1:
                    raise ContractError("mission claim race")
                self._append_evidence(
                    db,
                    row["mission_id"],
                    "mission_claimed",
                    {
                        "worker_id": worker_id,
                        "lease_generation": generation,
                    },
                )
                blob = row["encrypted_payload"]
                mission_id = row["mission_id"]
                db.execute("COMMIT")
            except BaseException:
                try:
                    db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
        payload = self._decrypt(mission_id, "mission", blob)
        binding = self._binding_from(payload["binding"])
        request = MissionRequest.from_dict(payload["request"])
        plan = ExecutionPlan.from_dict(payload["plan"])
        if (
            binding.binding_hash != self.status(mission_id)["binding_hash"]
            or binding.plan_hash != plan.graph_hash
            or binding.request_hash != request.request_hash
        ):
            raise ContractError("decrypted mission binding failed integrity checks")
        return QueuedMissionWork(
            binding=binding,
            request=request,
            plan=plan,
            lease_id=lease_id,
            lease_generation=generation,
            lease_expires_at=expires,
        )

    def _active_row(
        self,
        db: sqlite3.Connection,
        mission_id: str,
        lease_id: str,
    ) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
        ).fetchone()
        if row is None:
            raise ContractError("unknown mission")
        if row["state"] not in _ACTIVE or row["lease_id"] != lease_id:
            raise ContractError("stale or inactive mission lease")
        return row

    def heartbeat(
        self,
        mission_id: str,
        lease_id: str,
        *,
        lease_seconds: float = 60.0,
    ) -> dict[str, Any]:
        if type(lease_seconds) not in (int, float) or not 1 <= lease_seconds <= 3600:
            raise ContractError("lease_seconds is out of bounds")
        now = float(self._clock())
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = self._active_row(db, mission_id, lease_id)
                if row["lease_expires_at"] is not None and now > row["lease_expires_at"]:
                    raise ContractError("mission lease expired")
                expires = now + float(lease_seconds)
                db.execute(
                    """
                    UPDATE missions SET lease_expires_at=?, updated_at=?
                    WHERE mission_id=?
                    """,
                    (expires, now, mission_id),
                )
                updated = db.execute(
                    "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
                ).fetchone()
                db.execute("COMMIT")
                return self._row_status(updated)
            except BaseException:
                try:
                    db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def cancellation_requested(self, mission_id: str, lease_id: str) -> bool:
        with self._connect() as db:
            row = self._active_row(db, mission_id, lease_id)
        return bool(row["cancel_requested"])

    def complete(
        self,
        mission_id: str,
        lease_id: str,
        *,
        evidence: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        return self._terminalize(
            mission_id, lease_id, "completed", "mission_completed", evidence
        )

    def fail(
        self,
        mission_id: str,
        lease_id: str,
        *,
        error_code: str,
        evidence: tuple[dict[str, Any], ...] = (),
    ) -> dict[str, Any]:
        identifier(error_code)
        return self._terminalize(
            mission_id,
            lease_id,
            "failed",
            "mission_failed",
            ({"error_code": error_code},) + tuple(evidence),
        )

    def acknowledge_cancel(
        self,
        mission_id: str,
        lease_id: str,
        *,
        evidence: tuple[dict[str, Any], ...] = (),
    ) -> dict[str, Any]:
        return self._terminalize(
            mission_id, lease_id, "cancelled", "mission_cancelled", evidence,
            require_cancel=True,
        )

    def _terminalize(
        self,
        mission_id: str,
        lease_id: str,
        state: str,
        kind: str,
        evidence: tuple[dict[str, Any], ...],
        *,
        require_cancel: bool = False,
    ) -> dict[str, Any]:
        if state not in _TERMINAL:
            raise ContractError("invalid terminal mission state")
        if (
            not isinstance(evidence, tuple)
            or len(evidence) > 64
            or any(not isinstance(x, dict) for x in evidence)
        ):
            raise ContractError("mission evidence must be at most 64 objects")
        for item in evidence:
            if len(canonical(item).encode("utf-8")) > 64 * 1024:
                raise ContractError("mission evidence item exceeds 64 KB")
        now = float(self._clock())
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
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
                    """
                    UPDATE missions SET state=?, lease_id=NULL, lease_owner=NULL,
                        lease_expires_at=NULL, updated_at=?
                    WHERE mission_id=?
                    """,
                    (state, now, mission_id),
                )
                updated = db.execute(
                    "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
                ).fetchone()
                db.execute("COMMIT")
                return self._row_status(updated)
            except BaseException:
                try:
                    db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def sweep_expired(self) -> tuple[str, ...]:
        """Fail closed on lease loss; never automatically re-run uncertain work."""
        now = float(self._clock())
        expired: list[str] = []
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                rows = db.execute(
                    """
                    SELECT mission_id FROM missions
                    WHERE state IN ('running','cancellation_requested')
                      AND lease_expires_at IS NOT NULL
                      AND lease_expires_at < ?
                    ORDER BY mission_id
                    """,
                    (now,),
                ).fetchall()
                for row in rows:
                    mission_id = row["mission_id"]
                    self._append_evidence(
                        db, mission_id, "mission_lease_expired",
                        {"state": "lease_expired"},
                    )
                    db.execute(
                        """
                        UPDATE missions SET state='lease_expired',
                            lease_id=NULL, lease_owner=NULL,
                            lease_expires_at=NULL, updated_at=?
                        WHERE mission_id=?
                        """,
                        (now, mission_id),
                    )
                    expired.append(mission_id)
                db.execute("COMMIT")
            except BaseException:
                try:
                    db.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
        return tuple(expired)
