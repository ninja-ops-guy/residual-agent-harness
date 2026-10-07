# M4 adaptive scheduler

This stage implements the scheduler-intelligence half of SPEC-M4 on top of the receipt-backed Ready DAG and deterministic integrator. Scheduler decisions are host-owned, deterministic, bounded by explicit capacity/policy objects, and emitted as observations.

## Engine and node selection

`M4AdaptiveScheduler.select_engine()` evaluates only healthy nodes whose node capability and registered `VerifiedComputeMarket` engine capability both satisfy the task. Nodes with no remaining slots are unavailable.

Selection order is deterministic:

1. capability and policy eligibility;
2. local node before cloud when capability is equal;
3. lower market `cost_per_task`;
4. lower market latency;
5. lower node utilization;
6. engine ID and node ID as stable tie-breakers.

Cloud is selected when local capability is absent or all capable local slots are exhausted. Every placement emits `M4EngineSelected` with the task, capability, engine, node, locality, cost, and reason.

## Continuous bottleneck measurements

`measure()` binds measurements to an exact `ReadyDagSnapshot` and records:

- worker utilization = active workers / total workers;
- blocked task ratio = blocked / remaining tasks;
- verification queue depth;
- integration conflict rate = conflicts / integration attempts;
- independent/ready task count and blocked task count.

The measurement is content-addressed by `measurement_hash` and emitted as `M4SchedulerMeasurements`. The caller invokes this after scheduling/verification/integration transitions; there is no hidden background thread.

## Bounded resize policy

`SchedulerPolicy` makes the otherwise qualitative `>>` requirement explicit through a configurable `imbalance_ratio` (default 2.0). `resize()` applies the following deterministic rules:

- conflict count above threshold: pause integration and require human attention; no capacity expansion occurs in that decision;
- verification queue above threshold: add bounded verifier capacity;
- independent tasks dominate blocked tasks by the imbalance ratio: add bounded worker capacity;
- blocked tasks dominate independent tasks by the imbalance ratio: release bounded worker capacity.

Capacity can never exceed `SchedulerCapacity` min/max bounds. Every resize emits `M4SchedulerResize`; conflict pauses emit `M4SchedulerPaused`.

## Structural re-planning

When a task transitively blocks at least 10 downstream tasks and its failure count reaches at least 3, `structural_replan()` creates a new `ExecutionPlan` proposal in which the blocker is replaced by two or more deterministic subtasks. Downstream dependencies are rewired to require all replacement subtasks.

The currently approved plan is never edited. The proposal binds the source plan hash and replacement plan hash and emits `M4StructuralReplan`. The replacement plan must pass through the normal approval/freeze boundary before execution.

This means re-planning is automatic as a proposal, but execution authorization is not automatic.

## Requirement mapping

- M4-R8: `ReceiptBackedM4.ready_dag()` estimates independence from the dependency graph.
- M4-R9: capability/cost/locality/capacity engine-node selection.
- M4-R10: explicit continuous measurement snapshots for all required bottlenecks.
- M4-R11: bounded worker/verifier resize and conflict pause rules.
- M4-R12: deterministic structural decomposition proposal at 10+ downstream / 3+ failures.
- M4-R13: engine selection, measurements, resizing, pause, and re-plan decisions are all observed with their reasoning.

Together with `M4-INTEGRATION.md`, this completes the implemented M4 architecture. The next proof boundary is SPEC-EVAL-001: comparing single-agent, fixed-swarm, and dynamic-swarm execution on the same frozen workload using publication-grade signed evidence.
