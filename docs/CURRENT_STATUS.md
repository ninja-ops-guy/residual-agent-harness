# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@3bfa6abac719bb1ca5db225b32df347ae2afc079`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged **#330** on 2026-09-19.

Recent accepted changes materially affecting the current boundary are:

- **#307** — duplicate feature-branch CI fan-out repair. General PR qualification remains intact and production `main`/Pages first-attempt evidence remains non-cancelling.
- **#260** — provider bootstrap guard. The embedded provider Load control fails closed until its private bridge is initialized. This is accepted UI/transport behavior, not proof of paid/live Puter inference.
- **#288 / #208** — pre-dispatch Station budget/deadline authority repair. Runner and reviewer dispatch are admitted through host-owned run accounting, unknown usage fails conservatively, later authority effects are rechecked, and release export requires a successful run-control result bound to the exact project head/spec. #208 is closed. Historical #207/#212 frozen outcomes are retained rather than reclassified.
- **#320** — repository-side CSP and anti-clickjacking hardening. Production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328** — accepted core non-workflow security hardening: kernel isolation/fail-closed third-party execution, connector SSRF/bearer hardening, hardened SAML XML parsing, and bounded supporting controls/tests.
- **#330** — accepted the remaining workflow checkout credential-persistence hardening. Remaining `actions/checkout` steps now use `persist-credentials: false`, with structural regression coverage, while preserving the accepted #307 and #267 workflow semantics. This is a scoped workflow-security change, not blanket security qualification. The stale overlapping #324 branch must not be merged wholesale.

No accepted change above broadens Factory/M4, verifier, evidence-schema, provider, or acceptance authority.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For exact current main `3bfa6aba...`:

- production Pages run **`35437556200`**, attempt 1: **FAIL**;
- `build-and-browser-proof`: **PASS**;
- deployment plus published-revision identity and desktop real-guest acceptance: **PASS**;
- required narrow/mobile Chromium acceptance: **FAIL** after the live guest reached shell-ready and multiple Workbench stages;
- retained live-proof artifact: **`10582812524`**, SHA-256 **`868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`**;
- lower-level cause of the narrow/mobile failure: **UNKNOWN**. The observed failing proof command exited 1 while re-verifying retained Workbench runs; the evidence does not establish whether the cause belongs to browser/mobile runtime behavior, a retained-run race/state issue, another subsystem, or transient execution. Do not attribute it to #330, Puter/model quality, Factory/M4, or another component without further evidence;
- current repository queued-run snapshot: **0**. Six workflows were in progress at the snapshot, primarily the documentation branch's fresh exact-head checks; the historical #305 queue saturation remains historical evidence rather than current queued backlog.

Do not inherit qualification from the predecessor SHA after `main` moves. Production Pages run **`35431634267`**, attempt 1, remains a scoped **PASS for exact revision `0a675017a51f94e489528a607032e7463fbf7993` only**. The earlier production Pages run `35410875305` on `e7b72ad...` remains a retained **FAIL for that exact revision only**. The current `3bfa6aba...` cell is independently **FAIL** on its own first authoritative attempt.

The current failure is scoped to the required exact-main production Pages qualification. It does not establish paid/live Puter inference failure, model-quality failure, every-host M4 failure, production Vercel security posture, or blanket product failure. Conversely, the successful desktop path inside the same run does not override the required mobile/narrow failure.

## Accepted budget-authority repair and retained stress evidence

Merged #288 closes product issue #208. The accepted invariant is that Station-dispatched authority-bearing work must be admitted before dispatch against host-owned budget/deadline state, and export eligibility must be bound to a successful run-control result for the exact integrated revision/spec.

This changes current product behavior, but it does **not** rewrite frozen research evidence:

- #207 STRESS-B1 remains a historical **FAIL** where exhausted-budget accounting was observed after integration/release on its frozen baseline;
- #207 STRESS-B3 remains a historical **FAIL** where a release materialized after terminal verifier failure;
- #212's missing-usage case remains a historical **FAIL for accounting-before-authority** on its frozen baseline;
- #212's bounded containment/recovery PASS cells remain PASS in their own scope;
- #212 remains an open draft research apparatus rather than an accepted product change.

A stronger present-tense claim that the repaired path prevents these classes of authority-ordering failure requires fresh qualification against the accepted #288 path. Until such evidence is retained, describe the product defect as repaired/accepted and the stronger empirical claim as **UNKNOWN pending repaired-path requalification**, not as retroactively PASS.

## Research Workbench

Draft **#323** remains unaccepted. Its own contract required #288 to be accepted on `main` and then required #323 to be rebased and requalified before the first authoritative Workbench trial.

#288 is accepted, satisfying the first prerequisite. The remaining prerequisite is a fresh #323 base and qualification. Therefore:

- current #323 implementation: **UNACCEPTED / draft**;
- prior exact-head qualification results: retained historical branch evidence;
- first authoritative M6-WB-001 trial: **BLOCKED / not run** pending rebase and fresh qualification;
- staged experiment definitions: definition availability only, not experimental evidence.

## Security posture boundary

### #320 CSP / anti-clickjacking

Repository-side policy is accepted. Production Vercel response-header enforcement has not been established by retained post-merge production inspection in this status check, so that claim remains **UNKNOWN / pending**. The GitHub Pages origin cannot be described as emitting Vercel-only response headers; its repository-controlled mitigation is the HTML CSP fallback.

### #328 / #330 split

