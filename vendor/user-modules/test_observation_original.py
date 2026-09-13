"""Test suite for observation_layer. Run: python -m pytest tests/ -v"""

import os
import tempfile

from observation_layer import (
    ObservationBus, ObservationKind, ObservationSequencer,
    TraceContext, verify_chain,
)
from observation_layer.sinks import (
    FanoutSink, InMemorySink, JsonlFileSink, AsyncQueueSink, NullSink,
)
from observation_layer.filters import (
    allow_kinds, compose, redact_payload, sample_every,
)
from observation_layer.hooks import (
    instrument_tool, llm_call, emit_handoff, emit_agent_lifecycle,
)
from observation_layer.query import (
    replay, latency_summary, error_rate, event_counts, filter_events,
)


class TestCore:
    def test_chain_verifies(self):
        seq = ObservationSequencer("t1")
        events = [
            seq.next(ObservationKind.TOOL_INVOKED, {"tool": "a"}),
            seq.next(ObservationKind.TOOL_COMPLETED, {"tool": "a"}),
            seq.next(ObservationKind.TOOL_FAILED, {"tool": "b"}),
        ]
        assert verify_chain(events)
        assert seq.count == 3
        assert seq.head_hash == events[-1].hash()

    def test_tamper_detected(self):
        seq = ObservationSequencer("t1")
        e1 = seq.next(ObservationKind.TOOL_INVOKED, {"tool": "a"})
        e2 = seq.next(ObservationKind.TOOL_COMPLETED, {"tool": "a"})
        # mutate payload post-hoc
        object.__setattr__(e2, "payload", {"tool": "FORGED"})
        assert not verify_chain([e1, e2])

    def test_reorder_detected(self):
        seq = ObservationSequencer("t1")
        e1 = seq.next(ObservationKind.TOOL_INVOKED, {"n": 1})
        e2 = seq.next(ObservationKind.TOOL_COMPLETED, {"n": 2})
        assert not verify_chain([e2, e1])

    def test_genesis_link(self):
        seq = ObservationSequencer("t1")
        e1 = seq.next(ObservationKind.CHECKPOINT, {})
        assert e1.prev_hash == "GENESIS"


class TestBus:
    def test_emit_increments(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {"tool": "x"})
        bus.emit(ObservationKind.TOOL_COMPLETED, {"tool": "x"})
        assert bus.emitted == 2
        assert len(mem.events) == 2

    def test_filter_drop_counted(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, filter=allow_kinds("tool.invoked"), trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {})
        bus.emit(ObservationKind.TOOL_COMPLETED, {})
        assert bus.emitted == 1
        assert bus.dropped_by_filter == 1

    def test_sink_failure_does_not_raise(self):
        class BadSink(NullSink):
            def emit(self, obs):
                raise IOError("disk full")
        bus = ObservationBus(sink=BadSink(), trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {})  # must not raise
        assert bus.emitted == 0  # not counted as emitted

    def test_trace_context_merges_tags(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, trace_id="t")
        with TraceContext(bus, "t", default_tags={"env": "prod"}, source="agent") as t:
            t.emit(ObservationKind.CHECKPOINT, {})
        assert mem.events[0].tags["env"] == "prod"
        assert mem.events[0].source == "agent"


class TestSinks:
    def test_jsonl_roundtrip(self, tmp_path):
        p = str(tmp_path / "trace.jsonl")
        bus = ObservationBus(sink=JsonlFileSink(p), trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {"tool": "search", "args": "('q',)"})
        bus.emit(ObservationKind.TOOL_COMPLETED, {"tool": "search", "duration_ms": 12.5})
        bus.flush()
        events = replay(p, verify=True)
        assert len(events) == 2
        assert events[0].payload["tool"] == "search"

    def test_fanout_isolation(self):
        class BadSink(NullSink):
            def emit(self, obs):
                raise ValueError("boom")
        mem = InMemorySink()
        fo = FanoutSink([BadSink(), mem])
        bus = ObservationBus(sink=fo, trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {})
        assert len(mem.events) == 1           # good sink still got it
        assert len(fo.errors) == 1            # failure captured

    def test_async_sink_no_block(self):
        mem = InMemorySink()
        async_sink = AsyncQueueSink(mem, maxsize=100)
        bus = ObservationBus(sink=async_sink, trace_id="t")
        for i in range(50):
            bus.emit(ObservationKind.TOOL_INVOKED, {"i": i})
        bus.flush()
        assert len(mem.events) == 50


