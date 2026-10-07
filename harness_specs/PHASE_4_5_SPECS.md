# Residual Command Station — Phase 4-5 Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-command-station v0.4.0 → v1.0.0
**Depends on:** All previous specs

---

## Overview

Phase 4 transforms the integrated system into a production-hardened
platform. Phase 5 builds the ecosystem that makes it a control plane
for other agent frameworks. These specs assume all v0.4.0 integration
gaps are closed.

---

## SPEC-PROD-001: Production Validation Protocol

### Purpose
Define the evidence required to claim production readiness.

### Requirements

**PROD-R1.** A production readiness claim MUST include:
- 30-day continuous execution log with zero unhandled exceptions
- Cache hit rate ≥ 60% on repeated task patterns
- Token savings measurement: ≥ 40% reduction vs uncached execution
- Brake false positive rate ≤ 5% (trips that did not indicate real problems)
- Brake false negative rate ≤ 1% (missed problems that should have tripped)
- HITL escalation rate ≤ 10% of runs (higher indicates brakes are too aggressive)

**PROD-R2.** All measurements MUST be produced by the observation
layer's event log, not by external monitoring. The station's own
telemetry is the authoritative source.

**PROD-R3.** Production validation MUST include at least one
adversarial exercise: a red team attempt to bypass quarantine,
forge receipts, or trigger unsafe execution. The exercise MUST
be observed and receipts MUST be produced for each attempt.

**PROD-R4.** Performance benchmarks MUST include:
- 1000-task DAG completion time (target: < 30 minutes on commodity hardware)
- Peak memory usage (target: < 2 GB for 1000-task DAG)
- Ledger growth rate (target: < 1 MB per 100 tasks)
- Verification latency p99 (target: < 5 seconds per check)

**PROD-R5.** A public validation report MUST be published containing
all measurements, the adversarial exercise results, and known
limitations. The report MUST be cryptographically signed by the
station's identity key.

---

## SPEC-PROD-002: Async I/O Integration

### Purpose
Add asynchronous I/O for network operations while preserving the
synchronous verification constraint.

### Architecture

```
Synchronous Core (unchanged)
├── LoopController
├── Verifier
├── QuarantineStore evaluation
└── Brake evaluation

Async Periphery (new)
├── Telemetry fetch (NetOps)
├── HITL HTTP server
├── Mesh WebSocket transport
├── Observation sink flush
└── Engine adapter I/O
```

### Requirements

**PROD-R6.** Network I/O MUST be async. Verification MUST remain
synchronous. The boundary: async code fetches data, synchronous code
verifies it.

**PROD-R7.** The async periphery MUST NOT block the synchronous core.
If a telemetry fetch takes 30 seconds, the LoopController MUST NOT
wait. The verifier receives the most recent cached telemetry and
marks the check UNKNOWN if the cache is stale beyond
`max_telemetry_age_s`.

**PROD-R8.** Async tasks MUST be cancellable. When a run aborts,
all pending async I/O MUST be cancelled within 5 seconds.

**PROD-R9.** The observation sink MUST buffer events and flush
asynchronously. Synchronous emission MUST NOT block on I/O.
The buffer MUST be durable (survive process crash) up to
`buffer_capacity` events.

---

## SPEC-PROD-003: Observability Export

### Purpose
Export station metrics to external monitoring systems.

### Requirements

**PROD-R10.** A Prometheus exporter MUST be provided. Metrics MUST include:
- `residual_tokens_total` (counter, by provider)
- `residual_tokens_saved` (counter, by cache_hit)
- `residual_brake_trips_total` (counter, by brake_name, by action)
- `residual_verification_duration_seconds` (histogram, by check_name)
- `residual_quarantine_denials_total` (counter, by policy_name)
- `residual_hitl_challenges_pending` (gauge)
- `residual_receipts_issued_total` (counter, by verdict)

**PROD-R11.** Metrics MUST be emitted from observation layer events,
not from inline instrumentation. The observation layer is the
single source of truth.

**PROD-R12.** A Grafana dashboard MUST be provided with panels for:
- Token budget consumption rate
- Brake trip frequency by type
- Verification latency heatmap
- Cache hit rate trend
- HITL queue depth

**PROD-R13.** Structured logs MUST be emitted in JSON format with
fields: timestamp_ns, run_id, goal_id, event_kind, payload_hash.
Logs MUST NOT contain raw model outputs, secrets, or PII.

