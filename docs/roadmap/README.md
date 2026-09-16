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
| Factory M4 deterministic integration/scheduler | Implemented and current-main capable-runner qualified on `f1e62936...` by run `35046857256`: all prerequisite probes, actual `linux-userns-isolated-v1` execution, and a zero-skip 142-case + 84-subtest M4 suite passed on the named Ubuntu 22.04 / Python 3.12 environment. This is not every-host or production qualification. |
| Frozen evaluation framework | Implemented under `residual/eval/`: hash-locked workload, repeated runs, ablations, stats/reporting, fault injection and Factory measurement hooks |
| Sandbox / red-team | Implemented development surface; host capability determines whether specific kernel isolation paths can be qualified |
| Cluster / distributed execution | Implemented development surface with authenticated membership, heartbeat/reassignment and local-first routing |
| Orchestration | Implemented intent schema, requirement DAG, ambiguity detection, partitioning, deterministic plan hash and HITL approval gate |
| Lifecycle / side-effect gateway | Implemented deny-by-default gateway and deterministic resume/recovery mechanisms |
| Crypto / conformance / SLO / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Studio/product UI | Implemented development surface; some UI contract fixtures remain local stubs around protected runtime APIs |
| Research paper + evidence program | Active; mechanism evidence exists, but live R0–R5 results are still required for the central reliability hypothesis |

## Important documentation caveat

Issue #48 is closed. `implementation-status.yaml` now records M2, M3, M4 and EVAL as implemented, and `docs/status/IMPLEMENTATION_STATUS.md` is generated from that reconciled manifest. Read those implementation statuses together with exact-tree qualification evidence: implementation is not the same thing as production or live-research qualification.

Issue #63 is also closed. Its accepted-tree binding, filesystem/link-safety, verifier-isolation and Git-evidence implementation defects are no longer the active M4 blocker. Historical namespace-capability failures remain `UNKNOWN`/`BLOCKED` for hosts that cannot execute the required boundary.

## Current build order

The old #63/#48 closure sequence is complete. The current sequence is:

1. **Repair and requalify the WebVM lifecycle candidate.** PR #136 live head `1eaca5a2...` is a retained qualification **FAIL**. Its earlier FIFO/`mkfifo` `ENOSYS` failure remains historical evidence; the current Pages/WebVM run `35088995295` reaches guest attach, real demo verification and warm reload, then rejects `/data/residual-worker.control` as unsafe. Controller/provider run `35088995307` also fails. Repair the candidate without weakening mission binding, durable poison/recovery or fail-closed cleanup; then require one exact head with full green CI, desktop+narrow proof and independent technical acceptance.
2. **Independently review the refreshed runtime/DSM candidate.** PR #118 live head `334527da...` is now based on current `main@f1e62936...` and its applicable exact-head workflows are green. Retain the earlier first-attempt failures as evidence; do not convert component-level green CI into production process wiring, multi-host consensus, host-loss recovery, release/recovery or elapsed-soak claims.
3. **Independently review the refreshed core soak-state candidate.** PR #131 live head `368f3085...` is now based on current main and all seven applicable exact-head workflows are green. Its scope is local resumable-state persistence hardening only; the simulator remains non-qualifying for elapsed 24h/72h/30-day soak.
4. **Finish exact-head release-preparation qualification.** PR #115 live head `b1ffbb48...` is now based on current main, so the old “behind main” blocker is cleared. Its current exact-head controller/provider run `35087653566` is `CANCELLED`, however, so the candidate is not fully qualified. Require the complete required workflow set to finish green and obtain independent technical acceptance before integration; true bare-OS install, production HTTPS release-host, host-loss recovery and elapsed soak remain separate gates.
5. **Requalify the provider adapter only after lifecycle stabilization.** Keep PR #134 held until #126/#136 is resolved, then refresh it onto the stable runtime, run exact-head and production browser qualification, and only then request fresh real-provider iPhone evidence.
6. **Quantify WebVM reliability after lifecycle integration.** Keep issue #120 open, retain every failed attempt, and run a defined repeated-run campaign. A successful exact-revision browser run is not a production recurrence rate.
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
