# R5 phased convergence plan

This plan derives six phases from `R5_DAG.json`. It replaces the backlog's
coarse P0/P1/P2 grouping and removes two dependency cycles: state validation now
precedes hostile-receipt policy, and topology fencing precedes distributed
lookup authority. Each phase is a separate implementation PR series followed
by a separate qualification receipt; no giant R5 merge is permitted.

## R5-P0 — Qualification and evidence foundations

Scope: SC-015 and SC-016. Freeze evidence envelopes, authorization and retention
rules, corpus/fault registries, canonical serialization, deterministic schedule
replay, and negative controls. This phase implements test infrastructure only,
not R5 runtime behavior.

Exit: PG0 verifies two-run reproducibility and the full evidence-tampering
matrix. Rollback is deletion of unconsumed planning/test infrastructure; sealed
test evidence is retained.

## R5-P1 — Protocol and receipt authority

Scope: SC-011 then SC-002. Introduce explicit protocol/feature negotiation
before defining canonical signed receipt v1. Versioning precedes authenticity so
signature semantics and downgrade protection are not retrofitted ambiguously.

Exit: PG1 passes the compatibility and receipt-mutation matrices, including
upgrade and rollback readers. It does not claim concurrent recovery safety.

## R5-P2 — Fenced recovery and explicit reconciliation

Scope: SC-001, SC-003, SC-004. Establish fenced ownership, the explicit
INDETERMINATE state graph, then bounded malformed/cross-bound handling. This
phase owns local concurrency and receipt consumption but not ACK crash durability.

Exit: PG2 composes G01–G04 across every declared crash/takeover boundary with
one receiver effect. Rollback must preserve or quarantine newer states and fence
epochs.

## R5-P3 — Failure durability and operator policy

Scope: SC-005 through SC-008. Qualify crash-during-ACK, corruption, disk and
SQLite errors, then explicit stale-operation disposition. Work is split into at
least four feature PRs and one qualification-only convergence PR.

Exit: PG3 demonstrates safe restart and operator recovery for every fault
corpus. No storage or age condition may imply success, resend, or deletion.

## R5-P4 — Topology, observability, lookup, and lifecycle

Scope: SC-009, SC-010, SC-012, SC-013. First declare supported deployment and
lease topologies; then qualify observability, authority-aware distributed lookup,
and retention/tombstone behavior. Distributed claims are limited to the tested
topology matrix.

Exit: PG4 composes partition, telemetry-loss, lookup, GC, and backup-restore
schedules with stable effect identity and bounded storage. Rollback drains lease
epochs and retains uniqueness proof.

## R5-P5 — Formal claim and release convergence

Scope: SC-014 and SC-017. Refine the executable safety model against one pinned
release tree, consume all prior immutable phase receipts, rerun cross-phase
faults, and publish the exact at-most-once claim boundary.

Exit: PG5 verifies the complete topological closure, model refinement,
counterexample retention, compatibility/rollback matrix, and independent human
review. Eligibility still does not deploy or promote.

## Delivery controls

1. Every phase begins from the accepted predecessor receipt, not an unreviewed
   feature branch.
2. Runtime, qualification harness, and authoritative evidence changes use
   separate PRs and commits.
3. A phase may split further but may not combine with a dependent phase to hide
   an unmet gate.
4. Gate specifications are frozen before corresponding runtime implementation.
5. Counterexamples remain retained when fixes are rerun.
6. R4.1 and its evidence remain immutable and outside all R5 branches.

## Recommended first post-canary implementation phase

Complete R5-P0 first because every later gate depends on deterministic evidence
and fault identities. The first **runtime** implementation phase is R5-P1:
protocol versioning followed by authenticated request-bound receipts. This is
the smallest independently qualifiable slice that establishes authority for all
later ACK and reconciliation claims.

