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
| Mission Control/WebVM lifecycle | Bounded recovery, diagnostics, iOS fallback and provider/session/bootstrap hardening are accepted; exact-current-main production Pages run `35431634267` attempt 1 is **PASS** for publication/browser/real-guest qualification |
| Native setup path | #200 hardening is accepted; blank-environment qualification remains open |
| Live provider acceptance | Historical retained Puter failure remains scoped to its exact run; exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN** |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Research Workbench | Draft #323; #288 prerequisite is now accepted, but #323 must still be rebased/requalified before the first authoritative trial, which remains **BLOCKED** |
| Residual Studio | Draft #325; first IDE/control-plane observer slice exists on a branch, but authoritative mutation wiring and full qualification remain incomplete |
| Core security hardening | #328 accepted for kernel-isolated third-party execution, connector SSRF/bearer hardening, SAML XML hardening and supporting controls; remaining workflow credential-persistence work is isolated in focused current-main PR #330 and remains **OPEN / unaccepted** |
| CSP / anti-clickjacking | #320 repository configuration accepted; production Vercel response-header/Aikido validation remains **UNKNOWN / pending** |
| Release/recovery/soak | True blank-environment install, host-loss/recovery evidence and selected elapsed soak remain gates |
| Autonomous discovery / recursive improvement | Mixed bounded research evidence only; general capability remains **UNKNOWN / not established** and M6-008 remains **BLOCKED** |
| Cooperative mesh efficiency | M6-MESH-001 has one positive bounded two-obligation pilot cell; general performance benefit remains **UNKNOWN / not established** |
| Web Command Station control plane | Proposed/draft under #318; not accepted production capability |

`implementation-status.yaml` records implementation presence and remains current for that purpose. It is not a release-qualification manifest.

## Accepted main

Current `main` is **`0a675017a51f94e489528a607032e7463fbf7993`**, produced by merged **#328** on 2026-09-19.

Recent accepted changes relevant to roadmap status:

### #307 — duplicate feature-branch CI fan-out repair

The affected general workflows no longer produce redundant unrestricted feature-branch push copies in addition to PR qualification. PR qualification remains, superseded PR-head cancellation is bounded to the intended paths, and production-main/Pages first-attempt evidence remains non-cancelling. The current Actions queue snapshot is **0**; historical #305 saturation evidence remains retained.

### #260 — provider bootstrap guard

The embedded provider Load control fails closed until the private MessagePort bridge is initialized. This is accepted UI/transport behavior, not retained proof of successful paid/live Puter inference.

### #288 — pre-dispatch budget authority

#288 closes #208. Station runner/reviewer dispatch is admitted against host-owned budget/deadline state before authority-bearing work begins, unknown/invalid usage is handled conservatively, and release export requires a successful run-control result bound to the exact head/spec. Historical #207/#212 research failures remain retained; stronger present-tense claims need repaired-path requalification.

### #320 — repository-side CSP / anti-clickjacking

The repository now carries CSP/anti-clickjacking policy including `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff`, strict referrer policy and restrictive permissions policy for the Vercel deployment configuration, with an HTML CSP fallback for GitHub Pages. Production Vercel header inspection and Aikido revalidation remain **UNKNOWN / pending**.

### #328 — core security hardening split from #324

Accepted core changes require kernel isolation/fail closed for third-party supply-chain execution, harden connector origin/redirect/proxy handling against SSRF/bearer forwarding, harden SAML XML parsing, and add bounded marketplace/recovery/telemetry/demo-gateway controls and regression coverage. The remaining workflow `persist-credentials: false` changes have been rebuilt from exact current main as focused PR **#330**; they are not included in #328's accepted scope and remain **OPEN / unaccepted**. The stale overlapping #324 branch must not be merged wholesale.

None of these changes expands protected Factory/M4, verifier, evidence-schema or acceptance authority.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For `main@0a675017...`:

- production Pages run **`35431634267`**, attempt 1: **PASS**;
- Pages `build-and-browser-proof`: **PASS**;
- deployment: **PASS**;
- published WebVM revision + real guest execution: **PASS**;
- published narrow Chromium acceptance: **PASS**;
- retained live proof artifact: `10580449851`, SHA-256 `ebdecf8e4055679933f1941f648d422d37a38ba5e4dad1f285967b83ccf684aa`;
- Actions queued-run count at the current snapshot: **0**;
- every-host/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established**;
- paid/live provider semantic success: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**;
- production Vercel security-header validation: **UNKNOWN / pending**;
- recovery/elapsed-soak qualification: **not established**.

