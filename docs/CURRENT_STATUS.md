# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against accepted `main` at `f1e62936a7ce72b801c852c1d7428d4c6ed4152c`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests, workflow output, and retained machine-readable artifacts remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator-facing surfaces, and a bounded self-maintenance/research-bundle experiment.

The repository contains substantial implementation and development evidence for the mechanisms required to test its reliability hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that WebVM guest lifecycle reliability has an acceptable long-run recurrence rate, that release/recovery qualification is complete, that autonomous recursive self-improvement has been demonstrated, or that production soak targets have been met.

## Accepted main

Current accepted `main` remains **`f1e62936a7ce72b801c852c1d7428d4c6ed4152c`**, tree **`733b28ab38fec71e8029250e858db486cea22dd8`**, the merge of PR #132.

Important accepted milestones include:

- **PR #108 / `0430f2fa...`** — deterministic Factory sandbox-timing and termination repair.
- **PR #121 / `1a52e9a2...`** — provenance-only Factory ownership-anchor finalization.
- **PR #122 / `bc8b783d...`** — Mission Control real-provider reliability/UX hardening.
- **PR #124 / `9d88195a...`** — narrowly scoped WebVM immutable disk-chunk recovery.
- **PR #125 / `70e701d5...`** — provider completion-marker publication.
- **PR #127 / `7cf45ea8...`** — guest-shell dispatch for WebVM workbench missions.
- **PR #109 / `22a5bae5...`** — capable-runner M4 prerequisite/qualification path plus reviewed protected lifecycle CLI-process repair.
- **PR #132 / `f1e62936...`** — protected self-hosting trial, bounded self-maintenance controller, and frozen research-bundle tooling.

Issues #63 and #48 are closed. Their old present-tense blocker language is historical, not the current integration state.

## Current exact-main qualification

All seven push-triggered workflows observed for exact current `main` completed **PASS**:

- Factory ownership gate — run `35046857287`;
- measured-evaluation acceptance binding — run `35046857238`;
- clean-install qualification — run `35046857264`;
- capable-runner M4 qualification/prerequisite workflow — run `35046857256`;
- Command Station checks — run `35046857228`;
- controller/provider contracts — run `35046857233`;
- Deploy GitHub Pages — run `35046857227`.

These results are bound to revision `f1e62936...` and their named environments. They do **not** prove every-host capability, production reliability, elapsed soak, or live-model research claims.

### M4 qualification boundary

The retained post-#109 M4 qualification on revision `22a5bae54ec12987ffd7a90d881fb4533c9b4b97` is run `35036589940`: all prerequisite capability checks passed, actual `linux-userns-isolated-v1` execution passed, and the zero-skip M4 suite completed successfully with retained artifact `10423467722` (ZIP SHA-256 `18fbc15c5fb8b6dd2e1984e55a131530f38b0ea96860d1b86ccaf7d5a5812922`).

PR #132 did not modify protected Factory/M4 implementation or accepted ownership pins, and the capable-runner M4 workflow also passed after that merge on exact current main in run `35046857256`. The claim remains scoped to the named qualification boundary and environment; namespace-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not PASS.

## Protected self-hosting / research-bundle milestone

PR #132 is a meaningful research milestone, but its evidence is deliberately narrower than “RESIDUAL builds itself.”

The retained trial used exactly **one live external GPT-5.6 Sol interactive worker** to author a four-file research-bundle candidate against frozen base `22a5bae...`. RESIDUAL reconstructed the candidate and evaluated it through deterministic predicates. The final evidence records one live external-model-authored candidate, classification **PR_READY**, `merge_authorized=false`, zero protected paths touched, 6/6 visible feature tests, and hidden freeze/verify/tamper acceptance PASS including rejection of mutated frozen source.

The retained 100-generation, 1,000-fault, and 200-document-policy campaigns are controller/policy stress experiments. They are **not** repeated live model-authored generations, autonomous recursive self-modification attempts, or independent trust-domain qualification. The final protected-self-hosting workflow was run `35045986860`, with retained artifact `10427205992` and ZIP SHA-256 `09b627315255ea19f5be767634315929c5763f07d59eddbb8df3807ef6f41b31`.

Issue #35 remains open because the broader reproducibility program still includes claim-to-evidence maintenance, bibliography provenance, frozen statistical analysis choices, negative/`UNKNOWN` publication, unified manifests, artifact-derived paper tables, and threats-to-validity work.

