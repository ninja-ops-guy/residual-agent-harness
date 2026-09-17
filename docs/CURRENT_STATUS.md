# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against `main@2e1341c99fd7b72452e3b8c5278b1f557871b783` and the active release-stabilization lineage._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

RESIDUAL is an evidence-first reliability/control plane for heterogeneous AI computation. Current `main` includes the accepted browser build-output mitigation from #179 and the accepted mobile provider-session lifecycle repair from #183.

Current `main` has **mixed qualification**: six of seven observed push workflows are PASS, while Command Station run `35219212073` remains retained **FAIL** on Python 3.11. The failing test is now identified as `test_sandbox_timing_determinism.JournalContentionReadTests.test_readiness_polling_survives_concurrent_writer`; the observed mission status was `AUDIT_FAILED` with `OperationalError`, while Python 3.12, Python 3.13, browser, and Docker jobs passed. The failure remains authoritative for that exact main revision.

A separate release-stabilization lane is now active in draft PR #185 from `main@2e1341c99fd7b72452e3b8c5278b1f557871b783`. It is intentionally isolated so release-critical fixes can be qualified without moving `main`. PR #186 has already merged **into the stabilization branch, not main**, and supersedes closed-unmerged #182 for the iOS/WebKit safe-walkthrough path.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established**. Physical heavy-WebVM reliability on iPhone/Safari remains **FAIL/UNKNOWN** at the runtime boundary; the new iOS safe-mode work is a release fallback, not proof that heavyweight WebVM is reliable on physical iPhone Safari.

## Current main

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**.

It was created by merging PR #183, which adds bounded mobile provider-session lifecycle recovery:

- five-minute browser-side liveness grace;
- liveness refresh on bounded valid provider traffic;
- session-scoped recovery of the private BroadcastChannel capability;
- reuse of an already signed-in Puter session after eligible provider-tab reload;
- bfcache/foreground state refresh.

#183 does not change per-mission provider call budgets, model-selection authority, verifier/receipt authority, Factory/M4 authority, or shared evidence schemas, and it does not claim to fix the separate iPhone/WebVM crash.

### Exact-current-main qualification

| Workflow / gate | Outcome on `main@2e1341c9...` |
| --- | --- |
| Measured evaluation acceptance binding | **PASS** |
| Clean install qualification | **PASS** |
| Factory ownership gate | **PASS** |
| Controller and provider contracts | **PASS** |
| M4/applicable runner prerequisites | **PASS** |
| Deploy GitHub Pages | **PASS** — run `35219212133`, attempt 1 |
| Command Station checks | **FAIL** — run `35219212073`, attempt 1 |

The Command Station failure is now identified to the Python 3.11 readiness-polling/concurrent-writer regression. The retained failure must not be erased by sibling green jobs or by rerunning unchanged code merely to obtain green.

Pages PASS establishes only its named generated-browser/deployment scope. It does not establish paid/live Puter success, physical iPhone/WebKit reliability, long-run WebVM reliability, blank-machine release qualification, recovery qualification, or elapsed soak.

## Release stabilization lane — PR #185

Draft PR **#185**, `release/stabilization-2026-09-17`, is the integration and qualification lane for the next release candidate. It started from exact current main and has explicit rules to retain first failures, limit scope to release-critical fixes/evidence, preserve UNKNOWN/BLOCKED semantics, and promote only one fully qualified final exact head.

Current #185 head is **`068954dd6c1c9a56c9a18fbbce67b1504e2c4b7d`**. On that exact head GitHub reports **15 successful workflow runs** and **one failed workflow run**: the maintainer approval gate is **FAIL/BLOCKED**. Command Station is PASS on that stabilization head, but this is candidate evidence and does not rewrite the retained FAIL on current main.

The stabilization head includes a protected `residual/factory/runtime_journal.py` change and a corresponding advance of `verifier/v3/factory_ownership_baseline.json`. The candidate adds a bounded one-second retry budget only for mutation-free writer transaction admission on genuine SQLite BUSY/LOCKED contention; after `BEGIN IMMEDIATE` succeeds, journal mutation and COMMIT are not replayed. Non-contention `OperationalError` remains fail-closed and persistent contention remains bounded.

Because #185 changes a protected Factory blob and its ownership baseline, it is a **trust-boundary change**. Green CI is not sufficient by itself. Deliberate protected-byte review, ownership-baseline review, fresh exact-head qualification after the pin change, and exact-head maintainer attestation are required. This documentation PR must not merge or normalize that trust-boundary change automatically.

### Release exit criteria remain open

The stabilization branch is not releasable merely because the current technical workflows are green. Its retained release gates still include:

- exact-head required CI and capable-runner M4 qualification;
- Factory ownership and measured-evaluation binding;
- generated desktop+narrow Pages/WebVM proof;
- supported-device behavior and final physical-device validation;
- true blank-environment install evidence for the exact artifact;
- recovery/host-loss evidence for the selected deployment mode;
- a selected elapsed soak tier bound to the exact RC;
- retained real-account live-provider acceptance, or an explicit release claim that excludes it;
- evidence-aligned release notes/non-claims;
- exact-head maintainer attestation.

## iPhone/WebKit boundary — #182 superseded by #186

Physical evidence still shows desktop success while the heavyweight iPhone/Safari WebVM path can terminate. No retained typed browser exception establishes the lower-level WebKit process-kill mechanism, so the underlying heavy-WebVM cause remains **UNKNOWN**.

PR **#182 is closed unmerged and superseded for release stabilization**.

