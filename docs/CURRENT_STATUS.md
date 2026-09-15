# RESIDUAL current status

_Current-state check: 2026-09-15 against merged `main` at `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`._

This page is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests and retained machine-readable evidence remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability and operator-facing surfaces.

The central systems hypothesis remains:

> AI reliability does not necessarily require making individual models reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

The repository contains substantial implementation and development evidence for the mechanisms required to test that hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that the current M4 boundary has completed capable-runner namespace qualification, or that production soak targets have been met.

## What changed on 2026-09-15

Three changes materially advanced the integrated tree:

1. **PR #108 landed on `main` as `0430f2fa2d107fe48d26ae84a3c1550af029cb52`.** It carries the deterministic sandbox-timing and termination repair: lease tri-state semantics, a single wall-clock deadline owner, bounded lease-read contention, pending-reap ownership/recovery, typed timeout outcomes and receipt-v2 compatibility preservation. The merge explicitly retained namespace-dependent skips as **non-qualification** rather than treating them as passes.
2. **PR #122 advanced `main` to `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`.** It hardens the Mission Control real-provider experience with truthful failure categories, selected-model validation, a bounded browser/guest mailbox path, guided authorization state, blocked-build conversation behavior and real-browser acceptance coverage. These product/demo changes do not grant generated artifacts M4 authority.
3. **PR #121 advanced `main` to `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`.** It changes only the protected ownership manifest's provenance metadata: `pinned_at` now names the accepted #108 squash commit `0430f2fa...`; all 38 protected path-to-blob pins are unchanged. The refreshed exact-head review and applicable CI passed before merge. This records accepted source identity and does not add namespace, production, soak or research qualification.

Issue #63 is closed: the accepted-tree, filesystem/link, verifier-isolation and Git-evidence defects that it tracked are no longer the active M4 implementation blocker. Issue #48 is also closed: the implementation-status manifest has been reconciled with the merged Factory/evaluation tree.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing are covered by the repository test corpus. |
| Command Station | Implemented research/operations surface | Self-hosted run control, model/provider management, observations, HITL hooks, evidence download and operational UI are present. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface | Multi-turn artifact conversations, verified parent lineage, isolated preview, browser-local restoration and optional-provider transport exist. PR #122 adds typed provider failures and real-browser acceptance. Issue #120 retains an earlier intermittent guest-runtime import failure; one unchanged rerun passed, so the event is tracked as an operational reliability concern rather than erased. |
| Factory M2 — worker contract/runtime | Implemented | Real `WorkerContract`, bounded worker runtime, isolated worktrees, journaled observations, host-owned termination and sandbox enforcement exist under `residual/factory/`. |
| Factory M3 — evidence bus/receipts | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and signature/integrity checks exist. Trust is enforced at the trusted consumption/admission boundary, not merely because bytes were stored. |
| Factory M4 — deterministic integration/scheduler | Implemented trust-boundary mechanisms; **candidate capable-runner PASS, acceptance pending** | The original #63 implementation gaps are closed and #108's timing/termination repair is merged. PR #109's current-main synthetic candidate completed real namespace probes, actual isolated execution and the selected M4 suite with zero skips on Ubuntu 22.04. That evidence is exact-candidate qualification, not yet accepted-main qualification; independent review and a reproducibly failing Python 3.13 full-matrix check still block integration. |
| Evaluation | Implemented development/research apparatus | Hash-locked workloads, repeated runs, ablations, reporting, statistics, fault injection and measured Factory hooks exist. The measured-evaluation acceptance-binding workflow is a CI mechanism; it is not live research evidence. |
| Sandbox / red team | Implemented development surface | Namespace/rlimit/bubblewrap paths and adversarial tests exist. Host capability determines whether specific kernel isolation paths can actually be qualified. |
| Cluster / distributed execution | Implemented development surface | Versioned wire schema, authenticated join/leave, heartbeats, task reassignment, local-first routing and cluster CLI exist. Distributed/host-loss guarantees remain narrower than single-process fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway, lifecycle glue and deterministic resume/recovery mechanisms exist. Release/recovery qualification remains downstream of the active trust gate. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, connector conformance, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O are present. |
| Research / reproducibility | Active | The working paper, controlled-evaluation framework, claim/evidence discipline and fault-containment tooling are in place. Live R0–R5 measurements and soak remain future evidence gates. |

