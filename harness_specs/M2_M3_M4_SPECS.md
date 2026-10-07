# Residual Studio — M2/M3/M4 Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-agent-harness v1.0.0+
**Depends on:** STUDIO_SPECS.md, GAP_CLOSURE_SPECS.md

---

## Overview

Three milestone specs covering the swarm runtime, evidence bus,
deterministic integration, and scheduler intelligence. Plus an
evaluation framework for measuring single-agent vs fixed-swarm
vs dynamic-swarm performance.

---

## SPEC-M2: Worker Contract + Swarm Runtime

### Purpose
Define the bounded execution environment for every worker. Every
worker gets explicit inputs, outputs, allowed paths, tools, resource
limits, acceptance checks, and dependencies. Violations kill the
worker immediately.

### The WorkerContract

```python
@dataclass(frozen=True)
class WorkerContract:
    """Immutable contract between the swarm and one worker."""

    # Identity
    task_id: str
    worker_id: str
    swarm_id: str

    # Filesystem boundaries
    inputs: tuple[str, ...]           # Paths the worker may read
    allowed_outputs: tuple[str, ...]   # Paths the worker may write
    forbidden: tuple[str, ...]        # Paths that MUST NOT be touched
    workspace_root: str               # Root of the worker's sandbox

    # Task definition
    requirements: tuple[str, ...]     # Requirement IDs to satisfy
    acceptance: tuple[str, ...]       # Verification checks to pass
    dependencies: tuple[str, ...]     # task_ids that must complete first

    # Tools
    allowed_tools: tuple[str, ...]    # Tool names the worker may invoke
    forbidden_tools: tuple[str, ...]  # Tool names that MUST NOT be invoked

    # Resource limits
    token_budget: int
    wall_clock_budget_s: float
    max_tool_calls: int
    max_file_writes: int
    memory_limit_mb: int

    # Engine
    engine_hint: Optional[str]        # Preferred engine (advisory)
    engine_class: str                 # "local", "cloud", "any"
```

### Requirements

**M2-R1.** Every worker MUST receive a `WorkerContract` before
execution begins. The contract MUST be frozen. No worker MAY modify
its own contract. The contract MUST be stored in the observation
log before the worker starts.

**M2-R2.** The Swarm Runtime MUST enforce filesystem boundaries
via OS-level mechanisms (chroot, bind mounts, or container
filesystems), not by convention. A worker attempting to read
outside `inputs` or write outside `allowed_outputs` MUST be
terminated immediately.

**M2-R3.** The Swarm Runtime MUST enforce tool boundaries. A worker
attempting to invoke a tool in `forbidden_tools` or not in
`allowed_tools` MUST be terminated immediately. The tool invocation
MUST be observed with reason `contract_violation`.

**M2-R4.** The Swarm Runtime MUST enforce resource limits:
- Token budget: tracked per LLM call, worker terminated on exceed
- Wall clock: tracked from worker start, terminated on exceed
- Tool calls: counter incremented per invocation, terminated on exceed
- File writes: counter incremented per write, terminated on exceed
- Memory: polled at 1 Hz, terminated on exceed

**M2-R5.** Contract violations MUST produce a `ContractViolation`
observation containing: task_id, worker_id, violated boundary
(filesystem, tool, resource), the attempted action, and the
contract field that was violated.

**M2-R6.** Workers MUST execute in isolated worktrees. The Swarm
Runtime MUST create a fresh git worktree for each worker from the
current project commit. The worker's worktree MUST be at
`workspace_root`. On completion, the worktree MUST be either
merged (if receipt accepted) or destroyed (if receipt rejected).

**M2-R7.** Worker termination MUST be immediate and unconditional.
There is no appeal, no retry, no warning. A violated contract is
a terminal state. The task MAY be reassigned to a new worker with
the same contract.

**M2-R8.** The Swarm Runtime MUST maintain a `SwarmState` containing:
- Active workers and their contracts
- Completed workers and their receipts
- Blocked tasks (waiting on dependencies)
- Available capacity (tokens, wall clock, worker slots)

