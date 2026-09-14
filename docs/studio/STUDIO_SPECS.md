# Residual Studio — Multi-Swarm Engineering Platform Specifications

**Version:** 1.0.1  
**Date:** 2026-09-13  
**Normative language:** RFC 2119  
**Target:** residual-agent-harness v1.0.0+  
**Codename:** The Factory

## 0. Product Thesis

Residual Studio is a self-hosted, evidence-driven multi-swarm engineering platform. It is designed to turn heterogeneous AI compute into bounded, parallel engineering capacity.

The claim is not that LLMs are deterministic. The claim is:

> **Residual deterministically constrains, verifies, schedules, and integrates nondeterministic workers.**

Agent output is untrusted. Agent output plus a satisfied frozen contract and verified receipt is an integration-eligible artifact.

---

# SPEC-STUDIO-001: Five-Layer Architecture

## Purpose

Define the platform stack from browser IDE to heterogeneous compute cluster.

```text
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: Residual Cluster                                   │
│ Multi-device compute mesh, LAN discovery, GPU pooling,      │
│ remote nodes, and permitted cloud bursting.                 │
├─────────────────────────────────────────────────────────────┤
│ LAYER 4: Swarm Runtime                                      │
│ Coordinators, workers, verifiers, critics, integrators.     │
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: Residual Orchestrator                              │
│ Requirement DAG, partitioning, routing, scheduling,         │
│ resource estimation, replanning.                            │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: Residual Station                                   │
│ Existing verification and safety kernel: GoalSpec, brakes,  │
│ quarantine, receipts, HITL, verifier lifecycle.             │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: Residual Studio                                    │
│ Browser IDE, swarm panel, evidence view, graph, telemetry.  │
└─────────────────────────────────────────────────────────────┘
```

### Requirements

**STUDIO-R1.** Each layer MUST be independently deployable. Layer 1 MUST be usable against a remote Layer 3. Layer 3 MUST be usable without Layer 1 through API/CLI surfaces.

**STUDIO-R2.** Layers MUST communicate through versioned typed protocols. A layer MUST NOT import another layer's private implementation modules.

**STUDIO-R3.** Layer 2 is the authoritative verification and safety kernel. Any artifact promoted across trust boundaries MUST pass the configured Station verification path. No higher layer MAY bypass required Station policy.

**STUDIO-R4.** The platform MUST support three per-task operating modes: Pair, Team, and Factory. Pair is one human plus one agent; Team is a bounded small swarm; Factory is multi-swarm execution. Mode selection MUST be task-scoped rather than session-scoped.

---

# SPEC-STUDIO-002: Requirement Compiler

## Purpose

Transform user intent into a structured requirement graph suitable for deterministic scheduling.

```text
User Intent
    ↓
Intent Parser
    ↓
Structured Requirement Draft
    ↓
Canonicalizer + Validator
    ↓
Dependency Graph Builder
    ↓
Work Partitioner
    ↓
Human Plan Approval
```

### Requirements

**STUDIO-R5.** The compiler MUST produce a `RequirementGraph` containing requirements, proposed swarms, estimated parallelism, serial estimate, and risk assessment. Every requirement MUST have a stable ID, description, acceptance criteria, dependencies, and provenance back to the originating intent span.

**STUDIO-R6.** The compiler MUST produce canonical, schema-valid output. JSON schema constraints alone MUST NOT be described as making an LLM deterministic. Reproducibility MUST be strengthened through pinned model/provider revision where available, fixed decoding settings where supported, canonical ordering, stable IDs, and deterministic graph construction. If model output still differs, the resulting graph hash MUST differ and be visible to the user.

**STUDIO-R7.** The Plan Presenter MUST display requirement count, task count, dependency groups, proposed swarm composition, estimated parallelizable work, risk flags, and predicted critical path. The human MUST be able to approve, modify, or reject the plan before Factory Mode execution.

**STUDIO-R8.** Material ambiguity MUST block plan approval until resolved. The compiler MUST emit explicit clarification items rather than silently guessing. Pair/Team mode MAY permit best-effort assumptions only when the user has enabled an assumption policy, and every assumption MUST be recorded in the plan receipt.

---

# SPEC-STUDIO-003: Swarm Runtime

## Purpose

Execute bounded worker contracts in parallel while preventing uncontrolled shared-state mutation.

```text
Swarm
├── coordinator
├── workers (1-N)
├── verifier
├── critic
└── integrator
```

### Worker contract

```python
@dataclass(frozen=True)
class WorkerContract:
    task_id: str
    inputs: tuple[str, ...]
    allowed_outputs: tuple[str, ...]
    requirements: tuple[str, ...]
    acceptance: tuple[str, ...]
    dependencies: tuple[str, ...]
    forbidden: tuple[str, ...]
    engine_hint: str | None
    token_budget: int
    wall_clock_budget_s: float
```

### Requirements

**STUDIO-R9.** Every worker MUST receive a frozen `WorkerContract` before execution. Workers MUST NOT mutate their own contract.

