from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable

from ..verifier import CheckResult


class AsyncTelemetryClient:
    """Background telemetry refresh with a strictly synchronous read boundary."""

    def __init__(self, fetch: Callable[[], Awaitable[Any]], *, refresh_interval_s=5.0,
                 max_telemetry_age_s=30.0):
        self._fetch = fetch
        self.refresh_interval_s = float(refresh_interval_s)
        self.max_telemetry_age_s = float(max_telemetry_age_s)
        if self.refresh_interval_s <= 0 or self.max_telemetry_age_s <= 0:
            raise ValueError("telemetry intervals must be positive")
        self._value = None
        self._updated_at = 0.0
        self._lock = threading.Lock()
        self._task = None

    async def _run(self):
        while True:
            try:
                value = await self._fetch()
                with self._lock:
                    self._value, self._updated_at = value, time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Keep the last known value. Staleness, not transport exceptions,
                # determines whether synchronous verification may use it.
                pass
            await asyncio.sleep(self.refresh_interval_s)

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="residual-telemetry")
        return self._task

    def get_current_metrics(self):
        """Return cached telemetry or None when absent/stale; never performs I/O."""
        with self._lock:
            if self._value is None or time.monotonic() - self._updated_at > self.max_telemetry_age_s:
                return None
            return self._value

    def verify_cached(self, evaluator: Callable[[Any, dict], tuple[CheckResult, str]],
                      parameters: dict | None = None) -> tuple[CheckResult, str]:
        """Bridge async collection into the synchronous verifier contract."""
        value = self.get_current_metrics()
        if value is None:
            return CheckResult.UNKNOWN, "telemetry_stale"
        try:
            result, reason = evaluator(value, parameters or {})
        except Exception:
            return CheckResult.UNKNOWN, "telemetry_evaluator_error"
        if not isinstance(result, CheckResult) or result == CheckResult.SKIPPED or not isinstance(reason, str):
            return CheckResult.UNKNOWN, "telemetry_invalid_result"
        return result, reason[:1000]

    @property
    def stale(self):
        return self.get_current_metrics() is None

    async def cancel(self, timeout_s=5.0):
        if not self._task or self._task.done():
            return
        self._task.cancel()
        try:
            await asyncio.wait_for(self._task, timeout=min(float(timeout_s), 5.0))
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
