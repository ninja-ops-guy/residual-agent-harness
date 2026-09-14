# SPEC-EVAL-001 comparative evidence

SPEC-EVAL evaluates one frozen workload under `single`, `fixed`, and `dynamic` Factory configurations. The simulator path remains useful for validating the evidence machinery, but simulated runs are never measured production evidence.

## Measured claim boundary

`FrozenWorkload` describes experimental work; it is not authorization. A measured run must be preregistered against explicit Factory authority and must preserve that authority through M3, M4, scheduler, and final report issuance.

The approved measured path is:

1. `ApprovedFactoryRunBinding` preregisters the FrozenWorkload hash, configuration/run index, approval reference, Factory ExecutionPlan hash, allowed attempt IDs, approved worker bounds, and Station identity. The execution callback is zero-argument so benchmark prompt text cannot synthesize WorkerContracts, filesystem/tool scope, verifier policy, or approval policy.
2. The callback returns `AuthoritativeFactoryRunEvidence`: runtime counters and signed M3 `WorkerReceipt` values, an M4 `IntegrationReceipt`, and `FactoryTopologyTrace` built from real `ReadyDagSnapshot`, `SchedulerMeasurements`, and optional scheduler actions.
3. The adapter verifies every measured receipt belongs to the approved ExecutionPlan and attempt set. `accepted_tasks` must equal the passing M3 receipt count.
4. M4 final acceptance must be Station-signed, bind the exact measured M3 receipt set, contain clean accumulated verification PASS results, and explicitly carry `evidence_level=measured`.
5. `development_fixture` IntegrationReceipt v2 values are rejected. A receipt executed through `trusted_fixture_unsandboxed` is rejected even if someone tries to relabel its evidence level. Current trusted-fixture M4 therefore cannot manufacture a measured-live result.
6. Topology is never inferred from attempt or receipt count. `single` must observe one worker, `fixed` must observe its preregistered constant width, and `dynamic` must operate inside a preregistered non-degenerate worker range. Scheduler measurements must bind supplied Ready-DAG snapshot hashes, and scheduler actions must bind supplied measurement hashes.
7. `ApprovedMeasuredFactoryEvaluationRunner` runs the ordinary measured SPEC-EVAL machinery and then signs a provenance envelope containing the signed base comparison report plus, for every experiment cell, hashes of the approval reference, ExecutionPlan, M4 integration plan, M4 final-acceptance receipt, and scheduler topology trace.

This makes the final publication artifact commit cryptographically to the Factory acceptance/topology evidence used to justify the labels `single`, `fixed`, `dynamic`, and `measured`.

## Current M4 limitation

The reviewed M4 safety path intentionally emits `evidence_level=development_fixture` for its operator-authored trusted-fixture verifier. That lane is not an OS filesystem/network sandbox. As a result, this approved evaluation adapter is deliberately fail-closed today for live measured final acceptance. It becomes usable for measured claims only when an independently reviewed M4 execution boundary can legitimately issue a signed `evidence_level=measured` receipt.

Issue #63 therefore remains open. Passing simulator tests, M3 receipt checks, package qualification, or the existence of several workers does not close that boundary.

## Topology semantics

`approved_attempt_ids` are authorization only. They do not encode concurrency or scheduler policy.

- `single`: approved worker bounds must be `(1, 1)` and every scheduler measurement must report one total worker.
- `fixed`: bounds must be `(N, N)` for `N >= 2`; every measurement must report that width and no worker-resize action may occur.
- `dynamic`: bounds must satisfy `min < max`; observed scheduler worker counts and worker-resize actions must remain inside those bounds. Scheduler/Ready-DAG evidence proves the host scheduler participated; attempt count is irrelevant.

This fixes the earlier adapter design that treated one attempt as `single` and two-or-more attempts as `fixed`/`dynamic`. A sequential single-worker run may execute many tasks/attempts, and a fixed swarm width does not equal task count.

## Metrics and controls

The underlying `MeasuredFactoryEvaluationRunner` continues to measure wall clock outside the execution adapter and derives engine/revision controls from cryptographically verified M3 receipts. Every run records elapsed time, accepted tasks/hour, tokens, GPU time, coordination overhead, rework, merge conflicts, verifier rejection rate, final test pass rate, and cost analysis. The same FrozenWorkload, engine/model controls, temperature, and seed requirements still apply.

SPEC-EVAL requires at least three measured runs for each configuration before producing a comparison report.

## Evidence products

The ordinary `SignedComparisonReport` remains the system-metric report. The approved measured runner wraps it in a second Station-signed `residual.eval.approved-factory-comparison.v1` report containing:

- the complete signed base comparison report;
- the FrozenWorkload manifest hash;
- one provenance record for every configuration/run index;
- approval-reference hash;
- Factory ExecutionPlan hash;
- M4 integration-plan hash;
- M4 IntegrationReceipt hash;
- scheduler topology-trace hash.

For measured Factory performance claims, retain and publish the outer approved report together with the referenced M3/M4/scheduler evidence. The base comparison report by itself does not prove authoritative topology or final acceptance.

## Claim discipline

A green simulator run demonstrates the evaluation pipeline, not swarm performance. A green approved-adapter unit test demonstrates fail-closed evidence binding, not that a production OS-isolated M4 verifier exists. Real performance claims require real measured execution, an authoritative measured M4 acceptance receipt, scheduler/runtime topology evidence, unchanged experimental controls, and the signed approved comparison envelope.
