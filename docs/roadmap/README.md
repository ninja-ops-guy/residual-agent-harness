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
| Factory M4 deterministic integration/scheduler | Implemented and accepted-main capable-runner qualified on `22a5bae...`: all prerequisite probes, actual `linux-userns-isolated-v1` execution, and a zero-skip 142-case + 84-subtest M4 suite passed on the named Ubuntu 22.04 / Python 3.12 environment. This is not every-host or production qualification. |
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

1. **Review and integrate the refreshed runtime/DSM closure candidate.** PR #118 is based on accepted `main`; require terminal exact-head CI and independent technical acceptance before merge.
2. **Review release preparation, then run release/recovery qualification.** PR #115 is refreshed onto accepted `main`; independently review its implementer evidence and then exercise blank-environment setup, recovery and retained-evidence procedures without broadening fixture claims.
3. **Quantify WebVM reliability.** Keep issue #120 open, retain every failed attempt, and run a defined repeated-run campaign. A successful exact-revision browser run is not a production recurrence rate.
4. **Freeze the live evaluation protocol and selected evidence path.** Lock workload, task mapping, run identity, model/configuration, verifier policy/boundary, scheduler/topology evidence, metrics and analysis before observing confirmatory model results.
5. **Run R0–R5 with one fixed live model.** Measure raw correctness, acceptance coverage, accepted correctness, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency and throughput.
6. **Run model-degradation + heterogeneous-routing studies.** Test whether cheaper/weaker workers can contribute safely under the same acceptance boundary.
7. **Run live fault campaigns and staged soak tests.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
8. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md) — earlier ownership/delegation model
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md) — shared interface constraints
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md) — corrections to earlier uploaded drafts
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md) — v0.4 receipt/registry foundation
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md) — binding decisions from earlier integration phases

These documents are still useful for lineage, but they do not override current code, exact-commit evidence, open qualification issues, or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
