# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@0a675017a51f94e489528a607032e7463fbf7993`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`0a675017a51f94e489528a607032e7463fbf7993`**, produced by merged **#328** on 2026-09-19.

Five accepted changes since the preceding documented `e7b72ad...` boundary materially affect current status:

- **#307** — duplicate feature-branch CI fan-out repair. General PR qualification remains intact; production `main`/Pages first-attempt evidence remains non-cancelling. The Actions API currently reports **0 queued runs**. The historical #305 saturation snapshots remain evidence even though the acute queue is clear.
- **#260** — provider bootstrap guard. The embedded provider Load control now fails closed until its private bridge is initialized. This is accepted repository/UI transport behavior, not proof of paid/live Puter inference.
- **#288 / #208** — pre-dispatch Station budget/deadline authority repair. Runner and reviewer dispatch are admitted through host-owned run accounting, unknown usage fails conservatively, later authority effects are rechecked, and release export requires a successful run-control result bound to the exact project head/spec. #208 is closed. Historical #207/#212 frozen outcomes are retained rather than reclassified.
- **#320** — repository-side CSP and anti-clickjacking hardening. The Vercel configuration defines CSP, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff`, referrer policy and restrictive permissions policy. GitHub Pages can only use the HTML CSP fallback because arbitrary repository-controlled HTTP response headers are unavailable there. Post-merge production Vercel header inspection/Aikido validation is **UNKNOWN / pending**.
- **#328** — accepted core non-workflow split of #324. It replaces host-interpreter third-party execution with required kernel isolation/fail-closed behavior, hardens connector origin/redirect/proxy handling against SSRF/bearer forwarding, hardens SAML XML parsing, and adds bounded marketplace/recovery/telemetry/demo-gateway protections and regression coverage. The remaining workflow `persist-credentials: false` work has been split onto focused current-main PR **#330**; it remains **OPEN / unaccepted**, and stale overlapping #324 must not be merged wholesale.

No change above broadens Factory/M4, verifier, evidence-schema or acceptance authority.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For exact current main `0a675017...`:

- production Pages run **`35431634267`**, attempt 1: **PASS**;
- `build-and-browser-proof`: **PASS**;
- deployment: **PASS**;
- published WebVM revision + real guest execution verification: **PASS**;
- published narrow Chromium acceptance: **PASS**;
- retained live proof artifact: **`10580449851`**, SHA-256 **`ebdecf8e4055679933f1941f648d422d37a38ba5e4dad1f285967b83ccf684aa`**;
- retained generated browser proof artifact: **`10580818938`**, SHA-256 **`9ed51067d6fc7d1222edc9eec9c7a265d880e9a30f7080ba7f90ffe360627f06`**;
- queued Actions runs: **0** at the current API snapshot.

This is an exact-revision **PASS for the production Pages publication/browser/real-guest qualification scope**. It is not a global production-readiness PASS and does not establish paid/live Puter inference, model quality, physical heavyweight-WebVM iPhone reliability, every-host M4 qualification, or unrelated trust-boundary claims.

The earlier production Pages run `35410875305` on `e7b72ad...` remains a retained **FAIL for that exact revision only**. It is not erased or reclassified by the current-main PASS. Likewise, PR-head success from predecessor revisions is not substituted for this main result.

## Accepted budget-authority repair and retained stress evidence

Merged #288 closes product issue #208. The accepted invariant is that Station-dispatched authority-bearing work must be admitted before dispatch against host-owned budget/deadline state, and export eligibility must be bound to a successful run-control result for the exact integrated revision/spec.

This changes current product behavior, but it does **not** rewrite frozen research evidence:

- #207 STRESS-B1 remains a historical **FAIL** where exhausted-budget accounting was observed after integration/release on its frozen baseline;
- #207 STRESS-B3 remains a historical **FAIL** where a release materialized after terminal verifier failure;
- #212's missing-usage case remains a historical **FAIL for accounting-before-authority** on its frozen baseline;
- #212's bounded containment/recovery PASS cells remain PASS in their own scope;
- #212 remains an open draft research apparatus rather than an accepted product change.

A stronger present-tense claim that the repaired path prevents these classes of authority-ordering failure requires fresh qualification against the accepted #288 revision. Until such evidence is retained, describe the product defect as repaired/accepted and the affected stronger empirical claim as **UNKNOWN pending repaired-path requalification**, not as retroactively PASS.

## Research Workbench

