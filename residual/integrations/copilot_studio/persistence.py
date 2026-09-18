"""Durable SQLite store for Copilot Studio mission identity and replay state."""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from observation_layer.core import freeze

from ...control_plane.models import CapabilityGrant, Mission, MissionRevision
from ...core import ContractError, canonical, strict_json
from .contracts import CopilotAPIError, VerifiedPrincipal
from .service import (
    ACTIVE_STATES,
    STATE_TRANSITIONS,
    CopilotMissionRecord,
    CopilotMissionStore,
    MissionEvidenceRef,
)


def _record_dict(record: CopilotMissionRecord) -> dict[str, Any]:
    return {
        "mission": {
            "mission_id": record.mission.mission_id,
            "principal_id": record.mission.principal_id,
            "tenant_id": record.mission.tenant_id,
            "created_at": record.mission.created_at,
        },
        "revision": {
            "mission_id": record.revision.mission_id,
            "revision_id": record.revision.revision_id,
            "objective": record.revision.objective,
            "plan_hash": record.revision.plan_hash,
            "policy_hash": record.revision.policy_hash,
            "capability_grants": [
                {
                    "subject": grant.subject,
                    "action": grant.action,
                    "resource": grant.resource,
                    "scope": grant.scope,
                    "constraints": grant.constraints,
                    "conditions": grant.conditions,
                    "approval_policy": grant.approval_policy,
                    "expires_at": grant.expires_at,
                }
                for grant in record.revision.capability_grants
            ],
            "parent_revision": record.revision.parent_revision,
            "amendment_id": record.revision.amendment_id,
            "workspaces": list(record.revision.workspaces),
            "budget": record.revision.budget,
        },
        "request_id": record.request_id,
        "request_hash": record.request_hash,
        "claims_hash": record.claims_hash,
        "profile_id": record.profile_id,
        "template_id": record.template_id,
        "template_inputs": record.template_inputs,
        "state": record.state,
        "risk": record.risk,
        "approval_required": record.approval_required,
        "evidence_refs": [
            {
                "ref": item.ref,
                "mission_id": item.mission_id,
                "revision_id": item.revision_id,
                "plan_hash": item.plan_hash,
                "policy_hash": item.policy_hash,
                "claims_hash": item.claims_hash,
            }
            for item in record.evidence_refs
        ],
    }


def _record_from_dict(value: dict[str, Any]) -> CopilotMissionRecord:
    mission_data = value["mission"]
    revision_data = value["revision"]
    grants = tuple(
        CapabilityGrant(
            subject=item["subject"],
            action=item["action"],
            resource=item["resource"],
            scope=freeze(item.get("scope", {})),
            constraints=freeze(item.get("constraints", {})),
            conditions=freeze(item.get("conditions", {})),
            approval_policy=freeze(item.get("approval_policy", {})),
            expires_at=item.get("expires_at"),
        )
        for item in revision_data["capability_grants"]
    )
    revision = MissionRevision(
        mission_id=revision_data["mission_id"],
        revision_id=revision_data["revision_id"],
        objective=revision_data["objective"],
        plan_hash=revision_data["plan_hash"],
        policy_hash=revision_data["policy_hash"],
        capability_grants=grants,
        parent_revision=revision_data.get("parent_revision"),
        amendment_id=revision_data.get("amendment_id"),
        workspaces=tuple(revision_data.get("workspaces", ())),
        budget=freeze(revision_data.get("budget", {})),
    )
    return CopilotMissionRecord(
        mission=Mission(
            mission_id=mission_data["mission_id"],
            principal_id=mission_data["principal_id"],
            tenant_id=mission_data["tenant_id"],
            created_at=float(mission_data["created_at"]),
        ),
        revision=revision,
        request_id=value["request_id"],
        request_hash=value["request_hash"],
        claims_hash=value["claims_hash"],
        profile_id=value["profile_id"],
        template_id=value["template_id"],
        template_inputs=freeze(value["template_inputs"]),
        state=value["state"],
        risk=value["risk"],
        approval_required=bool(value["approval_required"]),
        evidence_refs=tuple(
            MissionEvidenceRef(**item) for item in value.get("evidence_refs", ())
        ),
    )


