# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against `main@e996b58566847e88153e6e5196625d52b93e081a`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

RESIDUAL is an evidence-first reliability/control plane for heterogeneous AI computation. Current `main` now includes merged **#185**, the release-stabilization integration, on top of #183 and #179.

#185 promotes two material release-path changes into accepted main:

- a bounded SQLite writer-admission retry in protected `residual/factory/runtime_journal.py`, together with the corresponding advance of `verifier/v3/factory_ownership_baseline.json`;
- the #186 iOS/iPadOS WebKit pre-boot fallback, which routes the unsupported heavyweight WebVM path to the lightweight walkthrough before guest/disk boot.

Those are now accepted current-main bytes because #185 merged. That fact does **not** broaden their qualification: the runtime-journal behavior is only the bounded writer-admission change actually reviewed/qualified, and the iOS fallback is not proof that heavyweight WebVM is reliable on physical iPhone Safari.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established**. Physical heavy-WebVM reliability on iPhone/Safari remains **UNKNOWN / unqualified**. Blank-environment install, host-loss/recovery evidence, selected elapsed soak, and the confirmatory R0–R5 research program remain open.

## Current main

Current `main` is **`e996b58566847e88153e6e5196625d52b93e081a`**, created by merging **PR #185** from final candidate head **`068954dd6c1c9a56c9a18fbbce67b1504e2c4b7d`**.

The final #185 head received exact-head maintainer attestation before merge. Under merged #168 governance this is **maintainer-reviewed with automated qualification**, not independent human assurance.

### Protected Factory / ownership-baseline change now accepted

#185 changes protected `residual/factory/runtime_journal.py` and advances `verifier/v3/factory_ownership_baseline.json`.

The accepted runtime-journal behavior is deliberately narrow: retry is bounded to mutation-free SQLite writer transaction admission on genuine BUSY/LOCKED contention. Once `BEGIN IMMEDIATE` succeeds, journal mutation and COMMIT are not replayed. Non-contention `OperationalError` remains fail-closed and persistent contention remains bounded.

Because these protected bytes and the ownership pin are now on `main`, documentation may describe them as accepted implementation. Do **not** infer from that acceptance that every Factory/M4 path, host, or historical failure is globally cleared.

## Exact-current-main qualification

Current-main retained CI is **mixed in history, green in the latest observed applicable runs**.

Latest observed runs on exact `main@e996b585...` include:

| Workflow / gate | Latest observed outcome |
| --- | --- |
| Factory ownership gate | **PASS** — run `35264069644` |
| Clean install qualification | **PASS** — run `35264069698` |
| Measured evaluation acceptance binding | **PASS** — run `35264069745` |
| M4 qualification runner prerequisites | **PASS** — run `35264069726` |
| Controller and provider contracts | **PASS** — run `35264069649` |
| Command Station checks | **PASS** — run `35264069706` |
| iOS WebKit preflight | **PASS** — run `35264069648` |
| Deploy GitHub Pages | **PASS** — run `35263783090`, attempt 1 |

A prior Controller/provider run on the **same SHA**, run **`35263782697`**, is retained **FAIL** in its Python 3.13 job. A later same-SHA run passed. Retained failure evidence and the focused #187 repair now identify the failure mechanism as a protected-test `/proc/<pid>/status` observation race: the test checked existence and then opened the status file, allowing the expected child exit between those operations to raise `ProcessLookupError`. This diagnoses the CI/test failure; it does **not** establish a runtime termination defect, and the retained FAIL is not erased by the later same-SHA PASS.

PR **#187** is the focused test-only candidate for that race. It performs one status read, treats only `FileNotFoundError` / `ProcessLookupError` as the successful disappeared-process outcome, preserves the bounded polling/failure condition for a live non-zombie child, and advances the protected ownership pin for that one test blob. Its exact head `6a5ee753abe6137214f3ee17c8bcc4a85c4f3461` currently has **PASS** for Factory ownership, measured binding, M4 runner prerequisites, clean install, Control Plane, Controller/provider, and Command Station, while the exact-head maintainer approval gate is **FAIL/BLOCKED** pending attestation. These candidate results do not make #187 accepted main and do not substitute for any capable-runner M4 qualification required by its merge policy.

The older `main@2e1341c9...` Command Station run `35219212073` also remains historical **FAIL** evidence for the readiness-polling/concurrent-writer case. Current-main Command Station is now PASS, but historical failures remain part of the evidence record.

Pages/iOS-preflight PASS establishes only the named automated/browser/deployment scopes. It does not establish paid/live Puter success, physical-device heavy-WebVM reliability, long-run WebVM reliability, blank-machine release qualification, host-loss recovery, or elapsed soak.

## iPhone/WebKit boundary

PR #182 is closed unmerged and superseded. PR **#186** was integrated into the stabilization lineage and is now present on `main` through #185.

The accepted fallback:

- detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot;
- routes that profile to `/walkthrough/?platform=ios-webkit`;
- preserves desktop WebVM behavior;
- retains `?full_vm=1` only as an explicit diagnostic override.

Dedicated iOS WebKit preflight CI is PASS on current main. This is **PASS for the pre-boot fallback contract**, not a physical-iPhone heavy-WebVM reliability claim. Published physical-device validation remains open, and the lower-level WebKit process-kill cause remains **UNKNOWN**.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of the invalid responses: **UNKNOWN**.

