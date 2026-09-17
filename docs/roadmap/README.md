# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; latest exact-current-main run is **PASS**, while historical exact-revision failures remain retained evidence |
| Factory M2/M3/M4 | Implemented; exact-revision/environment qualification and protected-byte governance remain authoritative |
| Mission Control/WebVM lifecycle | #159 recovery, #153 browser acceptance proof, #169 diagnostics, #179 build-output handling, #183 provider-session lifecycle, and #185/#186 iOS fallback integration are on main; long-run and physical heavy-WebVM reliability remain unqualified |
| iOS/WebKit release behavior | Accepted #186 fallback routes the unsupported/unqualified iOS WebKit profile to the walkthrough before heavyweight boot; current preflight CI is PASS, physical-device validation remains open |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Release/recovery/soak | True blank-environment install, recovery/host-loss evidence and selected elapsed soak remain gates |
| Live provider acceptance | Historical retained Puter failure remains **FAIL/BLOCKED**; exact-current-main paid/live provider success remains **UNKNOWN** until retained candidate→verifier→receipt evidence exists |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`e996b58566847e88153e6e5196625d52b93e081a`**, created by merged **#185** from final candidate head `068954dd6c1c9a56c9a18fbbce67b1504e2c4b7d`.

The merge accepts the stabilization lineage's protected `residual/factory/runtime_journal.py` writer-admission change, corresponding `verifier/v3/factory_ownership_baseline.json` advance, and #186 iOS/WebKit pre-boot walkthrough fallback. The final candidate received exact-head maintainer attestation before merge.

The protected runtime-journal change remains narrowly scoped: bounded retry applies only to mutation-free SQLite writer transaction admission on genuine BUSY/LOCKED contention. Once transaction admission succeeds, journal mutation and COMMIT are not replayed. Acceptance of these bytes does not imply universal Factory/M4 qualification or erase unrelated historical failures.

## Exact-current-main qualification

Latest observed applicable current-main runs are PASS:

- Factory ownership gate — `35264069644`
- Clean install qualification — `35264069698`
- Measured evaluation acceptance binding — `35264069745`
- M4 qualification runner prerequisites — `35264069726`
- Controller and provider contracts — `35264069649`
- Command Station checks — `35264069706`
- iOS WebKit preflight — `35264069648`
- Deploy GitHub Pages — `35263783090`, attempt 1

Retain the earlier same-SHA **Controller/provider FAIL** run `35263782697` in Python 3.13. The later same-SHA PASS does not erase it, and the exact cause remains **UNKNOWN** from the retained evidence reviewed here.

The prior `main@2e1341c9...` Command Station run `35219212073` also remains historical FAIL evidence. Current-main Command Station is PASS; that does not rewrite the older result.

## iOS/WebKit accepted fallback

PR #182 is closed unmerged and superseded. PR **#186** was integrated through #185 and is now on main.

The accepted behavior detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to `/walkthrough/?platform=ios-webkit`, preserving desktop WebVM behavior and `?full_vm=1` as an explicit diagnostic override.

Dedicated current-main iOS WebKit preflight is **PASS**. The claim remains narrow: this is a supported-device fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation and the lower-level process-kill cause remain open/UNKNOWN.

## Inference-economics planning

Draft specification PRs **#160, #161, #162, #163, #164, #166, and #167** stage corrected integration-authority contracts for IE-001→IE-007. They remain specification/test-planning branches only; they do not establish accepted runtime capability, performance improvement, cost reduction, scheduling/routing safety, or research results.

Merged #168 defines normal repository merge control as `automated qualification/review appropriate to scope -> exact-head maintainer attestation -> merge`. Independent human or third-party review remains useful and may be claim-specific, but is not the generic repository-wide merge prerequisite.

PR **#177 remains a candidate**. Its prior focused PASS/maintainer evidence is bound to its candidate head and must be reconciled/refreshed against the current IE-001 contract and applicable current-main qualification before final IE-001 qualification is claimed.

## Current build order

1. **Preserve the same-SHA Controller/provider FAIL.** Keep run `35263782697` as retained evidence and keep its cause UNKNOWN unless retained evidence identifies it.
2. **Physically validate the accepted #186 fallback after publication.** Do not broaden walkthrough success into a heavy-WebVM reliability claim.
3. **Retest the live-provider semantic boundary on exact deployed current main.** Historical mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` remains `FAIL/BLOCKED`; paid/live provider success stays UNKNOWN until a valid candidate crosses protocol validation and proceeds through normal verifier/receipt handling, or the release claim explicitly excludes it.
4. **Execute true blank-environment installation for the exact release artifact.** Rehearsal/procedure evidence is not release PASS.
5. **Retain recovery/host-loss evidence for the selected deployment mode.** Do not promote simulation into real-environment claims.
6. **Complete the selected elapsed-soak tier.** Simulation is not elapsed wall-clock soak; retain first failures rather than green-only summaries.
7. **Continue #120/#126 WebVM reliability work.** Do not infer long-run reliability from isolated Pages/preflight success or from the iOS walkthrough fallback.
8. **Keep the older protected #139→ownership-baseline→#134 sequence separate.** The accepted #185 runtime-journal history does not clear the older protected M4 observation-race lineage.
9. **Refresh/requalify #152 before using it as current release evidence.** Older aggregate qualification does not automatically qualify current main.
10. **Reconcile/refresh #177 against the current IE-001 contract before final qualification.** Prior prototype evidence remains historical to that candidate head.
11. **Freeze and run confirmatory research only after operational claims are bounded.** Lock workload, models/configuration, verifier policy, evidence path, metrics and analysis before R0–R5/degradation/heterogeneous-routing outcome access.

## Release evidence rule

A merge onto main establishes that the accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later exact-head runs pass.

## Planning and prototype work

- **#160/#161/#162/#163/#164/#166/#167** — IE-001→IE-007 specification/test-planning branches; no accepted production/performance/research claim.
- **#180** — narrow generated-build consistency candidate; unaccepted until applicable refresh/requalification.
- **#177** — IE-001 prototype candidate; reconcile/refresh before final qualification.
- **#178** — documentation-only IE-002→IE-007 implementation backlog; no runtime speedup/token/cost/routing/GPU claim.
- **#175** — specification-only OpenViking/context-provider proposal; no accepted runtime dependency.
- **#152** — Qualification v1 framework; refresh required before current release use.
- **#139 / #134** — separate protected M4/dependent hardening sequence with its own ownership-baseline obligations.

Planning artifacts and prototype-only candidates must not be counted as accepted production capability or used as a reason to change `implementation-status.yaml` by themselves.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents remain useful for lineage, but they do not override current code, exact-commit evidence, retained failures, current governance or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