## Exact-tree CI status at this refresh

For current `main` at `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`, the following metadata-triggered push workflows completed successfully:

- Clean install qualification;
- Measured evaluation acceptance binding;
- Factory ownership gate;
- Command Station checks;
- Controller and provider contracts.

PR #121 did not change the deployed browser surface, so Pages was not rerun for the metadata-only `1a52e9a...` push. The latest deployed application revision remains `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`. Its GitHub Pages/WebVM workflow failed its first live attempt in narrow Chromium after the deployed disk chunk returned HTTP 503 and the guest stalled after attachment. The unchanged rerun then completed successfully on desktop and narrow Chromium. Run [35003867644](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35003867644) retains both outcomes; failed-attempt artifact `10410904479` has ZIP SHA-256 `57ab059987126acbc4baf3b0b4b10bc7f3412fa8c38322c756fbd1b4b13564a5`, and successful-attempt artifact `10411624041` has ZIP SHA-256 `0cbfe28cc0cd1e94d4cde603ad4452b9834a6a6f6f14e41c4ec32565ffc25386`.

The applicable exact-current-main metadata checks are green, and the latest deployed application revision's Pages gate is green after an unchanged rerun, while issue #120 remains open because repeated intermittent failures on the live WebVM surface are a production-reliability concern. The separate Vercel commit status is red because of an account build-rate limit; that is an external deployment-capacity condition, not a repository test pass. None of these outcomes constitutes namespace qualification, production soak, live-provider research evidence or blanket production readiness.

## M4 claim boundary

### Closed implementation work

The implementation defects formerly tracked by issue #63 are closed. The merged M4 path now contains the reviewed mechanisms for:

- verified-tree/accepted-tree binding;
- descriptor-relative/non-following filesystem handling and link/race defenses;
- bounded verifier execution with explicit isolation semantics;
- fail-closed Git evidence semantics where unavailable/incomparable evidence is not silently treated as absence;
- deterministic timeout typing and preserved receipt-v2 signed serialization;
- lease uncertainty distinct from revocation;
- host-owned termination provenance and pending-reap recovery.

PR #108's retained contention work supports its named timing/termination tests under the measured conditions used by that PR. It does not prove arbitrary workloads, elapsed soak or every supported host.

### Still not qualified

Namespace-dependent M4 tests that skip because the host cannot provide the required isolation capability remain **UNKNOWN/BLOCKED for qualification**, not PASS. The earlier PR #109 Ubuntu 24.04 hosted attempt remains retained BLOCKED evidence. A new Ubuntu 22.04 run on synthetic candidate `dd27daa6672bff975e714d735eb05d1a5d8a2a9a`, tree `3924c1de206789d78296fddfaeb7085d24ef5862`, base `1a52e9a...`, produced `PASS`: all namespace probes passed, actual `linux-userns-isolated-v1` execution exited 0 with retained stdout/stderr hashes, and 135 selected test items plus 78 subtests completed with zero failures/errors/skips. Retained artifact `10412223138` has ZIP SHA-256 `94c9d0afeadc9e7535858118528dd52a5f5d3657d4cf77d905dc83f087b41bee` in [run 35008093028](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35008093028).

That PASS is bound to the PR synthetic candidate, not automatically to merged `main`. PR #109 still needs independent review and deliberate integration. Its broader Controller/provider workflow failed twice on Python 3.13.15 in protected lifecycle test `test_missing_cli_input_returns_sanitized_blocked_json_for_both_run_aliases` (`--trace-id` subtest): 1 error with 1,005 passes and 22 namespace-dependent skips, while Python 3.11/3.12 and the separate zero-skip M4 job completed their test steps. The named test passes alone on a matching Python 3.13.15 exact-candidate checkout; deferred SQLite `ResourceWarning` pollution in the full suite is the leading order/GC-sensitive hypothesis, not yet a proven root cause. This repository/test-runtime blocker is not waived by the M4 PASS. Ubuntu 22.04 is a temporary compatibility target and needs a migration path; passing #109 does not complete release, recovery, soak or research gates.

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is now the machine-readable implementation manifest and includes implemented M2/M3/M4/EVAL families rather than the previous stale `not_started` rows. Its generated status document is derived from that manifest.