Merged #179 is a bounded build-output/truncation mitigation, not proof that the old 1536-token ceiling was the sole root cause. Merged #183 is a provider-session lifecycle repair, not live-provider semantic proof. Merged #185/#186 adds a supported-device fallback, not provider success.

A fresh retained real-account mission on exact deployed `main@e996b585...` (or a later accepted release revision) is required before paid/live provider success can become PASS. It must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling. Test-double CI and Pages proof are not substitutes.

## WebVM reliability boundary

Issues #120 and #126 remain open. Historical diagnostics narrow a WebVM-specific, process-local CPython positive-duration timed-wait failure, but the relationship among that family, the physical iPhone crash, the poisoned-guest event, and older interpreter/allocator corruption evidence remains **UNKNOWN**.

Merged #159, #153, #169, #179, #183, and #185/#186 are bounded improvements. None alone establishes an acceptable long-run guest failure rate or a root cause for the broader historical corruption family.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

The #185 runtime-journal/ownership-baseline change is now accepted main. Keep it distinct from the protected `/proc/<pid>/status` test-observation race diagnosed above. PR #187 is the focused candidate for that specific test race and deliberately advances the ownership pin for `tests/test_factory_m4_safety.py`; because it touches a protected test blob and the ownership baseline, it requires its own protected-byte review, exact-head qualification, and maintainer governance before merge. The separate #139→ownership-baseline→#134 protected sequence remains independent and must not be treated as cleared by #187.

A green current Factory lane does not retroactively erase retained exact-revision failures or establish universal every-host M4 qualification.

## Inference-economics planning

Draft specification PRs #160/#161/#162/#163/#164/#166/#167 stage the IE-001→IE-007 program and corrected integration-authority contracts. They remain specification/test-planning branches, not accepted production performance, cost, scheduling/routing, or research claims.

Merged #168 defines normal repository merge control as:

`automated qualification/review appropriate to scope -> exact-head maintainer attestation -> merge`

Independent human/third-party review is separate evidence when it occurs or when a claim-specific rule requires it; it is not the generic repository-wide merge prerequisite.

PR #177 remains a prototype candidate. Its previous focused PASS/maintainer evidence is historical to its candidate head and must be reconciled/refreshed against the current IE-001 contract and applicable current-main qualification before any final IE-001 qualification claim.

## Other active work

- **#120 / #126** — long-run WebVM reliability/root-cause work remains open.
- **#187** — focused protected-test `/proc` race repair; technical exact-head workflows observed PASS, maintainer approval **BLOCKED**, protected ownership-baseline advance unaccepted until merge.
- **#139 / #134** — separate protected M4 repair/dependent hardening sequence remains open.
- **#152** — Qualification v1 evidence must be refreshed against the applicable current/release lineage before current release claims use it.
- **#177** — IE-001 prototype candidate; final qualification remains unclaimed.
- **#178** — documentation-only IE-002→IE-007 backlog; no runtime/performance claim.
- **#175** — specification-only OpenViking/context-provider proposal; no accepted runtime dependency.

## Research and release non-claims

The project does **not** yet claim that:

- the diagnosed same-SHA Controller/provider test race is erased by the later PASS or fixed on accepted main;
- #187 is accepted or provides universal/capable-runner M4 qualification merely because its observed hosted workflows are green;
- #185/#186 proves heavyweight WebVM reliability on physical iPhone Safari;
- paid/live Puter succeeds end to end on exact current main;
- WebVM long-run reliability is acceptable or the historical corruption family is root-caused;
- blank-environment install/recovery qualification is complete;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- the accepted #185 protected-byte change clears unrelated historical M4 failures;
- #177 has final IE-001 qualification;
- the solo-maintainer model supplies independent human assurance;
- confirmatory live-model evaluation has established the central reliability hypothesis.

## Next gates

1. Preserve Controller/provider run `35263782697` as retained same-SHA **FAIL** evidence. Review #187 as the focused protected-test diagnosis/repair, but do not treat it as accepted until its protected ownership-baseline change, applicable exact-head/capable-runner qualification, and exact-head maintainer attestation satisfy policy.
2. Validate the accepted #186 iOS/WebKit fallback on a physical device after publication; do not turn fallback success into a heavy-WebVM reliability claim.
3. Retain a fresh real-account Puter mission on the exact deployed accepted revision before claiming live-provider PASS, or explicitly exclude live-provider success from the release claim.
4. Execute true blank-environment install and recovery/host-loss qualification for the exact release artifact.
5. Complete the selected elapsed soak tier with retained first-failure evidence.
6. Continue #120/#126 reliability work and the separate #139→ownership-baseline→#134 protected sequence without conflating them with #187 or the accepted #185 runtime-journal change.
7. Refresh/requalify #152 before using it as current release evidence.
8. Reconcile/refresh #177 against the current IE-001 contract and current-main governance before final IE-001 qualification.
9. Freeze and run confirmatory R0–R5/degradation/heterogeneous-routing studies only under the stated research protocol.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues and explicit release policy;
4. submitted maintainer/protected-byte/ownership-baseline review records;
5. this current-status document;
6. `implementation-status.yaml` for implementation traceability;
7. historical specs/snapshots for design intent, not current qualification claims.
