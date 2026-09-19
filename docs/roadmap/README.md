# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; exact-revision workflow results remain authoritative |
| Factory M2/M3/M4 | Implemented; protected claims remain exact-revision/environment bound and universal capable-runner qualification is not implied |
| Station budget/deadline admission | #288 accepted; stronger repaired-path empirical claims still need fresh requalification |
| Mission Control/WebVM lifecycle | Exact-current-main production Pages is **FAIL** on run `35449637725`; #336 durability repair is accepted but proved necessary rather than sufficient because the later narrow retained-evidence compound assertion still fails |
| PR-Agent advisory governance | #337 accepted; advisory publication now requires substantive full-review evidence and review/status concurrency is separated |
| Native setup path | #200 hardening is accepted; blank-environment qualification remains open |
| Live provider acceptance | Historical retained Puter failure remains scoped to its exact run; exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN** |
| Provider/runtime expansion | #340 Moonshot/Kimi and Kimi Claw/OpenClaw adapters are open/unaccepted implementation work |
| Nested-runtime research | Draft #341 / EXP-NESTED-SWARM-001 is research-only; no general nested-swarm benefit is established |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Research Workbench | Draft #323; first authoritative trial remains **BLOCKED** pending rebase/requalification |
| Residual Studio | Draft #325; first IDE/control-plane observer slice exists on a branch, but authoritative mutation wiring and full qualification remain incomplete |
| Core security hardening | #328/#330 accepted for reviewed source/runtime/workflow scopes; not blanket security qualification |
| CSP / anti-clickjacking | #320 repository configuration accepted; production Vercel response-header/Aikido validation remains **UNKNOWN / pending** |
| Qualification-v1 | #152 is at `aeba996...`; exact-head run `35448856959` is **FAIL** because the deterministic gate remains red despite real bubblewrap provisioning and visible sibling jobs passing |
| Protected RuntimeJournal contention repair | #338 is open/unaccepted and rebased onto current main; it changes protected bytes and the ownership baseline, so explicit trust-boundary review is mandatory and automation must not merge it |
| Release/recovery/soak | True blank-environment install, host-loss/recovery evidence and selected elapsed soak remain gates |
| Autonomous discovery / recursive improvement | Mixed bounded research evidence only; general capability remains **UNKNOWN / not established** and M6-008 remains **BLOCKED** |
| Cooperative mesh efficiency | M6-MESH-001 has one positive bounded two-obligation pilot cell; general performance benefit remains **UNKNOWN / not established** |
| Web Command Station control plane | Proposed/draft under #318; not accepted production capability |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`d89c5d940a32d8a7df4dd55e699c158fff5f615c`**, produced by merged **#336** on 2026-09-19 after merged **#337**.

The new accepted changes are scoped. #337 repairs PR-Agent advisory publication/concurrency governance. #336 adds a guest evidence-durability boundary before reusable worker completion. Neither expands protected Factory/M4, verifier, evidence-schema, provider, or acceptance authority.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For `main@d89c5d94...`:

- production Pages run **`35449637725`**, attempt 1: **FAIL**;
- generated desktop+narrow artifact/browser proof: **PASS**;
- deployment: **PASS**;
- published desktop exact-revision + real-guest execution: **PASS**;
- multiple required narrow live-guest stages before final retention check: **PASS**;
- final compound retained-evidence assertion: **FAIL**;
- retained live-proof artifact: `webvm-live-proof-35449637725-1`;
- SHA-256: `edd0d84e1270b71cc53039cae85e42041c06767c52039bb6c418a3ffffd62ff8`;
- lower-level cause: **UNKNOWN**;
- every-host/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established**;
- paid/live provider semantic success: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**;
- production Vercel security-header validation: **UNKNOWN / pending**;
- recovery/elapsed-soak qualification: **not established**.

The failing narrow command chains file-existence predicates for live/build/follow-up outputs and `verify_run(...)` integrity checks for all three mission directories. Because those predicates are compound, this retained attempt does not establish which one failed first. #336's `os.sync()` durability boundary is therefore **necessary but insufficient**. The next changed-head repair should split the assertion into independently reported predicates without weakening acceptance and then repair the first observed failing invariant. Do not rerun unchanged current main merely for green.

Historical predecessor PASS/FAIL results remain bound to their own exact revisions and are not inherited.

### Protected Factory contention candidate

**#338** is rebased onto current main and remains unaccepted. It changes protected RuntimeJournal bytes and advances the Factory ownership-baseline pin. Because this is a protected trust-boundary change, no automation should merge it even if sibling checks are green; explicit review and exact-head evidence are mandatory.

