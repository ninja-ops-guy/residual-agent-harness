# Residual Command Station — Gap Closure Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-agent-harness v0.4.0 → v0.5.0
**Repo:** https://github.com/ninja-ops-guy/residual-agent-harness

---

## Overview

Six specs covering the gaps between v0.4.0 and production-ready
ecosystem. Each spec is self-contained and implementable in parallel.

---

## SPEC-GAP-001: Engine Adapter Layer

### Purpose
Enable Residual to orchestrate and verify outputs from LangGraph,
CrewAI, Claude SDK, OpenAI Assistants, and any future agent framework.

### Current State
- `ai_providers/` has provider-level adapters (Ollama, OpenAI, etc.)
- No framework-level adapters exist
- No `ExecutionEngine` protocol
- No capability router

### Architecture

```
┌─────────────────────────────────────────┐
│         Residual Control Plane           │
│  GoalSpec → LoopController → Verifier   │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  ┌──────────┐        ┌──────────┐
  │ Execution │        │ Execution │
  │ Engine A  │        │ Engine B  │
  │(LangGraph)│        │ (CrewAI)  │
  └────┬─────┘        └────┬─────┘
       │                   │
       ▼                   ▼
  ┌──────────┐        ┌──────────┐
  │ LangGraph │        │  CrewAI  │
  │  Runtime  │        │  Runtime │
  └──────────┘        └──────────┘
```

### Requirements

**GAP1-R1.** A new module `residual/engines/` MUST be created. It
MUST contain:
- `protocol.py` — ExecutionEngine protocol, EngineResult, TaskSpec
- `router.py` — CapabilityRouter
- `langgraph_adapter.py` — LangGraph ExecutionEngine
- `crewai_adapter.py` — CrewAI ExecutionEngine
- `sdk_adapter.py` — Claude SDK and OpenAI Assistants adapters
- `probe.py` — Capability validation probe suite

**GAP1-R2.** The `ExecutionEngine` protocol MUST be:

```python
class ExecutionEngine(Protocol):
    name: str
    version: str
    capability_class: str

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult: ...
    def supports(self, capability: str) -> bool: ...
    def health(self) -> EngineHealth: ...
    def normalize(self, raw_output: Any) -> EngineResult: ...
```

**GAP1-R3.** `EngineResult` MUST contain: candidate, tool_calls,
token_usage, wall_clock_ms, engine_trace, raw_metadata. The
engine's internal state MUST NOT be trusted — only observable
outputs enter Residual's verification.

**GAP1-R4.** Engine adapters MUST run in isolated processes.
The adapter is the sandbox boundary. Residual sends TaskSpec and
ContextAssembly in, receives EngineResult out.

**GAP1-R5.** The CapabilityRouter MUST maintain a registry of
engines and capabilities. Capabilities MUST be self-reported at
registration and re-validated by the probe suite. The router MUST
prefer local engines over cloud when capabilities are equal.

**GAP1-R6.** Engine selection MUST be deterministic. Given the
same GoalSpec, engine registry, and probe results, the router MUST
always select the same engine. Non-deterministic routing breaks
receipt verification.

**GAP1-R7.** The receipt MUST record which engine executed the
task. Receipt fields: `engine_name: str`, `engine_version: str`.

**GAP1-R8.** The LangGraph adapter MUST NOT modify the graph's
internal structure. It MUST convert TaskSpec to LangGraph input,
execute via `invoke()` or `run()`, and normalize the output state
to EngineResult.

**GAP1-R9.** The CrewAI adapter MUST disable CrewAI's internal
HITL. HITL is Residual's responsibility. CrewAI's internal HITL
MUST NOT trigger — it would bypass Residual's quarantine.

**GAP1-R10.** SDK adapters (Claude, OpenAI) MUST treat SDK safety
features as advisory. If the SDK refuses a task that Residual's
policies permit, the refusal MUST be recorded but MUST NOT block
execution. If the SDK permits a task that Residual's policies deny,
Residual's denial MUST prevail.

---

## SPEC-GAP-002: Async I/O Integration

### Purpose
Add asynchronous I/O for network operations while preserving the
synchronous verification constraint.

### Current State
- Station server is threaded but not async
- Telemetry fetch is synchronous (blocks verification)
- HITL HTTP is synchronous
- No async periphery exists

### Architecture

