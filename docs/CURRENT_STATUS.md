# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against accepted `main` at `3a41dc1e84335875537672a62340d9f8c7806417`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests, workflow output, retained machine-readable artifacts and explicit open issues remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator-facing surfaces, browser/WebVM execution, and a bounded self-maintenance/research-bundle experiment.

The repository contains substantial implementation and development evidence for the mechanisms required to test its reliability hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that WebVM reliability has an acceptable long-run recurrence rate, that the historical guest-corruption root cause is established, that release/recovery qualification is complete, that autonomous recursive self-improvement has been demonstrated, or that production soak targets have been met.

## Accepted main

Current accepted `main` is **`3a41dc1e84335875537672a62340d9f8c7806417`**, tree **`8018d6382266b225b0217baab7e345fe28185d1f`**, the merge of PR #136, **Keep Mission Control on one persistent guest Python worker**.

Important accepted milestones include:

- **PR #108 / `0430f2fa...`** — deterministic Factory sandbox-timing and termination repair.
- **PR #121 / `1a52e9a2...`** — provenance-only Factory ownership-anchor finalization.
- **PR #122 / `bc8b783d...`** — Mission Control real-provider reliability/UX hardening.
- **PR #124 / `9d88195a...`** — narrowly scoped WebVM immutable disk-chunk recovery.
- **PR #125 / `70e701d5...`** — provider completion-marker publication.
- **PR #127 / `7cf45ea8...`** — guest-shell dispatch for WebVM workbench missions.
- **PR #109 / `22a5bae5...`** — capable-runner M4 prerequisite/qualification path plus reviewed protected lifecycle CLI-process repair.
- **PR #132 / `f1e62936...`** — protected self-hosting trial, bounded self-maintenance controller and frozen research-bundle tooling.
- **PR #136 / `3a41dc1e...`** — persistent Mission Control guest worker, durable timeout poison/recovery, corruption-class fail-closed termination and related WebVM lifecycle hardening.

Issues #63 and #48 are closed. Their old present-tense blocker language is historical, not the current integration state.

## Current exact-main qualification

All seven observed push-triggered workflows for exact current `main@3a41dc1e...` completed **PASS**:

- Factory ownership gate — run `35101404885`;
- measured-evaluation acceptance binding — run `35101404928`;
- clean-install qualification — run `35101405039`;
- capable-runner M4 qualification/prerequisite workflow — run `35101404956`;
- Command Station checks — run `35101404932`;
- controller/provider contracts — run `35101404949`;
- Deploy GitHub Pages — run `35101404981`.

These results are bound to revision `3a41dc1e...` and their named environments. They do **not** prove every-host capability, long-run production reliability, elapsed soak, live-provider quality or live-model research claims.

### M4 qualification boundary

The retained post-#109 M4 qualification on revision `22a5bae54ec12987ffd7a90d881fb4533c9b4b97` is run `35036589940`: all prerequisite capability checks passed, actual `linux-userns-isolated-v1` execution passed, and the zero-skip M4 suite completed successfully with retained artifact `10423467722` (ZIP SHA-256 `18fbc15c5fb8b6dd2e1984e55a131530f38b0ea96860d1b86ccaf7d5a5812922`).

Current `main@3a41dc1e...` also passed the capable-runner M4 prerequisite/qualification workflow in run `35101404956`. PR #136 did not modify protected Factory/M4 implementation or ownership baselines. The claim remains scoped to the named qualification boundary and environment; namespace-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not PASS.

## PR #136 lifecycle integration and release evidence

PR #136 merged at `3a41dc1e84335875537672a62340d9f8c7806417`. Its earlier candidate heads retained several meaningful **FAIL** results, including unsupported FIFO creation in the real WebVM guest, incompatible DataDevice control-node assumptions, stale source-contract assertions, an obsolete shutdown path that left the worker live, and an unquoted post-worker verifier invocation. Those failures remain historical evidence and are not rewritten as PASS because the repaired head later qualified.

The final PR head `09fb5dc8c60307e3424f6bedc5026ffd6cacdc17` passed all eight applicable exact-head workflows before merge, including generated desktop+narrow browser proof in run `35097645386`.

### First post-merge release attempt

The exact merged revision then received the required first post-merge public browser acceptance. Pages run **`35101404981`**, attempt **1**, completed **PASS**.

The generated-artifact job passed desktop and narrow browser proof. The deploy job then passed:

- published exact-revision WebVM/guest execution acceptance;
- narrow Chromium acceptance;
- retained live-acceptance proof.

Retained artifacts for the exact merged revision are:

