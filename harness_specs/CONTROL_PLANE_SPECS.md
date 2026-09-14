# Residual Command Station — World-Class Control Plane Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-command-station v1.0.0+
**Depends on:** All previous specs

---

## Architectural Position

Residual Command Station is not a competitor to LangGraph, CrewAI,
Claude Agent SDK, or OpenAI Assistants API. It is the **control plane**
that sits above them, providing the safety, verification, and evidence
guarantees that none of them offer.

```
┌─────────────────────────────────────────────────────────┐
│           RESIDUAL COMMAND STATION (Control Plane)       │
│                                                          │
│  GoalSpec → LoopController → Quarantine → Verifier      │
│  → Brakes → Receipts → HITL → Trajectory → Memory       │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │LangGraph│   │ CrewAI  │   │  Claude │   │  OpenAI │
   │ Engine  │   │ Engine  │   │   SDK   │   │Assistants│
   └─────────┘   └─────────┘   └─────────┘   └─────────┘
        │              │              │              │
        └──────────────┴──────────────┴──────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
        ┌──────────┐      ┌──────────┐
        │  Ollama  │      │  Cloud   │
        │  Local   │      │  APIs    │
        └──────────┘      └──────────┘
```

Residual treats every downstream framework as an untrusted execution
engine. It doesn't matter what LangGraph does internally — Residual
verifies what comes out.

---

## SPEC-CP-001: Engine Adapter Protocol

### Purpose
Define how Residual integrates with downstream agent frameworks as
execution engines, without trusting their internal state management.

### Requirements

**CP-R1.** Every engine MUST implement the `ExecutionEngine` protocol:

```python
class ExecutionEngine(Protocol):
    name: str                    # "langgraph", "crewai", "claude_sdk", ...
    version: str

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult: ...
    def supports(self, capability: str) -> bool: ...
    def health(self) -> EngineHealth: ...
```

**CP-R2.** `EngineResult` MUST contain: the candidate output, a
structural trace of what the engine did (tool calls, state transitions),
token usage, wall-clock duration, and any engine-specific metadata.
The engine's internal state MUST NOT be trusted — only its observable
outputs enter Residual's verification pipeline.

**CP-R3.** Residual MUST NOT modify engine internal state. Engines are
black boxes. If LangGraph's state graph has a bug, Residual's
verification catches the bad output. Residual doesn't fix LangGraph.

**CP-R4.** Engine selection MUST be goal-directed. The `GoalSpec`
specifies required capabilities. Residual selects the cheapest engine
that satisfies all capabilities. If no registered engine satisfies
the capabilities, the task MUST NOT execute.

**CP-R5.** Engine failures MUST be contained. If LangGraph crashes,
Residual's LoopController treats it as a failed pass and applies
normal brake logic. Engine crashes MUST NOT crash Residual.

**CP-R6.** Multiple engines MAY be composed for a single task. A task
MAY use LangGraph for orchestration and Claude SDK for a specific
subtask. Residual verifies each engine's output independently.

---

## SPEC-CP-002: Capability-Based Engine Routing

### Purpose
Route tasks to engines based on what they can do, not what they are.

### The Capability Matrix

| Capability | LangGraph | CrewAI | Claude SDK | OpenAI | Ollama |
|---|---|---|---|---|---|
| tool_calling | ✅ | ✅ | ✅ | ✅ | model-dependent |
| multi_agent | ✅ | ✅ | ❌ | ❌ | ❌ |
| streaming | ✅ | ❌ | ✅ | ✅ | ✅ |
| structured_output | ✅ | ❌ | ✅ | ✅ | ❌ |
| planning | ✅ | ❌ | ❌ | ❌ | ❌ |
| code_execution | via tools | via tools | ✅ | ✅ | ❌ |
| local_execution | ❌ | ❌ | ❌ | ❌ | ✅ |
| cost_efficiency | medium | low | low | low | high |

### Requirements

**CP-R7.** The `CapabilityRouter` MUST maintain a registry of engines
and their capabilities. Capabilities MUST be self-reported by engines
at registration time and MUST be re-validated periodically.

**CP-R8.** Capability self-reports MUST be treated as claims, not
facts. The router MUST validate claimed capabilities with a probe
task before trusting them. A engine that claims `tool_calling` but
fails to produce valid tool calls in the probe MUST have that
capability revoked.

**CP-R9.** Task-to-engine assignment MUST be deterministic given the
same GoalSpec and engine registry. Non-deterministic routing breaks
receipt verification — the receipt must record which engine executed.

**CP-R10.** The router MUST prefer local engines (Ollama) over cloud
engines when capabilities are equal. Cost and privacy favor local.
Cloud escalation follows the existing three-attempt pattern.

---

## SPEC-CP-003: Cross-Engine Verification

### Purpose
Verify outputs from any engine using the same mechanical-first
pipeline, regardless of which engine produced them.

### Requirements