class TestFilters:
    def test_redact_payload(self):
        filt = redact_payload([r"sk-[a-zA-Z0-9]{4,}"])
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, filter=filt, trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {"args": "key=sk-abcdef1234", "nested": {"tok": "sk-zzzz9999"}})
        ev = mem.events[0]
        assert "sk-abcdef1234" not in str(ev.payload)
        assert "[REDACTED]" in str(ev.payload)
        assert ev.payload["nested"]["tok"] == "[REDACTED]"

    def test_compose_short_circuits(self):
        calls = []
        def counting_filt(obs):
            calls.append(1)
            return obs
        filt = compose(allow_kinds("nope"), counting_filt)
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, filter=filt, trace_id="t")
        bus.emit(ObservationKind.TOOL_INVOKED, {})
        assert calls == []  # second filter never ran

    def test_sample_every(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, filter=sample_every(5), trace_id="t")
        for _ in range(12):
            bus.emit(ObservationKind.TOOL_INVOKED, {})
        assert len(mem.events) == 3  # 0, 5, 10


class TestHooks:
    def test_tool_instrumentation_happy_path(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, trace_id="t")

        @instrument_tool(bus, "add")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5
        kinds = [e.kind.value for e in mem.events]
        assert kinds == ["tool.invoked", "tool.completed"]
        assert mem.events[1].payload["duration_ms"] >= 0

    def test_tool_instrumentation_failure_path(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, trace_id="t")

        @instrument_tool(bus, "explode")
        def explode():
            raise RuntimeError("kaput")

        try:
            explode()
            assert False, "should have raised"
        except RuntimeError:
            pass
        kinds = [e.kind.value for e in mem.events]
        assert kinds == ["tool.invoked", "tool.failed"]
        assert mem.events[1].payload["error"] == "RuntimeError"

    def test_tool_no_bus_is_passthrough(self):
        @instrument_tool(None, "add")
        def add(a, b):
            return a + b
        assert add(1, 1) == 2

    def test_llm_call_context_manager(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, trace_id="t")
        with llm_call(bus, "model-x"):
            pass
        kinds = [e.kind.value for e in mem.events]
        assert kinds == ["llm.request", "llm.response"]

    def test_handoff_and_lifecycle(self):
        mem = InMemorySink()
        bus = ObservationBus(sink=mem, trace_id="t")
        emit_agent_lifecycle(bus, "spawned", "agent-7", role="researcher")
        emit_handoff(bus, "agent-7", "agent-8", summary="done")
        assert mem.events[0].kind == ObservationKind.AGENT_SPAWNED
        assert mem.events[1].kind == ObservationKind.HANDOFF
        assert mem.events[1].tags["to"] == "agent-8"


class TestQuery:
    def _make_events(self, tmp_path):
        p = str(tmp_path / "t.jsonl")
        bus = ObservationBus(sink=JsonlFileSink(p), trace_id="t")

        @instrument_tool(bus, "fast")
        def fast():
            return 1

        @instrument_tool(bus, "slow")
        def slow():
            raise ValueError("nope")

        fast(); fast()
        try:
            slow()
        except ValueError:
            pass
        bus.flush()
        return p

    def test_latency_summary(self, tmp_path):
        p = self._make_events(tmp_path)
        events = replay(p)
        lat = latency_summary(events)
        assert lat["fast"]["n"] == 2
        assert "slow" not in lat  # only completed events have duration

    def test_error_rate(self, tmp_path):
        p = self._make_events(tmp_path)
        events = replay(p)
        er = error_rate(events)
        assert er["slow"]["error_rate"] == 1.0
        assert er["fast"]["error_rate"] == 0.0

    def test_event_counts(self, tmp_path):
        p = self._make_events(tmp_path)
        events = replay(p)
        c = event_counts(events)
        assert c["tool.invoked"] == 3
        assert c["tool.completed"] == 2
        assert c["tool.failed"] == 1

    def test_filter_events_by_tag(self, tmp_path):
        p = self._make_events(tmp_path)
        events = replay(p)
        fast_events = list(filter_events(events, kind="tool.completed", tag_key="tool", tag_value="fast"))
        assert len(fast_events) == 2
