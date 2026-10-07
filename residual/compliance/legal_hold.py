"""Legal hold scoped by user, task, and/or time range.

Implements ENT2-R3: while a hold is active for a scope, matching events
MUST NOT be deleted or archived. Activation and release are themselves
observed and receipted in the observation log.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from ..core import ContractError
from .log import ObservationEvent, ObservationLog


@dataclass(frozen=True)
class HoldScope:
    """A user/task/time-range scope. Implements ENT2-R3."""
    user: str | None = None
    task_id: str | None = None
    start: float | None = None
    end: float | None = None

    def __post_init__(self):
        if self.user is None and self.task_id is None and self.start is None and self.end is None:
            raise ContractError("hold scope must constrain user, task, or time")
        for value in (self.user, self.task_id):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ContractError("hold scope user/task must be nonempty strings")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ContractError("hold scope time range is inverted")

    def matches(self, event: ObservationEvent) -> bool:
        if self.user is not None and event.actor != self.user:
            return False
        if self.task_id is not None and event.task_id != self.task_id:
            return False
        if self.start is not None and event.timestamp < self.start:
            return False
        if self.end is not None and event.timestamp > self.end:
            return False
        return True


@dataclass(frozen=True)
class LegalHold:
    """An active or released hold with its receipts. Implements ENT2-R3."""
    id: int
    scope: HoldScope
    reason: str
    active: bool = True
    activate_receipt: str = ""
    release_receipt: str = ""


class LegalHoldManager:
    """Activates/releases holds and blocks retention. Implements ENT2-R3."""

    def __init__(self, log: ObservationLog):
        self.log = log
        self._holds: list[LegalHold] = []
        self._counter = itertools.count(1)

    def activate(self, scope: HoldScope, reason: str, timestamp: float,
                 actor: str = "compliance") -> LegalHold:
        """Activate a hold; the activation is observed and receipted."""
        if not isinstance(reason, str) or not reason.strip():
            raise ContractError("legal hold requires a reason")
        event = self.log.append("legal_hold", timestamp, actor, "system",
                                category="sox", region="local",
                                payload={"action": "activate", "reason": reason,
                                         "scope": {"user": scope.user, "task_id": scope.task_id,
                                                   "start": scope.start, "end": scope.end}},
                                tags=("SOX-CC7.2",))
        hold = LegalHold(next(self._counter), scope, reason, True, event.chain_hash)
        self._holds.append(hold)
        return hold

    def release(self, hold_id: int, timestamp: float, actor: str = "compliance") -> LegalHold:
        """Release a hold; the release is observed and receipted."""
        for i, hold in enumerate(self._holds):
            if hold.id == hold_id:
                if not hold.active:
                    raise ContractError("hold already released")
                event = self.log.append("legal_hold", timestamp, actor, "system",
                                        category="sox", region="local",
                                        payload={"action": "release", "hold_id": hold_id,
                                                 "reason": hold.reason},
                                        tags=("SOX-CC7.2",))
                released = LegalHold(hold.id, hold.scope, hold.reason, False,
                                     hold.activate_receipt, event.chain_hash)
                self._holds[i] = released
                return released
        raise ContractError("unknown hold id")

    def blocked(self, event: ObservationEvent) -> bool:
        """True when any active hold scope matches the event."""
        return any(h.active and h.scope.matches(event) for h in self._holds)

    @property
    def holds(self) -> tuple[LegalHold, ...]:
        return tuple(self._holds)