Merged #328 accepts the non-workflow core of the security remediation pass. Merged #330 now accepts the previously outstanding workflow checkout credential-persistence hardening on current main.

Therefore:

- #328 core source/runtime security changes: **ACCEPTED on main**;
- #330 workflow `persist-credentials: false` changes: **ACCEPTED on main**;
- stale overlapping #324: **must not be merged wholesale**;
- blanket repository security qualification: **not supported**;
- production deployment/security posture beyond the retained accepted changes: scoped to its own evidence, not globally PASS.

Aikido-generated #321/#322 remain separate vendor-generated candidates; vendor confidence text is not repository acceptance evidence.

## Qualification infrastructure

Issue #305 recorded severe Actions saturation, including a historical snapshot of 1,267 queued runs. That historical evidence remains valid.

Merged **#307** removes the identified duplicate generic feature-branch push fan-out for affected general CI workflows while preserving PR qualification and non-cancelling production evidence. The current queued-run snapshot is **0**. That is current operational state only; it does not erase historical saturation evidence or authorize cancelling/reinterpreting required first-attempt evidence.

### Qualification-v1 testing branch

PR **#331** merged only into `testing/qualification-v1`, not `main`. It repaired browser-adversarial harness defects and the concurrency reader/admission race without changing protected `residual/factory/runtime_journal.py` bytes or weakening the intended assertions. Open PR **#152** is now at exact testing-branch head **`24816ebc778b26497dd30497e59f6f2badcf39ed`**.

On that exact branch head, retained checks include **PASS** for `aggregate`, `browser-adversarial`, `concurrency`, `m4`, `m4-prereq`, the browser matrix, deterministic/fault/discovery lanes, and generated browser proof. The protected `maintainer-approval` gate is **FAIL** because no matching exact-head attestation is present. The same head's Aikido code check reported **2 new MEDIUM and 19 new LOW findings**, while Deep Review was **SKIPPED** because no credits were available.

Therefore:

- repaired Qualification-v1 branch technical gates named above: **PASS on exact testing-branch head `24816ebc...`**;
- prior Qualification-v1 attempt-1 failures: **retained historical FAIL evidence**, not erased;
- #152 accepted-main capability: **UNKNOWN / not established** because the PR remains open/unmerged;
- #152 maintainer approval: **FAIL** on that exact head;
- #152 security-review completeness: **UNKNOWN / incomplete** because findings remain and Deep Review did not execute;
- no #152 branch PASS broadens exact-current-main Factory/M4 or release qualification.

PR #332 only reconciled current main into another feature/qualification branch; it did not merge to `main` and changes no accepted production claim.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Accepted provider/session/bootstrap/publication changes do not substitute for fresh live semantic evidence. Therefore:

- successful paid/live Puter candidate→verifier→receipt execution on exact current main: **UNKNOWN / not established**;
- candidate correctness for the historical failed calls: **UNKNOWN**;
- model quality implied by Pages or transport CI: **UNKNOWN / not established**.

The current Pages failure occurred with `cloud_inference` recorded as `NOT_RUN` and therefore is not evidence of a live Puter/model failure.

The #186 iOS/WebKit fallback remains accepted only as a lightweight pre-boot route. Physical heavyweight-WebVM reliability and long-run recurrence/root cause under #120/#126 remain **UNKNOWN / unqualified**.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a production-qualification manifest.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 sequence and Qualification-v1 work remain independent evidence paths. No documentation update in this PR changes Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, provider authorization, or acceptance authority.

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

## Current priority gates

1. **Investigate and requalify the exact-current-main production Pages failure.** Preserve run `35437556200`, attempt 1, and artifact `10582812524`; the desktop success inside the run does not override the required mobile/narrow FAIL.
2. **Requalify repaired authority ordering.** Retain fresh tests/experiments against accepted #288 before promoting stronger present-tense budget/unknown-usage/release-ordering claims.
3. **Rebase/requalify #323.** Do not run the first authoritative Workbench trial until the branch is based on a main containing #288 and its required gates pass.
4. **Validate #320 in production.** Inspect the production Vercel response headers and rerun the relevant security check before calling production CSP/anti-clickjacking remediation PASS.
5. **Complete #152 governance/security review.** Its repaired testing-branch technical gates are positive evidence, but exact-head maintainer approval is FAIL and the scanner findings/Deep Review gap remain unresolved; do not import branch PASS into main.
6. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN.
7. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
8. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED.

## Claim discipline

- `PASS` applies only to the named revision/environment/gate.
- `FAIL` remains evidence after later repair.
- `UNKNOWN` means the required causal/evidentiary/qualification result is not established.
- `BLOCKED` means a required gate could not validly execute; it is not PASS.
- A research workflow can successfully retain a scenario-level FAIL; workflow success is not hypothesis success.
- PR-head or predecessor-main success is not accepted-current-main production evidence after `main` moves.
- A partial PASS inside a required multi-stage gate does not override that gate's terminal FAIL.
- A merge accepts repository bytes; it does not automatically establish every security, live-provider, physical-device, scientific, or release claim associated with them.

The repository does not currently claim blanket production readiness, universal worker correctness, every-host M4 qualification, successful exact-current-main paid/live provider execution, completed blank-environment/recovery/soak qualification, physical heavyweight-WebVM iPhone reliability, production Vercel security-header validation, general autonomous recursive self-improvement, general cooperative mesh efficiency, or proof of the central live-model reliability hypothesis.
