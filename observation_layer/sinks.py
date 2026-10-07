"""
observation_layer.sinks
=======================
Pluggable backends. The layer emits to one or more sinks; sinks are
swappable without touching instrumentation code. Failures in one sink
must not drop events destined for others (fan-out isolation).
"""

from __future__ import annotations

import json
import queue
import threading
from abc import ABC, abstractmethod
from typing import Iterable, Optional

from .core import Observation


class Sink(ABC):
    @abstractmethod
    def emit(self, obs: Observation) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...

    def close(self) -> None:
        self.flush()


class NullSink(Sink):
    def emit(self, obs): pass
    def flush(self): pass


class JsonlFileSink(Sink):
    """
    Append-only JSONL. Durable, greppable, replayable. Rotation is the
    caller's concern (or use RotatingJsonlSink below).
    """

    def __init__(self, path: str):
        self._f = open(path, "a", buffering=1)  # line-buffered

    def emit(self, obs: Observation) -> None:
        self._f.write(json.dumps(obs.to_dict(), ensure_ascii=False, allow_nan=False) + "\n")

    def flush(self) -> None:
        self._f.flush()

    def close(self) -> None:
        self._f.close()


class RotatingJsonlSink(Sink):
    """Rotate by size. Keeps the active file bounded for long agent runs."""

    def __init__(self, directory: str, prefix: str = "obs", max_bytes: int = 50_000_000):
        self.directory = directory
        self.prefix = prefix
        self.max_bytes = max_bytes
        self._idx = 0
        self._open_next()

    def _path(self) -> str:
        import os
        return os.path.join(self.directory, f"{self.prefix}-{self._idx:05d}.jsonl")

    def _open_next(self) -> None:
        self._f = open(self._path(), "a", buffering=1)

    def emit(self, obs: Observation) -> None:
        line = json.dumps(obs.to_dict(), ensure_ascii=False, allow_nan=False) + "\n"
        self._f.write(line)
        self._f.flush()
        if self._f.tell() >= self.max_bytes:
            self._f.close()
            self._idx += 1
            self._open_next()

    def flush(self) -> None:
        self._f.flush()

    def close(self) -> None:
        self._f.close()


class InMemorySink(Sink):
    """For tests and short-lived debugging. Not durable."""

    def __init__(self):
        self.events: list[Observation] = []

    def emit(self, obs: Observation) -> None:
        self.events.append(obs)

    def flush(self) -> None:
        pass


class AsyncQueueSink(Sink):
    """
    Decouples emit() from I/O. Producer never blocks on slow backends.
    Drop policy: on full queue, newest is dropped and a counter is incremented
    (fail-visible, not fail-silent).
    """

    def __init__(self, downstream: Sink, maxsize: int = 10_000):
        self.downstream = downstream
        self.q: queue.Queue = queue.Queue(maxsize=maxsize)
        self.dropped = 0
        self._closed = False
        self._lifecycle_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        while not self._stop.is_set() or not self.q.empty():
            try:
                obs = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.downstream.emit(obs)
            except Exception:
                self.dropped += 1  # downstream failure must not kill the worker
            finally:
                self.q.task_done()

    def emit(self, obs: Observation) -> None:
        with self._lifecycle_lock:
            if self._closed: raise RuntimeError("Observation queue is closed")
            try: self.q.put_nowait(obs)
            except queue.Full: self.dropped += 1

    def flush(self) -> None:
        self.q.join()
        self.downstream.flush()

    def close(self) -> None:
        with self._lifecycle_lock: self._closed = True
        self.flush()
        self._stop.set()
        self._thread.join(timeout=2)
        self.downstream.close()


class FanoutSink(Sink):
    """Multicast to many sinks. Per-sink exceptions are captured, not raised."""

    def __init__(self, sinks: Iterable[Sink]):
        self.sinks = list(sinks)
        self.errors: list[tuple[str, Exception]] = []

    def emit(self, obs: Observation) -> None:
        for s in self.sinks:
            try:
                s.emit(obs)
            except Exception as e:
                self.errors.append((type(s).__name__, "sink_failed"))
                self.errors[:] = self.errors[-100:]

    def flush(self) -> None:
        for s in self.sinks:
            try:
                s.flush()
            except Exception as e:
                self.errors.append((type(s).__name__, "sink_failed"))
                self.errors[:] = self.errors[-100:]

    def close(self) -> None:
        for sink in self.sinks:
            try: sink.close()
            except Exception: self.errors.append((type(sink).__name__, "sink_close_failed"))
