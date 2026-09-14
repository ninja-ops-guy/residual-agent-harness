# Residual Studio — Multi-Swarm Engineering Platform Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-agent-harness v1.0.0+
**Codename:** "The Factory"
**Positioning:** A deterministic distributed runtime that turns
heterogeneous AI compute into parallel engineering capacity.

---

## 0. Product Thesis

Cursor optimizes for one developer collaborating with one agent.
Residual Studio optimizes for coordinated parallel execution across
many agents, with explicit verification and deterministic integration.

The claim is not "AI writes software." The claim is:

**Residual deterministically constrains, verifies, and integrates
nondeterministic workers.**

Agent output is not trusted. Agent output plus verified contract
equals eligible artifact.

---

## SPEC-STUDIO-001: Five-Layer Architecture

### Purpose
Define the complete platform stack from IDE to cluster.

### Layer Map

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: Residual Cluster                                   │
│ Multi-device compute mesh. LAN discovery, GPU pooling,      │
│ cloud bursting.                                             │
├─────────────────────────────────────────────────────────────┤
│ LAYER 4: Swarm Runtime                                      │
│ Kubernetes-style agent orchestration. Coordinators,         │
│ workers, verifiers, critics, integrators.                   │
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: Residual Orchestrator                              │
│ The brain. Intent parsing, requirement DAG, task            │
│ decomposition, resource estimation, engine selection,       │
│ scheduling, replanning.                                     │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: Residual Station (existing v0.4.0)                 │
│ GoalSpec, LoopController, QuarantineStore, Verifier,        │
│ Brakes, Receipts, HITL. The safety kernel.                  │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: Residual Studio (IDE)                              │
│ The human interface. Editor, swarm panel, evidence view,    │
│ terminal, graph, telemetry.                                 │
└─────────────────────────────────────────────────────────────┘
```

### Requirements

**STUDIO-R1.** Each layer MUST be independently deployable. Layer 1
(IDE) MUST be usable against a remote Layer 3 (Orchestrator). Layer 3
MUST be usable without Layer 1 (CLI-only).

**STUDIO-R2.** Layers communicate through typed protocols only. No
layer MAY import from another layer's internal modules. The interface
between layers is the contract.

**STUDIO-R3.** Layer 2 (Station) is the safety kernel. Every artifact
that moves between layers MUST pass through Station verification.
No layer MAY bypass the kernel.

**STUDIO-R4.** The platform MUST support three operating modes:
- **Pair Mode:** One human, one agent. Cursor-like.
- **Team Mode:** 3-5 worker swarm with shared context.
- **Factory Mode:** Full multi-swarm autonomous execution.

Mode selection MUST be per-task, not per-session. A user MAY
start in Pair Mode and escalate to Factory Mode for a specific
feature without changing the session.

---

## SPEC-STUDIO-002: Requirement Compiler

### Purpose
Transform natural language intent into a structured, executable
requirement graph.

### Pipeline

```
User Intent
    │
    ▼
┌─────────────────┐
│  Intent Parser   │  ← LLM call: extract goals, constraints
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Spec Generator   │  ← LLM call: produce structured requirements
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Dependency       │  ← Deterministic: build DAG from requirements
│ Graph Builder    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Work Partitioner │  ← Deterministic: group into swarms
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Plan Presenter   │  ← Human review and approval
└─────────────────┘
```

### Requirements

**STUDIO-R5.** The Requirement Compiler MUST produce a
`RequirementGraph` containing:
- `requirements: tuple[Requirement, ...]` — each with ID, description,
  acceptance criteria, and dependencies
- `swarms: tuple[SwarmSpec, ...]` — proposed swarm decomposition
- `estimated_parallelism: float` — fraction of work that can run in
  parallel (0.0-1.0)
- `serial_estimate_minutes: float` — estimated time with one worker
- `risk_assessment: dict` — areas of high uncertainty

**STUDIO-R6.** The Requirement Compiler MUST be deterministic given
the same intent and model. If the LLM produces different outputs for
the same input, the compiler MUST use structured output constraints
(JSON schema) to enforce parseable, comparable results.

**STUDIO-R7.** The Plan Presenter MUST show the human:
- Total requirements count
- Total task count
- Dependency groups (tasks that can run in parallel)
- Proposed swarm count and composition
- Estimated parallelizable work percentage
- Approval button

The human MUST be able to: approve, modify (reassign tasks between
swarms), or reject the plan.

**STUDIO-R8.** The Requirement Compiler MUST handle ambiguity by
asking clarifying questions before generating the graph. It MUST NOT
guess when a requirement is underspecified. Questions MUST be
presented in the IDE, not on the command line.

---

## SPEC-STUDIO-003: Swarm Runtime

### Purpose
Kubernetes-style orchestration of agent swarms with bounded contracts,
dynamic resizing, and evidence-based coordination.

### Swarm Structure

```
Swarm
├── coordinator      — assigns tasks to workers, monitors progress
├── workers (1-N)    — execute tasks within bounded contracts
├── verifier         — checks worker outputs against acceptance criteria
├── critic           — adversarial reviewer, tries to find flaws
└── integrator       — merges verified outputs into shared state
```

### Worker Contract

Every worker receives a `WorkerContract`:

```python
@dataclass(frozen=True)
class WorkerContract:
    task_id: str
    inputs: tuple[str, ...]           # files/directories readable
    allowed_outputs: tuple[str, ...]   # files writable
    requirements: tuple[str, ...]     # requirement IDs to satisfy
    acceptance: tuple[str, ...]       # verification checks to pass
    dependencies: tuple[str, ...]     # task IDs that must complete first
    forbidden: tuple[str, ...]        # paths that MUST NOT be touched
    engine_hint: Optional[str]        # preferred engine (advisory)
    token_budget: int
    wall_clock_budget_s: float
