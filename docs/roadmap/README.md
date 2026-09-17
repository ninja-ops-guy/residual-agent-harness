# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; exact-current-main push qualification remains mixed because run `35219212073` is retained **FAIL** on Python 3.11 |
| Factory M2/M3/M4 | Implemented; exact-revision/environment qualification and protected-byte governance remain authoritative |
| Mission Control/WebVM lifecycle | #159 fresh-overlay recovery, #153 browser acceptance proof, #169 diagnostics, #179 bounded build-output handling and #183 provider-session lifecycle recovery are merged on main; physical iPhone heavy-WebVM reliability remains unqualified |
| iOS/WebKit release behavior | #182 is closed unmerged; #186 supersedes it on the release-stabilization branch with a pre-boot walkthrough fallback, not a heavy-WebVM reliability claim |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Release/recovery/soak | Active stabilization work; true blank-environment install, recovery/host-loss evidence and selected elapsed soak remain gates |
| Live provider acceptance | Historical retained Puter failure remains **FAIL/BLOCKED**; final-RC paid/live provider success remains **UNKNOWN** unless retained evidence crosses candidate→verifier→receipt |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**.

Recent accepted sequence includes #159, #168, #153, #171/#173, #169, #179 and #183. The final #183 candidate head completed its observed exact-head PR qualification and maintainer gate before merge.

Exact merged-main qualification is **not all-green**. Six of seven observed push workflows are PASS. Command Station run `35219212073`, attempt 1, remains **FAIL** on Python 3.11. The failure is now identified to `test_sandbox_timing_determinism.JournalContentionReadTests.test_readiness_polling_survives_concurrent_writer`, which observed `AUDIT_FAILED`/`OperationalError`; Python 3.12, Python 3.13, browser and Docker passed. Deploy GitHub Pages run `35219212133`, attempt 1, is PASS.

This retained main failure is not erased by later green candidate work.

## Release stabilization — PR #185

Draft **#185** is now the isolated release-candidate integration lane. It started from exact current main and intentionally keeps release-critical fixes off `main` until one final exact stabilization head satisfies the retained exit criteria.

Current stabilization head: **`068954dd6c1c9a56c9a18fbbce67b1504e2c4b7d`**.

On that exact head GitHub reports 15 successful workflow runs and one failed workflow run. The failed workflow is the **maintainer approval gate**, so the candidate remains **BLOCKED** for promotion. Command Station is PASS on the stabilization head, but that is candidate evidence only.

The stabilization lineage includes a protected change to `residual/factory/runtime_journal.py` plus an advance of `verifier/v3/factory_ownership_baseline.json`. The change introduces bounded retry only for mutation-free writer transaction admission on genuine SQLite BUSY/LOCKED contention; journal mutation and COMMIT are not replayed after transaction admission.

Because that diff changes a protected Factory blob and an ownership baseline, green CI does **not** make it automatically mergeable. Deliberate protected-byte review, ownership-baseline review, fresh exact-head qualification after the pin change, and exact-head maintainer attestation remain required.

## iOS/WebKit stabilization — #186

PR **#182 is closed unmerged and superseded**.

PR **#186 merged into `release/stabilization-2026-09-17`**, not main. It routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight guest/disk boot, while preserving desktop WebVM behavior and retaining `?full_vm=1` as an explicit diagnostic override.

The release claim remains narrow: this is a supported-device fallback. It does **not** establish that heavyweight WebVM is reliable on physical iPhone Safari, and physical-device validation of the published RC remains required.

## Inference-economics planning refresh

Draft specification PRs **#160, #161, #162, #163, #164, #166, and #167** have been refreshed onto accepted `main@2e1341c99fd7b72452e3b8c5278b1f557871b783` and stage corrected integration-authority contracts for the IE-001→IE-007 program. These remain specification/test-planning branches only; they do not establish accepted runtime capability, performance improvement, cost reduction, scheduling/routing safety, or research results.

PR #160 now reconciles its original Q11 language with merged solo-maintainer governance #168. The repository-wide normal merge control is `automated qualification/review appropriate to scope -> exact-head maintainer attestation -> merge`. Independent human or third-party review remains valuable evidence and may still be claim-specific, but it is not the generic repository-wide merge prerequisite.