Draft **#323** remains based on the older `e7b72ad...` main at exact head `f32b99b7d62bc35872daaf4da00787761b7ca8ea`. Its own contract required #288 to be accepted on `main` and then required #323 to be rebased and requalified before the first authoritative Workbench trial.

#288 is now accepted, so that prerequisite is satisfied. The second prerequisite is not: #323 has not yet been rebased/requalified onto the repaired main. Therefore:

- current #323 implementation: **UNACCEPTED / draft**;
- prior exact-head qualification failures: retained historical evidence for `f32b99b7...`;
- first authoritative M6-WB-001 trial: **BLOCKED / not run** pending rebase and fresh qualification;
- staged experiment definitions: definition availability only, not experimental evidence.

## Security posture boundary

### #320 CSP / anti-clickjacking

Repository-side policy is accepted. Production Vercel response-header enforcement has not been established by retained post-merge production inspection in this status check, so that claim remains **UNKNOWN / pending**. The GitHub Pages origin cannot be described as emitting the Vercel-only response headers; its repository-controlled mitigation is the HTML CSP fallback.

### #328 / #330 workflow-hardening split

Merged #328 accepts the non-workflow core of the Aikido remediation pass: kernel-enforced supply-chain execution isolation, connector SSRF/bearer hardening, defused XML parsing and bounded supporting security controls/tests.

The remaining GitHub Actions checkout credential-persistence hardening has been rebuilt directly from exact current main as focused PR **#330**, rather than carrying the stale overlapping #324 branch forward wholesale. #330 sets `persist-credentials: false` on the remaining checkout steps while preserving the accepted #307 and #267 workflow semantics and adds a structural regression test. At current exact head `97dca2bf1850ea67e0d0e5292081410c1eb0f1f0`, the protected `maintainer-approval` status is **FAIL** because no matching exact-head human attestation exists. Therefore:

- #328 core source/runtime security changes: **ACCEPTED on main**;
- #330 workflow credential-persistence hardening: **OPEN / unaccepted**;
- #330 merge/acceptance: **BLOCKED by the failed exact-head maintainer-approval gate** until governance is satisfied;
- stale overlapping #324: **must not be merged wholesale**;
- blanket claim that all #324-derived findings are closed: **not supported**;
- production deployment/security posture beyond the retained accepted changes: scoped to its own evidence, not globally PASS.

Aikido-generated #321/#322 remain separate vendor-generated candidates; vendor confidence text is not repository acceptance evidence.

## Qualification infrastructure

Issue #305 recorded severe Actions saturation, including an original snapshot of 1,267 queued runs. That historical evidence remains valid.

Merged **#307** now removes the identified duplicate generic feature-branch push fan-out for the affected general CI workflows while preserving PR qualification and non-cancelling production evidence. The current Actions API reports **0 queued runs**. Therefore the acute operational blocker is presently cleared and the structural repair is accepted, even though #305 itself remains open in GitHub.

Queue recovery is not permission to cancel, overwrite or reinterpret required first-attempt qualification evidence.

### Qualification-v1 testing branch

PR **#331** merged only into `testing/qualification-v1`, not `main`. It repaired the browser-adversarial harness defects and the concurrency-test reader/admission race without changing the protected `residual/factory/runtime_journal.py` bytes or weakening the asserted invariants. That moves open PR **#152** to exact testing-branch head **`24816ebc778b26497dd30497e59f6f2badcf39ed`**.

On that exact branch head, the retained check set includes **PASS** for `aggregate`, `browser-adversarial`, `concurrency`, `m4`, `m4-prereq`, the browser matrix, deterministic/fault/discovery lanes and the generated browser proof. The protected `maintainer-approval` gate is still **FAIL** because no exact-head attestation is present. The Aikido code check completed under its threshold but reported **2 new MEDIUM and 19 new LOW findings**, while its Deep Review was **SKIPPED** because no credits were available.

Therefore:

- repaired Qualification-v1 branch technical gates named above: **PASS on exact testing-branch head `24816ebc...`**;
- prior Qualification-v1 attempt-1 failures: **retained historical FAIL evidence**, not erased;
- #152 accepted-main capability: **UNKNOWN / not established** because the PR is still open/unmerged;
- #152 maintainer approval: **FAIL** on that exact head;
- #152 security review completeness: **UNKNOWN / incomplete** because reported findings remain and Deep Review did not execute;
- no #152 branch PASS broadens exact-current-main Factory/M4 or release qualification.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Accepted provider/session/bootstrap/publication changes, including #260, do not substitute for fresh live semantic evidence. Therefore:

- successful paid/live Puter candidate→verifier→receipt execution on exact current main: **UNKNOWN / not established**;
- candidate correctness for the historical failed calls: **UNKNOWN**;
- model quality implied by Pages or transport CI: **UNKNOWN / not established**.

The #186 iOS/WebKit fallback remains accepted only as a lightweight pre-boot route. Physical heavyweight-WebVM reliability and long-run recurrence/root cause under #120/#126 remain **UNKNOWN / unqualified**.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a production-qualification manifest.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 sequence and Qualification-v1 work remain independent evidence paths. No documentation update in this PR changes Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, provider authorization or acceptance authority.

Namespace/capability-unavailable execution remains `BLOCKED`/`UNKNOWN`, never PASS by documentation.

## Retained research evidence

The M6 record remains deliberately mixed:

- #203 / M6-SPEC-001: **FAIL**;
- #204 / M6-SPEC-002: **FAIL**;
- #215 / M6-SPEC-003: **FAIL**;
- #217 / M6-SPEC-004: **FAIL**;
- #220 / M6-SPEC-006: bounded corrected-path **PASS**;
- #257 / M6-SPEC-007J: bounded **PASS at formal MeasurementGap admission**;
- #264 / 007O: integrity-valid workflow/receipt with scientific conclusion **UNKNOWN** because admitted metric identity/semantics were ambiguous;
- #274 / 007S: bounded **PASS** for registry/receipt semantic-binding controls;
- #273/#277: retained provenance/planner **FAIL** cells, with positive host-owned provenance evidence inside an overall failed path.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its declared semantic/derivation admission gates are satisfied.

### M6-MESH-001

#319 retains one bounded real-model crossover pilot in which both sequential and two-call concurrent conditions passed their obligation checks and the observed mean wall time favored concurrency. The small three-repeat, one-host cell has warm-up/order sensitivity and does not establish a durable or general performance benefit. General mesh/swarm efficiency therefore remains **UNKNOWN / not established**.

### Other draft work

#317 RESIDUAL-RT, #318 Web Command Station architecture, #323 Research Workbench, #325 Residual Studio and #326 Mission Control time-travel work remain branch-scoped/unaccepted unless separately merged after their own gates. Their branch evidence does not become current-main capability by mention here.

## Current priority gates

1. **Requalify repaired authority ordering.** Retain fresh tests/experiments against accepted #288 before promoting stronger present-tense budget/unknown-usage/release-ordering claims.
2. **Rebase/requalify #323.** Do not run the first authoritative Workbench trial until the branch is based on a main containing #288 and its required gates pass.
3. **Validate #320 in production.** Inspect the production Vercel response headers and rerun the relevant security check before calling production CSP/anti-clickjacking remediation PASS.
4. **Finish and govern #330 workflow hardening.** Keep its unaccepted workflow credential-persistence changes separate from accepted #328 and do not merge stale overlapping #324 wholesale.
5. **Complete #152 governance/security review.** Its repaired testing-branch technical gates are positive evidence, but exact-head maintainer approval is FAIL and the scanner findings/Deep Review gap remain unresolved; do not import branch PASS into main.
6. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN.
7. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
8. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED.
9. **Preserve exact-main Pages evidence.** Keep run `35431634267`, attempt 1, as the scoped production Pages PASS for `0a675017...`; do not use that PASS to infer provider/model quality, physical-device reliability, every-host M4 qualification, or unrelated security claims.

## Claim discipline

- `PASS` applies only to the named revision/environment/gate.
- `FAIL` remains evidence after later repair.
- `UNKNOWN` means the required causal/evidentiary/qualification result is not established.
- `BLOCKED` means a required gate could not validly execute; it is not PASS.
- A research workflow can successfully retain a scenario-level FAIL; workflow success is not hypothesis success.
- PR-head success is not accepted-main production evidence.
- A merge accepts repository bytes; it does not automatically establish every security, live-provider, physical-device, scientific or release claim associated with them.

The repository does not currently claim blanket production readiness, universal worker correctness, every-host M4 qualification, successful exact-current-main paid/live provider execution, completed blank-environment/recovery/soak qualification, physical heavyweight-WebVM iPhone reliability, production Vercel security-header validation, general autonomous recursive self-improvement, general cooperative mesh efficiency, or proof of the central live-model reliability hypothesis.