**STUDIO-R10.** The runtime MUST enforce contract boundaries at the execution boundary, not only by prompt instruction. Out-of-scope reads, writes, tool use, or forbidden path access MUST terminate the worker and emit a `contract_violation` observation.

**STUDIO-R11.** Every completed worker attempt MUST produce a `WorkerReceipt` binding at minimum: task ID, attempt ID, engine identity/version, node identity, input commit, output artifact hashes, requirement verdicts, verification results, parent receipt hashes, start/end timestamps, resource usage, and final status.

**STUDIO-R12.** Integrators MUST consume accepted receipts and content-addressed artifacts, not unverified worker claims. Artifacts without a valid receipt, with a failed required verification, or whose content hash does not match the receipt MUST be rejected.

**STUDIO-R13.** The runtime MUST support dynamic resizing based on ready-frontier size, blocked work, worker utilization, queue age, and available cluster capacity. Resize policy MUST use deterministic thresholds supplied by configuration and MUST apply hysteresis/cooldown to prevent oscillation.

**STUDIO-R14.** Every resize action MUST emit an observation with reason, old worker count, new worker count, triggering metrics, policy revision, and timestamp.

**STUDIO-R15.** Multiple swarms MUST execute concurrently without sharing mutable worker memory or writable workspaces. Cross-swarm coordination MUST occur through typed Evidence Bus records and explicitly published artifacts.

---

# SPEC-STUDIO-004: Evidence Bus

## Purpose

Provide the append-only coordination fabric for receipts, artifacts, and verified cross-swarm state.

### Requirements

**STUDIO-R16.** The Evidence Bus MUST be the sole supported cross-swarm communication mechanism for authoritative coordination state. Direct reads of another swarm's private memory, mutable workspace, or internal runtime state MUST be prohibited.

**STUDIO-R17.** All stored artifacts MUST be content-addressed and verified on ingestion and retrieval. Hash mismatch MUST reject the artifact and emit an integrity event.

**STUDIO-R18.** Receipts MUST be append-only and immutable. Corrections MUST be represented by superseding receipts that reference the original receipt. The original record MUST remain queryable.

**STUDIO-R19.** The Evidence Bus MUST support indexed query by task ID, requirement ID, receipt hash, artifact hash, engine, node, swarm, run ID, time range, and verification status.

**STUDIO-R20.** Receipt publication, artifact publication, supersession, query, integrity failure, and retention action MUST emit observations suitable for audit and metrics export.

---

# SPEC-STUDIO-005: Parallel Efficiency Metrics

## Purpose

Measure useful concurrency rather than raw agent count.

### Requirements

**STUDIO-R21.** Factory Mode MUST compute `effective_speedup = serial_estimate_minutes / actual_elapsed_minutes`. The serial estimate source and estimator revision MUST be recorded so the metric is auditable.

**STUDIO-R22.** The system MUST track coordination overhead as wall-clock time attributable to planning, assignment, synchronization, verification, integration, conflict handling, and idle coordination waits. Measurement methodology MUST be versioned.

**STUDIO-R23.** The system MUST track rework rate as the fraction of initially completed worker attempts that require a revision attempt before acceptance.

**STUDIO-R24.** The system MUST track verifier rejection rate as rejected verification attempts divided by verification attempts, segmented by verifier, task class, model, and swarm where cardinality policy permits.

**STUDIO-R25.** The Studio swarm panel MUST display active workers, ready tasks, blocked tasks, critical-path state, effective speedup, coordination overhead, rework rate, and verifier rejection rate with live updates during active Factory Mode runs.

**STUDIO-R26.** Parallelism metrics MUST be emitted as observations and exportable to Prometheus or equivalent time-series telemetry. Metrics MUST be queryable by run ID for post-hoc analysis.

---

# SPEC-STUDIO-006: Residual Cluster

## Purpose

Pool heterogeneous self-hosted and permitted remote compute into one schedulable intelligence cluster.

### Requirements

**STUDIO-R27.** Local discovery SHOULD support mDNS for trusted LANs, but discovery MUST be separable from trust. A discovered node MUST NOT execute work until authenticated and admitted.

**STUDIO-R28.** Each admitted node MUST publish a signed capability advertisement containing node ID, supported engines/models, quantization where relevant, measured throughput, context limits, tool capabilities, available resources, policy tags, and advertisement expiry. Advertisements MUST NOT contain model weights or user file contents.

**STUDIO-R29.** Cluster routing MUST choose from capable, policy-eligible nodes using deterministic scoring over capability, locality, expected cost, latency, queue depth, reliability, privacy policy, and user preference. Local execution SHOULD be preferred when capability and policy outcomes are equivalent.

**STUDIO-R30.** `residual node join` MUST discover or target a cluster endpoint, authenticate the node, verify cluster identity, negotiate protocol version, publish capabilities, and enter a schedulable state only after admission succeeds.

**STUDIO-R31.** `residual node leave` MUST stop new assignment, drain in-flight tasks until a configurable deadline, publish departure, and remove the node from active routing. Forced leave MUST mark interrupted attempts for reassignment.

