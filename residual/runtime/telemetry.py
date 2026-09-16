"""RUN-R6: freshness-aware telemetry reads — UNKNOWN when stale.

Wraps the async telemetry boundary (``residual.async_io.telemetry``) with a
synchronous, clock-injectable freshness guard. A read NEVER reuses a stale
value as current truth: past ``max_age_s`` the reading's status is
``UNKNOWN`` and the payload is suppressed.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class TelemetryStatus(str, Enum):
    CURRENT = "current"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TelemetryReading:
    status: TelemetryStatus
    value: Any
    age_s: float
    reason: str

    @property
    def fresh(self) -> bool:
        return self.status == TelemetryStatus.CURRENT


class FreshnessGuard:
    """Staleness-guarded telemetry store with explicit freshness exposure."""

    def __init__(self, *, max_age_s: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        if max_age_s <= 0:
            raise ValueError("max_age_s must be positive")
        self.max_age_s = float(max_age_s)
        self._clock = clock
        self._value: Any = None
        self._updated_at: float | None = None
        self._lock = threading.Lock()

    def update(self, value: Any) -> None:
        with self._lock:
            self._value = value
            self._updated_at = self._clock()

    def read(self) -> TelemetryReading:
        """Return the reading with freshness; UNKNOWN when absent or stale."""
        with self._lock:
            value, updated_at = self._value, self._updated_at
        if updated_at is None:
            return TelemetryReading(TelemetryStatus.UNKNOWN, None, float("inf"),
                                    "telemetry_absent")
        age = self._clock() - updated_at
        if age > self.max_age_s:
            return TelemetryReading(TelemetryStatus.UNKNOWN, None, age, "telemetry_stale")
        return TelemetryReading(TelemetryStatus.CURRENT, value, age, "ok")

    @property
    def stale(self) -> bool:
        return not self.read().fresh