```
Synchronous Core (unchanged)          Async Periphery (new)
┌──────────────────────────┐          ┌──────────────────────────┐
│ LoopController           │          │ AsyncTelemetryClient     │
│ Verifier                 │◄─────────│ (background refresh)     │
│ QuarantineStore.evaluate │  cache   │                          │
│ Brake.evaluate           │          │ AsyncObservationSink     │
└──────────────────────────┘          │ (buffered flush)         │
                                      │                          │
                                      │ HITL HTTP server         │
                                      │ (async request handling) │
                                      └──────────────────────────┘
```

### Requirements

**GAP2-R1.** Network I/O MUST be async. Verification MUST remain
synchronous. The boundary: async code fetches data, synchronous
code verifies it.

**GAP2-R2.** The async periphery MUST NOT block the synchronous
core. If a telemetry fetch takes 30 seconds, the LoopController
MUST NOT wait. The verifier receives the most recent cached
telemetry and marks the check UNKNOWN if the cache is stale
beyond `max_telemetry_age_s`.

**GAP2-R3.** Async tasks MUST be cancellable. When a run aborts,
all pending async I/O MUST be cancelled within 5 seconds.

**GAP2-R4.** The observation sink MUST buffer events and flush
asynchronously. Synchronous emission MUST NOT block on I/O. The
buffer MUST be durable up to `buffer_capacity` events.

**GAP2-R5.** A new module `residual/async_io/` MUST be created:
- `telemetry.py` — AsyncTelemetryClient with staleness detection
- `sink.py` — AsyncObservationSink with buffered flush
- `server.py` — Async HTTP server for HITL and station API

**GAP2-R6.** The AsyncTelemetryClient MUST use a background
asyncio task to refresh telemetry at configurable intervals.
The synchronous `get_current_metrics()` MUST return the cached
value or None if stale. It MUST NOT trigger a fetch.

**GAP2-R7.** The AsyncObservationSink MUST accept events via a
synchronous `emit()` method that appends to an in-memory buffer.
A background asyncio task MUST flush the buffer to the downstream
sink at configurable intervals.

---

## SPEC-GAP-003: Prometheus Metrics Export

### Purpose
Export station metrics to Prometheus for operator visibility.

### Current State
- `station/observability.py` exists for internal events
- No Prometheus format export
- No metrics endpoint

### Requirements

**GAP3-R1.** A new module `residual/observability/` MUST be created:
- `metrics.py` — Counter, Gauge, Histogram, MetricsRegistry
- `exporter.py` — Prometheus text format exporter
- `bridge.py` — Observation event → metrics update bridge

**GAP3-R2.** The MetricsRegistry MUST be updated from observation
layer events, not from inline instrumentation. The observation
layer is the single source of truth.

**GAP3-R3.** The following metrics MUST be exported:

| Metric | Type | Labels | Source Event |
|---|---|---|---|
| residual_tokens_total | counter | provider | llm.response |
| residual_tokens_saved | counter | cache_hit | custom:cache_hit |
| residual_brake_trips_total | counter | brake_name, action | state.transition |
| residual_verification_duration_seconds | histogram | check_name | custom:verification_report |
| residual_quarantine_denials_total | counter | policy_name | tool.failed |
| residual_hitl_challenges_pending | gauge | — | checkpoint |
| residual_receipts_issued_total | counter | verdict | checkpoint |
| residual_engine_executions_total | counter | engine_name, outcome | custom:engine_result |

**GAP3-R4.** A `/metrics` HTTP endpoint MUST be exposed by the
station server. It MUST return Prometheus text exposition format.

**GAP3-R5.** A Grafana dashboard JSON MUST be provided with panels
for: token budget consumption, brake trip frequency, verification
latency heatmap, cache hit rate trend, HITL queue depth.

**GAP3-R6.** Structured logs MUST be emitted in JSON format with
fields: timestamp_ns, run_id, goal_id, event_kind, payload_hash.
Logs MUST NOT contain raw model outputs, secrets, or PII.

---

## SPEC-GAP-004: Module Lifecycle Wiring

### Purpose
Connect existing but unwired modules to the run lifecycle.

### Current State
- `residual/trajectory/recorder.py` exists (5.4K) — not wired
- `residual/memory/store.py` exists (5.1K) — not wired
- `residual/tui/dashboard.py` exists (6.1K) — not wired
- No automatic hooks into LoopController lifecycle

### Requirements

**GAP4-R1.** The `LoopController` MUST emit lifecycle events that
modules can subscribe to:
- `run_opened` — after checkpoint emission, before first pass
- `pass_complete` — after verification, before brake evaluation
- `run_closed` — after final checkpoint, before return

**GAP4-R2.** The `TrajectoryRecorder` MUST subscribe to
`run_closed` and automatically record the trajectory. It MUST
extract from RunResult: outcome, total_passes, per-check results,
brake trips. It MUST NOT require manual invocation.

