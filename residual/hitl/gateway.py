"""Durable escalation challenges. Operator authentication is host supplied.

A challenge MAC proves server-issued content, not operator identity. Without an
explicit authenticator, approvals fail closed. This module never resumes a run.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from observation_layer.core import freeze
from ..core import ContractError, canonical, strict_json, identifier
from ..goalspec import GoalSpec


class HITLStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass(frozen=True)
class HITLChallenge:
    challenge_id: str
    task_id: str
    proposed_action: dict[str, Any]
    reason: str
    goal_spec_hash: str
    timestamp_ns: int
    validity_window_s: float
    signature: str

    def __post_init__(self):
        object.__setattr__(self, "proposed_action", freeze(self.proposed_action))

    @property
    def is_expired(self):
        return (time.time_ns() - self.timestamp_ns) / 1e9 >= self.validity_window_s


class HITLEscalationGateway:
    def __init__(self, signing_key: bytes, challenge_dir: str,
                 validity_window_s: float = 3600.0, *, authenticate=None):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise ContractError("signing key requires at least 32 bytes")
        if type(validity_window_s) not in (int, float) or not math.isfinite(validity_window_s) or validity_window_s <= 0:
            raise ContractError("validity window must be positive and finite")
        if authenticate is not None and not callable(authenticate):
            raise ContractError("authenticator must be a host callable")
        self._key, self._validity_s, self._authenticate = signing_key, validity_window_s, authenticate
        directory = Path(challenge_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / "challenges.sqlite3"
        with sqlite3.connect(self._path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS challenges (id TEXT PRIMARY KEY, record TEXT NOT NULL)")

    def _sign(self, data):
        return hmac.new(self._key, ("residual.hitl.challenge.v1\n" + canonical(data)).encode(), hashlib.sha256).hexdigest()

    def _store(self, db, data):
        record = {**data, "signature": self._sign(data)}
        db.execute("INSERT OR REPLACE INTO challenges VALUES (?, ?)", (data["challenge_id"], canonical(record)))
        return record

    def generate_challenge(self, task_id: str, proposed_action: dict[str, Any], reason: str, goal_spec: GoalSpec):
        identifier(task_id)
        if not reason.strip():
            raise ContractError("challenge requires a reason")
        data = {"schema_version": "residual.hitl.challenge.v1", "challenge_id": str(uuid.uuid4()),
                "payload": {"task_id": task_id, "action": strict_json(canonical(proposed_action)),
                            "reason": reason, "goal_spec_hash": goal_spec.content_hash},
                "timestamp_ns": time.time_ns(), "validity_window_s": self._validity_s,
                "authorized_roles": list(goal_spec.amendment_rule.authorized_roles), "status": HITLStatus.PENDING.value}
        with sqlite3.connect(self._path) as db:
            record = self._store(db, data)
        return HITLChallenge(data["challenge_id"], task_id, proposed_action, reason, goal_spec.content_hash,
                             data["timestamp_ns"], self._validity_s, record["signature"])

    def _read(self, db, challenge_id):
        try:
            if str(uuid.UUID(challenge_id)) != challenge_id:
                return None
            row = db.execute("SELECT record FROM challenges WHERE id=?", (challenge_id,)).fetchone()
            if row is None:
                return None
            record = strict_json(row[0])
            signature = record.pop("signature")
            if record["challenge_id"] != challenge_id or not hmac.compare_digest(signature, self._sign(record)):
                return None
            return {**record, "signature": signature}
        except (ValueError, KeyError, TypeError, AttributeError):
            return None

    def verify_approval(self, challenge_id: str, operator_response: str,
                        operator_role: str, authorized_roles: tuple[str, ...]) -> HITLStatus:
        """Atomically consume one authenticated approval. Replays are denied.

        The host authenticator must validate its operator/session and bind the
        response to this exact challenge. A caller-supplied role is not identity.
        """
        with sqlite3.connect(self._path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            record = self._read(db, challenge_id)
            if record is None or record["status"] != HITLStatus.PENDING.value:
                return HITLStatus.DENIED
            data = {k: v for k, v in record.items() if k != "signature"}
            age = (time.time_ns() - record["timestamp_ns"]) / 1e9
            if age < 0 or age >= record["validity_window_s"]:
                data["status"] = HITLStatus.EXPIRED.value
                self._store(db, data)
                return HITLStatus.EXPIRED
            if operator_role not in record["authorized_roles"] or operator_role not in authorized_roles or self._authenticate is None:
                return HITLStatus.DENIED
            try:
                authenticated = self._authenticate(freeze(record), operator_response, operator_role)
            except Exception:
                return HITLStatus.DENIED
            if authenticated is not True:
                return HITLStatus.DENIED
            data["status"] = HITLStatus.APPROVED.value
            self._store(db, data)
            return HITLStatus.APPROVED

    def get_challenge(self, challenge_id: str):
        with sqlite3.connect(self._path) as db:
            return self._read(db, challenge_id)
