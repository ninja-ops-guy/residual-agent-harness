"""RUN-R8: observation sinks with buffered async flush + durable terminal flush.

Buffered events flush periodically in the background. ``close()`` performs a
durable terminal flush: every buffered event is written and fsync'd to the
downstream sink before close returns, and no event accepted before close is
dropped silently.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from collections import deque
from pathlib import Path
from typing import Any, Callable


class BufferedObservationSink:
    """Buffered async observation sink with durable terminal flush."""

    def __init__(self, downstream: Callable[[list[dict]], Any] | None = None, *,
                 buffer_capacity: int = 10_000, flush_interval_s: float = 0.25,
                 durable_path: str | Path | None = None):
        self._downstream = downstream
        self._buffer: deque[dict] = deque(maxlen=int(buffer_capacity))
        self._lock = threading.Lock()
        self.flush_interval_s = float(flush_interval_s)
        self._durable_path = Path(durable_path) if durable_path else None
        self._task: asyncio.Task | None = None
        self._closed = False
        self.dropped_events = 0
        self.flushed_events = 0

    def emit(self, kind: str, payload: dict) -> bool:
        with self._lock:
            if self._closed:
                return False
            if self._buffer.maxlen and len(self._buffer) >= self._buffer.maxlen:
                self.dropped_events += 1
            self._buffer.append({"kind": kind, "payload": dict(payload)})
            return True

    def _drain(self) -> list[dict]:
        with self._lock:
            items = list(self._buffer)
            self._buffer.clear()
            return items

    async def _deliver(self, batch: list[dict]) -> None:
        if self._downstream is not None:
            result = self._downstream(batch)
            if asyncio.iscoroutine(result):
                await result
        if self._durable_path is not None:
            # Durable leg: append JSONL and fsync so terminal state survives.
            def _write():
                with open(self._durable_path, "a", encoding="utf-8") as fh:
                    for item in batch:
                        fh.write(json.dumps(item, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            await asyncio.to_thread(_write)

    async def flush(self) -> int:
        batch = self._drain()
        if not batch:
            return 0
        try:
            await self._deliver(batch)
        except Exception:
            with self._lock:
                for item in reversed(batch):
                    if len(self._buffer) < self._buffer.maxlen:
                        self._buffer.appendleft(item)
                    else:
                        self.dropped_events += 1
            raise
        self.flushed_events += len(batch)
        return len(batch)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.flush_interval_s)
            await self.flush()

    def start(self) -> asyncio.Task:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="residual-runtime-sink")
        return self._task

    async def close(self, timeout_s: float = 5.0) -> int:
        """Durable terminal flush: stop background loop, flush everything, fsync."""
        with self._lock:
            self._closed = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=float(timeout_s))
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError as exc:
                raise TimeoutError("observation sink did not stop within terminal budget") from exc
        # Terminal flush is retried until the buffer is empty or budget is gone.
        total = 0
        loop = asyncio.get_running_loop()
        deadline = loop.time() + float(timeout_s)
        while True:
            try:
                total += await self.flush()
                break
            except Exception:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise
                await asyncio.sleep(min(0.05, remaining))
        return total

    # Conformance with AsyncRunCoordinator's cancel contract.
    async def cancel(self, timeout_s: float = 5.0) -> None:
        await self.close(timeout_s=timeout_s)
