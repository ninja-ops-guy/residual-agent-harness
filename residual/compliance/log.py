"""Hash-chained observation log shared by the compliance framework.

Implements ENT2-R1 through ENT2-R6: every observation is append-only,
carries compliance tags, a category for retention (ENT2-R2), a region for
residency (ENT2-R4), and a tamper-evident chain hash so receipts and
observations remain verifiable legal records (ENT2-R5).
"""
from __future__ import annotations

import hashlib
import itertools
import re
from dataclasses import dataclass, field, replace

from ..core import ContractError, canonical, digest

_TAG = re.compile(r"^[A-Z][A-Z0-9-]*-[A-Za-z0-9.]+$")
CATEGORIES = ("sox", "operational", "debug")
KINDS = (
    "receipt", "observation", "hitl_decision", "hitl_escalation",
    "contract_violation", "sensitive_access", "module_install",
    "task_execution", "retention", "legal_hold", "residency",
    "erasure", "report", "siem", "transfer",
)


def validate_tag(tag: str) -> str:
    """Validate one ``FRAMEWORK-Control`` tag. Implements ENT2-R1."""
    if not isinstance(tag, str) or not _TAG.fullmatch(tag):
        raise ContractError(f"invalid compliance tag: {tag!r}")
    return tag


@dataclass(frozen=True)
class ObservationEvent:
    """One immutable, hash-chained observation. Implements ENT2-R1."""
    id: int
    kind: str
    timestamp: float
    actor: str
    task_id: str
    category: str
    region: str
    payload: dict = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    chain_hash: str = ""

    def __post_init__(self):
        if type(self.id) is not int or self.id < 1:
            raise ContractError("event id must be a positive integer")
        if self.kind not in KINDS:
            raise ContractError(f"unknown observation kind: {self.kind!r}")
        if self.category not in CATEGORIES:
            raise ContractError(f"unknown retention category: {self.category!r}")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ContractError("event timestamp must be a nonnegative number")
        for value in (self.actor, self.task_id, self.region):
            if not isinstance(value, str) or not value.strip():
                raise ContractError("actor, task_id and region are required")
        for tag in self.tags:
            validate_tag(tag)
        canonical(self.payload)

    def body(self) -> dict:
        return {"id": self.id, "kind": self.kind, "timestamp": self.timestamp,
                "actor": self.actor, "task_id": self.task_id,
                "category": self.category, "region": self.region,
                "payload": self.payload, "tags": sorted(self.tags)}


class ObservationLog:
    """Append-only observation log with receipts. Implements ENT2-R1.

    Each event is receipted: ``chain_hash = sha256(prev_hash | body)``,
    making deletion or mutation tamper-evident.
    """

    def __init__(self):
        self._events: list[ObservationEvent] = []
        self._counter = itertools.count(1)
        self._archived: list[ObservationEvent] = []

    def _seal(self, event: ObservationEvent) -> ObservationEvent:
        prev = self._events[-1].chain_hash if self._events else "0" * 64
        chain = hashlib.sha256((prev + "\n" + canonical(event.body())).encode("utf-8")).hexdigest()
        return replace(event, chain_hash=chain)

    def append(self, kind: str, timestamp: float, actor: str, task_id: str,
               *, category: str = "operational", region: str = "local",
               payload: dict | None = None, tags: tuple[str, ...] = ()) -> ObservationEvent:
        """Append and receipt an observation. Implements ENT2-R1."""
        event = ObservationEvent(next(self._counter), kind, float(timestamp), actor,
                                 task_id, category, region, dict(payload or {}), tuple(tags))
        sealed = self._seal(event)
        self._events.append(sealed)
        return sealed

    @property
    def events(self) -> tuple[ObservationEvent, ...]:
        return tuple(self._events)

    def query(self, *, kinds=None, actor=None, task_id=None, region=None,
              start=None, end=None) -> list[ObservationEvent]:
        """Filter observations for reports and scoped holds. Implements ENT2-R6."""
        out = []
        for e in self._events:
            if kinds and e.kind not in kinds:
                continue
            if actor is not None and e.actor != actor:
                continue
            if task_id is not None and e.task_id != task_id:
                continue
            if region is not None and e.region != region:
                continue
            if start is not None and e.timestamp < start:
                continue
            if end is not None and e.timestamp > end:
                continue
            out.append(e)
        return out

    # -- retention support (ENT2-R2) -------------------------------------
    def remove(self, ids: set[int]) -> None:
        """Physically drop events (only after archive, no active hold)."""
        self._events = [e for e in self._events if e.id not in ids]

    def mark_archived(self, events: list[ObservationEvent]) -> None:
        self._archived.extend(events)

    @property
    def archived(self) -> tuple[ObservationEvent, ...]:
        return tuple(self._archived)

    def pseudonymize(self, event_ids: set[int], replacement: str) -> int:
        """Replace actor identity in place, preserving receipts. ENT2-R5."""
        count = 0
        prev = "0" * 64
        sealed_events = []
        for e in self._events:
            if e.id in event_ids and e.actor != replacement:
                payload = dict(e.payload)
                payload["pseudonymized"] = True
                e = replace(e, actor=replacement, payload=payload)
                count += 1
            chain = hashlib.sha256((prev + "\n" + canonical(e.body())).encode("utf-8")).hexdigest()
            e = replace(e, chain_hash=chain)
            sealed_events.append(e)
            prev = chain
        self._events = sealed_events
        return count

    def verify_chain(self) -> bool:
        """Recompute the hash chain; any tamper returns False. ENT2-R1."""
        prev = "0" * 64
        for e in self._events:
            expected = hashlib.sha256((prev + "\n" + canonical(e.body())).encode("utf-8")).hexdigest()
            if e.chain_hash != expected:
                return False
            prev = e.chain_hash
        return True
