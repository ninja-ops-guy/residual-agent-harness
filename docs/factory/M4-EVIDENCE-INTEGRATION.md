# M4 Evidence Integration Boundary

This layer connects accepted M3 `WorkerReceipt` evidence to M4 scheduler readiness and deterministic integration planning. It deliberately does **not** mutate the project checkout yet.

## Trust boundary

`ReceiptBackedM4` accepts receipt hashes, not worker output paths. Each receipt is reloaded through `EvidenceBus.consumable`, which locally verifies the Station signature, artifact hashes, stale state, and any required stale-receipt approval before M4 can use it.

A receipt must also bind the same `ExecutionPlan.graph_hash` and reference a task present in that plan.

## Ready DAG

`ready_dag(receipt_hashes)` derives scheduler state from two authoritative inputs only:

1. the frozen `ExecutionPlan`; and
2. locally consumable M3 receipts.

Completed tasks come from accepted receipt task IDs. A remaining task is ready only when all `FactoryTask.depends_on` task IDs have accepted receipts. The snapshot records ready, blocked, completed tasks and the current independence fraction. The snapshot is deterministically hashed and can be emitted as `M4SchedulerSnapshot` evidence.

## Integration planning

`integration_plan(receipt_hashes)` first validates that every supplied task dependency is present. It then requires the child receipt's `parent_receipts` to equal the exact receipt hashes corresponding to the task's declared dependencies.

Receipts are ordered deterministically by the task DAG, with lexical task ID ordering as the tie-break for simultaneously ready tasks. Caller input order therefore does not affect the resulting integration-plan hash.

## Overlap policy

This first M4 bridge is intentionally conservative:

- non-overlapping artifact paths are integration eligible;
- repeated identical artifact state for the same path is deduplicated;
- repeated identical deletion is deduplicated;
- different states for the same path are an `IntegrationConflict` and require HITL.

It does not yet claim the M4 strict-subset diff rule. That requires applying receipts against the base Git state and comparing normalized diffs, which belongs in the project-mutation stage rather than being approximated from artifact hashes.

## What this closes

This implements the trust and ordering boundary needed before deterministic project mutation:

`M3 signed receipt -> local verification -> task readiness -> parent binding -> topological order -> overlap detection -> integration-eligible evidence plan`

## What remains

The following M4 requirements remain downstream work:

- deterministic Git application and output commit creation;
- normalized diff subset detection;
- project-wide accumulated verification;
- binary-search attribution of failing receipts;
- signed final `IntegrationReceipt`;
- scheduler topology/engine/node decisions beyond readiness measurement;
- continuous bottleneck measurements and structural re-planning.

Those stages should consume `EvidenceIntegrationPlan` rather than reaching back into raw Factory worktrees or worker output.
