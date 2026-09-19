# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@3bfa6abac719bb1ca5db225b32df347ae2afc079`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged **#330** on 2026-09-19. No newer commit has landed on `main` in this check.

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
- current repository queued-run snapshot: **0**. The historical #305 queue saturation remains historical evidence rather than current queued backlog.

Do not inherit qualification from the predecessor SHA after `main` moves. Production Pages run **`35431634267`**, attempt 1, remains a scoped **PASS for exact revision `0a675017a51f94e489528a607032e7463fbf7993` only**. The earlier production Pages run `35410875305` on `e7b72ad...` remains a retained **FAIL for that exact revision only**. The current `3bfa6aba...` cell is independently **FAIL** on its own first authoritative attempt.

The current failure is scoped to the required exact-main production Pages qualification. It does not establish paid/live Puter inference failure, model-quality failure, every-host M4 failure, production Vercel security posture, or blanket product failure. Conversely, the successful desktop path inside the same run does not override the required mobile/narrow failure.

## Focused Pages repair and PR-review governance blocker

Open **#336** is the focused changed-head repair for the retained production Pages failure. At exact head **`92aca285a9287b73787b552f87aaa42062e73ba4`**, it changes only the persistent WebVM worker plus focused regression coverage and establishes an explicit guest-filesystem durability boundary before the worker publishes a reusable completion marker. Its generated PR Pages proof **`35438579639`**, attempt 1, is **PASS**; Control Plane, Factory ownership, measured-evaluation binding, clean install, Command Station and Controller/provider are also **PASS** on that exact branch head.

That evidence is **branch-only** and does not change the current production cell. #336 protected maintainer approval is **FAIL**, and a fresh advisory review was not established. The review provider exhausted its credits and emitted only `Failed to review PR`. The existing PR Agent verifier could count a fresh `github-actions[bot]` failure/status comment as a successful publication, creating false-green governance evidence; shared concurrency could also let bot issue comments cancel a legitimate review before the bot-triggered job was skipped.

Open **#337** at exact head **`46e522b4437d42d68df170285bd3a93366808bd1`** is the focused governance repair. It requires the explicit `<!-- pr-agent:review:full -->` marker from the current run and isolates concurrency by PR/event/sender class. Its named technical lanes are **PASS**, but PR Agent advisory and protected maintainer approval are **FAIL**, so #337 remains unaccepted.

Therefore:

- current production `main@3bfa6aba...` Pages: **FAIL**;
- #336 generated branch Pages proof: **PASS** for exact branch head only;
- #336 acceptance: **BLOCKED / HOLD** behind #337 plus fresh exact-head qualification and maintainer attestation;
- #337 acceptance: **FAIL / not accepted** because required governance gates are not satisfied;
- if #337 lands, #336 must reconcile onto the resulting new `main` and all merge-relevant exact-head evidence must be regenerated rather than inherited;
- even after #336 later merges, the resulting new `main` must pass its own first authoritative production Pages attempt before the production Pages claim becomes PASS.

The retained `35437556200` failure remains evidence throughout any repair sequence.

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

PR **#333** reverse-merged exact current main into `testing/qualification-v1`, not into production `main`. Open PR **#152** is now at exact testing-branch head **`11c0ac67f60f61a7243bcc79ce803d588a89aa94`**.

The first exact-head `RESIDUAL Qualification v1` run on that revision, **`35443955204` attempt 1**, is **FAIL**. Retained final evidence names three required gates that did not establish PASS:

- **`deterministic-regression`: FAIL** — retained regression output shows seven enterprise sandbox failures because the hosted runner reported `kernel-level sandbox isolation unavailable`; the gate also retained 29 general capability skips. This is not a hosted-runner PASS and must not be waived by prose.
- **`qualification-selftests`: FAIL** — one full provider-mission qualifier returned `FAIL` while 38 sibling selftests passed.
- **`toxic-provider-matrix`: FAIL** — the same full provider-mission qualifier returned `FAIL` while seven sibling tests passed.

The retained failure ledger classifies these required non-PASS gates as **UNCLASSIFIED**. The lower-level reason the provider-mission report itself returned FAIL is therefore **UNKNOWN** from the retained qualification evidence reviewed here; do not invent a product/provider cause.

On the same exact branch head, retained surrounding checks include **PASS** for Factory ownership, M4 prerequisites, Browser VM Demo, Controller/provider contracts, Command Station, clean install, Factory runtime/OS evidence, Control Plane, measured-evaluation binding, and generated PR Pages proof. Those partial PASSes do not override the required aggregate qualification **FAIL**. Protected maintainer approval is **FAIL**, and PR Agent advisory is also **FAIL**.

The predecessor head **`24816ebc778b26497dd30497e59f6f2badcf39ed`** retains its earlier positive technical evidence and earlier failures as exact-head historical evidence. It is not inherited by `11c0ac67...`.

Therefore:

- #152 exact-current testing-branch Qualification-v1 result: **FAIL**;
- #152 accepted-main capability: **UNKNOWN / not established** because the PR remains open/unmerged;
- #152 maintainer approval: **FAIL**;
- #152 advisory-review completion: **FAIL**;
- lower-level provider-mission cause: **UNKNOWN**;
- no #152 branch PASS broadens exact-current-main Factory/M4 or release qualification.

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

1. **Repair PR-review governance before accepting the Pages repair.** Review/qualify #337; if it lands, reconcile #336 onto the new main and rerun all required exact-head gates. Preserve production run `35437556200` attempt 1 as FAIL. A later branch PASS is not production PASS; the repaired merged-main SHA must pass its own first authoritative Pages attempt.
2. **Diagnose and repair #152 exact-head qualification.** Preserve run `35443955204` attempt 1 and its deterministic/selftest/toxic-provider failures. Do not classify the provider-mission cause beyond retained evidence. New qualification is justified only by a changed candidate head.
3. **Requalify repaired authority ordering.** Retain fresh tests/experiments against accepted #288 before promoting stronger present-tense budget/unknown-usage/release-ordering claims.
4. **Rebase/requalify #323.** Do not run the first authoritative Workbench trial until the branch is based on a main containing #288 and its required gates pass.
5. **Validate #320 in production.** Inspect the production Vercel response headers and rerun the relevant security check before calling production CSP/anti-clickjacking remediation PASS.
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