**M2-R9.** The Swarm Runtime MUST support dynamic resizing per
SPEC-STUDIO-003. The coordinator MUST monitor the ratio of
independent to blocked tasks and request or release workers
accordingly.

**M2-R10.** Multiple swarms MUST run in isolation. Swarms MUST NOT
share workers, worktrees, or memory. Inter-swarm communication
MUST flow through the Evidence Bus only.

---

## SPEC-M3: Evidence Bus + Receipts

### Purpose
Receipts are the only trusted handoff. Workers generate arbitrary
output. Downstream consumers only receive artifacts that have
passed Station verification and acquired a valid receipt.

### The Evidence Bus Architecture

```
Worker A                    Worker B
    │                          │
    ▼                          ▼
┌─────────────────────────────────────┐
│         Evidence Bus                 │
│                                      │
│  ┌───────────────────────────────┐   │
│  │  Raw Output Queue              │   │
│  │  (untrusted, ephemeral)        │   │
│  └───────────────┬───────────────┘   │
│                  │                    │
│                  ▼                    │
│  ┌───────────────────────────────┐   │
│  │  Station Verification          │   │
│  │  - Quarantine evaluation       │   │
│  │  - Mechanical checks           │   │
│  │  - Structural checks           │   │
│  │  - Judge checks (if needed)    │   │
│  └───────────────┬───────────────┘   │
│                  │                    │
│          ┌───────┴───────┐            │
│          ▼               ▼            │
│  ┌─────────────┐  ┌─────────────┐    │
│  │  ACCEPTED   │  │  REJECTED   │    │
│  │             │  │             │    │
│  │  Receipt    │  │  No receipt │    │
│  │  issued     │  │  Output     │    │
│  │  Artifact   │  │  destroyed  │    │
│  │  stored     │  │             │    │
│  └──────┬──────┘  └─────────────┘    │
│         │                            │
│         ▼                            │
│  ┌───────────────────────────────┐   │
│  │  Receipt Queue (append-only)   │   │
│  │  Hash-chained                  │   │
│  │  Queryable by task/req/engine  │   │
│  └───────────────┬───────────────┘   │
│                  │                    │
│                  ▼                    │
│  ┌───────────────────────────────┐   │
│  │  Artifact Store                │   │
│  │  Content-addressed             │   │
│  │  sha256:... → file content     │   │
│  └───────────────────────────────┘   │
└─────────────────────────────────────┘
         │
         ▼
   Integrator
   (consumes receipts only)
```

### The WorkerReceipt

```python
@dataclass(frozen=True)
class WorkerReceipt:
    """The only trusted artifact. Issued by Station, not by workers."""

    # Identity
    receipt_id: str
    task_id: str
    worker_id: str
    swarm_id: str

    # Provenance
    engine_name: str
    engine_version: str
    input_commit: str          # git commit hash of the input state
    contract_hash: str         # hash of the WorkerContract

    # Output
    artifact_hashes: tuple[tuple[str, str], ...]  # (path, sha256)
    output_commit: str         # git commit hash of the output state

    # Verification
    requirements_met: tuple[tuple[str, bool], ...]
    verification_results: tuple[tuple[str, str], ...]  # (check, result)
    overall_verdict: str       # "pass" | "fail" | "unknown"

    # Dependencies
    parent_receipts: tuple[str, ...]  # receipt_ids of dependencies

    # Cryptographic binding
    receipt_hash: str
    station_signature: str     # signed by the Station's identity key
```

### Requirements

**M3-R1.** The Evidence Bus MUST be the sole communication channel
between workers and consumers. No consumer MAY read a worker's
raw output directly. All consumption flows through receipts.

**M3-R2.** A receipt MUST be issued by the Station, not by the
worker. The Station's signature on the receipt is the trust root.
A worker-generated receipt is invalid by definition.

**M3-R3.** An artifact without a receipt MUST be treated as
untrusted. It MUST NOT enter the artifact store. It MUST NOT be
visible to any consumer. It MUST be destroyed after a configurable
retention period (default: 1 hour).

**M3-R4.** The receipt MUST bind the WorkerContract hash. A
receipt issued for a different contract than the one the worker
executed under is invalid.

