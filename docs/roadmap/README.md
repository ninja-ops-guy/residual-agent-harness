# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; #218 bounded repair-loop remediation is accepted; exact-revision workflow results remain authoritative |
| Factory M2/M3/M4 | Implemented; protected claims remain exact-revision/environment bound and universal capable-runner qualification is not implied |
| Mission Control/WebVM lifecycle | Bounded recovery, diagnostics, iOS fallback, provider publication, #205 reload/remount channel recovery, #218 shared repair ceiling, and #201 inline provider/guided UX are accepted; long-run and physical heavyweight-WebVM reliability remain unqualified |
| Native setup path | #200 hardening is accepted; persistent XDG defaults, loopback binding, opt-in shell macro, bounded venv repair, and constrained shell-rc edits are current behavior; blank-environment qualification remains open |
| Live provider acceptance | Historical retained Puter failure remains **FAIL/BLOCKED**; exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN** |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| M6 repair-loop research | #220 retains one bounded corrected-runtime **PASS**; earlier #203/#204/#215/#217 failures remain retained, so general autonomous self-maintenance remains **UNKNOWN / not established** |
| Release/recovery/soak | True blank-environment install, host-loss/recovery evidence and selected elapsed soak remain gates |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`**.

### #200 — native setup hardening

Merged #200 accepts safer setup defaults and repair behavior. It improves onboarding ergonomics and local safety, but does **not** establish a truly blank-machine installation result or broad host portability.

### #205 — provider-channel reload recovery

Merged #205 accepts session-scoped restoration of the private browser provider channel across Mission Control reload/remount. Restored tokens are validated fail-closed and explicit close clears the stored token. This does **not** establish successful paid/live Puter inference.

### #218 — bounded Station repair-loop remediation

Merged #218 accepts bounded previous-candidate repair context for declared writable files while preserving fresh baseline worktrees for subsequent candidates. Repair-context file hashes are retained, the runner contract separates transport JSON from file-language content, and Mission Control/Store share a five-attempt ceiling.

The accepted change preserves deterministic checks, review, receipts, integration, quarantine, promotion, verifier authority, and Factory/M4 trust boundaries. It is an engineering remediation, not proof of general repair reliability or autonomous self-maintenance.

### #201 — guided proof and inline Puter setup

Merged #201 accepts the frontend/guided-provider UX. The public site separates guided proof from the interactive WebVM lab, adds accessible real-command animation and local quickstart guidance, aligns Mission Control with the public visual system, and keeps RESIDUAL's Puter setup inline. Puter's secure authorization popup may still appear; authorization remains bound to explicit user gesture, credentials remain outside RESIDUAL, loading remains lazy, and provider protocol handling remains fail-closed.

This is accepted UI/provider-boundary behavior, **not** retained proof of paid/live provider semantic success.

## Exact-current-main qualification

PR #201's exact head `4e172aed...` completed **PASS** for Control Plane, Factory ownership, measured-evaluation binding, clean install, Browser VM Demo, Pages, Command Station, Controller/provider, and maintainer approval before merge.

Exact merged `main@260b5f9...` has a new seven-workflow ordinary `push` set. That exact-SHA set is **PENDING** at this status check; at least Pages/deployment remains in progress. Required interpretation:

- #201 exact PR-head named automated gates: **PASS**;
- exact merged-main ordinary push gates: **PENDING** until their exact-SHA runs complete;
- historical exact-revision failures: **remain retained evidence**;
- every-host/capable-runner M4 qualification: **not established**;
- true blank-environment install: **not established**;
- paid/live provider semantic success: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**;
- recovery/elapsed-soak qualification: **not established**.

## Research and development state

Research branches remain outside accepted production capability unless explicitly merged and qualified.

- **#202** — an earlier heterogeneous real-model DAG run remains **FAIL**; a later distinct exact-head run is a bounded **PASS** with 3/3 tasks integrated, retained receipts, dependency lineage, deliberate repair pressure, and release export. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.
- **#203/#204** — first-authoritative M6 ImprovementSpec self-host trials remain **FAIL**, 0/1 integrated with no verification receipt/release.
- **#206** — Campaign A remains mixed/negative in the retained cells: A4 **BLOCKED / invalid intervention**, A5 **FAIL / incomplete** at 3/6 integrated, A6 **FAIL in scope** at 0/3 successful Qwen2.5-Coder 7B trials.
- **#207** — deterministic Campaign B retained mixed results. STRESS-B1 is **FAIL** because exhausted-budget accounting was observed only after accepted integration/release; STRESS-B2 is a scoped **PASS** early-convergence control; STRESS-B3 is **FAIL** because a non-empty release materialized after terminal verifier failure; STRESS-B4 contains corrupt candidates in the exact scenario but does not recover to task success within the frozen pass budget.
- **#212** — deterministic Campaign C adds bounded containment/recovery PASS cells for malformed runner output, invalid reviewer schema, and denial→approval recovery, while the missing-usage case is a **FAIL** for accounting-before-authority because integration plus a receipt occurred before the later `usage_unknown_or_invalid` abort. The transient-500 case did not establish provider failover success.
- **#215/#217** — M6-SPEC-003/-004 remain authoritative **FAIL** results despite exercising prior-candidate repair context and transport/source clarification.
- **#220** — M6-SPEC-006 is a bounded corrected-runtime **PASS** on exact experiment head `7971a057...` using local Qwen2.5-Coder 7B. The first two candidates were rejected by the frozen checks; the third passed 2/2 checks, review approved, 1/1 integrated, a receipt was issued, and release export completed. This is one positive trial, not general autonomous self-maintenance/reliability.
- **#214** — draft repair candidate for #208 remains open/unaccepted and is still based on predecessor `main@4608afa...`; after #218/#201 it must be refreshed and requalified before acceptance. The #207/#212 authority-ordering defects therefore remain open on accepted main.

## Current build order

1. **Complete exact merged-SHA post-#201 qualification.** Preserve any first exact-SHA failure rather than inheriting the green PR-head result.
2. **Refresh and requalify the #207/#208 authority-ordering repair path on current main.** Budget/unknown-usage state and terminal verifier failure must prevent later accepted-state/release effects before stronger fail-closed claims are made; #214 is stale-base and unaccepted.
3. **Expand M6 evidence beyond the single #220 PASS without erasing negative cells.** Run preregistered repeated/self-discovery experiments on accepted #218 behavior while retaining #203/#204/#215/#217 FAILs and withholding autonomous-merge authority.
4. **Re-run a valid #206 repair-pressure intervention and retain the negative DAG/reliability cells.** Do not convert A4's invalid intervention or A5/A6 failures into PASS through workflow success or later reruns.
5. **Retain fresh exact-current-deployed live-provider evidence.** A real-account Puter mission must cross protocol validation into ordinary candidate/verifier/receipt handling before live-provider success can become PASS.
6. **Physically validate the #186 iOS fallback** without broadening fallback success into heavyweight-WebVM reliability.
7. **Execute true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak** for the exact release artifact.
8. **Continue #120/#126 WebVM reliability work** and preserve historical negative evidence.
9. **Resolve the #133/#132 retirement-versus-restoration discrepancy** explicitly rather than reconstructing absent capability in prose.
10. **Keep #139→ownership-baseline→fresh-qualification→#134 independent.** Unrelated green CI does not clear that protected sequence.
11. **Refresh/requalify broader stale candidates such as #152/#177** before current release/research claims use them.
12. **Freeze and run confirmatory research only after operational claims are bounded.** Preserve negative, blocked and missing cells.

## Release evidence rule

A merge onto main establishes that accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.