# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against accepted `main` at `f1e62936a7ce72b801c852c1d7428d4c6ed4152c`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests and retained machine-readable evidence remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator-facing surfaces, and now a bounded self-maintenance/research-bundle experiment.

The repository contains substantial implementation and development evidence for the mechanisms required to test its reliability hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that WebVM guest lifecycle reliability has been solved, that release/recovery qualification is complete, that autonomous recursive self-improvement has been demonstrated, or that production soak targets have been met.

## Accepted main

Current accepted `main` is **`f1e62936a7ce72b801c852c1d7428d4c6ed4152c`**, tree **`733b28ab38fec71e8029250e858db486cea22dd8`**, the merge of PR #132.

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

The detailed retained post-#109 M4 qualification on revision `22a5bae54ec12987ffd7a90d881fb4533c9b4b97` is run `35036589940`: all prerequisite capability checks passed, actual `linux-userns-isolated-v1` execution passed, and the zero-skip M4 suite completed successfully with retained artifact `10423467722` (ZIP SHA-256 `18fbc15c5fb8b6dd2e1984e55a131530f38b0ea96860d1b86ccaf7d5a5812922`).

PR #132 did not modify protected Factory/M4 implementation or accepted ownership pins, and the capable-runner M4 workflow also passed after the merge on exact current main in run `35046857256`. The claim remains scoped to the named qualification boundary and environment; namespace-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not PASS.

## Protected self-hosting / research-bundle milestone

PR #132 is a meaningful research milestone, but its evidence is deliberately narrower than “RESIDUAL builds itself.”

The retained trial used exactly **one live external GPT-5.6 Sol interactive worker** to author a four-file research-bundle candidate against the frozen base `22a5bae...`. The candidate files were:

- `residual/research_bundle.py`;
- `scripts/research_bundle.py`;
- `tests/test_research_bundle.py`;
- `docs/research/RESEARCH_BUNDLES.md`.

RESIDUAL reconstructed the candidate and evaluated it through deterministic predicates. The final PR #132 evidence records:

- live external-model-authored candidate count: **1**;
- classification: **PR_READY**;
- candidate merge authority: **false**;
- protected paths touched by the four-file candidate: **0**;
- visible feature tests: **6/6 PASS**;
- hidden freeze/verify/tamper acceptance: **PASS**, including rejection of mutated frozen source;
- acceptance execution domain: **single process**;
- three distinct acceptance predicates, explicitly **not** three independent external reviewers;
- synthetic controller-lineage stress: 100 generations, valid chain, 0 merge-authorized generations;
- synthetic fault campaign: 1,000 trials, 0 false accepts and 0 false rejects;
- synthetic documentation-policy simulation: 200 cases, 0 required-stale false accepts and 0 `UNKNOWN` accepts.

The final protected-self-hosting workflow was run `35045986860`, with retained artifact `10427205992` and ZIP SHA-256 `09b627315255ea19f5be767634315929c5763f07d59eddbb8df3807ef6f41b31`.

The 100/1,000/200 campaigns are controller/policy stress experiments. They are **not** repeated live model-authored generations, autonomous recursive self-modification attempts, or independent trust-domain qualification. The workflow token was read-only, and the controller retained `merge_authorized=false`; PR #132’s eventual repository merge was a separate external acceptance action.

Issue #35 remains open because the broader reproducibility program still includes claim-to-evidence maintenance, bibliography provenance, frozen statistical analysis choices, negative/`UNKNOWN` publication, unified manifests, artifact-derived paper tables, and threats-to-validity work.

## Mission Control / WebVM reliability boundary

The most important current operational change is that WebVM reliability is **not** green merely because exact-current-main Pages run `35046857227` passed.

Issue #120 remains open for intermittent Pages/WebVM delivery and guest-runtime failures. Issue #126 has been **reopened** after retained production evidence on the preceding main lineage showed a later fresh guest Python process failing inside the Python standard library after audit/build/follow-up/provider steps had already succeeded. A separate #134 candidate produced the same failure family as `munmap_chunk(): invalid pointer`.

