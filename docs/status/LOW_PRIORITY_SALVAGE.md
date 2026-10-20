# Low-priority roadmap salvage and retirement record

Date: 2026-09-15  
Baseline: `main@7cf45ea8eab675b870502fb76db1b6e63b562e9f`

This record handles the completion tracker's Class C cleanup without reviving obsolete runtime code. It preserves the unique benchmark fixtures and research probes by exact pull-request head and source path, while keeping current `main`, the accepted M4 trust boundary, shared evidence schemas, and the frozen research protocol authoritative.

The machine-readable source of this record is [`low_priority_salvage.v1.json`](low_priority_salvage.v1.json).

## Completed cleanup

The following low-priority proposals were retired without merge:

- **#83** — superseded Pages black-screen/demo path; current demo work has moved on.
- **#57** — superseded alternate Pages publisher; its own PR text says the definitive black-and-green presentation must not be replaced.
- **#10** — OpenClaw governed-engine integration; explicitly post-1.0 unless promoted into a preregistered condition.
- **#1** — original experimental FreeLLMAPI integration; superseded by the newer onboarding/provider lane.
- **#22** — already closed before this lane; superseded by the accepted M4 implementation.

Closing these PRs does not delete their Git history or make their claims current.

## Benchmark salvage

The old benchmark stack is not safe to merge as a stack because it predates the accepted current evaluation/runtime boundaries. Its useful contribution is the set of controlled workload designs:

- **FB001 / #38** — six independent, exactly verifiable synthesis tasks for scheduler/parallelism comparison.
- **FB002 / #46** — a six-task multi-file DAG for dependency-aware concurrency and semantic verification.
- **FB003 / #52** — same-artifact stale-base overlap to measure deterministic rework/conflict pressure.
- **FB004 / #54** — a 16-task TaskFlow mini-service whose success criterion is whole-project completion and exact final Git identity.
- **FB-CORPUS / #56** — corpus sequencing, model-digest continuity, resume/provenance requirements, signed aggregate-manifest intent, and host preflight.
- **#26** — evaluation-contract lineage (FrozenWorkload, single/fixed/dynamic comparison, measured provenance, signed-report intent), not a fixture that should displace the current frozen evaluation implementation.

These definitions are now indexed by exact source head and path. They are **not** declared runnable or qualified on current main. Any future use must re-author the fixture against the then-accepted evaluation and trust boundaries and produce new exact-revision evidence.

## Research-probe salvage

The historical reliability PRs retain useful experimental questions even where their implementations are obsolete:

- **#12 — classic harness:** malformed/truncated replies, abstention, provider failure, worker termination, invalid scope updates, undeclared/oversized evidence requests, and resource exhaustion. Preserve the separation of worker correctness from acceptance and the AER/FAR/FCR/ISR/ASSR measurement intent.
- **#17 — M2:** forbidden tool, forbidden filesystem write, raw filesystem syscall, and wall-clock exhaustion. Preserve the requirement that the intended injection must actually be observed and that containment includes no candidate publication plus process reaping.
- **#20 — M3:** receipt-signature tamper, artifact corruption, receipt-queue mutation, and dependency-receipt mismatch. Preserve the distinction between storage and trusted consumption.
- **#24 — M4:** input-order permutation, missing parent, true overlap conflict, verification failure, invalid human resolution, and integration-receipt tamper. Preserve these as reference-only probe definitions; this cleanup lane does not modify or qualify the protected M4 trust boundary.

None of these preserved definitions are empirical results. A historical PASS remains evidence only for its historical source tree and environment.

## Retirement gate

The remaining legacy benchmark PRs **#26, #38, #46, #52, #54, #56** and historical research PRs **#12, #17, #20, #24** should stay open until this preservation record is accepted on `main` (or their unique content is independently incorporated into the canonical experimental program). After that, they can be closed as historical/superseded without losing the experiment inventory.

This sequencing intentionally avoids closing a source before its unique content has an accepted canonical pointer.

## Non-claims and protected boundary

This cleanup lane:

- changes no `residual/factory/*` runtime implementation;
- changes no M4 trust-boundary file;
- changes no shared evidence schema;
- runs no live model or benchmark;
- produces no release, reliability, security, production, or research qualification;
- does not promote historical fixture output into current evidence;
- does not authorize merging any legacy implementation branch.

The only executable addition in this lane is a structural regression test for the salvage manifest itself.