**M3-R5.** The receipt MUST bind the input and output git commits.
This enables deterministic replay: given the same input commit
and contract, the same output should be verifiable.

**M3-R6.** The Evidence Bus MUST maintain an append-only receipt
queue. Receipts MUST NOT be modified or deleted. Corrections MUST
be new receipts that reference and supersede the original.

**M3-R7.** The Evidence Bus MUST support querying by: task_id,
requirement_id, artifact_hash, engine_name, verification_status,
time range, and swarm_id.

**M3-R8.** The Evidence Bus MUST emit observations for every
receipt issued, every artifact stored, every query executed, and
every rejection. These observations feed the metrics system.

**M3-R9.** Receipt verification MUST be local. A consumer MUST
verify the Station's signature, the contract hash, and the artifact
hashes without contacting any remote service.

**M3-R10.** The Evidence Bus MUST handle receipt expiration.
A receipt whose parent receipts have been superseded MUST be
marked `stale`. Stale receipts MUST NOT be consumed by the
integrator without explicit human approval.

---

## SPEC-M4: Deterministic Integrator + Scheduler Intelligence

### Purpose
Consume accepted receipts in dependency order, detect overlapping
changes, reject unresolved conflicts, run accumulated project
verification, and emit the final IntegrationReceipt. Then add
scheduler intelligence: measure, resize, replan.

### Part 1: Deterministic Integration

```
Accepted Receipts (sorted by dependency order)
         │
         ▼
┌─────────────────────┐
│  Topological Sort    │  Deterministic: same input = same order
│  by parent receipts  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Apply Changes       │  In topological order
│  Receipt by Receipt  │  Each to its own worktree
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Overlap Detection   │  Which files appear in multiple receipts?
│                      │  Same file, different changes = conflict
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│ No      │  │ Conflict │
│ Overlap │  │ Detected │
└────┬────┘  └────┬────┘
     │            │
     ▼            ▼
┌─────────┐  ┌─────────────────┐
│ Merge   │  │ Conflict        │
│ All     │  │ Resolution      │
│ Changes │  │                 │
└────┬────┘  │ - Same change:  │
     │       │   keep one      │
     │       │ - Subset:       │
     │       │   keep superset │
     │       │ - True conflict:│
     │       │   REJECT        │
     │       └─────────────────┘
     │            │
     ▼            ▼ (if resolved)
┌─────────────────────┐
│  Project Verification│  Full test suite, type check,
│  (accumulated)       │  contract validation, security scan
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│ PASS    │  │ FAIL    │
└────┬────┘  └────┬────┘
     │            │
     ▼            ▼
┌─────────────────────┐  ┌─────────────────────┐
│  IntegrationReceipt │  │  Identify offending │
│  (final artifact)   │  │  receipt            │
│                     │  │  Mark for revision  │
│  Binds:             │  │  Re-plan task       │
│  - All input        │  └─────────────────────┘
│    receipt hashes   │
│  - Output commit    │
│  - Verification     │
│    results          │
│  - Timestamp        │
│  - Station signature│
└─────────────────────┘
```

### Part 2: Scheduler Intelligence

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEDULER LOOP                            │
│                                                              │
│  ┌──────────┐                                                │
│  │ Ready DAG │  Tasks with all dependencies satisfied        │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ Estimate │  How many tasks are independent?               │
│  │Independence│ What fraction can run in parallel?           │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │  Select  │  How many swarms? How many workers each?       │
│  │  Swarm   │  Based on independence estimate               │
│  │ Topology │                                                │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │  Select  │  Which engines? Which nodes?                   │
│  │  Engines │  Local preferred, cloud for capability gaps    │
│  │  /Nodes  │                                                │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ Execute  │  Run swarms, monitor progress                  │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ Measure  │  Bottlenecks? Utilization? Blocked tasks?      │
│  │Bottlenecks│                                               │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │  Resize  │  Add workers where independent,               │
│  │          │  remove where blocked                         │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────┐                                                │
│  │ Re-plan  │  If bottleneck is structural,                  │
│  │          │  re-decompose remaining work                   │
│  └────┬─────┘                                                │
│       │                                                      │
│       └──────────► (loop back to Ready DAG)                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Requirements