The current interpretation is a guest/interpreter lifecycle risk, not a proven application-level defect. PR #136 is the current-main mitigation candidate. Its current head keeps Mission Control on one persistent in-guest Python worker, serializes missions, validates worker PID/FIFO identity, promotes impossible browser-mailbox `TypeError` corruption into a fatal non-reusable worker outcome, and adds durable poison/identity-bound timeout recovery that preserves incomplete mission evidence and fails closed when cleanup cannot be proven. Those changes harden the lifecycle boundary; they remain a candidate mitigation, **not** a proven root-cause fix or production reliability clearance.

Fresh exact-head qualification for PR #136 is currently **FAIL** at the Pages/WebVM browser gate. Run `35067563563` tested synthetic merge `17af2517d52699b0fd46f94afa73932dbcd51e6e` for PR head `52e820e012403c189e93679f41129ee5cddee510`. The provider-contract tests and focused 79-test WebVM Python suite passed, and the desktop proof reached guest attachment, real demo verification, and warm reload. The persistent worker then failed to start in the actual WebVM guest because `os.mkfifo()` returned `OSError: [Errno 38] Function not implemented`; the desktop browser proof timed out and the narrow proof was not reached. The failed proof was retained as artifact `10434517793`, ZIP SHA-256 `f76b08416debf55dc225531bc47c696549318e1b011ca8ce6a73e58398f88c1e`. This is a candidate-transport qualification **FAIL** for #136, not an accepted-main regression and not proof of the historical corruption root cause.

PR #134, which hardens the real browser provider adapter, remains held until the runtime lifecycle boundary is stabilized and production-qualified. Its provider-transport changes must be rebased/requalified after #126/#136 is resolved before fresh real-provider iPhone evidence is requested.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing exist. |
| Command Station | Implemented research/operations surface | Run control, provider/model management, observations, HITL hooks, evidence export and operational UI exist. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface; **reliability gate open** | Real guest workflows, multi-turn artifact lineage and provider transport exist. #120/#126 remain open; #136 current head is **FAIL** at Pages/WebVM qualification because FIFO creation is unsupported in the generated guest. |
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

Two substantial candidates were prepared against the previous accepted main and therefore require current-main refresh discipline before integration:

- **PR #118 — runtime/DSM closure.** Its exact old head reports green CI after retained unchanged reruns and still requires genuinely independent technical acceptance. Its base remains `22a5bae...`, so it should be refreshed/requalified against `f1e629...` before integration. Cross-process/multi-host serialization, production process wiring and host-loss behavior remain separate non-claims.
- **PR #115 — release preparation.** It strengthens durability, blank-VM evidence handling, HTTPS/provenance discipline and soak claim labeling, but its base also remains `22a5bae...`. Fresh current-main qualification and independent technical acceptance are required; true bare-OS install, production HTTPS release-host, host-loss recovery and elapsed soak remain unproven.

## Research status

### Supported today

- Generation authority is separated from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms.
- Accepted main has current push-level Factory ownership, measured binding, clean-install, Station, controller/provider, capable-runner M4 and Pages workflow passes.
- Frozen research-bundle tooling can bind manuscript metrics to exact retained artifact bytes and reproduce them without model credentials.
- One bounded external-model self-maintenance trial produced a PR-ready candidate while preserving `merge_authorized=false`.

### Not yet supported

The project does not yet claim that:

- live heterogeneous models demonstrate materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax;
- WebVM lifecycle corruption has been root-caused or shown to have an acceptable recurrence rate;
- PR #132 proves autonomous recursive self-improvement, independent trust-domain qualification, or autonomous merge authority;
- release/recovery qualification is complete;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Repair and requalify the WebVM worker transport.** PR #136 head `52e820e...` is currently **FAIL** in run `35067563563`: the actual WebVM guest returns `ENOSYS` for `mkfifo`, so the desktop proof cannot start the persistent worker and the narrow proof is not reached. Preserve artifact `10434517793`, redesign the transport without weakening fail-closed mailbox/identity semantics, rerun exact-head full CI plus desktop+narrow proof, then obtain genuinely independent technical review. Only after merge should the exact production revision be required to pass its first qualified desktop+narrow release attempt.
2. **Requalify the provider adapter only after lifecycle stabilization.** Refresh PR #134 onto the stable runtime, then run exact-head and production browser qualification before a fresh real-provider iPhone run.
3. **Refresh pending runtime/release candidates.** Rebase/reconcile #118 and #115 onto current accepted main, rerun exact-head qualification, and preserve their independent-review requirements.
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
