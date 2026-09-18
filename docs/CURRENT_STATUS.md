# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`**.

Meaningful accepted changes since `main@4608afabf5de4c87d77aaf149dfc12538d364f43`:

- **#216** merged the documentation-only status refresh after exact-head maintainer attestation. It changed descriptive docs only and did not alter implementation, qualification anchors, ownership baselines, protected bytes, verifier authority, or evidence schemas.
- **#218** applied bounded M6 repair-loop lessons to Station: prior failed-candidate writable-file content can be supplied as bounded repair context while each new candidate still starts from a clean baseline worktree; repair-context hashes are retained; the runner contract separates its JSON transport envelope from file-language content; and Mission Control/Store share a bounded five-attempt ceiling. The PR does not weaken deterministic checks, review, receipt, integration, quarantine, promotion, Factory/M4, or verifier authority.
- **#201** merged as current main and accepts the guided frontend/provider UX: guided proof is separated from the interactive WebVM lab, the site animates real RESIDUAL CLI commands with reduced-motion support, and Mission Control keeps Puter setup inline rather than opening a separate RESIDUAL provider tab. Puter's own secure authorization popup may still appear; authorization remains tied to explicit user gesture, credentials remain outside RESIDUAL, provider loading remains lazy, and protocol validation remains fail-closed.

PR #201's exact head `4e172aed91d5105e750835e14289e002e109c41a` completed **PASS** for Control Plane, Factory ownership, measured-evaluation binding, clean install, Browser VM Demo, Pages, Command Station, Controller/provider, and maintainer approval before merge. Exact merged `main@260b5f9...` ordinary push qualification is **PENDING** at this status check and must not inherit predecessor-main or PR-head PASS automatically.

New research evidence is also material: draft #220 M6-SPEC-006 retained a bounded exact-head **PASS** on the corrected #218 runtime using local Qwen2.5-Coder 7B. Attempts 1 and 2 were rejected by the frozen checks; attempt 3 passed 2/2 checks, independent Station review approved it, 1/1 integrated, a verification receipt was issued, and release export completed. This single successful trial does not erase earlier M6 failures or establish general autonomous self-maintenance reliability.

## Accepted #200 setup hardening

#200 remains accepted main behavior.

The setup path:

- defaults the managed venv/state to persistent XDG-style locations rather than `/tmp`;
- binds Station to `127.0.0.1` by default;
- makes the no-argument convenience shell macro opt-in, including non-interactive execution;
- performs bounded repair of a broken/incomplete managed venv;
- edits shell startup files only inside marked managed blocks, using atomic same-directory replacement;
- invokes installation through the venv interpreter rather than relying on activation;
- does not open a browser before the server is started.

Claim discipline:

- accepted setup-hardening bytes: **PASS / on main**;
- ordinary automated setup tests: **PASS within their tested scope**;
- true blank-environment installation: **UNKNOWN / not established**;
- broad portability across unsupported hosts: **UNKNOWN / not established**.

A host Python 3.11+ installation and ordinary OS/network prerequisites remain external assumptions.

## Accepted #205 provider-channel recovery

#205 remains accepted main behavior.

The browser provider-session layer persists the private provider-channel token in `sessionStorage`, validates a restored token before reuse, reattaches the same session channel after Mission Control reload/remount, ignores invalid stored state fail-closed, and clears the token on explicit close.

Claim discipline:

- accepted reload/remount channel recovery behavior: **PASS / on main**;
- browser regression coverage for restored/invalid/closed channel state: **PASS within the tested scope**;
- successful paid/live Puter inference: **UNKNOWN / not established**;
- retained manual production SDK/sign-in success on exact current main: **UNKNOWN / not established**.

## Accepted #218 repair-loop remediation

#218 remains accepted main behavior.

The bounded change does four relevant things:

1. a repair attempt may receive content from the immediately prior failed candidate, limited to declared writable files;
2. that repair context is content-bound with retained hashes while the new candidate is still generated from a fresh baseline worktree;
3. the runner contract explicitly distinguishes the outer JSON response envelope from literal file-language content;
4. Mission Control and Store share a five-attempt ceiling instead of the earlier three-versus-five mismatch.

The regression suite retained by #218 includes the prior-candidate-context case and a case where three failed candidates are repaired by a fourth attempt without bypassing deterministic checks, review, receipt, or integration.

Claim discipline:

- accepted bounded repair-context transport and shared attempt ceiling: **PASS / on main**;
- #218 exact merged-sha named ordinary CI: **PASS on its retained exact revision**;
- general repair reliability across tasks/models: **UNKNOWN / not established**;
- autonomous self-maintenance reliability: **UNKNOWN / not established**;
- #207/#208 accounting/release authority-ordering defect: **FAIL/open until separately repaired and requalified**.

#218 does not alter protected Factory/M4 code/evidence contracts and does not resolve the independent #207/#208 governance defects.

## Accepted #201 guided frontend/provider UX

#201 is accepted main behavior at `260b5f9...`.

The accepted browser/frontend change:

- separates the guided proof path from the interactive WebVM lab;
- adds accessible command animation using real RESIDUAL CLI commands and respects reduced-motion preferences;
- moves local quickstart guidance onto the landing page;
- aligns Mission Control with the public site's black/green visual system;
- keeps RESIDUAL provider setup inline in Mission Control rather than opening a separate RESIDUAL provider tab;
- keeps Puter authorization under explicit user gesture and allows Puter's secure authorization popup when required;
- keeps credentials outside RESIDUAL and provider loading lazy;
- preserves fail-closed provider protocol handling and credentialless provider-frame boundaries.

PR-head qualification on exact `4e172aed...` was **PASS** for Control Plane, Factory ownership, measured binding, clean install, Browser VM Demo, Pages, Command Station, Controller/provider, and maintainer approval. The merged exact main SHA is different, so post-merge qualification remains **PENDING** until its exact-SHA push workflows settle.

Claim discipline:

- accepted guided/inline frontend bytes: **PASS / on main**;
- exact PR-head automated qualification: **PASS for the named PR workflows**;
- exact merged-SHA post-#201 push qualification: **PENDING**;
- successful paid/live Puter candidate→verifier→receipt path: **UNKNOWN / not established**;
- physical iPhone heavyweight-WebVM reliability: **UNKNOWN / unqualified**.

## Exact-current-main qualification boundary

Exact `main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9` has seven ordinary `push` workflows created after #201 merged. At this status check, the set is still **PENDING**; at least Pages/deployment remains in progress. Do not inherit the green `4e172aed...` PR-head workflows or predecessor-main `d665b18...` push results as merged-SHA qualification.

Required interpretation:

- exact-current-main named automated push gates: **PENDING until the exact-SHA set completes**;
- #201 exact PR-head workflows: **PASS in their named scope**;
- historical exact-revision FAIL results: **still retained evidence**;
- universal/capable-runner M4 qualification: **not established**;
- true blank-environment install: **not established**;
- production long-run reliability: **not established**;
- physical iPhone heavyweight-WebVM reliability: **not established**;
- live-provider candidate→verifier→receipt success: **not established**.

## Retained research evidence: #202

Draft #202 remains research apparatus, not accepted product capability.

An earlier exact-head heterogeneous DAG run on `6b30125...` remains a retained **FAIL**: 1/3 tasks integrated, repair did not recover the dependent branch, and run control escalated with no runnable tasks.

A later distinct exact-head experiment on `03c77d12...` retained a bounded **PASS** using real local Ollama models across a three-task heterogeneous DAG with forced repair:

- runner: Qwen2.5-Coder 3B;
- reviewer: Llama 3.2 1B;
- 3/3 tasks integrated;
- verification receipts present for all three tasks;
- dependency lineage retained;
- deliberate bad candidates were rejected before later valid candidates integrated;
- release export was produced.