```

### Requirements

**STUDIO-R9.** Every worker MUST receive a `WorkerContract` before
execution. The contract MUST be frozen. No worker MAY modify its own
contract.

**STUDIO-R10.** The Swarm Runtime MUST enforce contract boundaries:
- Workers MUST NOT read files outside `inputs`
- Workers MUST NOT write files outside `allowed_outputs`
- Workers MUST NOT touch paths in `forbidden`
- Violations MUST trigger immediate worker termination and a
  `contract_violation` observation

**STUDIO-R11.** Each worker MUST produce a `WorkerReceipt` on
completion:

```python
@dataclass(frozen=True)
class WorkerReceipt:
    task_id: str
    engine_name: str
    engine_version: str
    input_commit: str          # git commit hash of input state
    outputs: tuple[str, ...]   # files produced
    requirements: tuple[tuple[str, bool], ...]  # (req_id, satisfied)
    verification: tuple[tuple[str, str], ...]   # (check_name, result)
    parent_receipts: tuple[str, ...]  # hashes of dependency receipts
    artifact_hash: str
    status: str                # "accepted" | "rejected" | "needs_revision"
```

**STUDIO-R12.** The integrator MUST NOT consume worker outputs
directly. It MUST consume `WorkerReceipt`s. An output without a
receipt MUST be rejected. An output with a receipt showing any
failed verification MUST be rejected.

**STUDIO-R13.** The Swarm Runtime MUST support dynamic resizing.
The coordinator MUST monitor:
- `independent_tasks: int` — tasks with no unresolved dependencies
- `blocked_tasks: int` — tasks waiting on dependencies
- `worker_utilization: float` — fraction of workers actively executing

When `independent_tasks >> blocked_tasks`, the coordinator MUST
request more workers. When `blocked_tasks >> independent_tasks`,
the coordinator MUST release workers to other swarms.

**STUDIO-R14.** Swarm resizing MUST be logged as observations. Every
resize event MUST include: reason, old worker count, new worker count,
and the metric that triggered the resize.

**STUDIO-R15.** Multiple swarms MUST be able to run simultaneously.
Swarms MUST NOT share workers. Swarms MUST coordinate through the
Evidence Bus, not through shared memory or direct communication.

---

## SPEC-STUDIO-004: Evidence Bus

### Purpose
The shared coordination primitive. All inter-swarm and inter-worker
communication flows through verified receipts on the Evidence Bus.

### Architecture

```
Swarm A Worker          Swarm B Worker
     │                       │
     ▼                       ▼
┌─────────────────────────────────────┐
│           Evidence Bus              │
│  ┌─────────────────────────────┐    │
│  │  Receipt Queue (append-only) │    │
│  │  - WorkerReceipts            │    │
│  │  - IntegrationReceipts       │    │
│  │  - VerificationReceipts      │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │  Artifact Store             │    │
│  │  (content-addressed)        │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
     │                       │
     ▼                       ▼