## Mission Control / WebVM reliability boundary

Exact-current-main Pages run `35046857227` is green, but that does **not** close the WebVM lifecycle reliability program.

Issue #120 remains open for intermittent Pages/WebVM delivery and guest-runtime failures. Issue #126 remains reopened after retained production evidence on an earlier accepted lineage showed a later fresh guest Python process failing inside the Python standard library after earlier audit/build/follow-up/provider steps had succeeded. PR #134 separately retained the same broad failure family as `munmap_chunk(): invalid pointer`. Root cause remains unproven.

PR #136 is the current-main persistent-worker mitigation candidate. Its earlier candidate heads retained several meaningful failures: FIFO creation was unsupported in the real WebVM guest (`ENOSYS`); a DataDevice control record failed POSIX ownership/type assumptions; stale source-contract assertions blocked browser execution; an obsolete shutdown path left the worker live and exposed a later `OverflowError`; and a post-worker verifier invocation failed because embedded paths were not shell-quoted. Those failures remain retained historical evidence and are not rewritten as PASS.

### Current PR #136 exact-head state

Live PR #136 head is **`09fb5dc8c60307e3424f6bedc5026ffd6cacdc17`**, based directly on accepted `main@f1e62936...`.

All eight applicable exact-head workflows completed **PASS**:

- Deploy GitHub Pages — run `35097645386`;
- Browser VM Demo CI — run `35097644568`;
- Clean install qualification — run `35097644790`;
- Control Plane — run `35097644573`;
- Factory ownership gate — run `35097644666`;
- measured-evaluation acceptance binding — run `35097644750`;
- controller/provider contracts — run `35097644846`;
- Command Station checks — run `35097644520`.

Pages run `35097645386` passed generated desktop and narrow/mobile Chromium proof on the same synthetic merge tree. The retained proof demonstrated one persistent worker PID across audit/build/follow-up/live flows, clean control-record shutdown, post-worker evidence-chain verification, standalone CLI projection, reload continuity, consent gating, and truthful provider failure behavior.

Retained artifacts for that exact head are:

- `webvm-proof-35097645386-1` — artifact **`10446559623`**, SHA-256 **`c23dafbc8001384a079c2195f4c060e02bbccc23da471b18cc3ac739c2a24a86`**;
- `github-pages-35097645386-1` — artifact **`10446993144`**, SHA-256 **`a0964df76f098d67325446faa0a42dacf7a17b43759deb7e68b676591423b84a`**.

This is exact-head test-double/provider-contract and real-browser qualification evidence for the candidate. It is **not** proof of the historical guest-corruption root cause, not a live paid-provider quality result, not an acceptable long-run recurrence-rate result, and not production release certification.

A technical audit of this exact head found no new blocker in the reviewed scope, but that review was posted through the repository owner's connected account and is therefore **not independent acceptance**. PR #136 must remain unmerged until a genuinely independent reviewer/account accepts this exact qualified head. If it later merges, the exact accepted revision must pass its **first** qualified public desktop+narrow release attempt; a failing first attempt remains evidence and must not be rerun merely to obtain green.

PR #134 remains held until the runtime lifecycle boundary is integrated and independently qualified. Its provider-transport changes must then be rebased/requalified before fresh real-provider iPhone evidence is requested.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing exist. |
| Command Station | Implemented research/operations surface | Run control, provider/model management, observations, HITL hooks, evidence export and operational UI exist. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface; **reliability gate open** | Accepted main is green at its exact revision. PR #136 exact head is now fully green across eight applicable workflows including desktop+narrow browser proof, but independent acceptance, post-merge first-attempt release proof, and long-run reliability evidence remain open. |
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

Accepted `main` itself has not changed since the prior check, but the pending candidates have materially different integration states:

