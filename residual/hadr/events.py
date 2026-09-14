"""Observation journal for HA/DR operations.

Implements ENT4-R8: all failover events, backup operations, and
restoration tests are observed and receipted. Every recorded event
produces a content-addressed event receipt so the HA/DR audit trail is
itself tamper-evident.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..core import ContractError, canonical

EVENT_SCHEMA = "residual.hadr.event.v1"

FAILOVER_EVENT = "failover"
BACKUP_EVENT = "backup"
RESTORE_EVENT = "restore-test"
TAKEOVER_EVENT = "takeover"
SYNC_EVENT = "degraded-sync"
LAG_ALERT_EVENT = "replication-lag-alert"

_KINDS = {
    FAILOVER_EVENT,
    BACKUP_EVENT,
    RESTORE_EVENT,
    TAKEOVER_EVENT,
    SYNC_EVENT,
    LAG_ALERT_EVENT,
}


@dataclass(frozen=True)
class EventReceipt:
    """A receipted HA/DR observation. Implements ENT4-R8."""

    event_hash: str
    kind: str
    at: float
    details: tuple[tuple[str, str], ...]
    prev_hash: str

    def detail_map(self) -> dict[str, str]:
        return dict(self.details)


@dataclass
class EventJournal:
    """Append-only, hash-chained journal of HA/DR events.

    Implements ENT4-R8: failover events, backup operations, and
    restoration tests recorded here are observed and receipted.
    """

    clock: object
    receipts: list[EventReceipt] = field(default_factory=list)

    def record(self, kind: str, details: dict[str, object]) -> EventReceipt:
        """Observe an operation and return its receipt. Implements ENT4-R8."""
        if kind not in _KINDS:
            raise ContractError(f"unknown HA/DR event kind: {kind!r}")
        at = float(self.clock.now())
        normalized = tuple(sorted((str(k), canonical(v)) for k, v in details.items()))
        prev = self.receipts[-1].event_hash if self.receipts else "0" * 64
        body = {"kind": kind, "at": at, "details": list(normalized), "prev_hash": prev}
        event_hash = hashlib.sha256(
            (EVENT_SCHEMA + "\n" + canonical(body)).encode("utf-8")).hexdigest()
        receipt = EventReceipt(event_hash, kind, at, normalized, prev)
        self.receipts.append(receipt)
        return receipt

    def of_kind(self, kind: str) -> list[EventReceipt]:
        return [r for r in self.receipts if r.kind == kind]

    def verify(self) -> bool:
        prev = "0" * 64
        for receipt in self.receipts:
            body = {
                "kind": receipt.kind,
                "at": receipt.at,
                "details": list(receipt.details),
                "prev_hash": receipt.prev_hash,
            }
            expect = hashlib.sha256(
                (EVENT_SCHEMA + "\n" + canonical(body)).encode("utf-8")).hexdigest()
            if receipt.prev_hash != prev or receipt.event_hash != expect:
                return False
            prev = receipt.event_hash
        return True
