# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; exact-revision workflow results remain authoritative |
| Factory M2/M3/M4 | Implemented; protected claims remain exact-revision/environment bound and universal capable-runner qualification is not implied |
| Mission Control/WebVM lifecycle | Bounded recovery, diagnostics, iOS fallback and provider/session hardening are accepted; exact-current-main production Pages is **FAIL** and long-run/physical heavyweight-WebVM reliability remains unqualified |
| Native setup path | #200 hardening is accepted; persistent XDG defaults, loopback binding, opt-in shell macro, bounded venv repair and constrained shell-rc edits are current behavior; blank-environment qualification remains open |
| Live provider acceptance | Historical retained Puter failure remains **FAIL/BLOCKED**; exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN** |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Release/recovery/soak | True blank-environment install, host-loss/recovery evidence and selected elapsed soak remain gates |
| Autonomous discovery / recursive improvement | Mixed bounded research evidence only; general capability remains **UNKNOWN / not established** and M6-008 remains **BLOCKED** |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`e7b72ad18df5729f16d36771971c8a8828d71a10`**.

Recent accepted changes relevant to roadmap status:

### #275 — exact-head maintainer approval publication

Merged #275 closes #268 by ensuring a valid explicit exact-head human attestation can publish the protected `maintainer-approval` result to the exact live PR head. This is governance hardening only; it does not expand model, verifier, Factory/M4, provider or acceptance authority.

### #276 — mandatory production Pages attempt for every main SHA

Merged #276 closes #267 by removing the prior `push.paths` bypass from the production Pages gate. Every new `main` SHA must now receive its own non-cancelling authoritative production Pages attempt.

The first authoritative production Pages attempt for exact current main is run **`35410875305`**, attempt 1, and is **FAIL**. Generated desktop+narrow proof and deployment passed; published live guest verification failed and subsequent narrow published acceptance was skipped. Exact lower-level root cause remains **UNKNOWN from the inspected retained metadata**. This result is not evidence of paid/live Puter or model-quality failure.

## Exact-current-main qualification

Required interpretation for `main@e7b72ad...`:

- Controller/provider, Command Station and Factory ownership have retained **PASS** results in their named exact-main workflow scopes;
- production Pages run `35410875305`, attempt 1: **FAIL**;
- generated browser proof: **PASS**;
- deployment: **PASS**;
- published live guest verification: **FAIL**;
- published narrow follow-up: **NOT RUN / skipped** after the desktop failure;
- every-host/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established**;
- paid/live provider semantic success: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**;
- recovery/elapsed-soak qualification: **not established**.

A green named gate does not erase a failing sibling gate, and a later revision cannot retroactively make this exact-main first production attempt PASS.

## Research and development state

Research branches remain outside accepted production capability unless explicitly merged and qualified.

- **#202** — earlier heterogeneous real-model DAG **FAIL** plus later distinct bounded **PASS**; neither erases the other.
- **#203/#204/#215/#217** — authoritative bounded M6 self-host attempts remain **FAIL**.
- **#220 / M6-SPEC-006** — bounded corrected-path **PASS**; not general self-maintenance proof.
- **#206** — Campaign A retains BLOCKED/FAIL repair/DAG/reliability cells.
- **#207/#212** — retain accounting/release-ordering **FAIL** evidence that blocks stronger fail-closed authority claims until repaired and requalified.
- **#257 / M6-SPEC-007J** — first bounded autonomous-discovery **PASS at formal MeasurementGap admission**.
- **#264** — integrity-valid workflow/receipt but scientific conclusion **UNKNOWN** because metric identity/semantics were ambiguous.
- **#274 / 007S** — bounded **PASS** for registry/receipt semantic binding.
- **#273/#277** — retained provenance/planner **FAIL** cells; #277 demonstrates host-owned provenance binding while the overall trial still fails at Planner transcription.
- **#265/#270/#298/#299/#300** — Metric Registry and proof-carrying derivation-graph work remain trust/research infrastructure, not accepted production capability.
- **#293** — M7 governed recursive self-improvement bootstrap is unaccepted and explicitly preserves an external promotion gate.
- **#313/#314** — new A2A and Vector/Wire-Pod experiments are draft/unaccepted; they do not modify current accepted authority or empirical claims.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its declared positive semantic/derivation admission gates are satisfied.

## Qualification infrastructure

Issue **#305** remains open after a retained snapshot of 1,267 queued Actions runs and 15 in progress on 2026-09-18. Queue pressure is an operational qualification blocker, not a reason to weaken or reinterpret gates.

Open **#307** is a candidate repair for duplicate feature-branch CI fan-out. It remains unmerged and therefore does not clear #305. Production Pages/main first-attempt evidence must remain non-cancelling.

Qualification-v1 work under #152/#303/#312 remains on the separate testing branch and does not alter current production `main` or broaden M4 claims.

## Current build order

1. **Repair the exact-current-main production Pages FAIL.** Diagnose run `35410875305`, preserve its first-attempt failure, fix on a new revision and require that revision's own production attempt.
2. **Repair and requalify #207/#208/#212 authority-ordering failures.** Budget/unknown-usage and terminal verifier state must prevent later accepted-state/release effects before stronger claims are made.
3. **Retain fresh exact-current-deployed live-provider evidence.** A real-account Puter mission must cross protocol validation into ordinary candidate/verifier/receipt handling before live-provider success can become PASS.
4. **Continue bounded M6 discovery/derivation work without promoting it into product capability.** Preserve mixed PASS/FAIL/UNKNOWN evidence; keep M6-008 blocked until its explicit gates are met.
5. **Physically validate the #186 iOS fallback** without broadening fallback success into heavyweight-WebVM reliability.
6. **Execute true blank-environment installation, recovery/host-loss qualification and selected elapsed soak** for the exact release artifact.
7. **Continue #120/#126 WebVM reliability work** and preserve historical negative evidence.
8. **Reduce Actions queue saturation under #305** without cancelling required first-attempt production evidence; #307 remains unaccepted until merged and observed effective.
9. **Keep protected sequences independent.** #139→ownership-baseline→fresh-qualification→#134 and Qualification-v1 evidence must not inherit unrelated green CI.
10. **Freeze confirmatory research before outcome access.** Preserve negative, blocked, unknown and missing cells.

## Release evidence rule

A merge onto main establishes that accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.