- `webvm-proof-35101404981-1` — artifact **`10448920863`**, SHA-256 **`aa0cd75837464bf11fd7ddd75040288b0837c139816a1ac6c119b0ca14f979af`**;
- `webvm-live-proof-35101404981-1` — artifact **`10448708218`**, SHA-256 **`15f6a982be57c8ecb66f7de7f4ec8949ac2c3c0e3c261b37f4e96f2017b3e79c`**;
- `github-pages-35101404981-1` — artifact **`10449160205`**, SHA-256 **`98864b7669d842a64cbbcec1028b5d9227d7d2cf9ae2d7586830c84c172daf0a`**.

This clears the exact merged revision's first-attempt desktop+narrow release-proof gate. It does **not** prove an acceptable long-run WebVM failure rate, prove the historical guest/interpreter corruption root cause, establish paid/live-provider quality, complete release/recovery qualification, or create elapsed-soak evidence.

### Independent-review evidence gap

PR #136's own qualification checklist required a genuinely independent technical reviewer/account to accept the exact qualified head before merge. The retained review record contains only owner-account `COMMENTED` reviews; the final exact-head audit explicitly stated that it **did not satisfy** the independent-review gate and said not to merge on the strength of that review.

The repository nevertheless records PR #136 as merged. Treat those as two separate facts:

- the merge and post-merge exact-revision browser **PASS** are retained repository/CI evidence;
- genuinely independent technical acceptance before merge is **not recorded** in the retained review evidence.

Do not relabel the successful post-merge CI as independent review or erase the missing-review evidence.

## Mission Control / WebVM reliability boundary

Issue #120 remains open for intermittent Pages/WebVM delivery and guest-runtime failures. Issue #126 remains open/reopened after retained production evidence on earlier accepted revisions showed later fresh guest Python processes failing inside the Python standard library; PR #134 separately retained the same broad failure family as `munmap_chunk(): invalid pointer`.

The persistent-worker integration plus first-attempt post-merge browser PASS is meaningful mitigation/release evidence. The historical root cause remains **UNKNOWN**, and one qualified release attempt does not establish a long-run recurrence rate. Keep #120/#126 open until their own closure criteria are satisfied by retained evidence.

PR #134 remains open on an older base. The lifecycle prerequisite has materially advanced because #136 is integrated and its first post-merge browser attempt passed, but #134 itself must still be refreshed/rebased onto current `main`, requalified, and separately accepted before any fresh real-provider iPhone result can be treated as evidence for that adapter lane.

## Protected self-hosting / research-bundle milestone

PR #132 remains a meaningful research milestone, but its evidence is deliberately narrower than “RESIDUAL builds itself.”

The retained trial used exactly **one live external GPT-5.6 Sol interactive worker** to author a four-file research-bundle candidate against frozen base `22a5bae...`. RESIDUAL reconstructed the candidate and evaluated it through deterministic predicates. The final evidence records one live external-model-authored candidate, classification **PR_READY**, `merge_authorized=false`, zero protected paths touched, 6/6 visible feature tests, and hidden freeze/verify/tamper acceptance PASS including rejection of mutated frozen source.

The retained 100-generation, 1,000-fault, and 200-document-policy campaigns are controller/policy stress experiments. They are **not** repeated live model-authored generations, autonomous recursive self-modification attempts, or independent trust-domain qualification. The final protected-self-hosting workflow was run `35045986860`, with retained artifact `10427205992` and ZIP SHA-256 `09b627315255ea19f5be767634315929c5763f07d59eddbb8df3807ef6f41b31`.

Issue #35 remains open because the broader reproducibility program still includes claim-to-evidence maintenance, bibliography provenance, frozen statistical analysis choices, negative/`UNKNOWN` publication, unified manifests, artifact-derived paper tables and threats-to-validity work.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing exist. |
| Command Station | Implemented research/operations surface | Run control, provider/model management, observations, HITL hooks, evidence export and operational UI exist. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface; **long-run reliability gate open** | PR #136 is integrated. Exact merged revision `3a41dc1e...` passed its first public desktop+narrow release attempt. #120/#126 remain open; root cause, recurrence rate and live-provider quality remain separate. |
| Factory M2 | Implemented | Worker contracts, bounded runtime, isolated worktrees, journaled observations and host-owned termination exist. |
| Factory M3 | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and integrity checks exist. |
| Factory M4 | Implemented; capable-runner qualified on named environments | Closed #63 implementation gaps, #108 timing repair, fail-closed prerequisite probing and zero-skip qualification path exist. Not every-host or production qualification. |
| Evaluation | Implemented development/research apparatus | Frozen workloads, repeated runs, ablations, statistics, fault injection and measured Factory hooks exist. CI binding is not live research evidence. |
| Self-maintenance / research bundles | Implemented experimental surface | PR #132 demonstrates bounded PR-ready proposal evaluation with no merge authority. One live authored candidate is evidence of one bounded trial, not recursive autonomy. |
| Cluster / distributed execution | Implemented development surface | Versioned schema, authenticated membership, heartbeats, reassignment and local-first routing exist. Distributed guarantees remain narrower than fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway and recovery mechanisms exist. Release/recovery qualification remains downstream. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O exist. |
| Research / reproducibility | Active | Controlled-evaluation framework, exact-tree evidence practice, frozen research bundles and working paper exist. Live R0–R5 and soak remain future evidence gates. |

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is the machine-readable implementation manifest and its generated summary is traceability evidence for implementation presence. It must not be read as production/research qualification.