PR **#177 remains a candidate**. Its existing focused PASS evidence and exact-head maintainer gate are bound to its current prototype head, but that branch/body predates the refreshed #160 contract and still describes independent Q11 review as a universal pending gate. Before final IE-001 qualification, reconcile/refresh #177 against the revised current contract and applicable current-main governance, then requalify the resulting exact head. Do not broaden its prior evidence into final qualification.

## Current build order

1. **Preserve the exact-current-main Command Station FAIL.** Do not rerun unchanged main merely to obtain green. The failing test identity is now known; keep the original run as retained evidence.
2. **Complete #185 protected-byte review.** Review the `runtime_journal.py` candidate and the corresponding Factory ownership-baseline advance as trust-boundary changes. Do not auto-merge them from technical CI alone.
3. **Finish exact-head stabilization qualification.** One final RC head must satisfy all applicable required CI, capable-runner M4, Factory ownership, measured binding and generated browser/Pages proof before promotion.
4. **Resolve the maintainer gate on the final exact head.** Current #185 maintainer approval is `FAIL/BLOCKED`; only an exact-head attestation after the final qualifying head is appropriate.
5. **Physically validate the #186 mobile fallback after publication.** Keep physical heavy-WebVM reliability and lower-level WebKit process-kill cause UNKNOWN unless retained device evidence proves otherwise.
6. **Retest #183 provider-session lifecycle separately.** Follow-up/reload recovery on a physical device is distinct from the WebVM runtime gate.
7. **Retest the live-provider semantic boundary on the final accepted/deployed RC lineage.** Historical mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` remains `FAIL/BLOCKED`; paid/live provider success remains UNKNOWN until a valid candidate crosses protocol validation and proceeds through normal verifier/receipt handling, or the release claim explicitly excludes it.
8. **Execute true blank-environment installation for the exact RC artifact.** Rehearsal/procedure evidence is not production release PASS.
9. **Retain recovery/host-loss evidence for the selected deployment mode.** Do not promote simulated recovery into real-environment claims.
10. **Complete the selected elapsed-soak tier.** Simulation is not elapsed wall-clock soak; retain first failures rather than green-only summaries.
11. **Continue #120/#126 WebVM reliability work.** Do not infer long-run reliability from isolated Pages/browser success or from the iOS walkthrough fallback.
12. **Keep the older protected #139→ownership-baseline→#134 sequence separate.** The #185 runtime-journal protected change is a different trust-boundary history and does not clear the older protected M4 observation-race lineage.
13. **Refresh/requalify #152 before using it as release evidence.** Older aggregate qualification does not automatically qualify the current RC.
14. **Reconcile/refresh #177 against the revised #160 contract before final IE-001 qualification.** Prior 203-PASS prototype evidence remains historical to that candidate head; under merged #168, independent human review is not a generic repository-wide merge prerequisite unless a claim-specific rule requires it.
15. **Freeze and run confirmatory research only after release claims are bounded.** Lock workload, models/configuration, verifier policy, evidence path, metrics and analysis before R0–R5/degradation/heterogeneous-routing outcome access.

## Release promotion rule

Do not merge release-hardening commits from #185 piecemeal into main merely because isolated tests are green. Promotion should occur only when one final exact stabilization head satisfies the chosen release tier, the retained evidence package is reviewable, release notes match the evidence, and exact-head maintainer attestation exists.

Any change touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, or equivalent trust-boundary material requires the applicable deliberate review. Documentation must not silently convert those changes into accepted facts.

## Planning and prototype work

- **#160/#161/#162/#163/#164/#166/#167** — refreshed IE-001→IE-007 specification/test-planning branches with corrected integration-authority contracts; no accepted production/performance/research claim.
- **#180** — narrow generated-build consistency candidate; unaccepted until refreshed/requalified on the applicable lineage.
- **#177** — IE-001 prototype qualification candidate; must be reconciled/refreshed against revised #160/current governance before final qualification is claimed.
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

These documents remain useful for lineage, but they do not override current code, exact-commit evidence, retained failures, release-stabilization policy, current governance or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
