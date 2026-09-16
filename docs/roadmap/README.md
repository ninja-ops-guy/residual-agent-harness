# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and should be treated as historical input unless a newer reconciliation document says otherwise. Checkmarks in those source documents mean **specified/documented**, not necessarily implemented or qualified on the current tree.

The project has moved well beyond the v0.3/v0.4 Command Station baseline. Current `main` contains the core harness, Command Station, Factory M2/M3/M4 implementation, evaluation infrastructure, sandbox/red-team tooling, cluster execution, orchestration, lifecycle/gateway controls, crypto/hardening, observability, connector conformance, Studio/product surfaces and research/reproducibility machinery.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented research/operations surface; deployment-specific production qualification still applies |
| Factory M2 worker contracts/runtime | Implemented under `residual/factory/`; real OS-boundary development tests exist |
| Factory M3 evidence bus/Station receipts | Implemented; trusted consumption/admission is the authority boundary |
| Factory M4 deterministic integration/scheduler | Implemented and current-main capable-runner qualified on `3a41dc1e...` by run `35101404956`. The claim is scoped to the named runner/environment and is not every-host or production qualification. |
| Mission Control/WebVM lifecycle | PR #136 integrated on `3a41dc1e...`; first post-merge generated + published desktop/narrow acceptance **PASS** on attempt 1 in run `35101404981`. Long-run reliability, root cause and live-provider quality remain open. |
| Frozen evaluation framework | Implemented under `residual/eval/`: hash-locked workload, repeated runs, ablations, stats/reporting, fault injection and Factory measurement hooks |
| Sandbox / red-team | Implemented development surface; host capability determines whether specific kernel isolation paths can be qualified |
| Cluster / distributed execution | Implemented development surface with authenticated membership, heartbeat/reassignment and local-first routing |
| Orchestration | Implemented intent schema, requirement DAG, ambiguity detection, partitioning, deterministic plan hash and HITL approval gate |
| Lifecycle / side-effect gateway | Implemented deny-by-default gateway and deterministic resume/recovery mechanisms |
| Crypto / conformance / SLO / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Studio/product UI | Implemented development surface; some UI contract fixtures remain local stubs around protected runtime APIs |
| Research paper + evidence program | Active; mechanism evidence exists, but live R0–R5 results are still required for the central reliability hypothesis |

## Important documentation caveat

Issue #48 is closed. `implementation-status.yaml` records M2, M3, M4 and EVAL as implemented, and `docs/status/IMPLEMENTATION_STATUS.md` is generated from that reconciled manifest. Read those implementation statuses together with exact-tree qualification evidence: implementation is not the same thing as production or live-research qualification.

Issue #63 is also closed. Its accepted-tree binding, filesystem/link-safety, verifier-isolation and Git-evidence implementation defects are no longer the active M4 blocker. Historical namespace-capability failures remain `UNKNOWN`/`BLOCKED` for hosts that cannot execute the required boundary.

## Current build order

PR #136's lifecycle integration and first merged-revision browser release gate are complete as exact-revision **PASS** evidence. The retained review record, however, does not contain the genuinely independent pre-merge acceptance required by that PR's own checklist; the final owner-account audit explicitly stated it did not satisfy that gate. Do not rewrite the merge or post-merge PASS as independent review evidence.

The current sequence is:

1. **Refresh and requalify the real-provider adapter lane.** PR #134 remains open on an older base. Rebase/refresh it onto current `main@3a41dc1e...`, rerun exact-head provider/mailbox tests, full CI, generated Pages desktop+narrow proof and production desktop+narrow proof, then obtain fresh real-provider iPhone evidence. No live-provider quality PASS exists yet.
2. **Quantify WebVM reliability.** Issues #120 and #126 remain open. The historical corruption root cause remains `UNKNOWN`, and one first-attempt release PASS does not establish a production recurrence rate. Retain every failed attempt and run a defined repeated-run campaign.
3. **Refresh the runtime/DSM candidate.** PR #118 head `334527da...` had its applicable exact-head workflows **PASS** on prior `main@f1e62936...`, with first-attempt failures retained. Since main advanced with #136, refresh/rebase it onto `3a41dc1e...`, rerun the required workflow set and obtain genuinely independent technical acceptance before integration. Component-level green CI does not establish production process wiring, multi-host consensus, host-loss recovery, release/recovery or elapsed soak.
4. **Refresh the core soak-state candidate.** PR #131 head `368f3085...` had all seven applicable exact-head workflows **PASS** on the prior base. Refresh/rebase, requalify and obtain independent acceptance. Its scope remains local resumable-state persistence hardening; it does not create elapsed 24h/72h/30-day soak evidence.
5. **Refresh and finish release-preparation qualification.** PR #115 head `b1ffbb48...` was already incompletely qualified on the prior base because controller/provider run `35087653566` was **CANCELLED**. Refresh onto current main and require the full exact-head workflow set to finish PASS plus independent technical acceptance. True bare-OS install, production HTTPS release-host, host-loss recovery and elapsed soak remain separate gates.
6. **Execute broader release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures without converting rehearsal or simulation evidence into release PASS.
7. **Freeze the live evaluation protocol and selected evidence path.** Lock workload, task mapping, run identity, model/configuration, verifier policy/boundary, scheduler/topology evidence, metrics and analysis before observing confirmatory model results.
8. **Run R0–R5 with one fixed live model.** Measure raw correctness, acceptance coverage, accepted correctness, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency and throughput.
9. **Run model-degradation + heterogeneous-routing studies.** Test whether cheaper/weaker workers can contribute safely under the same acceptance boundary.
10. **Run live fault campaigns and staged soak tests.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
11. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md) — earlier ownership/delegation model
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md) — shared interface constraints
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md) — corrections to earlier uploaded drafts
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md) — v0.4 receipt/registry foundation
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md) — binding decisions from earlier integration phases

These documents are still useful for lineage, but they do not override current code, exact-commit evidence, open qualification issues, or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