The current Pages result is a scoped exact-revision PASS, not blanket production readiness or live-provider/model-quality evidence. The earlier production Pages **FAIL** on `e7b72ad...` remains exact-revision historical evidence and is not erased by the later PASS.

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
- **#293** — M7 governed recursive self-improvement bootstrap remains unaccepted and preserves an external promotion gate.
- **#310** — live-core adapter binding remains draft/unaccepted and dependent on the normative adapter contract being merged/tagged and pinned before production use.
- **#313/#314** — A2A and Vector/Wire-Pod experiments remain draft/unaccepted.
- **#316** — RAC evidence-gated improvement StationModule remains branch-scoped/unaccepted.
- **#317** — RESIDUAL-RT bounded-authority adversary-emulation research remains draft/unaccepted; proposal/lab evidence does not establish real-world exploit reliability.
- **#318** — Web Command Station/Vercel control-plane architecture remains draft/unaccepted.
- **#319 / M6-MESH-001 Trial 0** — bounded apparatus/task success with an observed concurrency wall-time advantage across three repeats on one host. General mesh/swarm efficiency remains **UNKNOWN / not established**.
- **#323** — built-in Research Workbench remains draft. #288 is now accepted, satisfying the first prerequisite, but #323 is still based on older `e7b72ad...`; its first authoritative trial remains **BLOCKED** pending rebase and fresh qualification.
- **#325** — first Residual Studio IDE/control-plane slice remains draft/unaccepted; authoritative mutation wiring and full qualification remain incomplete.
- **#326** — Mission Control time-travel debugger remains branch-scoped unless separately accepted; it is a read-only historical debugger, not deterministic execution replay.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its declared positive semantic/derivation gates are satisfied. General cooperative mesh/swarm efficiency likewise remains **UNKNOWN / not established** until larger frozen measurements establish a durable effect without verifier-success loss.

## Security work still open

Accepted work and remaining work must be kept distinct:

- **#320:** repository-side CSP/anti-clickjacking policy is accepted; production Vercel response-header/Aikido validation is **UNKNOWN / pending**.
- **#328:** core non-workflow security hardening is accepted.
- **#330:** focused workflow checkout credential-persistence hardening remains **OPEN / unaccepted** on exact head `97dca2bf1850ea67e0d0e5292081410c1eb0f1f0`; the protected maintainer-approval status is **FAIL** because no matching exact-head attestation exists.
- **#324:** stale overlapping predecessor; it must not be merged wholesale.
- **#321/#322:** scanner-generated candidates remain separate and are not acceptance evidence merely because vendor confidence is high.
- **#319:** experiment-branch security findings remain separate from the experiment's apparatus result.

Do not describe this as blanket security qualification. Each accepted change is scoped to its reviewed bytes and retained evidence.

## Qualification infrastructure

Issue **#305** remains open, but two facts must be separated:

1. its historical queue-saturation snapshots remain valid evidence;
2. **#307 is now merged** as the structural duplicate feature-branch fan-out repair, and the current Actions queue snapshot is **0**.

Production Pages/main first-attempt evidence remains non-cancelling. Queue recovery or CI deduplication does not authorize skipping, cancelling or rewriting required qualification outcomes.

Qualification-v1 remains separate testing-branch evidence. PR **#331** merged into `testing/qualification-v1` only, moving open PR **#152** to exact head `24816ebc778b26497dd30497e59f6f2badcf39ed`. On that head, the retained checks show **PASS** for `aggregate`, `browser-adversarial`, `concurrency`, `m4`, `m4-prereq`, the browser matrix and the surrounding qualification lanes. The protected `maintainer-approval` gate remains **FAIL**, so #152 remains unaccepted and none of its PASSes broaden current production `main` or M4 claims. Earlier attempt-1 failures remain retained historical evidence. The same head's Aikido code check reported **2 new MEDIUM and 19 new LOW findings** and Deep Review was **SKIPPED** because no credits were available; security-review completeness is therefore **UNKNOWN / incomplete**.

## Current build order

1. **Requalify the repaired #288 authority path.** Retain fresh evidence for budget exhaustion, unknown usage, terminal verifier/release ordering and export binding before making stronger present-tense claims.
2. **Rebase/requalify Research Workbench #323.** #288 is accepted; the remaining prerequisite is a fresh #323 base and qualification before M6-WB-001 can run authoritatively.
3. **Validate #320 on production Vercel.** Inspect actual response headers and rerun the relevant security check; do not treat configuration merge alone as production-header PASS.
4. **Finish and govern #330 workflow hardening** independently of accepted #328 core source/runtime changes; do not merge stale overlapping #324 wholesale.
5. **Complete #152 exact-head governance/security review.** Its repaired testing-branch technical gates are positive branch evidence, but maintainer approval is FAIL and scanner review is incomplete.
6. **Retain fresh exact-current-deployed live-provider evidence.** A real-account Puter mission must cross protocol validation into ordinary candidate/verifier/receipt handling before live-provider success can become PASS.
7. **Continue bounded M6 discovery/derivation and M6-MESH measurement** without promoting pilot results into product capability; keep M6-008 blocked until explicit gates are met.
8. **Advance Residual Studio only through its bounded control boundary.** Keep authoritative Factory mutation and browser/control-plane state separate until their own gates pass.
9. **Physically validate the #186 iOS fallback** without broadening fallback success into heavyweight-WebVM reliability.
10. **Execute true blank-environment installation, recovery/host-loss qualification and selected elapsed soak** for the exact release artifact.
11. **Continue #120/#126 WebVM reliability work** and preserve historical negative evidence.
12. **Keep protected sequences independent.** Factory ownership/qualification paths must not inherit unrelated green CI.
13. **Freeze confirmatory research before outcome access.** Preserve negative, blocked, unknown and missing cells.
14. **Preserve exact-main Pages evidence.** Keep run `35431634267`, attempt 1, as the exact-revision PASS for publication/browser/real-guest qualification without broadening it into provider/model, physical-device, M4, or blanket production claims.

## Release evidence rule

A merge onto main establishes that accepted bytes are part of the repository. It does not automatically establish every release claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, production security headers, recovery or soak must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN`, and `BLOCKED` results remain visible even when later revisions pass.
