from __future__ import annotations
import asyncio,threading,time
from typing import Any,Awaitable,Callable
class AsyncTelemetryClient:
    def __init__(self,fetch:Callable[[],Awaitable[Any]],*,refresh_interval_s=5.0,max_telemetry_age_s=30.0):
        self._fetch=fetch; self.refresh_interval_s=float(refresh_interval_s); self.max_telemetry_age_s=float(max_telemetry_age_s); self._value=None; self._updated_at=0.0; self._lock=threading.Lock(); self._task=None
    async def _run(self):
        while True:
            try:
                value=await self._fetch()
                with self._lock: self._value,self._updated_at=value,time.monotonic()
            except asyncio.CancelledError: raise
            except Exception: pass
            await asyncio.sleep(self.refresh_interval_s)
    def start(self):
        if self._task is None or self._task.done(): self._task=asyncio.create_task(self._run(),name="residual-telemetry")
        return self._task
    def get_current_metrics(self):
        with self._lock:
            if self._value is None or time.monotonic()-self._updated_at>self.max_telemetry_age_s: return None
            return self._value
    @property
    def stale(self): return self.get_current_metrics() is None
    async def cancel(self,timeout_s=5.0):
        if not self._task or self._task.done(): return
        self._task.cancel()
        try: await asyncio.wait_for(self._task,timeout=float(timeout_s))
        except (asyncio.CancelledError,asyncio.TimeoutError): pass
