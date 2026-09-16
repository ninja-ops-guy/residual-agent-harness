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
| Factory M4 deterministic integration/scheduler | Implemented, but **current live qualification is blocked by issue #63** until accepted-tree binding, filesystem/link safety, verifier isolation and Git-evidence semantics are closed |
| Frozen evaluation framework | Implemented under `residual/eval/`: hash-locked workload, repeated runs, ablations, stats/reporting, fault injection and Factory measurement hooks |
| Sandbox / red-team | Implemented development surface; host capability determines whether cgroup-v2 enforcement is available |
| Cluster / distributed execution | Implemented development surface with authenticated membership, heartbeat/reassignment and local-first routing |
| Orchestration | Implemented intent schema, requirement DAG, ambiguity detection, partitioning, deterministic plan hash and HITL approval gate |
| Lifecycle / side-effect gateway | Implemented deny-by-default gateway and deterministic resume/recovery mechanisms |
| Crypto / conformance / SLO / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Studio/product UI | Implemented development surface; some UI contract fixtures remain local stubs around protected runtime APIs |
| Research paper + evidence program | Active; mechanism evidence exists, but live R0–R5 results are still required for the central reliability hypothesis |

## Important documentation caveat

`implementation-status.yaml` and the generated `docs/status/IMPLEMENTATION_STATUS.md` still contain pre-merge `not_started` entries for M2, M3, M4 and EVAL. That drift is tracked by **issue #48**. Until #48 is reconciled, use [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md), the actual code/tests, and exact-commit verifier artifacts for current-state claims.

## Current build order

The old build order is complete or superseded. The current sequence is:

1. **Close M4 trust-boundary gaps (#63).** Bind accepted state to the verified tree, harden filesystem writes, isolate candidate-dependent verification, and preserve `UNKNOWN` for missing Git evidence.
2. **Reconcile traceability (#48).** Update M2/M3/M4/EVAL status, regenerate the generated status document, and add drift prevention.
3. **Resolve Factory OS timing nondeterminism.** Determine whether the retained retry-only failures represent runtime races or test flakiness.
4. **Qualify measured-evidence integrity (PR #71 or an explicit alternative).** The reviewed Factory adapter needs fresh run/execution binding, anti-replay across independent repetitions, authenticated run-bound scheduler/topology evidence, an exact workload-to-task mapping, and a qualified verifier policy/boundary. Correct and requalify it, or explicitly exclude it from the live protocol and independently qualify the chosen evidence path under the [live evaluation gate](../evaluation.md#live-evaluation-gate). Closing #63/#48/timing alone does not clear this gate.
5. **Freeze the live evaluation protocol and selected evidence path.** Do not tune workloads/metrics after observing model outcomes.
6. **Run R0–R5 with one fixed live model.** Measure raw correctness, acceptance coverage, accepted correctness, AER/ASSR, cost, latency and throughput.
7. **Run model-degradation + heterogeneous-routing studies.** Test whether cheaper/weaker workers can contribute safely under the same acceptance boundary.
8. **Run live fault campaigns and staged soak tests.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
9. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md) — earlier ownership/delegation model
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md) — shared interface constraints
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md) — corrections to earlier uploaded drafts
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md) — v0.4 receipt/registry foundation
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md) — binding decisions from earlier integration phases

These documents are still useful for lineage, but they do not override current code, exact-commit evidence, open qualification issues, or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