---

## SPEC-ECO-001: Engine Adapter Protocol

### Purpose
Enable Residual to orchestrate and verify outputs from LangGraph,
CrewAI, Claude SDK, OpenAI Assistants, and any future agent framework.

### The ExecutionEngine Protocol

```python
class ExecutionEngine(Protocol):
    """Adapter between Residual and a downstream agent framework."""

    name: str                    # "langgraph", "crewai", "claude_sdk", ...
    version: str
    capability_class: str        # "orchestration", "generation", "solver"

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult: ...
    def supports(self, capability: str) -> bool: ...
    def health(self) -> EngineHealth: ...
    def normalize(self, raw_output: Any) -> EngineResult: ...


@dataclass(frozen=True)
class EngineResult:
    """Normalized output from any engine. This is what Residual verifies."""

    candidate: Any
    tool_calls: tuple[ToolCall, ...]
    token_usage: TokenUsage
    wall_clock_ms: float
    engine_trace: tuple[EngineTraceEvent, ...]
    raw_metadata: dict[str, Any]


@dataclass(frozen=True)
class EngineTraceEvent:
    """One observable step the engine took."""
    step_number: int
    kind: str                    # "llm_call", "tool_call", "state_change"
    detail: dict[str, Any]
    timestamp_ns: int
```

### Requirements

**ECO-R1.** Every engine adapter MUST implement `ExecutionEngine`.
No engine-specific code MAY appear in Residual's core modules.
All engine interaction goes through the adapter.

**ECO-R2.** Engine adapters MUST run in isolated processes (per
SPEC-CP-004). The adapter is the sandbox boundary. Residual sends
`TaskSpec` and `ContextAssembly` in, receives `EngineResult` out.

**ECO-R3.** The `normalize()` method MUST convert engine-specific
output to `EngineResult`. If normalization fails, the result MUST
be rejected as UNKNOWN. The engine's `supports()` claim for the
relevant capability MUST be flagged for revalidation.

**ECO-R4.** Engine capability claims MUST be validated by a probe
suite before the engine is registered. The probe suite MUST test:
- Can the engine accept a TaskSpec?
- Can the engine produce a normalizable output?
- Does the engine respect token budgets?
- Does the engine crash gracefully?

**ECO-R5.** Engine selection MUST be deterministic. Given the same
GoalSpec, engine registry, and probe results, the router MUST
always select the same engine. Non-deterministic routing breaks
receipt verification.

**ECO-R6.** The receipt MUST record which engine executed the task.
Receipt field: `engine_name: str`, `engine_version: str`. This
enables post-hoc analysis of engine reliability.

---

## SPEC-ECO-002: LangGraph Adapter

### Purpose
Wrap LangGraph as an ExecutionEngine.

### Requirements

**ECO-R7.** The LangGraph adapter MUST accept a LangGraph `StateGraph`
or compiled graph as configuration. The adapter MUST NOT modify
the graph's internal structure.

**ECO-R8.** The adapter MUST convert Residual's `TaskSpec` into
LangGraph's input format. The conversion MUST be lossless — all
GoalSpec constraints, context items, and tool definitions MUST
be preserved.

**ECO-R9.** The adapter MUST convert LangGraph's output (the final
state) into `EngineResult`. The conversion MUST extract: the
candidate answer, any tool calls made, token usage if available,
and the sequence of state transitions as `EngineTraceEvent`s.

**ECO-R10.** If LangGraph's output state contains fields that
cannot be mapped to `EngineResult`, those fields MUST be preserved
in `raw_metadata` for debugging. They MUST NOT be silently dropped.

**ECO-R11.** The adapter MUST enforce Residual's token budget by
passing it to LangGraph's recursion limit or equivalent mechanism.
If LangGraph cannot enforce the budget, the adapter MUST track
token usage and abort the graph if the budget is exceeded.

---

## SPEC-ECO-003: CrewAI Adapter

### Purpose
Wrap CrewAI as an ExecutionEngine.

### Requirements

**ECO-R12.** The CrewAI adapter MUST accept a CrewAI `Crew` or
`Agent` configuration. The adapter MUST NOT modify the crew's
internal agent definitions.

**ECO-R13.** The adapter MUST map Residual's `TaskSpec` to CrewAI's
`Task` format. Agent roles, goals, and backstories MUST be
preserved from the original CrewAI configuration.