The old documentation that described issue #63 as an open M4 closure gate is stale. Current claim discipline is: M4 implementation closure is accepted and capable-runner qualification exists; every-host, release/recovery, reliability, soak and live-model research claims remain separate.

## Open integration and release gates

`main` advanced from `f1e62936...` to `3a41dc1e...` when PR #136 merged. Exact-head evidence retained for other open PRs remains valid for those exact heads, but those candidates are no longer based on the current accepted main and must not be described as current-main-qualified without refresh/requalification.

- **PR #134 — real browser provider-adapter boundary.** Still open on an older base and explicitly held pending lifecycle stabilization. Refresh/rebase it onto `3a41dc1e...`, rerun exact-head provider/mailbox + full CI + generated Pages desktop/narrow proof + production desktop/narrow proof, then obtain fresh real-provider iPhone evidence. Current status: **BLOCKED pending refresh/requalification**; no live-provider quality PASS is claimed.
- **PR #118 — runtime/DSM closure.** Head `334527da...` had its applicable exact-head workflow set **PASS** on the prior `f1e62936...` base, with retained first-attempt failures. Refresh/rebase onto current main, requalify and obtain genuinely independent technical acceptance. Cross-process/multi-host serialization, production process wiring, host-loss behavior, release/recovery and elapsed soak remain separate non-claims.
- **PR #131 — core SoakState persistence hardening.** Head `368f3085...` had all seven applicable exact-head workflows **PASS** on the prior base. The change hardens local resumable-state persistence only; it does not establish elapsed soak or release readiness. Refresh/rebase, requalify and obtain independent acceptance before integration.
- **PR #115 — release preparation.** Head `b1ffbb48...` was already incompletely qualified on the prior base because controller/provider run `35087653566` was **CANCELLED**, not PASS. Refresh onto current main and require a complete green exact-head workflow set plus independent review. True bare-OS install, production HTTPS release-host, host-loss recovery and elapsed soak remain unproven.

## Research status

### Supported today

- Generation authority is separated from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms.
- Accepted main has current push-level Factory ownership, measured binding, clean-install, Station, controller/provider, capable-runner M4 and Pages workflow **PASS** results.
- The integrated persistent-worker WebVM revision passed its first qualified public desktop+narrow browser release attempt on attempt 1.
- Frozen research-bundle tooling can bind manuscript metrics to exact retained artifact bytes and reproduce them without model credentials.
- One bounded external-model self-maintenance trial produced a PR-ready candidate while preserving `merge_authorized=false`.

### Not yet supported

The project does not yet claim that:

- live heterogeneous models demonstrate materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax;
- WebVM lifecycle corruption has been root-caused or shown to have an acceptable recurrence rate;
- PR #132 proves autonomous recursive self-improvement, independent trust-domain qualification or autonomous merge authority;
- PR #136 had a recorded genuinely independent technical acceptance before merge;
- release/recovery qualification is complete;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Refresh/requalify PR #134 on the integrated lifecycle runtime.** Require exact-head provider/mailbox tests, full CI, generated desktop+narrow browser proof and production desktop+narrow proof before any fresh real-provider iPhone run.
2. **Quantify WebVM reliability.** Keep #120/#126 open, retain every failure, and run a defined repeated-run campaign; one successful first release attempt is not a long-run production failure rate. Preserve root cause as `UNKNOWN` until evidence establishes it.
3. **Refresh the remaining integration candidates onto current main.** #118 and #131 had prior-base exact-head PASS evidence; #115 had an incomplete/cancelled exact-head gate. Rebase/refresh, requalify and obtain required independent reviews without broadening their claims.
4. **Execute release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures without converting rehearsal/simulation evidence into release PASS.
5. **Complete remaining reproducibility preparation.** Continue #35 work, freeze the live workload/evidence path/metrics/analysis choices before confirmatory model results, and publish negative/`UNKNOWN` outcomes.
6. **Run fixed-model R0–R5**, followed by degradation and heterogeneous-routing studies.
7. **Progress through elapsed 24h → 72h → 30-day soak** only after shorter gates are clean.
8. **Update the paper only from frozen retained artifacts.**

## Documentation authority

Use this order when determining current truth:

1. exact code at the commit being discussed;
2. tests, workflow output and retained machine-readable artifacts for that exact commit;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and generated implementation summary for traceability;
6. historical specs/snapshots for design intent, not current implementation claims.

RESIDUAL’s strongest research claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.