### Provider and research split

**#340** contains the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw adapter work. It remains unaccepted branch work.

Draft **#341 / EXP-NESTED-SWARM-001** contains the governed nested-runtime research/evaluation material split out of #340 and is explicitly research-only. It does not establish accepted provider capability, nested-swarm efficiency, or recursive self-improvement.

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
- **#273/#277** — retained provenance/planner **FAIL** cells.
- **#319 / M6-MESH-001 Trial 0** — bounded positive concurrency pilot; general mesh/swarm efficiency remains **UNKNOWN / not established**.
- **#323** — Research Workbench remains draft; first authoritative trial remains **BLOCKED** pending rebase and qualification.
- **#325** — first Residual Studio IDE/control-plane slice remains draft/unaccepted.
- **#326** — Mission Control time-travel debugger is a read-only historical debugger, not deterministic execution replay.
- **#341** — nested-runtime governed evaluation is draft/research-only; general benefit remains **UNKNOWN / not established**.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its declared positive semantic/derivation gates are satisfied.

## Security work still open

Accepted work and remaining evidence must be kept distinct:

- **#320:** repository-side CSP/anti-clickjacking policy is accepted; production Vercel response-header/Aikido validation is **UNKNOWN / pending**.
- **#328:** core source/runtime security hardening is accepted.
- **#330:** workflow checkout credential-persistence hardening is accepted.
- **#337:** PR-Agent advisory publication/concurrency governance hardening is accepted.
- **#338:** protected Factory candidate remains unaccepted and requires explicit trust-boundary review.
- **#152:** exact current testing-branch Qualification-v1 is **FAIL**; no branch result can be promoted into current-main capability.

Do not describe this as blanket security qualification. Each accepted change is scoped to reviewed bytes and retained evidence.

## Qualification infrastructure

Production Pages/main first-attempt evidence remains non-cancelling. Queue recovery or CI deduplication does not authorize skipping, cancelling, or rewriting required qualification outcomes.

Qualification-v1 remains separate testing-branch evidence. Open PR **#152** is at exact head `aeba9962918c3659693e1efcd5603275cfb77cb4`. Exact-head Qualification-v1 run **`35448856959` attempt 1 = FAIL**. Real bubblewrap provisioning succeeds, as do the visible selftest, toxic-provider, M4, browser, discovery, concurrency, fault-injection and lifecycle siblings, but the required deterministic job fails at `Full deterministic regression gate`, causing the fail-closed aggregate to fail. The lower-level deterministic-regression cause remains **UNKNOWN** on the currently retained summary.

## Current build order

1. **Diagnose the exact-current-main Pages FAIL without weakening acceptance.** Split the narrow retained-evidence compound assertion into independent existence and `verify_run(...)` results on a changed head; preserve `35449637725` attempt 1.
2. **Resolve #152's remaining deterministic Qualification-v1 failure.** Keep real sandbox provisioning and all fail-closed requirements intact; preserve the first-attempt FAIL.
3. **Review #338 as a protected trust-boundary change.** Never auto-merge its RuntimeJournal/ownership-baseline change.
4. **Keep #340 implementation and #341 research separate.** Each must satisfy its own evidence/governance path before any claim changes.
5. **Requalify the repaired #288 authority path.** Retain fresh evidence for budget exhaustion, unknown usage, terminal verifier/release ordering, and export binding before making stronger present-tense claims.
6. **Rebase/requalify Research Workbench #323** before M6-WB-001 can run authoritatively.
7. **Validate #320 on production Vercel.** Configuration merge alone is not production-header PASS.
8. **Retain fresh exact-current-deployed live-provider evidence.** A real-account provider mission must cross protocol validation into ordinary candidate/verifier/receipt handling before live-provider success can become PASS.
9. **Continue bounded M6 discovery/derivation and M6-MESH measurement** without promoting pilot results into product capability; keep M6-008 blocked until explicit gates are met.
10. **Execute true blank-environment installation, recovery/host-loss qualification, selected elapsed soak, and physical/mobile validation** for the exact release path.
11. **Continue #120/#126 WebVM reliability work** and preserve historical negative evidence.
12. **Keep protected sequences independent.** Factory ownership/qualification paths must not inherit unrelated green CI.
13. **Freeze confirmatory research before outcome access.** Preserve negative, blocked, unknown, and missing cells.

## Release evidence rule

A merge onto main establishes that accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, production security headers, recovery, or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.