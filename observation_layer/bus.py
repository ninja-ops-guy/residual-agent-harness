"""Filter before sealing; isolate diagnostics failures without exposing exception bodies."""
from __future__ import annotations
import threading
from .core import Observation, ObservationSequencer
from .sinks import NullSink


class ObservationBus:
    def __init__(self, sink=None, filter=None, trace_id='default'):
        self.sequencer = ObservationSequencer(trace_id)
        self.sink = sink if sink is not None else NullSink()
        self.filter = filter
        self._lock = threading.RLock()
        self.emitted = self.dropped_by_filter = self.errors = 0
        self.last_error = None

    def emit(self, kind, payload, *, tags=None, source='unknown'):
        with self._lock:
            try:
                obs = self.sequencer.draft(kind, payload, tags=tags, source=source)
                if self.filter is not None:
                    obs = self.filter(obs)
                    if obs is None:
                        self.dropped_by_filter += 1
                        return None
                if not isinstance(obs, Observation): raise ValueError('Invalid filter output')
                obs = self.sequencer.commit(obs)
                self.sink.emit(obs)
                self.emitted += 1
                return obs
            except Exception:
                # A failed write can leave a visible chain gap. Never silently renumber it.
                self.errors += 1; self.last_error = 'observation_delivery_failed'
                return None

    def flush(self):
        try: self.sink.flush()
        except Exception:
            self.errors += 1; self.last_error = 'observation_flush_failed'

    def close(self):
        try: self.sink.close()
        except Exception:
            self.errors += 1; self.last_error = 'observation_close_failed'


class TraceContext:
    def __init__(self, bus, trace_id, default_tags=None, source='trace'):
        if bus.sequencer.trace_id != trace_id:
            raise ValueError('A trace context must match its bus; create a bus for another trace')
        self.bus, self.trace_id = bus, trace_id
        self.default_tags, self.source = default_tags or {}, source
    def emit(self, kind, payload, *, tags=None, source=None):
        return self.bus.emit(kind, payload, tags={**self.default_tags, **(tags or {})}, source=source or self.source)
    def __enter__(self): return self
    def __exit__(self, *exc):
        self.bus.flush()
        return False