**M4-R1.** Integration MUST be deterministic. Given the same set
of accepted receipts, the integration MUST produce the same output
commit. No randomness, no LLM calls in the merge logic.

**M4-R2.** Integration MUST process receipts in topological order
by dependency. A receipt whose parents have not been integrated
MUST NOT be processed.

**M4-R3.** Overlap detection MUST identify files that appear in
multiple receipts. For each overlapping file:
- If the changes are identical (same diff): keep one copy
- If one change is a strict subset of the other: keep the superset
- If the changes conflict (different non-subset diffs): mark as
  `integration_conflict` and reject

**M4-R4.** Integration conflicts MUST NOT be resolved automatically.
They MUST be presented to a human via HITL. The human's resolution
MUST be recorded as a new observation and bound into the
IntegrationReceipt.

**M4-R5.** After merging all non-conflicting changes, the
integrator MUST run accumulated project verification:
- Full test suite
- Type checking
- Contract validation
- Security scan (if SecOps module active)

**M4-R6.** If project verification fails, the integrator MUST
identify the offending receipt by binary search: revert half the
changes, re-run verification, narrow down. The offending receipt
MUST be marked for revision and the task re-planned.

**M4-R7.** The IntegrationReceipt MUST bind: all input receipt
hashes, the output commit hash, the project verification results,
the integration timestamp, and the Station's signature. This is
the final human-approvable artifact.

**M4-R8.** The scheduler MUST estimate independence before
selecting swarm topology. The estimate MUST be based on the
dependency graph: fraction of tasks with no unresolved
dependencies.

**M4-R9.** The scheduler MUST select engines and nodes based on
capability, cost, and locality. Local engines MUST be preferred
when capability is equal. Cloud engines MUST be selected for
capability gaps or when local capacity is exhausted.

**M4-R10.** The scheduler MUST measure bottlenecks continuously:
- Worker utilization (active / total)
- Blocked task ratio (blocked / total)
- Verification queue depth
- Integration conflict rate

**M4-R11.** The scheduler MUST resize swarms based on measurements:
- If independent_tasks >> blocked_tasks: add workers
- If blocked_tasks >> independent_tasks: release workers
- If verification_queue > threshold: add verifiers
- If integration_conflicts > threshold: pause and alert human

**M4-R12.** The scheduler MUST re-plan when structural bottlenecks
are detected. If a task is blocking 10+ downstream tasks and has
failed 3+ times, the scheduler MUST re-decompose the task into
smaller subtasks.

**M4-R13.** All scheduler decisions MUST be observed. Every
resize, re-plan, and engine selection MUST emit an observation
with the reasoning.

---

## SPEC-EVAL-001: Evaluation Framework

### Purpose
Measure single-agent vs fixed-swarm vs dynamic-swarm performance
across the same frozen workload. Produce evidence for claims
about parallelism efficiency.

### The Frozen Workload

A `FrozenWorkload` is a fixed set of tasks with:
- Fixed requirements (no ambiguity)
- Fixed dependency graph
- Fixed acceptance criteria
- Fixed input state (git commit)
- Fixed expected output state

The same FrozenWorkload MUST be run under three configurations:

```
┌─────────────────────────────────────────────────────────────┐
│                    FROZEN WORKLOAD                           │
│                                                              │
│  40 requirements                                             │
│  31 tasks                                                    │
│  8 dependency groups                                         │
│  Fixed input commit: abc123                                  │
│  Fixed expected output: def456                               │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Config A │  │ Config B │  │ Config C │                 │
│  │          │  │          │  │          │                 │
│  │ Single   │  │ Fixed    │  │ Dynamic  │                 │
│  │ Agent    │  │ Swarm    │  │ Swarm    │                 │
│  │          │  │ (4 work) │  │ (resize) │                 │
│  │          │  │          │  │          │                 │
│  │ No swarm │  │ No resize│  │ Scheduler│                 │
│  │ runtime  │  │          │  │ intelligent│               │
│  └──────────┘  └──────────┘  └──────────┘                 │
│       │             │              │                        │
│       ▼             ▼              ▼                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  Run 1   │  │  Run 1   │  │  Run 1   │                 │
│  │  Run 2   │  │  Run 2   │  │  Run 2   │                 │
│  │  Run 3   │  │  Run 3   │  │  Run 3   │                 │
│  │ (n=3)    │  │ (n=3)    │  │ (n=3)    │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
│       │             │              │                        │
│       └─────────────┴──────────────┘                        │
│                     │                                       │
│                     ▼                                       │
│  ┌─────────────────────────────────────────────┐            │
│  │              COMPARISON REPORT               │            │
│  │                                              │            │
│  │  Metric          A      B      C             │            │
│  │  ─────────────────────────────────           │            │
│  │  Elapsed (min)   164    41     31            │            │
│  │  Accepted/hr     11     45     60            │            │
│  │  Token cost      890K  920K   780K           │            │
│  │  GPU time (min)  142    38     29            │            │
│  │  Coordination %  0      18     12            │            │
│  │  Rework %        8       6      4            │            │
│  │  Merge conflicts 0       3      1            │            │
│  │  Verifier reject 12%    15%    8%            │            │
│  │  Test pass rate  100%   97%   100%           │            │
│  │                                              │            │
│  │  Speedup:        1.0×   4.0×   5.3×          │            │
│  │  Efficiency:     100%   82%    91%           │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Metrics

**EVAL-R1.** The evaluation MUST measure:
- `elapsed_time_minutes`: wall clock from start to IntegrationReceipt
- `accepted_tasks_per_hour`: completed tasks / elapsed hours
- `token_cost_total`: sum of all LLM tokens used
- `gpu_time_minutes`: sum of GPU inference time (local models)
- `coordination_overhead_pct`: time on non-execution / total time
- `rework_rate_pct`: tasks requiring revision / total tasks
- `merge_conflicts`: count of integration conflicts
- `verifier_rejection_rate_pct`: rejected outputs / total outputs
- `final_test_pass_rate_pct`: project tests passing at integration

**EVAL-R2.** Each configuration MUST run at least 3 times on the
same FrozenWorkload. Results MUST report mean, median, and
standard deviation.

**EVAL-R3.** The evaluation MUST control for model nondeterminism.
Each run MUST use the same model versions, same temperatures
(temperature=0 where supported), and same seed where available.
Residual receipts MUST verify that the same engine was used
across all runs.

**EVAL-R4.** The evaluation MUST produce a `ComparisonReport`
containing all metrics for all configurations, with statistical
significance tests (t-test or Mann-Whitney U) for differences
between configurations.

**EVAL-R5.** The ComparisonReport MUST be cryptographically signed
by the Station. It MUST be suitable for publication as research
evidence.

**EVAL-R6.** The evaluation framework MUST be runnable via CLI:
```
residual evaluate --workload spec.json --configs single,fixed,dynamic --runs 3
```

**EVAL-R7.** The evaluation MUST emit all observations through
the observation layer. The ComparisonReport MUST be derivable
from the observation log alone.

**EVAL-R8.** The evaluation MUST include a cost analysis:
- API cost (cloud tokens × price per token)
- GPU cost (GPU hours × cloud GPU price or amortized hardware cost)
- Infrastructure cost (compute, storage, network)
- Total cost per accepted task

---

## Implementation Order

| Phase | Spec | Deliverable | Depends On |
|---|---|---|---|
| 1 | SPEC-M2 (Worker Contract) | Contract + enforcement | None |
| 2 | SPEC-M3 (Evidence Bus) | Receipt system | M2 |
| 3 | SPEC-M4 Part 1 (Integrator) | Deterministic merge | M3 |
| 4 | SPEC-M4 Part 2 (Scheduler) | Intelligence layer | M4 Part 1 |
| 5 | SPEC-EVAL-001 (Evaluation) | Measurement framework | M4 Part 2 |

**Critical path:** M2 → M3 → M4 → EVAL. Each builds on the
previous. The evaluation framework is the proof that the
architecture delivers on its claims.
