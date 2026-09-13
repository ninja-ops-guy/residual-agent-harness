"""
observation_layer
=================
Modular observation layer for agentic harnesses.

Layers:
  core      — immutable, hash-chained event spine
  bus       — single emission entry point (sequencer + filter + fanout)
  sinks     — pluggable backends (JSONL, rotating, async, fanout, memory)
  filters   — in-stream drop/redact before persistence
  hooks     — decorators/context managers for tools, LLM calls, agent lifecycle
  query     — replay, chain verification, latency/error analytics

Quick start:
    from observation_layer import ObservationBus, ObservationKind
    from observation_layer.sinks import JsonlFileSink
    from observation_layer.hooks import instrument_tool, llm_call

    bus = ObservationBus(sink=JsonlFileSink("trace.jsonl"), trace_id="run-1")

    @instrument_tool(bus, "web_search")
    def search(q): ...

    with llm_call(bus, "claude-opus-4-1"):
        ...
"""

from .core import Observation, ObservationKind, ObservationSequencer, verify_chain, SCHEMA_VERSION
from .bus import ObservationBus, TraceContext

__all__ = [
    "Observation",
    "ObservationKind",
    "ObservationSequencer",
    "verify_chain",
    "SCHEMA_VERSION",
    "ObservationBus",
    "TraceContext",
]

__version__ = "0.1.0"