Swarm A Integrator      Swarm B Integrator
```

### Requirements

**STUDIO-R16.** The Evidence Bus MUST be the sole communication
channel between swarms. No swarm MAY read another swarm's internal
state, memory, or filesystem.

**STUDIO-R17.** All artifacts on the Evidence Bus MUST be
content-addressed. The content hash MUST be verified on receipt.
A hash mismatch MUST reject the artifact.

**STUDIO-R18.** The Evidence Bus MUST be append-only. Receipts MUST
NOT be modified or deleted. Corrections MUST be new receipts that
reference and supersede the original.

**STUDIO-R19.** The Evidence Bus MUST support querying by:
- task_id
- requirement_id
- artifact_hash
- engine_name
- time range
- verification status

**STUDIO-R20.** The Evidence Bus MUST emit observations for every
receipt added, every artifact stored, and every query executed.
These observations feed the metrics system.

---

## SPEC-STUDIO-005: Parallel Efficiency Metrics

### Purpose
Measure and display useful parallelism, not just agent count.

### Metrics

```
Parallel Efficiency Report
---------------------------
Workers active:          14
Independent tasks:       11
Blocked tasks:            3
Serial estimate:        164 min
Actual elapsed:          31 min
Effective speedup:       5.29×
Coordination overhead:   12.4%
Rework rate:              4.1%
Verifier rejection:       7.8%
```

### Requirements

**STUDIO-R21.** The system MUST compute and display `effective_speedup`
for every Factory Mode run. The formula MUST be:

```
effective_speedup = serial_estimate_minutes / actual_elapsed_minutes
```

**STUDIO-R22.** The system MUST track `coordination_overhead`:
the fraction of wall-clock time spent on non-execution activities
(task assignment, receipt verification, integration, conflict
resolution). Target: < 20%.

**STUDIO-R23.** The system MUST track `rework_rate`: the fraction
of worker outputs that required revision after initial verification.
Target: < 10%.

**STUDIO-R24.** The system MUST track `verifier_rejection_rate`:
the fraction of worker outputs rejected by the verifier. Target: < 15%.

**STUDIO-R25.** The Parallel Efficiency Report MUST be displayed
in the IDE swarm panel in real time. It MUST update at least once
per second during Factory Mode execution.

**STUDIO-R26.** All parallelism metrics MUST be recorded as
observations and exported to Prometheus. They MUST be queryable
by run_id for post-hoc analysis.

---

## SPEC-STUDIO-006: Residual Cluster

### Purpose
Multi-device compute mesh. Pool local GPUs, workstations, homelab
servers, and cloud APIs into a single intelligence cluster.

### Cluster View

```
INTELLIGENCE CLUSTER
├── node-a (RTX 4090 workstation)
│   ├── Qwen2.5-Coder-32B  48 tok/s
│   └── llama3.3-70b       32 tok/s
├── node-b (Mac Studio)
│   ├── DeepSeek-V3        71 tok/s
│   └── qwen2.5-14b        89 tok/s
├── node-c (homelab server)
│   └── vision-model       12 tok/s
├── cloud-openai
│   └── gpt-4o             high reasoning
└── cloud-anthropic
    └── claude-opus-4-1    large context
