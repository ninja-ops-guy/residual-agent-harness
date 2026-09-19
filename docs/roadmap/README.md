# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; exact-revision workflow results remain authoritative |
| Factory M2/M3/M4 | Implemented; protected claims remain exact-revision/environment bound and universal capable-runner qualification is not implied |
| Station budget/deadline admission | #288 accepted; pre-dispatch runner/reviewer admission and exact run-control-bound export eligibility are current behavior; stronger repaired-path empirical claims still need fresh requalification |
| Mission Control/WebVM lifecycle | Exact-current-main production Pages is **FAIL** on run `35437556200`; #336 has a branch-only generated Pages **PASS** but is held behind #337 governance repair, fresh exact-head qualification, maintainer attestation, merge, and a new main SHA's own first production Pages attempt |
| Native setup path | #200 hardening is accepted; blank-environment qualification remains open |
| Live provider acceptance | Historical retained Puter failure remains scoped to its exact run; exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN** |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Research Workbench | Draft #323; #288 prerequisite is accepted, but #323 must still be rebased/requalified before the first authoritative trial, which remains **BLOCKED** |
| Residual Studio | Draft #325; first IDE/control-plane observer slice exists on a branch, but authoritative mutation wiring and full qualification remain incomplete |
| Core security hardening | #328 accepted for core execution/egress/XML hardening; #330 accepts workflow checkout credential-persistence hardening. This is scoped accepted security work, not blanket security qualification |
| CSP / anti-clickjacking | #320 repository configuration accepted; production Vercel response-header/Aikido validation remains **UNKNOWN / pending** |
| Qualification-v1 | #333 synced current main into `testing/qualification-v1`; #152 is now at `11c0ac67...` and exact-head run `35443955204` is **FAIL** on three required gates. Predecessor `24816ebc...` positive evidence remains historical only |
| Release/recovery/soak | True blank-environment install, host-loss/recovery evidence and selected elapsed soak remain gates |
| Autonomous discovery / recursive improvement | Mixed bounded research evidence only; general capability remains **UNKNOWN / not established** and M6-008 remains **BLOCKED** |
| Cooperative mesh efficiency | M6-MESH-001 has one positive bounded two-obligation pilot cell; general performance benefit remains **UNKNOWN / not established** |
| Web Command Station control plane | Proposed/draft under #318; not accepted production capability |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged **#330** on 2026-09-19. No newer production-main commit landed in this check.

Recent accepted changes relevant to roadmap status remain #307 (CI fan-out repair), #260 (provider bootstrap guard), #288 (pre-dispatch budget/deadline authority), #320 (repository-side CSP/anti-clickjacking), #328 (core source/runtime security hardening), and #330 (workflow checkout credential hardening). None expands protected Factory/M4, verifier, evidence-schema, provider, or acceptance authority.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For `main@3bfa6aba...`:

- production Pages run **`35437556200`**, attempt 1: **FAIL**;
- generated artifact/browser proof: **PASS**;
- deployment, served revision identity, and desktop real-guest acceptance: **PASS**;
- required narrow/mobile Chromium acceptance: **FAIL** after reaching the live guest and several Workbench stages;
- retained live-proof artifact: `10582812524`, SHA-256 `868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`;
- lower-level mobile/narrow failure cause: **UNKNOWN**;
- current queued Actions snapshot: **0**;
- every-host/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established**;
- paid/live provider semantic success: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**;
- production Vercel security-header validation: **UNKNOWN / pending**;
- recovery/elapsed-soak qualification: **not established**.

The predecessor `main@0a675017...` production Pages run `35431634267`, attempt 1, remains a scoped exact-revision **PASS**. It is historical evidence after main moved and must not be inherited by `3bfa6aba...`. The still earlier production Pages **FAIL** on `e7b72ad...` likewise remains exact-revision historical evidence. The current `3bfa6aba...` run is an independent first-attempt FAIL; the desktop sub-check PASS does not override the terminal qualification result.

### Focused repair chain

**#336** is the current focused durability repair at exact head `92aca285a9287b73787b552f87aaa42062e73ba4`. Its generated PR Pages run `35438579639` attempt 1 is **PASS**, with named surrounding technical lanes also green. This is branch evidence only. Protected maintainer approval is **FAIL**, and a substantive PR Agent advisory was not established because the review provider exhausted credits and the old publication verifier could mistake the resulting bot failure/status comment for advisory evidence.

**#337** repairs that governance defect by requiring an explicit full-review marker and separating concurrency classes so status-bot comments cannot cancel a legitimate review path. It is open at `46e522b4437d42d68df170285bd3a93366808bd1`; named technical lanes are **PASS**, but PR Agent advisory and protected maintainer approval remain **FAIL**. Therefore #337 is unaccepted, #336 remains on HOLD behind it, and production remains FAIL.

If #337 lands, #336 must rebase/reconcile onto the new `main`, regenerate all merge-relevant exact-head evidence, and receive fresh maintainer attestation. If #336 then lands, the resulting new main must still pass its own first authoritative production Pages attempt. No branch or predecessor PASS is inherited.

## Research and development state

Research branches remain outside accepted production capability unless explicitly merged and qualified.