This reconciliation fixes implementation traceability; it does **not** promote implementation into live qualification. Read status values together with their closure/non-claim notes and exact-tree evidence.

## Mission Control / WebVM reliability boundary

PR #122 improves the real-provider path without converting provider success into an acceptance proof. The browser surface now distinguishes authorization/setup and provider failure classes, keeps conversation history truthful when builds are blocked, and routes browser missions through a bounded guest mailbox contract.

Issue #120 remains open for two retained intermittent failures on the Pages/WebVM surface. The first, on `afb9a191...`, was a guest Python `_sha512` import failure. The second, on current main `bc8b783...`, was a narrow-viewport disk-chunk HTTP 503 followed by a WebVM runtime abort and proof timeout. Each exact revision passed its unchanged rerun without code or test changes. That supports an **intermittent delivery/guest-runtime** classification, not a claim that the reliability risk is solved. Recurrences must be retained and measured rather than hidden behind silent retries. Draft PR #124 adds a bounded same-origin retry only for immutable WebVM disk-chunk GETs after network/5xx failures; its repaired exact head passed the GitHub workflow suite on the pre-#121 base, but it still requires refresh onto current main, review, and post-merge public-site acceptance. That hardening does not by itself establish an acceptable recurrence rate.

## Research status

### What is supported today

- The architecture separates generation authority from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms rather than paper-only abstractions.
- The protected M4 implementation gaps tracked by #63 are closed, and the timing/termination repair from #108 is merged.
- The repository contains evaluation machinery capable of preserving raw observations and recomputing paper-facing metrics.
- Mission Control can exercise real guest workflows and optional provider transport while retaining explicit non-claims around semantic correctness and authority.

### What is not yet supported

The project does not yet claim, for live heterogeneous models, that:

- `P(correct | accepted)` is materially greater than raw worker correctness under matched model capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax in cost/latency/throughput;
- lower-cost or weaker workers can be substituted without unacceptable verifier false-acceptance risk;
- the capable-runner PASS on PR #109's exact synthetic candidate has been independently reviewed and integrated into accepted `main`;
- 24-hour, 72-hour or 30-day production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Control live WebVM reliability.** Keep the exact-current-main Pages/WebVM gate green, retain every failed attempt, quantify the recurrence rate under a defined repeated-run campaign, and investigate delivery/runtime failures without weakening acceptance assertions.
2. **Accept the capable-runner M4 candidate.** Preserve PR #109's retained zero-skip isolated PASS; root-cause or safely isolate the reproducible Python 3.13 full-suite failure without weakening the protected assertion; obtain independent review; then rerun the complete exact-candidate matrix and deliberately integrate it.
3. **Run release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures on the accepted candidate without broadening claims from fixture evidence.
4. **Freeze the live evaluation protocol.** Lock workload, evidence path, metrics, model/configuration and analysis choices before observing confirmatory model results.
5. **Run one fixed live model across R0–R5.** Measure `P(X)`, `P(A)`, `P(X|A)`, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, latency, throughput and cost.
6. **Run model-degradation and heterogeneous-routing studies.** Preserve negative results and denominator discipline.
7. **Run fault campaigns under live execution.** Do not infer live containment from development fixtures.
8. **Progress through 24-hour → 72-hour → 30-day soak** only after shorter qualification gates are clean.
9. **Update the paper from retained artifacts only.** No simulated, historical or synthetic evidence should be presented as live current-tree evidence.

## Documentation authority

Use the following order when determining current truth:

1. exact code at the commit being discussed;
2. tests, verifier output and retained machine-readable artifacts for that exact commit;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and its generated implementation summary for implementation traceability;
6. historical specs and snapshots for design intent, not current implementation claims.

RESIDUAL's strongest claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.
