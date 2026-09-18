# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@d665b188ccc5bb659fb37bc52ac387ab4d85f976`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`d665b188ccc5bb659fb37bc52ac387ab4d85f976`**.

Meaningful accepted changes since `main@4608afabf5de4c87d77aaf149dfc12538d364f43`:

- **#216** merged the documentation-only status refresh after exact-head maintainer attestation. It changed descriptive docs only and did not alter implementation, qualification anchors, ownership baselines, protected bytes, verifier authority, or evidence schemas.
- **#218** merged as current main and applies bounded M6 repair-loop lessons to Station: prior failed-candidate writable-file content can be supplied as bounded repair context while each new candidate still starts from a clean baseline worktree; repair-context hashes are retained; the runner contract separates its JSON transport envelope from file-language content; and Mission Control/Store share a bounded five-attempt ceiling. The PR does not weaken deterministic checks, review, receipt, integration, quarantine, promotion, Factory/M4, or verifier authority.

For exact `main@d665b18...`, seven observed ordinary `push` workflows completed **PASS on attempt 1**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station, and Pages/deployment. These are scoped automated results only. They do not establish every-host/capable-runner M4 qualification, true blank-environment install, host-loss recovery, elapsed soak, live-provider semantic success, physical heavyweight-WebVM iPhone reliability, or confirmatory research.

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

#218 is accepted main behavior at `d665b18...`.

The bounded change does four relevant things:

1. a repair attempt may receive content from the immediately prior failed candidate, limited to declared writable files;
2. that repair context is content-bound with retained hashes while the new candidate is still generated from a fresh baseline worktree;
3. the runner contract explicitly distinguishes the outer JSON response envelope from literal file-language content;
4. Mission Control and Store share a five-attempt ceiling instead of the earlier three-versus-five mismatch.

The regression suite retained by #218 includes the prior-candidate-context case and a case where three failed candidates are repaired by a fourth attempt without bypassing deterministic checks, review, receipt, or integration.

Claim discipline:

- accepted bounded repair-context transport and shared attempt ceiling: **PASS / on main**;
- exact-current-main ordinary CI for the named seven push gates: **PASS on attempt 1**;
- general repair reliability across tasks/models: **UNKNOWN / not established**;
- autonomous self-maintenance reliability: **UNKNOWN / not established**;
- #207/#208 accounting/release authority-ordering defect: **FAIL/open until separately repaired and requalified**.

#218 does not alter protected Factory/M4 code/evidence contracts and does not resolve the independent #207/#208 governance defects.

## Exact-current-main qualification boundary

For exact `main@d665b188ccc5bb659fb37bc52ac387ab4d85f976`, the retained ordinary `push` run set observed for this status refresh contains seven named workflows, all **PASS on attempt 1**:

- Factory ownership gate;
- M4 qualification runner prerequisites;
- Measured evaluation acceptance binding;
- Clean install qualification;
- Controller and provider contracts;
- Command Station checks;
- Deploy GitHub Pages.

Do not broaden that statement. In particular:

- exact-main named automated gates: **PASS for the seven observed runs above**;
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

Draft #220 is research-only and remains unmerged. Its authoritative workflow ran against exact experiment head **`7971a05798fbc77f7be344dd15f920adf1fad03c`** on base `main@d665b18...` using Qwen2.5-Coder 7B and the accepted #218 repair-loop behavior.

Retained first-run evidence shows:

- attempt 1: candidate compiled but failed the frozen behavioral/import contract and was rejected;
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

This is the first bounded positive M6 repair-loop result after the retained negative sequence, not a reason to rewrite the negative cells as success.

## Deterministic stress campaign A: #206

Draft #206 Campaign A completed its authoritative corrected exact-head runs at `e173719...` against frozen baseline `699e286...`. The earlier apparatus revision is explicitly invalid because it would have used GitHub's synthetic pull-request merge commit; only the corrected exact-head campaign is used for claims below. Workflow `success` means the experiment executed and retained artifacts, not that each scenario passed.

### STRESS-A4 — repair pressure: BLOCKED / invalid intervention

The retained run recorded 0 injected faults. Its single provider call ended in a model-connection/structured-output failure, usage became unknown, run control aborted on `usage_unknown_or_invalid`, 0/1 integrated, and no verification receipt was produced. The intended repair-pressure intervention was not exercised, so this scenario is **BLOCKED / invalid for repair-pressure qualification**, not PASS.

### STRESS-A5 — DAG pressure: FAIL / incomplete

The retained six-task DAG integrated 3/6 tasks across five passes, then escalated on `no_runnable_tasks`. DAG-A/B/C integrated with receipts; DAG-D remained `repair_required`; DAG-E/F did not complete; no release export was attempted. This is **FAIL / incomplete for that frozen DAG-pressure scenario**.

### STRESS-A6 — real-model reliability: FAIL in scope