The later PASS does **not** erase the earlier FAIL and does not establish general DAG/recovery reliability, production readiness, or provider-independent model quality.

## Retained M6 self-host experiments: #203, #204, #215, #217 and #220

Draft #203 first-authoritative ImprovementSpec self-host trial remains **FAIL**: 0/1 integrated, three attempts, max-iteration escalation, no verification receipt, and no release.

Draft #204 M6-SPEC-002 with Qwen2.5-Coder 7B remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no verification receipt, and no release.

M6-SPEC-003 on draft #215 exercised prior-candidate repair context but remains **FAIL**: 0/1 integrated, no review/verification receipt/release/promotion. Retained candidates showed transport/source conflation.

M6-SPEC-004 on draft #217 explicitly separated transport JSON from file-language content while retaining prior-candidate context, but remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no review/receipt/release. Attempt 1 had an indentation error; attempts 2 and 3 imported a nonexistent `dataclasses.frozen` symbol.

### M6-SPEC-006 on #220 — bounded PASS

Draft #220 is research-only and remains unmerged. Its authoritative workflow ran against exact experiment head **`7971a05798fbc77f7be344dd15f920adf1fad03c`** on the corrected #218 runtime using Qwen2.5-Coder 7B.

Retained first-run evidence shows:

- attempt 1: candidate failed the frozen check and was rejected;
- attempt 2: candidate still accepted whitespace-only invalid values and was rejected;
- attempt 3: 2/2 frozen checks passed;
- Station reviewer: approved;
- integration: 1/1 task integrated;
- verification receipt: present;
- release export: present;
- batch outcome: success after 3 passes;
- workflow run `35334715201`: completed successfully on attempt 1 and retained artifact `m6-spec-006-corrected-runtime-evidence` (artifact `10543236401`).

Interpretation:

- M6-SPEC-006 exact trial: **PASS**;
- #203/#204/#215/#217 historical trials: **remain FAIL**;
- general M6 repair reliability: **UNKNOWN / not established**;
- autonomous discovery of improvements: **not tested by this fixed ImprovementSpec trial**;
- autonomous merge authority: **not granted**;
- central self-improvement/reliability research hypothesis: **not established by one positive trial**.

## Deterministic stress campaign A: #206

Draft #206 Campaign A completed its authoritative corrected exact-head runs at `e173719...` against frozen baseline `699e286...`. Workflow `success` means the experiment executed and retained artifacts, not that each scenario passed.

- **STRESS-A4 repair pressure: BLOCKED / invalid intervention.** Zero intended faults were injected; the scenario cannot be called PASS.
- **STRESS-A5 DAG pressure: FAIL / incomplete.** 3/6 tasks integrated before `no_runnable_tasks` escalation; no release export completed.
- **STRESS-A6 real-model reliability: FAIL in scope.** Three frozen Qwen2.5-Coder 7B trials produced 0 successes and accepted rate 0.0.

The later #220 PASS is a different intervention/runtime/spec trial. It does not erase A4/A5/A6.

## Deterministic stress campaign B: #207

Draft #207 remains research-only stress apparatus. Its scenario-level results remain:

- **STRESS-B1 budget ordering: FAIL** — exhausted-budget accounting occurred only after accepted integration/release;
- **STRESS-B2 early convergence: PASS** within that exact control;
- **STRESS-B3 terminal verifier failure/release: FAIL** — a non-empty release materialized after terminal verifier failure;
- **STRESS-B4 repeated repair pressure: containment PASS / recovery FAIL** — corrupt candidates were rejected, but the task did not recover to success within the frozen pass budget.

#218/#220 do not repair or requalify B1/B3; those authority-ordering failures remain independent blockers.

## Deterministic failure matrix: #212

Draft #212 Campaign C retained five deliberately different failure/recovery paths:

- malformed runner JSON: **PASS for fail-closed containment**;
- invalid reviewer schema: **PASS for fail-closed containment**;
- reviewer denial followed by approval: **PASS for that bounded recovery path**;
- transient HTTP 500: no integration, but provider retry/failover success remains **UNKNOWN / not established**;
- missing usage: **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` abort, corroborating #208.

## #214 governance repair candidate: BLOCKED / stale-base / unaccepted

Draft #214 targets #208 by moving token/deadline checks ahead of Station review/integration authority effects and tightening release eligibility around successful run control. It remains open and unmerged, with head `d3e8a5ec...` still based on predecessor `main@4608afa...`. After #218/#201 moved main to `260b5f9...`, #214 is not an exact-current-main candidate and must be refreshed/requalified before any acceptance decision.

Therefore no accepted-main claim changes: the #207/#212 accounting-ordering defect remains **FAIL/open** until a current-base repair is accepted and the applicable scenarios are requalified.

## WebVM runtime diagnostics and #133/#132 discrepancy

Accepted #133 diagnostics narrow one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()` in the tested guest/runtime combination. The exact lower-level CPython/i386 ABI/emulation cause remains **UNKNOWN**.

#133 also removed the previously accepted #132 protected self-hosting/research-bundle implementation, tests, workflow, example and dedicated docs. #132 remains retained historical evidence, but that tooling is **not current accepted capability**. Whether removal was intentional retirement or an integration regression remains **UNKNOWN / unresolved**.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of the historical invalid responses: **UNKNOWN**;
- current-main live-provider semantic success after #201/#205/#218: **UNKNOWN / not established**.

A fresh retained real-account mission on the exact deployed accepted revision is required before paid/live provider success can become PASS.

## iPhone/WebKit and WebVM reliability boundary

The accepted #186 fallback detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to the lightweight walkthrough, retaining the full VM only as an explicit diagnostic override.

This is a fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation remains open, and the lower-level WebKit process-kill cause remains **UNKNOWN**.

Issues #120 and #126 remain open. Existing diagnostics and bounded lifecycle repairs do not quantify an acceptable recurrence rate or establish a production fix for the broader reliability family.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

Accepted #185/#187 protected-byte/ownership-baseline changes remain scoped to their reviewed behavior. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent and must not be treated as cleared by unrelated green CI.

This documentation branch changes no Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier/evidence schemas, provider authorization, or acceptance authority.

## Current priority blockers

1. Let exact `main@260b5f9...` post-#201 push qualification settle; preserve any first exact-SHA failure rather than inheriting PR-head PASS.
2. Refresh/rebase, review, and requalify the #207/#208 accounting/release-ordering repair path on current main; #214 is stale-base and unaccepted, and #212's missing-usage case remains a retained FAIL.
3. Preserve #220 as one bounded M6 PASS while continuing preregistered repeated/self-discovery validation; do not erase #203/#204/#215/#217 or claim general autonomous self-maintenance.
4. Re-run a valid #206 repair-pressure intervention; A4 remains BLOCKED, while A5/A6 remain negative cells.
5. Retain a fresh exact-current-deployed-revision real-account Puter candidate→verifier→receipt success, or keep live-provider success UNKNOWN.
6. Physically validate the accepted #186 fallback without broadening it into a heavyweight-WebVM reliability claim.
7. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak.
8. Continue #120/#126 WebVM root-cause and long-run reliability work.
9. Resolve the #133/#132 retirement-versus-restoration discrepancy explicitly.
10. Keep #139→ownership-baseline→fresh-qualification→#134 independent.
11. Refresh/requalify broader stale candidates such as #152/#177 before current claims use them.
12. Freeze the confirmatory R0–R5 protocol before paper-facing outcome collection.

## Documentation scope

`README.md`, `HARNESS.md`, this status document, the roadmap, research, and evaluation prose are descriptive. `START-HERE.md` remains valid operator guidance and is intentionally unchanged. `implementation-status.yaml` remains accurate as an implementation-presence manifest and is intentionally unchanged.

No documentation-only change may be used to infer qualification beyond retained repository/CI/evidence artifacts.