- **#202** — earlier heterogeneous real-model DAG **FAIL** plus later distinct bounded **PASS**; neither erases the other.
- **#203/#204/#215/#217** — bounded M6 self-host attempts retain **FAIL** evidence.
- **#220 / M6-SPEC-006** — bounded corrected-path **PASS**; not general self-maintenance proof.
- **#206** — Campaign A retains BLOCKED/FAIL repair/DAG/reliability cells.
- **#207/#212** — retain historical accounting/release-ordering and missing-usage failure evidence. #288 repairs the accepted product path, but those frozen cells do not become PASS; affected stronger claims need repaired-path requalification.
- **#257 / M6-SPEC-007J** — first bounded autonomous-discovery **PASS at formal MeasurementGap admission**.
- **#264** — integrity-valid workflow/receipt but scientific conclusion **UNKNOWN** because metric identity/semantics were ambiguous.
- **#274 / 007S** — bounded **PASS** for registry/receipt semantic binding.
- **#273/#277** — retained provenance/planner **FAIL** cells; #277 demonstrates host-owned provenance binding while the overall trial still fails at Planner transcription.
- **#319 / M6-MESH-001 Trial 0** — bounded apparatus/task success with an observed concurrency wall-time advantage across three repeats on one host. General mesh/swarm efficiency remains **UNKNOWN / not established**.
- **#323** — built-in Research Workbench remains draft. #288 is accepted, satisfying the first prerequisite, but its first authoritative trial remains **BLOCKED** pending rebase and fresh qualification.
- **#325** — first Residual Studio IDE/control-plane slice remains draft/unaccepted; authoritative mutation wiring and full qualification remain incomplete.
- **#326** — Mission Control time-travel debugger remains branch-scoped unless separately accepted; it is a read-only historical debugger, not deterministic execution replay.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its declared positive semantic/derivation gates are satisfied. General cooperative mesh/swarm efficiency likewise remains **UNKNOWN / not established** until larger frozen measurements establish a durable effect without verifier-success loss.

## Security work still open

Accepted work and remaining evidence must be kept distinct:

- **#320:** repository-side CSP/anti-clickjacking policy is accepted; production Vercel response-header/Aikido validation is **UNKNOWN / pending**.
- **#328:** core source/runtime security hardening is accepted.
- **#330:** workflow checkout credential-persistence hardening is accepted.
- **#324:** stale overlapping predecessor; it must not be merged wholesale.
- **#321/#322:** scanner-generated candidates remain separate and are not acceptance evidence merely because vendor confidence is high.
- **#152:** exact current testing-branch Qualification-v1 is **FAIL** and governance remains unsatisfied; no branch result can be promoted into current-main capability.

Do not describe this as blanket security qualification. Each accepted change is scoped to reviewed bytes and retained evidence.

## Qualification infrastructure

Issue **#305** remains historical evidence of severe queue saturation. **#307 is merged** as the structural duplicate feature-branch fan-out repair. The current queued-run snapshot is **0**, which is current operational state only and does not erase the historical saturation record.

Production Pages/main first-attempt evidence remains non-cancelling. Queue recovery or CI deduplication does not authorize skipping, cancelling, or rewriting required qualification outcomes.

Qualification-v1 remains separate testing-branch evidence. PR **#333** reverse-merged current `main` into `testing/qualification-v1`, moving open PR **#152** to exact head `11c0ac67f60f61a7243bcc79ce803d588a89aa94`. Exact-head Qualification-v1 run **`35443955204` attempt 1 = FAIL**. The retained final manifest names three required failures:

- `deterministic-regression=FAIL`: seven enterprise sandbox tests failed because the hosted runner reported `kernel-level sandbox isolation unavailable`; 1,817 tests passed, 29 skipped, and 387 subtests passed in that gate.
- `qualification-selftests=FAIL`: the full provider-mission qualifier returned FAIL; 38 sibling selftests passed.
- `toxic-provider-matrix=FAIL`: the same provider-mission qualifier returned FAIL; seven sibling tests passed.

The lower-level provider-mission cause remains **UNKNOWN** from retained evidence, and the final failure ledger leaves these required failures **UNCLASSIFIED**. Factory ownership, M4 prerequisites, Browser VM Demo, Controller/provider, Command Station, clean install, Factory runtime/OS evidence, Control Plane, measured-evaluation binding, and generated PR Pages proof are **PASS** on the exact current testing head, but they do not override the overall required-gate FAIL. Protected maintainer approval and PR Agent advisory are also **FAIL**.

The predecessor `24816ebc...` technical PASS remains historical exact-head evidence and is not inherited after #333 changed the branch head.

## Current build order

1. **Fix PR-review governance first.** Review and qualify #337. Do not attest/merge #336 ahead of it. If #337 lands, reconcile #336 to the new main and rerun all merge-relevant exact-head gates; after any #336 merge, require the new main SHA's first production Pages attempt to PASS.
2. **Diagnose exact-head #152 Qualification-v1 failures.** Preserve run `35443955204` attempt 1, including deterministic sandbox-unavailable failures and the provider-mission failures; do not rerun an unchanged head merely to obtain green.
3. **Requalify the repaired #288 authority path.** Retain fresh evidence for budget exhaustion, unknown usage, terminal verifier/release ordering, and export binding before making stronger present-tense claims.
4. **Rebase/requalify Research Workbench #323** before M6-WB-001 can run authoritatively.
5. **Validate #320 on production Vercel.** Inspect actual response headers and rerun the relevant security check; configuration merge alone is not production-header PASS.
6. **Retain fresh exact-current-deployed live-provider evidence.** A real-account Puter mission must cross protocol validation into ordinary candidate/verifier/receipt handling before live-provider success can become PASS.
7. **Continue bounded M6 discovery/derivation and M6-MESH measurement** without promoting pilot results into product capability; keep M6-008 blocked until explicit gates are met.
8. **Execute true blank-environment installation, recovery/host-loss qualification, selected elapsed soak, and physical/mobile validation** for the exact release path.
9. **Continue #120/#126 WebVM reliability work** and preserve historical negative evidence.
10. **Keep protected sequences independent.** Factory ownership/qualification paths must not inherit unrelated green CI.
11. **Freeze confirmatory research before outcome access.** Preserve negative, blocked, unknown, and missing cells.

## Release evidence rule

A merge onto main establishes that accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, production security headers, recovery, or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.
