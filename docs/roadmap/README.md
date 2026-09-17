# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; exact-revision workflow results remain authoritative |
| Factory M2/M3/M4 | Implemented; #187 protected test-only `/proc` observation repair and ownership-pin advance are accepted, but universal/capable-runner qualification is not implied |
| Mission Control/WebVM lifecycle | #159 recovery, #153 browser acceptance, #169 diagnostics, #179 build-output handling, #183 provider-session lifecycle, #185/#186 iOS fallback, and #189 provider-helper COI boundary are on main; long-run and physical heavyweight-WebVM reliability remain unqualified |
| iOS/WebKit release behavior | #186 fallback routes the unsupported/unqualified iOS WebKit profile to the walkthrough before heavyweight boot; physical-device validation remains open |
| Provider helper publication | #189 fixes the static Pages COI/CORP boundary; post-merge production verification is pending |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Release/recovery/soak | True blank-environment install, recovery/host-loss evidence and selected elapsed soak remain gates |
| Live provider acceptance | Historical retained Puter failure remains **FAIL/BLOCKED**; exact-current-main paid/live provider success remains **UNKNOWN** until retained candidate→verifier→receipt evidence exists |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`dcf1e5071deb624c637aa72df575089435d72ac9`**, created by merged **#189** on top of merged **#187**.

### #187 — protected test observation repair

#187 final head `6a5ee753abe6137214f3ee17c8bcc4a85c4f3461` merged as `8592ba3b331c4d9cc16e038d0e9d7cdbfa6fbf24`.

The accepted change performs a single `/proc/<pid>/status` read, treats only `FileNotFoundError` / `ProcessLookupError` as the expected disappeared-child outcome, preserves the bounded failure condition for a live non-zombie child, and advances the ownership pin for the changed protected test blob. It changes no runtime code or acceptance semantics.

Exact-head Factory ownership, measured binding, M4 prerequisites, clean install, Control Plane, Controller/provider, Command Station, and maintainer approval were PASS before merge. These scoped results do not imply every-host M4 qualification.

### #189 — provider helper isolation boundary

#189 final head `a307460228d1f1562805856085d471915f93e3f4` merged as current main.

The accepted change keeps same-origin `/provider/` navigation outside COOP/COEP response rewriting so Puter's SDK is not blocked by the Pages service worker's cross-origin isolation policy. `/demo/` and the heavyweight WebVM isolation boundary remain unchanged.

Exact-head Factory ownership, clean install, measured binding, Control Plane, Controller/provider, Command Station, Browser VM Demo, Pages, and maintainer approval were PASS before merge.

## Exact-current-main qualification

The first exact-current-main push/deployment workflows after #189 were **still queued at the latest observation**. Do not call current main post-merge-qualified on the basis of pre-merge #189 CI.

Required interpretation:

- accepted bytes on main: **PASS**;
- #189 exact-head pre-merge technical qualification: **PASS within named workflows**;
- first merged-sha workflow/deployment set: **PENDING**;
- production provider-helper SDK/sign-in verification after #189: **UNKNOWN** until retained evidence exists.

Historical Controller/provider run `35263782697` on `main@e996b585...` remains retained **FAIL** in Python 3.13. #187 diagnoses/repairs that protected-test observation race; the historical failure is not erased.

## iOS/WebKit accepted fallback

The accepted #186 behavior detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to `/walkthrough/?platform=ios-webkit`, preserving desktop WebVM behavior and `?full_vm=1` as an explicit diagnostic override.

This is a supported-device fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation and the lower-level process-kill cause remain open/UNKNOWN.

## Current build order

1. **Complete the first post-#189 merged-sha workflow/deployment observation.** Retain any first-attempt failure rather than rerunning it away.
2. **Verify the provider helper in production after #189 deploys.** SDK load and sign-in availability must be observed on the merged revision before that boundary becomes PASS.
3. **Refresh/requalify #190 against current main.** Its recorded base is the #187 merge before #189; do not integrate stale-head session recovery without fresh exact-head qualification.
4. **Retest the live-provider semantic boundary on the exact deployed current main.** Historical mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` remains `FAIL/BLOCKED`; paid/live provider success stays UNKNOWN until a candidate crosses protocol validation and proceeds through normal verifier/receipt handling.
5. **Physically validate the accepted #186 fallback.** Do not broaden fallback success into a heavyweight-WebVM reliability claim.
6. **Execute true blank-environment installation and recovery/host-loss qualification for the exact release artifact.**
7. **Complete the selected elapsed-soak tier.** Simulation is not elapsed wall-clock soak.
8. **Continue #120/#126 WebVM reliability work.** Do not infer long-run reliability from isolated Pages/preflight success.
9. **Keep #139→ownership-baseline→#134 independent.** #187 does not automatically clear that older protected sequence.
10. **Refresh/requalify #152 and #177 before current release/research claims use them.**
11. **Freeze and run confirmatory research only after operational claims are bounded.**

## Planning and prototype work

- **#188** — additive AQ-GOV-001 unanimous-consensus authority-escalation lab; unaccepted research candidate, no kernel/container/hypervisor/broker escape claim.
- **#190** — provider BroadcastChannel recovery candidate; based on pre-#189 main and requires refresh/requalification.
- **#191** — automated PR-review workflow candidate; unaccepted and not governance until merged/qualified.
- **#160/#161/#162/#163/#164/#166/#167** — IE-001→IE-007 specification/test-planning branches; no accepted production/performance/research claim.
- **#177** — IE-001 prototype candidate; reconcile/refresh before final qualification.
- **#178** — documentation-only IE-002→IE-007 implementation backlog; no runtime speedup/token/cost/routing/GPU claim.
- **#175** — specification-only OpenViking/context-provider proposal; no accepted runtime dependency.
- **#152** — Qualification v1 framework; refresh required before current release use.
- **#139 / #134** — separate protected M4/dependent hardening sequence with its own ownership-baseline obligations.

Planning artifacts and prototype-only candidates must not be counted as accepted production capability or used as a reason to change `implementation-status.yaml` by themselves.

## Release evidence rule

A merge onto main establishes that the accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.