**CP-R11.** All engine outputs MUST pass through the same `Verifier`
regardless of source. LangGraph output is verified identically to
CrewAI output. No engine gets a verification shortcut.

**CP-R12.** Engine-specific output formats MUST be normalized to
`EngineResult` before verification. The normalization adapter is
engine-specific. The verification pipeline is engine-agnostic.

**CP-R13.** If an engine produces output that cannot be normalized
to `EngineResult`, the output MUST be rejected as `UNKNOWN`. The
engine's `supports()` claim for the relevant capability MUST be
flagged for re-validation.

**CP-R14.** Cross-engine consistency checks MAY be implemented as a
structural verifier. If two engines produce different outputs for
the same task, a consistency check verifier MAY compare them and
flag divergence. This is optional and expensive — use sparingly.

---

## SPEC-CP-004: Engine Sandbox Isolation

### Purpose
Ensure that a compromised or buggy engine cannot corrupt Residual's
state or other engines.

### Requirements

**CP-R15.** Each engine MUST run in an isolated process. Engines MUST
NOT share memory space with Residual or with each other.

**CP-R16.** Engine processes MUST be resource-constrained: CPU, memory,
file descriptors, network access. Constraints MUST be enforced by the
OS (cgroups, containers, or equivalent), not by the engine.

**CP-R17.** Engines MUST NOT have write access to Residual's observation
log, quarantine store, or receipt chain. Engines produce outputs.
Residual owns state.

**CP-R18.** Engine network access MUST be proxied through Residual's
disclosure lattice. An engine that tries to make an undeclared network
call MUST be blocked by the sandbox, not by Residual's quarantine
(which operates at a higher level).

**CP-R19.** Engine crash recovery MUST be automatic. If an engine
process dies, Residual detects it via process monitoring, marks the
task as failed, and applies normal brake logic. No human intervention
required for engine crashes.

---

## SPEC-CP-005: The Residual Advantage Matrix

### What Residual Provides That No Engine Does

| Capability | LangGraph | CrewAI | Claude SDK | OpenAI | Residual |
|---|---|---|---|---|---|
| Cryptographic receipts | ❌ | ❌ | ❌ | ❌ | ✅ |
| Hash-chained audit trail | ❌ | ❌ | ❌ | ❌ | ✅ |
| Quarantine before execution | ❌ | ❌ | ❌ | ❌ | ✅ |
| Mechanical-first verification | ❌ | ❌ | ❌ | ❌ | ✅ |
| Frozen GoalSpec | ❌ | ❌ | ❌ | ❌ | ✅ |
| Independent brake system | ❌ | ❌ | ❌ | ❌ | ✅ |
| Disclosure lattice | ❌ | ❌ | ❌ | ❌ | ✅ |
| Receipt-bound caching | ❌ | ❌ | ❌ | ❌ | ✅ |
| HITL with crypto signatures | ❌ | ❌ | partial | partial | ✅ |
| Trajectory regression | ❌ | ❌ | ❌ | ❌ | ✅ |
| Cross-session memory | ❌ | ❌ | ❌ | partial | ✅ |
| Multi-engine routing | ❌ | ❌ | ❌ | ❌ | ✅ |
| Local model support | ❌ | ❌ | ❌ | ❌ | ✅ |
| Provider failover | ❌ | ❌ | ❌ | ❌ | ✅ |

### What Engines Provide That Residual Doesn't (Yet)

| Capability | Status |
|---|---|
| Async execution | Spec'd, not implemented |
| Streaming | Spec'd, not implemented |
| Multimodal (vision, audio) | Not spec'd |
| Production-grade error handling | Partial |
| Ecosystem / integrations | None |
| Documentation | Specs only |
| Community | One user |

---

## SPEC-CP-006: Integration Roadmap

### Phase 1: Engine Adapters (Weeks 1-2)
- `LangGraphAdapter` — wraps LangGraph as an ExecutionEngine
- `OllamaAdapter` — already exists, formalize as ExecutionEngine
- `ClaudeSDKAdapter` — wraps Claude Agent SDK
- `CapabilityRouter` — implements CP-R7 through CP-R10

### Phase 2: Sandbox (Weeks 3-4)
- Process isolation via `multiprocessing` or containers
- Resource constraints via cgroups
- Network proxy for disclosure lattice enforcement
- Crash detection and recovery

### Phase 3: Verification Normalization (Weeks 5-6)
- `EngineResult` normalizers for each adapter
- Cross-engine consistency checker (optional)
- Engine capability probe suite

### Phase 4: Production Hardening (Weeks 7-8)
- Error handling and retry logic
- Observability integration (Prometheus, Grafana)
- Documentation and examples
- Performance benchmarking

---

## The Honest Position

Residual is not a framework. It is a **safety kernel** for agent
systems. The frameworks are the applications. The kernel doesn't
compete with applications — it makes them trustworthy.

The market doesn't need another agent framework. It needs a way to
trust the agent frameworks it already uses. That's Residual.