**ECO-R14.** The adapter MUST extract from CrewAI's output: the
final result, inter-agent message log (as `EngineTraceEvent`s),
and token usage. CrewAI's internal memory MUST NOT be trusted —
only the observable outputs enter Residual's verification.

**ECO-R15.** CrewAI's human-in-the-loop features MUST be disabled
when running under Residual. HITL is Residual's responsibility.
CrewAI's internal HITL MUST NOT trigger — it would bypass
Residual's quarantine and brake system.

---

## SPEC-ECO-004: Claude SDK / OpenAI Assistants Adapter

### Purpose
Wrap first-party SDKs as ExecutionEngines.

### Requirements

**ECO-R16.** The Claude SDK adapter MUST accept a Claude Agent
or Assistant configuration. The adapter MUST NOT modify the
SDK's internal tool definitions.

**ECO-R17.** The adapter MUST extract from the SDK's output: the
final response, tool calls made, token usage, and conversation
turns (as `EngineTraceEvent`s).

**ECO-R18.** The SDK's built-in safety features MUST be treated as
advisory. Residual's quarantine and verification are authoritative.
If the SDK refuses a task that Residual's policies permit, the
refusal MUST be recorded but MUST NOT block execution. If the SDK
permits a task that Residual's policies deny, Residual's denial
MUST prevail.

**ECO-R19.** The adapter MUST NOT send Residual's observation log,
receipt chain, or quarantine state to the cloud provider. Only
the TaskSpec and ContextAssembly cross the boundary.

---

## SPEC-ECO-005: Module Marketplace

### Purpose
Enable third-party modules to be published, discovered, and installed.

### Requirements

**ECO-R20.** A module MUST be publishable as a Python package with
a `pyproject.toml` declaring:
- `name`: `residual-module-{domain}`
- `entry_points`: `residual.modules` → `{domain} = {module_class}`
- `dependencies`: minimum Residual version

**ECO-R21.** A module MUST pass the validation suite before
publication. The suite MUST test:
- StationModule protocol conformance
- Quarantine policy signature correctness
- Verifier return type correctness
- Brake protocol implementation
- No imports from Residual core modules (only from interfaces)

**ECO-R22.** Published modules MUST be signed. The signature MUST
cover the package hash and the module's public key. Residual MUST
verify the signature before loading a module.

**ECO-R23.** A module registry (PyPI-compatible) MUST be maintained.
The registry MUST reject modules that fail validation or have
invalid signatures.

**ECO-R24.** Module installation MUST be atomic. A failed install
MUST NOT leave partial state. The registry MUST be frozen during
installation (per Conflict Resolution 1).

---

## SPEC-ECO-006: Documentation and Examples

### Purpose
Enable adoption through clear documentation and working examples.

### Requirements

**ECO-R25.** A quickstart guide MUST exist that takes a user from
`pip install residual-command-station` to a running task in under
10 minutes.

**ECO-R26.** A module development tutorial MUST exist that covers:
- Implementing StationModule
- Writing quarantine policies
- Writing verifiers
- Writing brakes
- Testing with the validation suite

**ECO-R27.** Three reference architectures MUST be documented:
- CI/CD pipeline integration (verify builds before merge)
- Incident response automation (NetOps remediation with HITL)
- Compliance audit (SecOps evidence collection with receipts)

**ECO-R28.** All documentation MUST be tested. Code examples MUST
be executable and MUST pass in CI. Stale documentation is worse
than no documentation.

---

## Implementation Priority

| Priority | Spec | Effort | Blocks |
|---|---|---|---|
| P0 | SPEC-ECO-001 (Engine Protocol) | 2 weeks | All adapters |
| P0 | SPEC-PROD-002 (Async I/O) | 2 weeks | Production |
| P1 | SPEC-ECO-002 (LangGraph) | 1 week | Ecosystem |
| P1 | SPEC-PROD-003 (Observability) | 1 week | Operations |
| P2 | SPEC-ECO-003 (CrewAI) | 1 week | Ecosystem |
| P2 | SPEC-ECO-004 (Claude/OpenAI) | 1 week | Ecosystem |
| P2 | SPEC-PROD-001 (Validation) | 4 weeks | Production claim |
| P3 | SPEC-ECO-005 (Marketplace) | 4 weeks | Distribution |
| P3 | SPEC-ECO-006 (Documentation) | 2 weeks | Adoption |
