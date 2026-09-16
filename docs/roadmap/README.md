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

Several integration candidates have now been refreshed directly onto `main@3a41dc1e...`. Their CI is candidate-specific; none of it becomes accepted-main evidence merely because the branch is green.

The current sequence is:

1. **Resolve the protected M4 test-race gate.** PR #139 head `2d885527...` isolates the `/proc/<pid>/status` observation-race repair in protected `tests/test_factory_m4_safety.py`. Capable-runner M4 run `35111486331` is **PASS**, while Factory ownership and dependent workflows **FAIL closed** because the protected-byte baseline still pins the previous blob. Obtain genuinely independent exact-head review first; if accepted, deliberately advance the ownership baseline and requalify. Do not change the pin merely to make CI green.
2. **Requalify the real-provider adapter lane after #139.** PR #134 is now based directly on current main at head `5006d441...`, but its first exact-head Command Station run `35109573754` remains **FAIL** because of the protected test race. Browser-mailbox tests passed in that failing job, but the full workflow is not PASS. After the protected repair is accepted/integrated, refresh/requalify #134 and only then obtain fresh real-provider iPhone evidence.
3. **Review the focused browser-acceptance synchronization repair before requalifying #89.** PR #140 head `36c59627...` changes only the browser acceptance harness: it preserves active-mission control-lock assertions, adds bounded waiting for the separate post-run unlock transition, and leaves production Mission Control/WebVM/onboarding/provider behavior unchanged. All eight observed exact-head workflows are **PASS**, including Pages/WebVM run `35122316061` and Browser VM Demo CI run `35122316013`; no submitted review is recorded. The retained PR #89 Pages/WebVM failure in run `35112465799` remains authoritative and is not rewritten by #140. Require genuinely independent exact-head review before integration, then refresh/requalify #89 rather than treating #140's green CI as qualification of #89 itself.
4. **Obtain independent acceptance for the current-main runtime/DSM candidate.** PR #118 head `e0f042c6...` has all seven observed exact-head workflows **PASS**, including Pages/WebVM. Retained first-attempt failures remain in the record. Cross-process/multi-host serialization, production process wiring, host-loss recovery, release/recovery and elapsed soak remain separate non-claims.
5. **Obtain independent acceptance for release preparation.** PR #115 head `f1862e15...` has all seven observed exact-head workflows **PASS**, including Release preparation procedures. Its blank-VM/recovery fixtures and two-simulated-day rehearsal remain procedure/simulation evidence only, not true bare-OS, production HTTPS, actual host-loss or elapsed-soak qualification.
6. **Obtain independent acceptance for core soak-state persistence.** PR #131 head `1c416970...` has all seven observed exact-head workflows **PASS**, including Pages/WebVM. Its scope remains local resumable-state persistence hardening; it does not create elapsed 24h/72h/30-day soak evidence.
7. **Obtain independent acceptance for economics/observability.** PR #93 head `17189262...` has all eight applicable workflows **PASS**, including Economics and observability qualification and Pages/WebVM. Retained/generated results remain development-fixture evidence; they do not establish live SLOs, real-model economics, production reliability, confirmatory research results or release readiness.
8. **Continue the WebVM reliability diagnosis below Python `time.sleep()`.** Issues #120 and #126 remain open. PR #133 now shows a process-local Python positive-duration sleep failure at call 273 that resets or is avoided by fresh process creation. On exact diagnostic head `3bca5a7...`, direct libc `clock_nanosleep` relative/absolute and `nanosleep` each **PASS** 300 iterations while Python `time.sleep(0.05)` still **FAILS at call 273**. Raw legacy i386 `clock_nanosleep` relative/absolute **PASS**, while the raw time64 relative/absolute syscall probes are **UNSUPPORTED** with `ENOSYS`, not call-count failures. This narrows the investigation toward CPython/Python sleep plus WebVM i386 ABI/fallback behavior without proving time64 unavailability as root cause. Inspect CPython/glibc fallback and ABI handling around `ENOSYS`, repeat sequential fresh-process resets, and compare an alternate/minimal WebVM runtime while keeping the lower mechanism and relationship to the historical corruption family `UNKNOWN` until proven.
9. **Execute broader release/recovery qualification.** Exercise blank-environment setup, actual recovery and retained-evidence procedures without converting rehearsal or simulation evidence into release PASS.
10. **Freeze the live evaluation protocol and selected evidence path.** Lock workload, task mapping, run identity, model/configuration, verifier policy/boundary, scheduler/topology evidence, metrics and analysis before observing confirmatory model results.
11. **Run R0–R5 with one fixed live model.** Measure raw correctness, acceptance coverage, accepted correctness, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency and throughput.
12. **Run model-degradation + heterogeneous-routing studies.** Test whether cheaper/weaker workers can contribute safely under the same acceptance boundary.
13. **Run live fault campaigns and staged soak tests.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
14. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md) — earlier ownership/delegation model
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md) — shared interface constraints
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md) — corrections to earlier uploaded drafts
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md) — v0.4 receipt/registry foundation
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md) — binding decisions from earlier integration phases

These documents are still useful for lineage, but they do not override current code, exact-commit evidence, open qualification issues, or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
