# M4 deterministic integration and scheduler

This branch stacks on M3 and implements the first headless M4 integration/scheduling slice from `M2_M3_M4_SPECS.md`.

## Deterministic integration

`DeterministicIntegrator` accepts only locally consumable M3 receipts. All receipts in one integration must bind the same `ExecutionPlan.graph_hash` and base Git commit. Receipt application order is a deterministic topological sort with receipt-hash tie breaking.

For overlapping paths, identical content is deduplicated. For UTF-8 files, one candidate is accepted as a strict superset only when its normalized edit set strictly contains every other candidate's edit set. Otherwise the path becomes an `IntegrationConflict`; no LLM or heuristic merge is permitted.

A true conflict returns `CONFLICT` until the caller supplies a `HumanResolution`. The resulting IntegrationReceipt binds the resolved content SHA-256, approver identity, and decision ID. This is the HITL provenance record for that conflict.

After materialization into a detached integration worktree, configured project verification commands run. Any FAIL or UNKNOWN blocks issuance. The implementation then performs the specification's binary-search narrowing over receipt prefixes and returns the first failing prefix receipt as the revision candidate. This is intentionally diagnostic rather than proof of single-cause failure when interactions are non-monotonic.

Successful integration emits a deterministic candidate Git tree and commit. Commit author, committer, date, message and parent are canonicalized so the same base and ordered receipt set produce the same commit ID. The final `IntegrationReceipt` is Ed25519-signed under a domain separate from WorkerReceipts and binds plan hash, base, all ordered input receipts, output tree/commit, verification results, HITL/automatic resolutions and signer identity.

## Scheduler

`FactoryScheduler` derives the ready frontier strictly from the approved `ExecutionPlan` DAG. It exposes independence fraction, deterministic engine/node selection, bottleneck snapshots, resize decisions and the structural-replan trigger.

Engine routing is fail-closed and deterministic: filter to capable/available engines, prefer local locality, then cost rank, engine name and node name. Scheduler decisions emit an observation containing the chosen action and reasoning.

Resize behavior follows the spec thresholds for independent-vs-blocked work, verification queue pressure and integration conflict pressure. Structural replanning does **not** mutate the frozen plan: when a task has failed at least three times and blocks at least ten downstream tasks, the scheduler emits `replan_required`; a new plan must return through the M1 compiler/approval boundary.

## Deliberate boundaries

- No automatic conflict resolution by an LLM.
- No mutation of an approved `ExecutionPlan`.
- No claim that prefix binary search identifies every possible interacting multi-receipt failure.
- No cluster protocol or EVAL comparison framework yet.
- This is still a headless platform runtime; the IDE remains deferred.
