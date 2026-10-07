# observation_layer

Modular observation layer for agentic harnesses. Append-only, hash-chained,
filterable, multi-sink telemetry for multi-agent systems.

## Architecture

```
instrumented code
      │
      ▼
  hooks (decorators / context managers)
      │
      ▼
  bus  ── sequencer (hash chain per trace)
      │      │
      │      ▼
      │   filters (drop / redact / sample)
      │      │
      ▼      ▼
   sinks (fanout: JSONL, rotating, async, memory, null)
      │
      ▼
  query (replay, verify_chain, latency, error rates)
```

## Design constraints

1. **Evidence integrity.** Every event is immutable and chained via SHA-256
   (`prev_hash`). `verify_chain()` detects any post-hoc edit. Chain roots can
   be anchored externally at checkpoint time.
2. **Fail-visible, never fail-silent.** Async sink drops are counted.
   Downstream sink errors are captured per-sink in `FanoutSink.errors`.
   Emission never raises into agent code.
3. **Redaction precedes persistence.** Filters run before any sink sees an
   event. Once it hits disk it's too late.
4. **Closed vocabularies.** `ObservationKind` is an enum. Schema version is
   stamped on every event. Extensions go through migration, not ad-hoc strings.
5. **Zero-cost when off.** All hooks accept `bus=None` and become pass-throughs.

## Usage

```python
from observation_layer import ObservationBus, ObservationKind, TraceContext
from observation_layer.sinks import JsonlFileSink, FanoutSink, InMemorySink
from observation_layer.filters import redact_payload, allow_kinds, compose
from observation_layer.hooks import instrument_tool, llm_call, emit_handoff

redact = redact_payload([r"sk-[a-zA-Z0-9]{20,}", r"Bearer\s+\S+"])
filt = compose(allow_kinds("tool.invoked", "tool.completed", "tool.failed"), redact)

mem = InMemorySink()
bus = ObservationBus(
    sink=FanoutSink([JsonlFileSink("trace.jsonl"), mem]),
    filter=filt,
    trace_id="run-42",
)

@instrument_tool(bus, "web_search", agent_id="researcher-1")
def search(q: str): ...

with TraceContext(bus, "run-42", default_tags={"env": "prod"}, source="agent.main") as t:
    with llm_call(bus, "claude-opus-4-1", agent_id="researcher-1"):
        ...
    emit_handoff(bus, "researcher-1", "writer-1", summary="facts gathered")
```

## Query

```python
from observation_layer.query import replay, latency_summary, error_rate, event_counts

events = replay("trace.jsonl", verify=True)   # raises if chain broken
print(event_counts(events))
print(latency_summary(events))
print(error_rate(events))
```

## Module map

| Module | Responsibility |
|---|---|
| `core` | `Observation`, `ObservationKind`, `ObservationSequencer`, `verify_chain` |
| `bus` | `ObservationBus` (single entry point), `TraceContext` (scoped helper) |
| `sinks` | `JsonlFileSink`, `RotatingJsonlSink`, `AsyncQueueSink`, `FanoutSink`, `InMemorySink`, `NullSink` |
| `filters` | `compose`, `allow_kinds`, `deny_kinds`, `require_tags`, `sample_every`, `redact_payload` |
| `hooks` | `instrument_tool`, `llm_call`, `emit_agent_lifecycle`, `emit_state_transition`, `emit_handoff` |
| `query` | `load_jsonl`, `replay`, `filter_events`, `latency_summary`, `error_rate`, `event_counts`, `trace_timeline` |

## Extension points

- **New sink:** subclass `Sink`, implement `emit`/`flush`.
- **New filter:** any `Observation -> Optional[Observation]`; compose with `compose()`.
- **New hook:** follow the pattern in `hooks.py` — never raise into wrapped code,
  always emit both the start and terminal event (completed/failed).
- **Schema migration:** bump `SCHEMA_VERSION`, add a migration path in `query.load_jsonl`.
