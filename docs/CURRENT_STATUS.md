# RESIDUAL current status

_Reviewed baseline: 2026-09-15 at `a8082109e01aff9eda72030b837103c09d1393d3`. This is a dated snapshot, not a claim that later PRs inherit these results._

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
| Factory M4 — deterministic integration/scheduler | Implemented but **not yet fully qualified for live claims** | Hardening from closed issue #63 landed via #81. Live qualification on a namespace-capable runner remains PR #88's gate; a skipped isolation test is not containment evidence. |
| Evaluation | Implemented apparatus, unqualified live experiment | `residual/eval_frozen/` contains the frozen R0–R5 apparatus. PR #103 rebuilt the binding intended by closed PR #71 with negative tests for replay, topology, task mapping and verifier qualification. Passing those tests does not establish live provider/model results or independently authenticate its prerequisite reports. |
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

### 1. Required enforcement and exact-tree integration

Workflow activation (#101) has landed, but the reviewed `main` branch was unprotected and its repository ruleset list was empty. An active workflow can report failure without preventing a merge. A maintainer must require the appropriate checks and approvals; see the [integration handoff](status/INTEGRATION_HANDOFF.md). Independently submitted tracks still need disposition and validation against their eventual combined tree.

### 2. M4 live qualification

The accepted-tree, filesystem/link, isolation and Git-evidence code-hardening review in closed issue #63 is historical, not an open issue to close again. PR #88 remains the capable-runner qualification lane. Preserve `UNKNOWN`, infrastructure errors and skipped namespace tests as evidence gaps; none may count as a passed trust-boundary qualification.

### 3. Runtime reproducibility

PR #96 merged termination provenance and a repetition matrix, but the ordinary Command Station Python 3.13 job at this baseline still failed `test_ptrace_is_kernel_killed`: expected SIGSYS (`-31`), observed SIGKILL (`-9`). Run `34927698993`, attempt `1`, job `104249155773` retained 895 tests, one failure and 21 skips. The cause is **unclassified**. A later passing run would not erase this failure. The matrix's raw-file/audit pair does not exercise this ptrace selector.

The supplementary diagnostic runner retains per-test outcomes and returned Factory fixture termination records in the ordinary CI runs. It changes neither runtime code nor assertions, performs no retries, and cannot recover records for calls that never return or bypass `Fixture.run_source`. See the handoff for those limits and the retained-run format.

### 4. Measured binding and experimental qualification

PR #103 replaced the path intended by closed PR #71. Its acceptance-binding workflow now has an active location under `.github/workflows/`; branch enforcement is still a separate setting. These negative/contract tests are not live R0–R5 measurements. Review the [binding's explicit trust limits](measured-eval-binding.md): prerequisite inputs are unauthenticated, timestamps are operator-asserted, and signature-only verification does not establish freshness without the retained chain.

The live protocol and corpus still need freezing and execution under the [live evaluation gate](evaluation.md#live-evaluation-gate). No new empirical reliability, cost or throughput values are claimed here.

### 5. Release and soak evidence

Clean-install tooling (#100) and the baseline's clean-install workflow are present/passing. That does not establish a blank-VM release-candidate run or completed 24-hour, 72-hour or 30-day live soak. Retain environment, exact revision and every failed attempt for these separate lanes.

### Traceability scope

Implementation manifest: M2=implemented; M3=implemented; M4=implemented; EVAL=implemented.

The basic reconciliation in closed issue #48 is historical. PR #94's broader family coverage and remaining manifest-note reconciliation are separate work; this change does not replace its scope or change the protected checker. `scripts/check_current_status.py` checks the two active summaries against the local manifest and explicit closed-reference wording. It is intentionally not an exhaustive natural-language or live-GitHub consistency proof.

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

1. Require active checks on `main`, then integrate submitted tracks against exact head/base/tree revisions.
2. Obtain namespace-capable M4 qualification while the corpus acquisition lane proceeds independently.
3. Classify the retained signal mismatch and fix its cause through a separately reviewed runtime change if needed.
4. Qualify the #103 measured-evidence path and retain the prerequisite reports, identity chain and signed artifacts.
5. Freeze the live evaluation protocol, selected evidence path and workload before seeing model results.
6. Run one fixed live model across R0–R5 configurations to measure `P(X)`, `P(A)`, `P(X|A)`, AER, ASSR, latency, throughput and cost.
7. Run model-degradation and heterogeneous-routing studies.
8. Run fault campaigns under live execution.
9. Progress through 24-hour → 72-hour → 30-day soak only after shorter qualification gates are clean.
10. Update the paper from retained artifacts only.

## Documentation authority

Use the following order when determining current truth:

1. exact code at the commit being discussed;
2. tests, verifier output and retained machine-readable artifacts for that exact commit;
3. open qualification/security issues that narrow claims;
4. this current-status document;
5. generated implementation-status/roadmap summaries once they are reconciled;
6. historical specs and snapshots for design intent, not current implementation claims.

RESIDUAL's strongest claim is architectural until the live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.
