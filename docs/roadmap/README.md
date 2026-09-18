# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; exact-revision workflow results remain authoritative |
| Factory M2/M3/M4 | Implemented; protected claims remain exact-revision/environment bound and universal capable-runner qualification is not implied |
| Mission Control/WebVM lifecycle | Bounded recovery, diagnostics, iOS fallback, provider publication, and #205 reload/remount channel recovery are accepted; long-run and physical heavyweight-WebVM reliability remain unqualified |
| Native setup path | #200 hardening is accepted; persistent XDG defaults, loopback binding, opt-in shell macro, bounded venv repair, and constrained shell-rc edits are current behavior; blank-environment qualification remains open |
| Live provider acceptance | Historical retained Puter failure remains **FAIL/BLOCKED**; exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN** |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Release/recovery/soak | True blank-environment install, host-loss/recovery evidence and selected elapsed soak remain gates |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`4608afabf5de4c87d77aaf149dfc12538d364f43`**.

### #200 — native setup hardening

Merged #200 accepts the safer setup defaults and repair behavior described above. It improves onboarding ergonomics and local safety, but does **not** establish a truly blank-machine installation result or broad host portability.

### #205 — provider-channel reload recovery

Merged #205 accepts session-scoped restoration of the private browser provider channel across Mission Control reload/remount. Restored tokens are validated fail-closed and explicit close clears the stored token.

This closes the accepted-byte lifecycle gap targeted by older provider-channel recovery work, but it does **not** establish successful paid/live Puter inference or production provider-helper sign-in on the exact deployed revision.

## Exact-current-main qualification

For exact `main@4608afa...`, the retained exact-SHA Actions query used for this status refresh returned a completed set with no pending, cancelled, or failing run observed; a sampled Controller/provider workflow completed **PASS on attempt 1**.

Required interpretation:

- exact-main named automated gates: **PASS where retained exact-SHA runs report PASS**;
- historical exact-revision failures: **remain retained evidence**;
- every-host/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established**;
- paid/live provider semantic success: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**;
- recovery/elapsed-soak qualification: **not established**.

## Research and development state

Research branches remain outside accepted production capability unless explicitly merged and qualified.

- **#202** — an earlier heterogeneous real-model DAG run remains **FAIL**; a later distinct exact-head run is a bounded **PASS** with 3/3 tasks integrated, retained receipts, dependency lineage, deliberate repair pressure, and release export. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.
- **#203** — first-authoritative M6 ImprovementSpec self-host trial remains **FAIL**.
- **#204** — stronger-model M6-SPEC-002 authoritative trial remains **FAIL**: 0/1 integrated, max-iteration escalation, no verification receipt and no release.
- **#206** — M6 stress campaign A remains **PENDING** at the latest observation; its dedicated workflow is still in progress and no result is promoted here.
- **#207** — deterministic stress campaign B retained mixed results. STRESS-B1 is **FAIL** because exhausted-budget accounting was observed only after accepted integration/release; STRESS-B2 is a scoped **PASS** early-convergence control; STRESS-B3 is **FAIL** because a non-empty release materialized after terminal verifier failure; STRESS-B4 contains corrupt candidates in the exact scenario but does not recover to task success within the frozen pass budget.

## Current build order

1. **Repair and requalify the #207 governance-ordering failures.** Budget exhaustion and terminal verifier failure must block release/accepted-state materialization before stronger fail-closed claims are made.
2. **Retain fresh exact-current-deployed live-provider evidence.** A real-account Puter mission must cross protocol validation into ordinary candidate/verifier/receipt handling before live-provider success can become PASS.
3. **Physically validate the #186 iOS fallback** without broadening fallback success into heavyweight-WebVM reliability.
4. **Execute true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak** for the exact release artifact.
5. **Continue #120/#126 WebVM reliability work** and preserve historical negative evidence.
6. **Resolve the #133/#132 retirement-versus-restoration discrepancy** explicitly rather than reconstructing absent capability in prose.
7. **Keep #139→ownership-baseline→fresh-qualification→#134 independent.** Unrelated green CI does not clear that protected sequence.
8. **Refresh/requalify broader stale candidates such as #152/#177** before current release/research claims use them.
9. **Freeze and run confirmatory research only after operational claims are bounded.** Preserve negative and missing cells.

## Release evidence rule

A merge onto main establishes that accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.