- **PR #136 — WebVM persistent-worker lifecycle hardening.** Live head **`09fb5dc8c60307e3424f6bedc5026ffd6cacdc17`** has all eight applicable exact-head workflows **PASS**, including generated desktop+narrow browser proof. Historical failed heads remain evidence. The remaining pre-merge gate is genuinely independent technical acceptance of this exact qualified head. Post-merge first-attempt public desktop+narrow acceptance and long-run reliability measurement remain separate gates.
- **PR #118 — runtime/DSM closure.** Live head **`334527da6025293ffc1ff485362fa38b6e296345`** is based on current `main@f1e62936...`. All applicable exact-head workflows observed for that head are **PASS**, including controller/provider, Command Station, ownership, clean install, measured binding, Control Plane and Pages browser proof. Retained first-attempt failures remain historical evidence. The remaining merge gate is genuinely independent technical acceptance of this exact repaired head. Cross-process/multi-host serialization, production process wiring, host-loss behavior, release/recovery and elapsed soak remain separate non-claims.
- **PR #131 — core SoakState persistence hardening.** Live head **`368f308504c5398c79f9935a9c360ae390144c36`** is based on current `main@f1e62936...`. All seven applicable exact-head workflows are **PASS**. The change hardens local resumable state persistence against predictable-temp symlink attacks; it does **not** establish elapsed soak or release readiness. Fresh independent technical acceptance is still required before integration.
- **PR #115 — release preparation.** Live head **`b1ffbb486585c81b5aa4771f29ffb17aab3946c7`** is based on current `main@f1e62936...`. Its exact-head qualification remains **incomplete** because controller/provider run **`35087653566`** is **CANCELLED** rather than PASS. Do not merge until the required exact-head workflow set completes green and independent technical acceptance is recorded. True bare-OS install, production HTTPS release-host, host-loss recovery and elapsed soak remain unproven.

## Research status

### Supported today

- Generation authority is separated from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms.
- Accepted main has current push-level Factory ownership, measured binding, clean-install, Station, controller/provider, capable-runner M4 and Pages workflow passes.
- Frozen research-bundle tooling can bind manuscript metrics to exact retained artifact bytes and reproduce them without model credentials.
- One bounded external-model self-maintenance trial produced a PR-ready candidate while preserving `merge_authorized=false`.
- PR #136 has exact-head browser and repository qualification evidence for its current repaired lifecycle candidate.

### Not yet supported

The project does not yet claim that:

- live heterogeneous models demonstrate materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax;
- WebVM lifecycle corruption has been root-caused or shown to have an acceptable recurrence rate;
- PR #132 proves autonomous recursive self-improvement, independent trust-domain qualification, or autonomous merge authority;
- PR #136 has independent technical acceptance or post-merge production release evidence;
- release/recovery qualification is complete;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Obtain genuinely independent technical acceptance of exact-qualified PR #136 head `09fb5dc8...`.** Same-author/implementer commentary is not independent acceptance. Preserve every earlier failing head/run as historical evidence.
2. **If #136 merges, require the exact merged revision to pass its first qualified public desktop+narrow release attempt.** A failing first attempt remains evidence and must not be rerun merely to obtain green.
3. **Requalify the provider adapter only after lifecycle integration.** Refresh PR #134 onto the stable runtime, then run exact-head and production browser qualification before a fresh real-provider iPhone run.
4. **Review the current-main-qualified component candidates.** PR #118 and PR #131 are exact-head green; their remaining integration gate is independent technical acceptance, with their stated non-claims preserved.
5. **Finish exact-head release-preparation qualification.** PR #115 currently has a cancelled controller/provider run. Require a complete green exact-head workflow set and independent review before integration; do not treat procedure/rehearsal evidence as release PASS.
6. **Execute release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures without converting rehearsal/simulation evidence into release PASS.
7. **Quantify WebVM reliability.** Keep #120 open, retain every failure, and run a defined repeated-run campaign; one qualified candidate run is not a long-run production failure rate.
8. **Complete remaining reproducibility preparation.** Continue #35 work, freeze the live workload/evidence path/metrics/analysis choices before confirmatory model results, and publish negative/`UNKNOWN` outcomes.
9. **Run fixed-model R0–R5**, followed by degradation and heterogeneous-routing studies.
10. **Progress through elapsed 24h → 72h → 30-day soak** only after shorter gates are clean.
11. **Update the paper only from frozen retained artifacts.**

## Documentation authority

Use this order when determining current truth:

1. exact code at the commit being discussed;
2. tests, workflow output and retained machine-readable artifacts for that exact commit;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and generated implementation summary for traceability;
6. historical specs/snapshots for design intent, not current implementation claims.

RESIDUAL’s strongest research claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.