PR **#186 merged into `release/stabilization-2026-09-17`**, not `main`. It ports the bounded pre-boot safe-mode design to the release lineage:

- synchronous iPhone/iPad/iPod + iPadOS WebKit preflight before heavyweight guest/disk boot;
- route unsupported/unqualified iOS WebKit to `/walkthrough/?platform=ios-webkit`;
- preserve desktop WebVM behavior;
- retain `?full_vm=1` only as an explicit diagnostic override;
- dedicated pinned WebKit CI proves the iPhone profile reaches the walkthrough without requesting the heavyweight guest/disk artifacts.

This is a **supported-device fallback**, not a PASS claim for heavyweight WebVM on physical iPhone Safari. Final physical-device validation of the published RC remains required.

## Live-provider evidence

Historical real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of the invalid responses: **UNKNOWN**.

Merged #179 is a bounded build-output/truncation mitigation, not proof that the old 1536-token ceiling was the sole root cause. Merged #183 is a provider-session lifecycle repair, not live-provider semantic proof.

A fresh retained real-account mission on the final accepted/deployed release lineage is required before paid/live provider success becomes PASS. It must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling. Test-double CI and Pages proof are not substitutes.

## WebVM reliability boundary

Issues #120 and #126 remain open. Historical diagnostics narrow a WebVM-specific, process-local CPython positive-duration timed-wait failure, but the relationship among that family, the physical iPhone crash, the poisoned-guest event, and older interpreter/allocator corruption evidence remains **UNKNOWN**.

Merged #159, #153, #169, #179, and #183 are bounded improvements. None alone establishes acceptable long-run guest reliability.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

The older protected `/proc/<pid>/status` observation-race evidence remains historical FAIL evidence. PR #139 remains the isolated protected repair lane for that issue where applicable; dependent #134 work must still respect the protected-byte/ownership-baseline sequence.

The release-stabilization lane now introduces a **different protected Factory change** in `runtime_journal.py` plus an ownership-baseline update. Do not conflate those two protected histories, and do not infer that one green lane clears the other.

## Other active work

- **#185** — draft release-stabilization lane; current exact head has technical success plus maintainer gate **FAIL/BLOCKED**, and it contains a protected Factory blob + ownership-baseline change requiring deliberate trust-boundary handling.
- **#186** — merged into #185's stabilization lineage; iOS/WebKit safe walkthrough fallback, not physical heavy-WebVM reliability proof.
- **#182** — closed unmerged; superseded by #186 for release stabilization.
- **#180** — narrow generated-build consistency candidate; unaccepted and stale to current accepted/release lineages until refreshed/requalified.
- **#177** — IE-001 prototype candidate; focused suite previously reported 203 PASS, but Q11 genuinely independent current-head review remains pending and final qualification is not claimed.
- **#178** — documentation-only IE-002→IE-007 backlog; no runtime speedup/token/cost/routing/GPU claim.
- **#175** — specification-only OpenViking/context-provider proposal; no accepted runtime dependency.
- **#152** — Qualification v1 framework; historical aggregate evidence must be refreshed against the applicable release lineage, and simulated time is not elapsed soak.
- **#139 / #134** — protected M4 repair and dependent hardening sequence remain governed by their own protected-byte process.

## Research and release non-claims

The project does **not** yet claim that:

- exact current main is all-green;
- the retained current-main Command Station failure is erased by the stabilization candidate;
- #185 is promotion-ready merely because its technical workflows are green;
- the protected `runtime_journal.py`/ownership-baseline change is accepted without deliberate review and attestation;
- heavyweight WebVM is reliable on physical iPhone Safari;
- #186 proves physical heavy-WebVM reliability;
- paid/live Puter succeeds end to end on the final RC lineage;
- WebVM long-run reliability is acceptable or root-caused;
- blank-environment install/recovery qualification is complete;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- #177 has final IE-001 qualification;
- the solo-maintainer model supplies independent human assurance;
- draft/open candidates are accepted production capability.

## Next gates

1. Preserve current-main Command Station run `35219212073` as retained FAIL evidence.
2. Complete deliberate review of #185's protected `runtime_journal.py` change and ownership-baseline advance; do not auto-normalize or auto-merge that trust-boundary change.
3. Obtain exact-head maintainer attestation for the final stabilization head only after fresh exact-head qualification is complete.
4. Validate the #186 iOS/WebKit fallback on a physical device after publication; keep the heavy-WebVM root cause UNKNOWN unless retained evidence proves it.
5. Retest #183 provider-session follow-up/reload behavior separately from WebVM runtime behavior.
6. Retain a fresh real-account Puter mission on the final accepted/deployed RC lineage before claiming live-provider PASS, or explicitly exclude live-provider success from the release claim.
7. Execute true blank-environment install and recovery/host-loss qualification for the exact RC artifact.
8. Complete the selected elapsed soak tier with retained first-failure evidence.
9. Continue #120/#126 reliability work and the separate #139→ownership-baseline→#134 protected sequence without conflating them with the #185 runtime-journal change.
10. Refresh/requalify #152 and keep #177 at candidate status until its independent-review gate is satisfied.
11. Freeze and run confirmatory R0–R5/degradation/heterogeneous-routing studies only under the stated research protocol.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues and explicit release-stabilization policy;
4. submitted maintainer/protected-byte/ownership-baseline review records;
5. this current-status document;
6. `implementation-status.yaml` for implementation traceability;
7. historical specs/snapshots for design intent, not current qualification claims.
