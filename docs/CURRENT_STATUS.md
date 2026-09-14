# RESIDUAL current status

_Last updated: 2026-09-14 against `main` at `5b89be1014de5e648f76a2bb8ada920871719f03`._

This page is the human-readable current-state summary for RESIDUAL. Historical roadmap documents and generated implementation tables may lag active integration work; when they disagree with this page, follow the code, tests, open qualification issues, and the machine-readable evidence produced by the current tree.

## Executive summary

RESIDUAL has evolved from a verification-oriented agent harness into an evidence-first reliability and control plane for heterogeneous AI computation. The platform now spans requirement compilation, bounded execution, evidence/receipt handling, deterministic integration, cluster execution, lifecycle recovery, evaluation, observability, crypto/hardening, and operator-facing surfaces.

The central systems hypothesis remains:

> AI reliability does not necessarily require making individual models reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

The repository contains substantial implementation and development evidence for the mechanisms required to test that hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing are covered by the existing test corpus. |
| Command Station | Implemented research/operations surface | Self-hosted run control, model/provider management, observations, HITL hooks, evidence download and operational UI are present. Deployment-specific production readiness still depends on the environment. |
| Factory M2 — worker contract/runtime | Implemented | Real `WorkerContract`, bounded worker runtime, isolated worktrees, journaled observations, host-owned termination and sandbox enforcement exist under `residual/factory/`. Development fault-containment work has exercised real OS boundaries. |
| Factory M3 — evidence bus/receipts | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and signature/integrity checks exist. Trust is enforced at the trusted consumption/admission boundary, not merely because bytes were stored. |
| Factory M4 — deterministic integration/scheduler | Implemented but **not yet fully qualified for live claims** | Deterministic integration and scheduler code exist. Issue #63 tracks remaining accepted-tree binding, filesystem/link safety, verifier-execution isolation, and missing-Git-evidence semantics that must be closed before treating current M4 as a fully hardened trust boundary. |
| Evaluation | Implemented | `residual/eval/` contains hash-locked `FrozenWorkload`, repeated-run execution, ablations, reporting, statistics, fault injection and measured Factory evaluation hooks. Live provider/model evidence remains the next research gate. |
| Sandbox / red team | Implemented development surface | Bubblewrap/namespace/rlimit paths plus live containment tests and a receipted red-team corpus are present. cgroup-v2-specific enforcement depends on host capability. |
| Cluster / distributed execution | Implemented development surface | Versioned wire schema, authenticated join/leave, heartbeats, task reassignment, local-first routing and cluster CLI exist. Some optional network transports degrade gracefully when optional dependencies are absent. |
| Orchestration | Implemented | Intent schema, requirement DAG construction, ambiguity detection, deterministic plan hashes, partitioning and HITL approval gating exist. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway, lifecycle glue and deterministic resume/recovery mechanisms exist. |
| Hardening / observability | Implemented development surface | KMS abstraction, encrypted backup/rotation, connector conformance, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O are present. |
| Studio / product surfaces | Implemented development surface | No-build Studio frontend, evidence/requirement/swarm views and onboarding/demo paths exist. Some frontend contracts are intentionally local stubs around protected runtime interfaces. |
| Research / reproducibility | Active | The IEEE-style paper, controlled evaluation framework, fault-containment experiments and claim/evidence discipline are in place. Live R0–R5 measurements are still required for the central empirical claim. |

## Verified integration milestone

The large swarm integration milestone at commit `412b66c35f7c0e1ac479fe60a5b7d33d5510e3af` recorded a merged-tree verifier pass with:

- 1,033 tests plus 166 subtests green;
- verifier v2 green;
- machine-checked ownership protection for M2–M4 paths;
- prior failed verifier attempts retained rather than overwritten.

`main` has advanced substantially beyond that commit. Those results remain valid evidence for that exact tree only; later commits do not automatically inherit them.

## Current qualification blockers

### 1. M4 trust-boundary hardening — issue #63

Before live qualification or paper-facing claims depend on current M4, close the following:

1. **Accepted-tree binding:** verify and accept the same artifact tree, or explicitly authorize and re-verify any transformation.
2. **Filesystem/link safety:** use non-following, descriptor-relative access with explicit regular-file/link policies and race-resistant handling.
3. **Verifier execution isolation:** candidate-dependent project verification must run under a bounded verification execution boundary instead of inheriting unrestricted host authority.
4. **Git evidence semantics:** distinguish proven absence from unavailable/corrupt/incomparable Git evidence; missing evidence must remain `UNKNOWN`/error, not silently become absence.

### 2. Traceability reconciliation — issue #48

`implementation-status.yaml` and the generated `docs/status/IMPLEMENTATION_STATUS.md` still contain pre-merge entries marking M2, M3, M4 and EVAL as `not_started`. That is stale relative to the current tree. Do not use those four entries as current-state evidence until #48 is reconciled and the generated status document is rebuilt from the corrected manifest.

### 3. Clean-install qualification

A hardened clean-install qualification stack was developed with isolated wheel installation, `pip check`, `python -I`, installed CLI smoke tests, asset checks, Python 3.11/3.12/3.13 coverage and retained artifacts. Its branch validation also exposed two timing-sensitive Factory OS tests that failed once and passed unchanged on rerun. Treat that as unresolved reproducibility evidence until the race/flakiness source is classified rather than hiding it behind retries.

## Research status

### What is supported today

- The architecture cleanly separates generation authority from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms rather than paper-only abstractions.
- Controlled fault-containment work has exercised M2, M3 and M4 boundaries in development fixtures.
- The repository contains an evaluation framework capable of preserving raw observations and recomputing paper-facing metrics.

### What is not yet supported

The project does not yet claim, for live heterogeneous models, that:

- `P(correct | accepted)` is materially greater than raw worker correctness under matched model capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax in cost/latency/throughput;
- lower-cost or weaker workers can be substituted without unacceptable verifier false-acceptance risk;
- 24-hour, 72-hour or 30-day production soak targets have been satisfied.

## Next gates

The recommended order is:

1. Close #63 and requalify the exact current M4 tree.
2. Close #48 and regenerate the implementation-status documentation.
3. Classify and fix the timing-sensitive Factory OS reproducibility failures.
4. Freeze the live evaluation protocol and workload before seeing model results.
5. Run one fixed live model across R0–R5 configurations to measure `P(X)`, `P(A)`, `P(X|A)`, AER, ASSR, latency, throughput and cost.
6. Run model-degradation and heterogeneous-routing studies.
7. Run fault campaigns under live execution.
8. Progress through 24-hour → 72-hour → 30-day soak only after shorter qualification gates are clean.
9. Update the paper from retained artifacts only.

## Documentation authority

Use the following order when determining current truth:

1. exact code at the commit being discussed;
2. tests, verifier output and retained machine-readable artifacts for that exact commit;
3. open qualification/security issues that narrow claims;
4. this current-status document;
5. generated implementation-status/roadmap summaries once they are reconciled;
6. historical specs and snapshots for design intent, not current implementation claims.

RESIDUAL's strongest claim is architectural until the live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.