**GAP4-R3.** The `EpistemicMemoryStore` MUST subscribe to
`run_closed` and automatically index the receipt. It MUST extract
from RunResult: goal_spec_hash, outcome, receipt_hash. It MUST
NOT index failed runs (outcome != SUCCESS).

**GAP4-R4.** The `StationTUI` MUST subscribe to all observation
events and update its DashboardState in real time. It MUST run
in a separate thread and MUST NOT block the LoopController.

**GAP4-R5.** A `ModuleLifecycleBus` MUST be created in
`residual/lifecycle.py`. It MUST provide:
- `subscribe(event: str, handler: Callable) -> None`
- `emit(event: str, payload: dict) -> None`
- `unsubscribe(event: str, handler: Callable) -> None`

**GAP4-R6.** The ModuleLifecycleBus MUST be wired into the
LoopController's emit path. Every observation event MUST also
be emitted on the lifecycle bus. Modules subscribe to the bus,
not to the observation layer directly.

---

## SPEC-GAP-005: Module Marketplace

### Purpose
Enable third-party modules to be published, discovered, and
installed.

### Current State
- No module packaging standard
- No entry_points registration
- No validation suite
- No signing mechanism

### Requirements

**GAP5-R1.** A module MUST be publishable as a Python package with
`pyproject.toml` declaring:
```toml
[project.entry-points."residual.modules"]
netops = "residual_modules.netops:NetOpsModule"
secops = "residual_modules.secops:SecOpsModule"
```

**GAP5-R2.** A `residual-module validate` CLI command MUST exist.
It MUST test:
- StationModule protocol conformance
- Quarantine policy signature correctness (returns Optional[str])
- Verifier return type correctness (returns tuple[CheckResult, str])
- Brake protocol implementation (has update() and reset())
- No imports from Residual core internals

**GAP5-R3.** Published modules MUST be signed. The signature MUST
cover the package hash and the module's public key. Residual MUST
verify the signature before loading a module.

**GAP5-R4.** A module registry (PyPI-compatible) MUST be
maintained. The registry MUST reject modules that fail validation
or have invalid signatures.

**GAP5-R5.** Module installation MUST be atomic. A failed install
MUST NOT leave partial state. The registry MUST be frozen during
installation.

**GAP5-R6.** A `residual-module install <package>` CLI command
MUST exist. It MUST: download the package, verify signature, run
validation, install to the module path, and update the registry.

---

## SPEC-GAP-006: Documentation and Onboarding

### Purpose
Enable adoption through clear documentation and working examples.

### Current State
- `docs/` has architecture and research docs
- No quickstart guide
- No module development tutorial
- No reference architectures

### Requirements

**GAP6-R1.** A quickstart guide MUST exist at `docs/quickstart.md`.
It MUST take a user from `pip install residual-command-station`
to a running task in under 10 minutes. It MUST include:
- Installation
- Starting a local Ollama model
- Running a simple task
- Viewing the receipt

**GAP6-R2.** A module development tutorial MUST exist at
`docs/module-tutorial.md`. It MUST cover:
- Implementing StationModule
- Writing quarantine policies
- Writing verifiers
- Writing brakes
- Testing with the validation suite

**GAP6-R3.** Three reference architectures MUST be documented:
- `docs/architecture/ci-cd.md` — CI/CD pipeline integration
- `docs/architecture/incident-response.md` — NetOps remediation
- `docs/architecture/compliance-audit.md` — SecOps evidence collection

**GAP6-R4.** All documentation code examples MUST be executable
and MUST pass in CI. Stale documentation is worse than no
documentation.

**GAP6-R5.** A `docs/faq.md` MUST exist covering common issues:
- "Why is my task stuck in quarantine?"
- "How do I add a new model provider?"
- "How do I debug a brake trip?"
- "How do I escalate to a human?"

---

## Implementation Priority

| Priority | Spec | Effort | Blocks |
|---|---|---|---|
| P0 | SPEC-GAP-001 (Engine Adapters) | 3 weeks | Ecosystem |
| P0 | SPEC-GAP-002 (Async I/O) | 2 weeks | Production |
| P1 | SPEC-GAP-003 (Prometheus) | 1 week | Operations |
| P1 | SPEC-GAP-004 (Module Wiring) | 1 week | Completeness |
| P2 | SPEC-GAP-005 (Marketplace) | 3 weeks | Distribution |
| P2 | SPEC-GAP-006 (Documentation) | 2 weeks | Adoption |
