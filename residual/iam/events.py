"""Lightweight IAM observation and receipt emitters.

Implements ENT1-R6 (all authentication events are observed and
receipted with user identity, timestamp, source IP, and authorization
result), ENT1-R4 (JIT elevation is observed and receipted), and
ENT1-R5 (service-account actions emit observations and are
distinguishable from human accounts in receipts).

These emitters are deliberately local to the IAM package and do not
depend on the station server; they follow the repository's receipt
style (canonical JSON + SHA-256 hash chaining).
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from ..core import ContractError, canonical, identifier


def subject_identifier(value: str) -> str:
    """Validate an IAM subject id. Unlike core identifiers, IdP subjects
    may be emails or URNs (ENT1-R1)."""
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.@:+\-/]{0,127}", value):
        raise ContractError("invalid subject identifier")
    return value


OBSERVATION_SCHEMA = "residual.iam.observation.v1"
RECEIPT_SCHEMA = "residual.iam.receipt.v1"

#: Authentication event types that MUST be observed (ENT1-R6).
EVENT_LOGIN = "login"
EVENT_LOGOUT = "logout"
EVENT_TOKEN_REFRESH = "token_refresh"
EVENT_ELEVATION = "permission_elevation"
EVENT_ACCESS_DENIED = "access_denied"
EVENT_SERVICE_ACTION = "service_account_action"
EVENT_SESSION_REVOKED = "session_revoked"
EVENT_MFA = "mfa_event"

AUTH_EVENT_TYPES = frozenset({
    EVENT_LOGIN,
    EVENT_LOGOUT,
    EVENT_TOKEN_REFRESH,
    EVENT_ELEVATION,
    EVENT_ACCESS_DENIED,
    EVENT_SERVICE_ACTION,
    EVENT_SESSION_REVOKED,
    EVENT_MFA,
})

#: Subject kinds; service accounts are distinguishable in receipts (ENT1-R5).
SUBJECT_HUMAN = "human"
SUBJECT_SERVICE = "service"


def validate_ip(value: str) -> str:
    """Validate that a value is a syntactically valid IP address."""
    if not isinstance(value, str):
        raise ContractError("source IP must be a string")
    try:
        ipaddress.ip_address(value)
    except ValueError as exc:
        raise ContractError("invalid source IP address") from exc
    return value


@dataclass(frozen=True)
class Observation:
    """A single observed IAM event. Implements ENT1-R6."""

    event_type: str
    subject_id: str
    timestamp: int
    source_ip: str
    result: str  # "allow" or "deny"
    subject_type: str = SUBJECT_HUMAN
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.event_type not in AUTH_EVENT_TYPES:
            raise ContractError("unknown IAM observation event type")
        subject_identifier(self.subject_id)
        if type(self.timestamp) is not int:
            raise ContractError("observation timestamp must be an integer")
        validate_ip(self.source_ip)
        if self.result not in ("allow", "deny"):
            raise ContractError("observation result must be 'allow' or 'deny'")
        if self.subject_type not in (SUBJECT_HUMAN, SUBJECT_SERVICE):
            raise ContractError("invalid subject type")
        if not isinstance(self.details, dict):
            raise ContractError("observation details must be a dict")
        canonical(self.details)

    def payload(self) -> dict:
        return {
            "schema": OBSERVATION_SCHEMA,
            "event_type": self.event_type,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "timestamp": self.timestamp,
            "source_ip": self.source_ip,
            "result": self.result,
            "details": self.details,
        }


@dataclass(frozen=True)
class EventReceipt:
    """Tamper-evident receipt for an observation. Implements ENT1-R6.

    Receipts form a hash chain so deletion or reordering of the IAM
    audit trail is detectable.
    """

    receipt_hash: str
    observation_hash: str
    previous_hash: str
    event_type: str
    subject_id: str
    subject_type: str
    timestamp: int

    def __post_init__(self):
        for value in (self.receipt_hash, self.observation_hash):
            if not isinstance(value, str) or len(value) != 64:
                raise ContractError("receipt hashes must be SHA-256 digests")
        if not isinstance(self.previous_hash, str):
            raise ContractError("previous hash must be a string")

    def payload(self) -> dict:
        return {
            "schema": RECEIPT_SCHEMA,
            "receipt_hash": self.receipt_hash,
            "observation_hash": self.observation_hash,
            "previous_hash": self.previous_hash,
            "event_type": self.event_type,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "timestamp": self.timestamp,
        }


GENESIS_HASH = "0" * 64


class EventLog:
    """In-memory, append-only IAM observation/receipt log.

    Implements ENT1-R6: every observed event yields an Observation and
    a chained EventReceipt. Implements ENT1-R4 and ENT1-R5 by serving
    as the sink for elevation and service-account events.
    """

    def __init__(self, clock: Callable[[], int]):
        if not callable(clock):
            raise ContractError("clock must be callable")
        self._clock = clock
        self._observations: list[Observation] = []
        self._receipts: list[EventReceipt] = []

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    @property
    def receipts(self) -> tuple[EventReceipt, ...]:
        return tuple(self._receipts)

    def record(
        self,
        event_type: str,
        subject_id: str,
        source_ip: str,
        result: str,
        *,
        subject_type: str = SUBJECT_HUMAN,
        details: dict | None = None,
        timestamp: int | None = None,
    ) -> tuple[Observation, EventReceipt]:
        """Observe an IAM event and issue a chained receipt (ENT1-R6)."""
        ts = self._clock() if timestamp is None else timestamp
        if type(ts) is not int:
            raise ContractError("clock must return integer time")
        observation = Observation(
            event_type=event_type,
            subject_id=subject_id,
            timestamp=ts,
            source_ip=source_ip,
            result=result,
            subject_type=subject_type,
            details=dict(details or {}),
        )
        observation_hash = hashlib.sha256(canonical(observation.payload()).encode("utf-8")).hexdigest()
        previous_hash = self._receipts[-1].receipt_hash if self._receipts else GENESIS_HASH
        receipt_core = {
            "schema": RECEIPT_SCHEMA,
            "observation_hash": observation_hash,
            "previous_hash": previous_hash,
            "event_type": observation.event_type,
            "subject_id": observation.subject_id,
            "subject_type": observation.subject_type,
            "timestamp": observation.timestamp,
        }
        receipt_hash = hashlib.sha256(canonical(receipt_core).encode("utf-8")).hexdigest()
        receipt = EventReceipt(
            receipt_hash=receipt_hash,
            observation_hash=observation_hash,
            previous_hash=previous_hash,
            event_type=observation.event_type,
            subject_id=observation.subject_id,
            subject_type=observation.subject_type,
            timestamp=observation.timestamp,
        )
        self._observations.append(observation)
        self._receipts.append(receipt)
        return observation, receipt

    def verify_chain(self) -> bool:
        """Verify the hash chain and that receipts match observations."""
        previous = GENESIS_HASH
        for observation, receipt in zip(self._observations, self._receipts):
            expected_obs_hash = hashlib.sha256(
                canonical(observation.payload()).encode("utf-8")
            ).hexdigest()
            if receipt.observation_hash != expected_obs_hash:
                return False
            if receipt.previous_hash != previous:
                return False
            core = receipt.payload()
            expected_receipt_hash = hashlib.sha256(
                canonical({k: v for k, v in core.items() if k != "receipt_hash"}).encode("utf-8")
            ).hexdigest()
            if receipt.receipt_hash != expected_receipt_hash:
                return False
            previous = receipt.receipt_hash
        return len(self._observations) == len(self._receipts)


def record_auth_event(
    log: EventLog,
    event_type: str,
    user_id: str,
    source_ip: str,
    result: str,
    details: dict | None = None,
) -> tuple[Observation, EventReceipt]:
    """Convenience helper implementing ENT1-R6 for login/logout/token
    refresh/elevation/access-denial events."""
    return log.record(event_type, user_id, source_ip, result, details=details)
