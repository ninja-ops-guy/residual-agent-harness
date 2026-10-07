from __future__ import annotations
import asyncio,threading
from collections import deque
class AsyncObservationSink:
    def __init__(self,downstream,*,buffer_capacity=10000,flush_interval_s=.25): self._downstream=downstream; self._buffer=deque(maxlen=int(buffer_capacity)); self._lock=threading.Lock(); self.flush_interval_s=float(flush_interval_s); self._task=None; self.dropped_events=0
    def emit(self,kind,payload):
        with self._lock:
            if self._buffer.maxlen and len(self._buffer)>=self._buffer.maxlen: self.dropped_events+=1
            self._buffer.append({"kind":kind,"payload":dict(payload)})
    def _drain(self):
        with self._lock: items=list(self._buffer); self._buffer.clear(); return items
    async def flush(self):
        batch=self._drain()
        if not batch: return
        try: await self._downstream(batch)
        except Exception:
            with self._lock:
                for item in reversed(batch):
                    if len(self._buffer)<self._buffer.maxlen: self._buffer.appendleft(item)
                    else: self.dropped_events+=1
    async def _run(self):
        while True: await asyncio.sleep(self.flush_interval_s); await self.flush()
    def start(self):
        if self._task is None or self._task.done(): self._task=asyncio.create_task(self._run(),name="residual-observation-sink")
        return self._task
    async def cancel(self,timeout_s=5.0):
        if self._task and not self._task.done():
            self._task.cancel()
            try: await asyncio.wait_for(self._task,timeout=float(timeout_s))
            except (asyncio.CancelledError,asyncio.TimeoutError): pass
        await self.flush()