Three frozen Qwen2.5-Coder 7B trials produced 0 successes and accepted rate 0.0. Each ended 0/1 integrated after the three-pass max-iteration brake. This is **FAIL for that exact model/spec/baseline campaign** and must not be generalized into a blanket model-quality claim.

The later #220 PASS is a different intervention/runtime/spec trial. It does not erase A4/A5/A6.

## Deterministic stress campaign B: #207

Draft #207 is research-only stress apparatus against a frozen baseline. A successful GitHub Actions workflow means the campaign executed and retained its artifacts; it does **not** mean every scenario passed.

Retained campaign-B evidence contains two important governance failures and one bounded containment result:

### STRESS-B1 — budget ordering: FAIL

The run recorded token-budget exhaustion, but accepted integration/release had already occurred before final accounting observed the exhausted budget. This is a **FAIL** for the stronger claim that exhausted budget accounting always prevents later accepted integration/release.

### STRESS-B2 — early convergence: PASS

The frozen early-convergence control completed with 2/2 integrated and the normal completion brake, without the budget/max-iteration trips under study. This is **PASS within that exact control scenario**.

### STRESS-B3 — terminal verifier failure / release: FAIL

The batch recorded a terminal verifier failure and aborted with 0 integrated, yet a non-empty release was still materialized after the terminal failure. This is a **FAIL** for the stronger fail-closed release-eligibility claim.

### STRESS-B4 — repeated repair pressure: mixed bounded result

Two deterministic corrupt candidates were injected and rejected; none integrated. The third attempt still failed its behavior check and the run escalated at the maximum pass count. Therefore corrupt-candidate containment in this exact scenario is **PASS**, successful recovery-to-completion is **FAIL / not achieved**, and general repair reliability remains **UNKNOWN**.

#218/#220 do not repair or requalify B1/B3; those authority-ordering failures remain independent blockers.

## Deterministic failure matrix: #212

Draft #212 Campaign C retained five deliberately different failure/recovery paths:

- malformed runner JSON was rejected three times with no review/integration: **PASS for fail-closed containment in that exact scenario**;
- invalid reviewer schema was rejected three times while the valid candidate stayed `review_ready`, with no integration/receipt: **PASS for fail-closed containment in that exact scenario**;
- reviewer denial followed by a repaired runner/reviewer cycle integrated on attempt 2: **PASS for that bounded recovery path**;
- a transient HTTP 500 was marked retryable but had no alternate failover candidate; usage became unknown and the host budget aborted with no integration. Provider retry/failover success remains **UNKNOWN / not established**;
- missing usage allowed a valid runner and reviewer result to integrate and receive a receipt before the host later aborted on `usage_unknown_or_invalid`: **FAIL for the stronger accounting-before-authority claim**, corroborating #208.

## #214 governance repair candidate: BLOCKED / stale-base / unaccepted

Draft #214 targets #208 by moving token/deadline checks ahead of Station review/integration authority effects and tightening release eligibility around successful run control. It remains open and unmerged, with head `d3e8a5ec...` still based on predecessor `main@4608afa...`. After #218 moved main to `d665b18...`, #214 is no longer an exact-current-main candidate and must be refreshed/requalified before any acceptance decision.

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
- current-main live-provider semantic success after #205/#218: **UNKNOWN / not established**.

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

1. Refresh/rebase, review, and requalify the #207/#208 accounting/release-ordering repair path on current main; #214 is stale-base and unaccepted, and #212's missing-usage case remains a retained FAIL.
2. Preserve #220 as one bounded M6 PASS while continuing preregistered repeated/self-discovery validation; do not erase #203/#204/#215/#217 or claim general autonomous self-maintenance.
3. Re-run a valid #206 repair-pressure intervention; A4 remains BLOCKED because its intended fault was not injected, while A5/A6 remain negative cells.
4. Retain a fresh exact-current-deployed-revision real-account Puter candidate→verifier→receipt success, or keep live-provider success UNKNOWN.
5. Physically validate the accepted #186 fallback without broadening it into a heavyweight-WebVM reliability claim.
6. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak.
7. Continue #120/#126 WebVM root-cause and long-run reliability work.
8. Resolve the #133/#132 retirement-versus-restoration discrepancy explicitly.
9. Keep #139→ownership-baseline→fresh-qualification→#134 independent.
10. Refresh/requalify broader stale candidates such as #152/#177 before current claims use them.
11. Freeze the confirmatory R0–R5 protocol before paper-facing outcome collection.

## Documentation scope

`README.md`, `HARNESS.md`, this status document, the roadmap, research, and evaluation prose are descriptive. `START-HERE.md` remains valid operator guidance and is intentionally unchanged. `implementation-status.yaml` remains accurate as an implementation-presence manifest and is intentionally unchanged.

No documentation-only change may be used to infer qualification beyond retained repository/CI/evidence artifacts.