```

### Requirements

**STUDIO-R27.** The Cluster MUST support automatic LAN discovery
via mDNS. A new node MUST appear in the cluster view within 10
seconds of joining the network.

**STUDIO-R28.** Each node MUST announce its capabilities: model
names, quantization, tokens/second, context window, and available
tools. Capability announcement MUST NOT include model weights or
local file contents.

**STUDIO-R29.** The Cluster MUST route tasks to the cheapest capable
node. Local nodes MUST be preferred over cloud when capability is
equal. The CapabilityRouter from SPEC-GAP-001 MUST be extended to
operate across cluster nodes.

**STUDIO-R30.** A `residual node join` CLI command MUST exist. It
MUST: discover the cluster, authenticate with the cluster key,
announce capabilities, and begin accepting tasks.

**STUDIO-R31.** A `residual node leave` CLI command MUST exist. It
MUST: finish in-flight tasks, announce departure, and remove itself
from the routing table.

**STUDIO-R32.** The Cluster MUST handle node failure gracefully.
If a node becomes unresponsive, the Cluster MUST reassign its
in-flight tasks to other capable nodes. The failed node's receipts
MUST be marked `node_failed` and excluded from integration.

**STUDIO-R33.** The Cluster MUST display aggregate capacity:
total GPUs, total models, total workers, total memory. This MUST
be visible in the IDE cluster panel.

---

## SPEC-STUDIO-007: IDE (Residual Studio)

### Purpose
The human interface. Not the product — the window into the product.

### Layout

```
┌───────────────────────────────────────────────────────────┐
│ Explorer │ Editor                    │ Swarm             │
│          │                           │                   │
│ files    │ src/...                   │ ● Planner         │
│ specs    │                           │ ● Backend x4      │
│ proofs   │                           │ ● Tests x3        │
│          │                           │ ● Security x2     │
├──────────┴───────────────────────────┴───────────────────┤
│ Terminal │ Graph │ Tests │ Evidence │ Git │ Telemetry    │
└───────────────────────────────────────────────────────────┘
```

### Requirements

**STUDIO-R34.** The IDE MUST be a web application. It MUST be
servable from the Orchestrator (Layer 3) and accessible via browser.
It MUST NOT require Electron or a desktop install.

**STUDIO-R35.** The Swarm Panel MUST have equal visual weight to
the Editor. It MUST display: active swarms, worker count per swarm,
task progress per swarm, and the Parallel Efficiency Report.

**STUDIO-R36.** The user MUST be able to initiate work with a
single natural language prompt. The prompt MUST NOT require
specifying swarms, workers, or engines. The Orchestrator handles
decomposition.

**STUDIO-R37.** The IDE MUST show real-time progress during Factory
Mode execution:

```
████████████████░░░░ 78%
Backend        12/12 ✓
Frontend        7/9
Tests          18/23
Security        4/5
3 workers active
2 verifier retries
0 unresolved conflicts
```

**STUDIO-R38.** The Evidence View MUST allow drilling into any
receipt: viewing the worker contract, verification results,
artifact hash, and parent receipts. It MUST be possible to trace
any line of code back to the requirement that produced it.

**STUDIO-R39.** The IDE MUST support all three operating modes
(Pair, Team, Factory) with a mode selector. Mode switching MUST
be per-task, not per-session.

**STUDIO-R40.** The IDE MUST be usable in read-only "observer mode"
— watching a Factory Mode run without the ability to modify it.
This is for managers and auditors.

---

## SPEC-STUDIO-008: Deterministic Integration

### Purpose
The merge coordinator. Combines verified worker outputs into a
coherent project state with deterministic rules.

### Requirements

**STUDIO-R41.** Integration MUST be deterministic. Given the same
set of accepted WorkerReceipts, the integration MUST produce the
same output state. No randomness, no LLM calls in the merge logic.

**STUDIO-R42.** Integration MUST follow these rules in order:
1. Topological sort by dependency graph
2. Apply changes in dependency order
3. If two workers modified the same file, use the later
   Worker'sReceipt (by timestamp) only if the earlier receipt's
   changes are a strict subset
4. If changes conflict (both modified the same lines), mark
   as `integration_conflict` and require human resolution
5. Run project-level verification (full test suite, type check,
   contract validation)
6. If project-level verification fails, identify the offending
   receipt and mark it for revision

**STUDIO-R43.** Integration conflicts MUST be rare. If the
Work Partitioner (SPEC-STUDIO-002) is doing its job, workers
should have disjoint `allowed_outputs`. Frequent integration
conflicts indicate poor task decomposition.

**STUDIO-R44.** The Integration Receipt MUST be produced on
every merge. It MUST bind: all input WorkerReceipt hashes,
the output commit hash, the project-level verification results,
and the integration timestamp.

**STUDIO-R45.** The Integration Receipt is the final artifact.
It is what the human approves. It is what gets committed to
the project repository. It is the proof that the change was
correctly implemented.

---

## Implementation Roadmap

| Phase | Specs | Deliverable |
|---|---|---|
| 1 | SPEC-STUDIO-002 (Requirement Compiler) | Intent → DAG → Plan |
| 2 | SPEC-STUDIO-003 (Swarm Runtime) + SPEC-STUDIO-004 (Evidence Bus) | Multi-swarm execution |
| 3 | SPEC-STUDIO-005 (Parallel Metrics) + SPEC-STUDIO-008 (Integration) | Measurable parallelism |
| 4 | SPEC-STUDIO-006 (Cluster) | Multi-device mesh |
| 5 | SPEC-STUDIO-007 (IDE) | Full Studio experience |
| 6 | SPEC-STUDIO-001 (Integration) | All layers working together |

**Critical path:** Requirement Compiler → Swarm Runtime →
Integration → IDE. Cluster and Metrics can be built in parallel
with the critical path.
