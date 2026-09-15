# Architecture invariants: executable coverage and remaining obligations

Status is intentionally scoped to this lane. A test name is not proof that all
possible executions preserve an invariant. No missing invariant is represented
by a vacuous passing test.

| ID | Invariant | Current executable evidence | Remaining obligation |
|---|---|---|---|
| INV-01 | UNKNOWN is not PASS | `test_only_exact_pass_can_authorize_integration`; unavailable namespace test proves no process launch | Cross-component propagation to M5/recovery is not checked by this suite |
| INV-02 | Accepted tree equals verified tree | Generated real Git integrations compare receipt commit tree, exact paths and bytes; signed fixture receipts explicitly identify development evidence | Isolated verifier transient mutation/remount attacks not executed on this host; not fully established |
| INV-03 | Worker text cannot authorize capabilities | **No executable check in this lane** | Inject capability requests via worker stdout, tool output, artifact bodies, forged policy objects and receipts at the Station boundary |
| INV-04 | Providers cannot bypass Station policy | **No executable check in this lane** | Exercise each engine adapter and fallback against one restrictive contract; require original policy identity and denial evidence |
| INV-05 | M5 cannot mutate M4 evidence | **No executable check in this lane** | Multi-iteration test against stable M5/M4 APIs and content-addressed evidence, including rejected iterations |
| INV-06 | Metrics cannot create authoritative state | **No executable check in this lane** | Forge/replay metric samples; assert accepted head, leases, policy and receipts unchanged |
| INV-07 | Retry cannot silently change identity | Receipt metadata mutation without a new bound hash is rejected | Retry orchestration and identity transition semantics **not checked here**; a valid new signature alone does not prove correct retry policy |
| INV-08 | Replay cannot create a second acceptance | **No executable check in this lane** | Replay final receipts across process restart with a durable uniqueness/fencing oracle; distinguish idempotent same-tree computation from duplicate acceptance |
| INV-09 | Invalid paths cannot escape the artifact boundary | Canonical path properties; deterministic leaf-link swap with external sentinel unchanged | Parent relocation, concurrent inode substitution during snapshot, filesystem-specific races and durable crash boundaries remain separate gates |
| INV-10 | Execution failure is not verifier correctness evidence | `_verification_available` tests exclude timeout, output limit, signal and launch failure | Whole-pipeline aggregation must retain these exclusions |
| INV-11 | Receipt serialization preserves bound identity | JSON round-trip, mapping-order invariance and retained-hash tamper rejection | Verifier input schema strictness has reproduced gap TRUST-003 |
| INV-12 | Scheduler preserves frozen plan and configured bounds | Generated resize sequences retain original plan hash, bounded capacity and measurement references | NaN policy threshold rejected only by strict expected-failure test; distributed ownership and authoritative state transitions not covered |

Release claims must reference the completed evidence row and retain its stated
scope. Required unknown or unimplemented rows cannot be silently excluded from
a trust qualification denominator.
