"""Injectable clocks for deterministic HA/DR simulation.

Implements ENT4-R4 by making Recovery Time Objective (RTO) measurable
with an injected clock instead of wall time, so failover timing claims
are testable offline.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from ..core import ContractError


class Clock(Protocol):
    """Clock protocol. Implements ENT4-R4 (injectable time source)."""

    def now(self) -> float:
        """Return the current time in seconds."""
        ...


class SystemClock:
    """Wall-clock implementation. Implements ENT4-R4."""

    def now(self) -> float:
        return time.monotonic()


@dataclass
class ManualClock:
    """Deterministic manually advanced clock.

    Implements ENT4-R4: tests advance time explicitly to measure RTO
    and replication lag (ENT4-R2's 30 second budget) without sleeping.
    """

    current: float = 0.0

    def now(self) -> float:
        return self.current

    def advance(self, seconds: float) -> float:
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise ContractError("clock advance must be a nonnegative number")
        self.current = float(self.current) + float(seconds)
        return self.current