class SQLiteCopilotMissionStore:
    """Transactional store that preserves idempotency and ownership across restarts."""

    def __init__(self, path: str | Path):
        if path != ":memory:":
            db_path = Path(path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            if not db_path.exists():
                fd = os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            self.path = str(db_path)
        else:
            self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            isolation_level=None,
            timeout=30.0,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout=30000")
        if self.path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS copilot_missions (
                mission_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                state TEXT NOT NULL,
                record_json TEXT NOT NULL,
                UNIQUE(tenant_id, principal_id, request_id)
            )
        """)

    @staticmethod
    def _decode(row: sqlite3.Row) -> CopilotMissionRecord:
        try:
            value = strict_json(row["record_json"])
            record = _record_from_dict(value)
        except Exception:
            raise ContractError("stored Copilot mission record is invalid") from None
        if (
            record.mission.mission_id != row["mission_id"]
            or record.mission.tenant_id != row["tenant_id"]
            or record.mission.principal_id != row["principal_id"]
            or record.request_id != row["request_id"]
            or record.state != row["state"]
        ):
            raise ContractError("stored Copilot mission index does not match record")
        return record

    def _write(self, record: CopilotMissionRecord) -> None:
        self._conn.execute(
            """
            UPDATE copilot_missions
               SET state = ?, record_json = ?
             WHERE mission_id = ?
            """,
            (
                record.state,
                canonical(_record_dict(record)),
                record.mission.mission_id,
            ),
        )

    def create(
        self,
        record: CopilotMissionRecord,
        *,
        max_active: int,
    ) -> tuple[CopilotMissionRecord, bool]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    """
                    SELECT * FROM copilot_missions
                     WHERE tenant_id = ? AND principal_id = ? AND request_id = ?
                    """,
                    (
                        record.mission.tenant_id,
                        record.mission.principal_id,
                        record.request_id,
                    ),
                ).fetchone()
                if row is not None:
                    existing = self._decode(row)
                    CopilotMissionStore._check_retry(existing, record)
                    self._conn.execute("COMMIT")
                    return existing, False
                placeholders = ",".join("?" for _ in ACTIVE_STATES)
                active = self._conn.execute(
                    f"""
                    SELECT COUNT(*) AS n FROM copilot_missions
                     WHERE tenant_id = ? AND principal_id = ?
                       AND state IN ({placeholders})
                    """,
                    (
                        record.mission.tenant_id,
                        record.mission.principal_id,
                        *sorted(ACTIVE_STATES),
                    ),
                ).fetchone()["n"]
                if active >= max_active:
                    raise CopilotAPIError(
                        429,
                        "mission_limit",
                        "too many active missions for the signed-in identity",
                    )
                self._conn.execute(
                    """
                    INSERT INTO copilot_missions
                        (mission_id, tenant_id, principal_id, request_id, state, record_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.mission.mission_id,
                        record.mission.tenant_id,
                        record.mission.principal_id,
                        record.request_id,
                        record.state,
                        canonical(_record_dict(record)),
                    ),
                )
                self._conn.execute("COMMIT")
                return record, True
            except sqlite3.IntegrityError:
                self._conn.execute("ROLLBACK")
                raise CopilotAPIError(
                    409, "mission_conflict", "mission identity collision"
                ) from None
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def visible(
        self,
        mission_id: str,
        principal: VerifiedPrincipal,
    ) -> CopilotMissionRecord:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM copilot_missions
                 WHERE mission_id = ? AND tenant_id = ? AND principal_id = ?
                """,
                (mission_id, principal.tenant_id, principal.principal_id),
            ).fetchone()
            if row is None:
                raise CopilotAPIError(
                    404, "mission_not_found", "mission was not found"
                )
            return self._decode(row)

    @staticmethod
    def _transition(
        record: CopilotMissionRecord,
        state: str,
    ) -> CopilotMissionRecord:
        if state not in STATE_TRANSITIONS:
            raise ContractError("invalid Copilot mission state")
        if state not in STATE_TRANSITIONS[record.state]:
            raise ContractError(
                f"invalid Copilot mission transition {record.state}->{state}"
            )
        from dataclasses import replace
        return replace(record, state=state)

    def cancel(
        self,
        mission_id: str,
        principal: VerifiedPrincipal,
    ) -> CopilotMissionRecord:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                record = self.visible(mission_id, principal)
                if record.state in {
                    "cancel_requested", "cancelled", "complete", "failed"
                }:
                    self._conn.execute("COMMIT")
                    return record
                updated = self._transition(record, "cancel_requested")
                self._write(updated)
                self._conn.execute("COMMIT")
                return updated
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def attach_evidence(
        self,
        mission_id: str,
        evidence: MissionEvidenceRef,
    ) -> CopilotMissionRecord:
        if not isinstance(evidence, MissionEvidenceRef):
            raise ContractError("evidence must be an authority-bound reference")
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT * FROM copilot_missions WHERE mission_id = ?",
                    (mission_id,),
                ).fetchone()
                if row is None:
                    raise ContractError("unknown mission")
                record = self._decode(row)
                if evidence != record.bind_evidence(evidence.ref):
                    raise ContractError(
                        "evidence binding does not match mission authority"
                    )
                if any(item.ref == evidence.ref for item in record.evidence_refs):
                    self._conn.execute("COMMIT")
                    return record
                from dataclasses import replace
                updated = replace(
                    record, evidence_refs=record.evidence_refs + (evidence,)
                )
                self._write(updated)
                self._conn.execute("COMMIT")
                return updated
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def set_state(
        self,
        mission_id: str,
        state: str,
    ) -> CopilotMissionRecord:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT * FROM copilot_missions WHERE mission_id = ?",
                    (mission_id,),
                ).fetchone()
                if row is None:
                    raise ContractError("unknown mission")
                updated = self._transition(self._decode(row), state)
                self._write(updated)
                self._conn.execute("COMMIT")
                return updated
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    @property
    def records(self) -> tuple[CopilotMissionRecord, ...]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM copilot_missions ORDER BY mission_id"
            ).fetchall()
            return tuple(self._decode(row) for row in rows)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