**STUDIO-R32.** The cluster MUST detect node failure using leases/heartbeats. Work whose accepted receipt was not durably published MUST be considered incomplete and reassigned. Late results from an expired lease MUST NOT be integrated unless explicitly revalidated under a current lease.

**STUDIO-R33.** Studio MUST display aggregate and per-node capacity including workers, engines/models, accelerator resources, memory, queue depth, health, and current assignment state.

---

# SPEC-STUDIO-007: IDE — Residual Studio

## Purpose

Provide a Cursor-like coding surface where swarm execution, evidence, and verification are first-class rather than hidden background behavior.

```text
┌────────────────────────────────────────────────────────────┐
│ Explorer │ Editor                     │ Swarm              │
│ files    │ source / diffs / specs     │ plan + workers     │
│ proofs   │                            │ progress + metrics  │
├──────────┴────────────────────────────┴────────────────────┤
│ Terminal │ Graph │ Tests │ Evidence │ Git │ Telemetry      │
└────────────────────────────────────────────────────────────┘
```

### Requirements

**STUDIO-R34.** Studio MUST be a browser-accessible web application served independently or by the Orchestrator. Electron MUST NOT be required.

**STUDIO-R35.** The Swarm Panel MUST have first-class visual weight alongside the editor. It MUST expose active swarms, worker counts, ready/blocked tasks, task progress, critical path, verifier retries, integration conflicts, and parallel efficiency metrics.

**STUDIO-R36.** A user MUST be able to initiate work from a single natural-language request without manually choosing worker count, engine, or swarm topology. Advanced controls MAY override defaults before plan approval.

**STUDIO-R37.** Factory Mode MUST stream plan, scheduling, execution, verification, integration, and retry events to the UI. Reconnection MUST reconstruct authoritative state from persisted observations rather than relying on browser memory.

**STUDIO-R38.** The Evidence View MUST permit drill-down from requirement → task → worker contract → attempt → verification → receipt → artifact → integration receipt. Source-line provenance SHOULD be represented through generated provenance maps that bind file ranges to producing receipt hashes and requirement IDs.

**STUDIO-R39.** Pair, Team, and Factory modes MUST be available per task. Escalating a task to a higher-concurrency mode MUST create a new plan revision and MUST NOT silently alter already-approved contracts.

**STUDIO-R40.** Studio MUST support read-only observer mode for managers, reviewers, and auditors. Observer sessions MUST be technically prevented from mutation rather than merely hiding controls.

---

# SPEC-STUDIO-008: Deterministic Integration

## Purpose

Integrate verified artifacts into a coherent project state using deterministic, replayable rules.

### Requirements

**STUDIO-R41.** Given the same base commit, accepted receipt set, artifact contents, integration policy revision, and verifier revisions, integration MUST produce the same candidate project state and integration decision. Merge logic MUST NOT invoke an LLM.

**STUDIO-R42.** Integration MUST: (1) validate receipt graph and artifact hashes, (2) topologically order accepted work by dependencies, (3) apply non-overlapping changes in canonical task order, (4) permit overlapping changes only when deterministic containment/commutativity checks prove one change is a strict compatible subset, (5) otherwise emit `integration_conflict`, (6) run project-level verification, and (7) bind the result in an Integration Receipt. Timestamp MUST NOT be used to resolve semantic conflicts.

**STUDIO-R43.** The Work Partitioner SHOULD minimize overlapping writable scopes. Conflict frequency MUST be measured and treated as a decomposition-quality signal.

**STUDIO-R44.** Every integration attempt MUST produce an `IntegrationReceipt` binding run ID, base commit, ordered input receipt hashes, artifact hashes, integration policy revision, verifier revisions, project-level verification results, candidate output commit/tree hash, conflict set, and timestamp.

**STUDIO-R45.** The Integration Receipt is the final human-approvable evidence object for a project change. Approval MUST bind the exact receipt hash and candidate output commit/tree hash; any subsequent mutation MUST invalidate that approval and require a new receipt.

---

# Implementation Roadmap

| Phase | Specs | Deliverable |
|---|---|---|
| 1 | STUDIO-002 | Intent → canonical RequirementGraph → approved plan |
| 2 | STUDIO-003 + STUDIO-004 | Bounded multi-swarm runtime + Evidence Bus |
| 3 | STUDIO-008 + STUDIO-005 | Deterministic integration + measurable parallelism |
| 4 | STUDIO-007 | Cursor-like Studio control plane |
| 5 | STUDIO-006 | Multi-device self-hosted cluster |
| 6 | STUDIO-001 | Full independently deployable platform composition |

**Critical path:** Requirement Compiler → Swarm Runtime → Evidence Bus → Deterministic Integration → Studio IDE.

Cluster work can proceed in parallel once engine abstraction, node identity, leases, and capability routing are stable.

# Acceptance Gate for v1.0

Residual Studio MUST NOT be called deterministic merely because workers use fixed prompts or structured outputs. The v1.0 claim requires a replayable requirement graph, frozen contracts, bounded worker execution, content-addressed evidence, deterministic integration, verifier-bound receipts, and approval binding to exact artifacts.
