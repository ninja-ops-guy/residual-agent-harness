# RESIDUAL current status

_Triage baseline: 2026-09-15 at `1cf4e46c0ace8e3cdc76147ad4c7dc6480a9fb34`, including merged #106. Branch findings are identified separately in the [PR ledger](status/PR_TRIAGE_2026-09-15.md); later revisions do not inherit qualification automatically._

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
| Factory M4 — deterministic integration/scheduler | Implemented but **not yet fully qualified for live claims** | Hardening from closed issue #63 landed via #81. #109 carries the capable-runner gate after closed #88/#114; its hosted-runner probe is BLOCKED, not containment evidence. |
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

Workflow activation (#101) has landed. The initial snapshot found no protection; a subsequent live settings check on 2026-09-15 confirms `main` is now protected by active ruleset `23436488`, with 12 required checks, strict up-to-date validation, resolved review threads, deletion/force-push restrictions and no configured bypass actors. This is real enforcement progress.

Enforcement is still incomplete: the required approving-review count is **0**, and `current-status` and `measured-eval-binding` are absent from the required-check list. Copilot review-on-push is enabled, but it does not make an independent approval mandatory. A maintainer must complete those settings; see the [integration handoff](status/INTEGRATION_HANDOFF.md). Independently submitted tracks still need disposition and validation against their eventual combined tree. Policy settings are separate from code revisions; the live main observed during this follow-up was `eefee6ac005c93278f483e002e38a768920f0fae`.

### 2. M4 live qualification

The accepted-tree, filesystem/link, isolation and Git-evidence code-hardening review in closed issue #63 is historical. #109 succeeds closed #88/#114 as the M4 prerequisite/zero-skips lane. Its actual execution smoke at `e873dd62` reported UNKNOWN because namespace isolation was unavailable; the prerequisite job correctly failed. Preserve `UNKNOWN`, infrastructure errors and skipped namespace tests as evidence gaps; none may count as a passed trust-boundary qualification.

### 3. Runtime reproducibility

PR #96 merged termination provenance and a repetition matrix. The historical Command Station Python 3.13 job on baseline `a8082109` failed `test_ptrace_is_kernel_killed`: expected SIGSYS (`-31`), observed SIGKILL (`-9`). Run `34927698993`, attempt `1`, job `104249155773` retained 895 tests, one failure and 21 skips. The cause remains **unclassified** by that evidence. Later passing runs do not erase this failure. #108's current repair requires independent review at its final head.

#117 replaces closed #97 and exposes three missing local runtime/DSM guarantees:
process-group tracking, fencing held through authoritative append, and rejection
of reused event IDs with changed payloads. Its focused suite is **3 failed,
60 passed, zero skipped** locally. Those pytest functions are now explicitly
run in its required CI matrix; ordinary unittest discovery did not collect them.

The supplementary diagnostic runner retains per-test outcomes and returned Factory fixture termination records in the ordinary CI runs. It changes neither runtime code nor assertions, performs no retries, and cannot recover records for calls that never return or bypass `Fixture.run_source`. See the handoff for those limits and the retained-run format.

### 4. Measured binding and experimental qualification

PR #103 replaced the path intended by closed PR #71. #106 has merged its active acceptance-binding workflow after all required checks and the binding job passed; making that new check mandatory is still a separate setting. These negative/contract tests are not live R0–R5 measurements. Review the [binding's explicit trust limits](measured-eval-binding.md): prerequisite inputs are unauthenticated, timestamps are operator-asserted, and signature-only verification does not establish freshness without the retained chain.

The live protocol and corpus still need freezing and execution under the [live evaluation gate](evaluation.md#live-evaluation-gate). No new empirical reliability, cost or throughput values are claimed here.

### 5. Release and soak evidence

Clean-install tooling (#100) and the baseline's clean-install workflow are present/passing. That does not establish a blank-VM release-candidate run or completed 24-hour, 72-hour or 30-day live soak. Retain environment, exact revision and every failed attempt for these separate lanes.

#115 adds preparation tooling, but review reproduced accepted truncated evidence
logs and a capped synthetic schedule incorrectly reported COMPLETE. Repair its
integrity/completion checks and label simulated days before using those procedures
as qualification evidence. A synthetic soak rehearsal is not elapsed runtime.

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

The completion target is **Residual 1.0 + Experimental Release 1**. Track all
17 steps, completed prerequisites and the six final acceptance gates in
[COMPLETION_TRACKER.md](status/COMPLETION_TRACKER.md). An unfavorable hypothesis
result does not block completion when the experiment answers the question credibly.

The recommended order is:

1. Require active checks on `main`, then integrate submitted tracks against exact head/base/tree revisions.
2. Obtain namespace-capable M4 qualification while the corpus acquisition lane proceeds independently.
3. Classify the retained signal mismatch and fix its cause through a separately reviewed runtime change if needed.
4. Qualify the #103 measured-evidence path and retain the prerequisite reports, identity chain and signed artifacts.
5. Freeze the live evaluation protocol, selected evidence path and workload before seeing model results.
6. Run one fixed live model across R0–R5 configurations to measure `P(X)`, `P(A)`, `P(X|A)`, AER, ASSR, latency, throughput and cost.
7. Run model-degradation and heterogeneous-routing studies.
8. Run fault campaigns under live execution.
9. Complete the reviewed 24-hour/72-hour elapsed soak ladder. A later 30-day production-maturity run is outside the agreed six-gate 1.0 target.
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
