# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@4608afabf5de4c87d77aaf149dfc12538d364f43`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`4608afabf5de4c87d77aaf149dfc12538d364f43`**.

Meaningful accepted changes since `main@699e2869e294fe157b4bfd73a272057683a2f7e0`:

- **#200** merged as `fc1eb8b19f4de9c4d3ecf9f797b76e29884a281d`: native setup defaults are now local/persistent and shell integration is opt-in.
- **#205** merged as current main: Mission Control restores its private provider channel across reload/remount using validated session-scoped state and clears it on explicit close.

Neither merge changes protected Factory/M4 implementation, ownership-baseline schemas, qualification anchors, verifier authority, or evidence schemas.

The exact-current-main Actions query for `4608afa...` returned a completed run set with no pending, cancelled, or failing conclusion observed; a sampled Controller/provider run completed **PASS on attempt 1**. These are scoped automated results only. They do not establish every-host/capable-runner M4 qualification, blank-environment install, host-loss recovery, elapsed soak, live-provider semantic success, physical heavyweight-WebVM iPhone reliability, or confirmatory research.

Since the prior status refresh, accepted `main` has not moved. New research evidence has, however, closed several previously pending experiment cells: #206 Campaign A completed with BLOCKED/FAIL outcomes in its repair/DAG/reliability scenarios, #212 reproduced the accounting-before-authority defect for missing usage while also retaining bounded fail-closed/recovery controls, and #215/#217 retained additional failed M6 self-maintenance trials. Draft #214 is a candidate repair for #208; it is not accepted main behavior.

## Accepted #200 setup hardening

#200 is now accepted main behavior.

The setup path now:

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

#205 is now accepted main behavior.

The browser provider-session layer persists the private provider-channel token in `sessionStorage`, validates a restored token before reuse, reattaches the same session channel after Mission Control reload/remount, ignores invalid stored state fail-closed, and clears the token on explicit close.

This supersedes the previously open provider-channel recovery problem represented by #190 at the accepted-byte level. Historical #190 candidate evidence remains historical and does not need to be reinterpreted as accepted proof.

Claim discipline:

- accepted reload/remount channel recovery behavior: **PASS / on main**;
- browser regression coverage for restored/invalid/closed channel state: **PASS within the tested scope**;
- successful paid/live Puter inference: **UNKNOWN / not established**;
- retained manual production SDK/sign-in success on exact current main: **UNKNOWN / not established**.

## Exact-current-main qualification boundary

Exact `main@4608afa...` has a completed exact-SHA Actions set with no pending, cancelled, or failing run observed in the retained query used for this status refresh. The sampled Controller/provider workflow completed **PASS on attempt 1**.

Do not broaden that statement. In particular:

- exact-main named automated gates: **PASS where retained exact-SHA runs say PASS**;
- historical exact-revision FAIL results: **still retained evidence**;
- universal/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established**;
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
- a deliberate first-candidate SyntaxError was rejected and transitioned to repair before a later candidate integrated;
- an out-of-contract write was rejected before a later attempt succeeded;
- invalid/truncated reviewer output was rejected before a valid review was accepted;
- release export was produced.

The later PASS does **not** erase the earlier FAIL and does not establish general DAG/recovery reliability, production readiness, or provider-independent model quality.

## Retained M6 self-host experiments: #203, #204, #215 and #217

Draft #203 first-authoritative ImprovementSpec self-host trial remains **FAIL**: 0/1 integrated, three attempts, max-iteration escalation, no verification receipt, and no release.

Draft #204 repeated the bounded research question with Qwen2.5-Coder 7B. Its first-authoritative M6-SPEC-002 run also remains **FAIL**:

- batch outcome: escalated;
- integrated: 0/1;
- passes: 3;
- run-control brake: max iteration;
- verification receipt: absent;
- release: absent.

Observed candidate defects changed across attempts, but the stronger model did not establish the requested contract within the frozen pass budget.

M6-SPEC-003 on draft #215 added prior-candidate repair context. The intervention was exercised and repair-context hashes were retained on attempts 2 and 3, but the first authoritative run remains **FAIL**: 0/1 integrated, three calls, no review/verification receipt/release/promotion. Retained candidates showed transport/source conflation rather than a successful `ImprovementSpec` implementation.

M6-SPEC-004 on draft #217 retained prior-candidate context and explicitly separated transport JSON from file-language content without changing acceptance policy. Its authoritative exact-head workflow retained evidence but the experiment remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no review/receipt/release. The generated source changed from the M6-SPEC-003 data-object failure mode, but still failed checks: attempt 1 had an indentation error; attempts 2 and 3 imported a nonexistent `dataclasses.frozen` symbol.

The implementation candidate underlying the repair-context work (#213) remains unaccepted. These are negative research results, not proof of autonomous recursive self-improvement and not restoration of removed #132 capability.

## Deterministic stress campaign A: #206

Draft #206 Campaign A has completed its authoritative corrected exact-head runs at `e173719...` against frozen baseline `699e286...`. The earlier apparatus revision is explicitly invalid because it would have used GitHub's synthetic pull-request merge commit; only the corrected exact-head campaign is used for claims below. Workflow `success` means the experiment executed and retained artifacts, not that each scenario passed.

### STRESS-A4 — repair pressure: BLOCKED / invalid intervention

The retained run recorded 0 injected faults. Its single provider call ended in a model-connection/structured-output failure, usage became unknown, run control aborted on `usage_unknown_or_invalid`, 0/1 integrated, and no verification receipt was produced. The intended repair-pressure intervention was not exercised, so this scenario is **BLOCKED / invalid for repair-pressure qualification**, not PASS.

### STRESS-A5 — DAG pressure: FAIL / incomplete

The retained six-task DAG integrated 3/6 tasks across five passes, then escalated on `no_runnable_tasks`. DAG-A/B/C integrated with receipts; DAG-D remained `repair_required`; DAG-E/F did not complete; no release export was attempted. This is **FAIL / incomplete for that frozen DAG-pressure scenario**, not evidence of general DAG reliability.

### STRESS-A6 — real-model reliability: FAIL in scope

Three frozen Qwen2.5-Coder 7B trials produced 0 successes and accepted rate 0.0. Each ended 0/1 integrated after the three-pass max-iteration brake. This is **FAIL for that exact model/spec/baseline campaign** and must not be generalized into a blanket model-quality claim.

Campaign A also retained bounded control/injection artifacts. They do not erase the BLOCKED/FAIL cells above.

## Deterministic stress campaign B: #207

Draft #207 is research-only stress apparatus against a frozen baseline. A successful GitHub Actions workflow means the campaign executed and retained its artifacts; it does **not** mean every scenario passed.

Retained campaign-B evidence contains two important governance failures and one bounded containment result:

### STRESS-B1 — budget ordering: FAIL

The run recorded a token-budget exhaustion, but accepted integration/release had already occurred before final accounting observed the exhausted budget. This is a **FAIL** for the stronger claim that exhausted budget accounting always prevents later accepted integration/release.

### STRESS-B2 — early convergence: PASS

The frozen early-convergence control completed with 2/2 integrated and the normal completion brake, without the budget/max-iteration trips under study. This is **PASS within that exact control scenario**.

### STRESS-B3 — terminal verifier failure / release: FAIL

The batch recorded a terminal verifier failure and aborted with 0 integrated, yet a non-empty release was still materialized after the terminal failure. This is a **FAIL** for the stronger fail-closed release-eligibility claim and is a current research blocker until repaired/requalified.

### STRESS-B4 — repeated repair pressure: mixed bounded result

Two deterministic corrupt candidates were injected and rejected; `corrupted_candidate_integrated=false` and integrated remained 0/1. The third attempt still failed its behavior check and the run escalated at the maximum pass count. Therefore:

- corrupt-candidate containment in this exact scenario: **PASS**;
- successful recovery-to-completion within the frozen pass budget: **FAIL / not achieved**;
- general repair reliability: **UNKNOWN / not established**.

These negative findings must remain visible and should drive a focused implementation/requalification sequence before stronger governance claims are made.

## Deterministic failure matrix: #212

Draft #212 Campaign C retained five deliberately different failure/recovery paths:

- malformed runner JSON was rejected three times with no review/integration: **PASS for fail-closed containment in that exact scenario**;
- invalid reviewer schema was rejected three times while the valid candidate stayed `review_ready`, with no integration/receipt: **PASS for fail-closed containment in that exact scenario**;
- reviewer denial followed by a repaired runner/reviewer cycle integrated on attempt 2: **PASS for that bounded recovery path**;
- a transient HTTP 500 was marked retryable but had no alternate failover candidate; the call ended, usage became unknown, and the host budget aborted with no integration. Provider retry/failover success therefore remains **UNKNOWN / not established**;
- missing usage allowed a valid runner and reviewer result to integrate and receive a receipt before the host later aborted on `usage_unknown_or_invalid`: **FAIL for the stronger accounting-before-authority claim**, corroborating #208 beyond the numeric over-budget case.

## #214 governance repair candidate: BLOCKED / unaccepted

Draft #214 targets #208 by moving token/deadline checks ahead of Station review/integration authority effects and tightening release eligibility around successful run control. On its observed exact head, the ordinary technical workflows are green, but the maintainer approval gate remains **FAIL/BLOCKED** and the PR is still draft/unaccepted. Therefore no accepted-main claim is changed: the #207/#212 ordering defect remains open until a repair is accepted and the applicable scenarios are requalified.

## WebVM runtime diagnostics and #133/#132 discrepancy

Accepted #133 diagnostics narrow one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()` in the tested guest/runtime combination. The exact lower-level CPython/i386 ABI/emulation cause remains **UNKNOWN**.

#133 also removed the previously accepted #132 protected self-hosting/research-bundle implementation, tests, workflow, example and dedicated docs. #132 remains retained historical evidence, but that tooling is **not current accepted capability**. Whether removal was intentional retirement or an integration regression remains **UNKNOWN / unresolved** and should be decided explicitly rather than reconstructed in documentation.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of the historical invalid responses: **UNKNOWN**;
- current-main live-provider semantic success after #205: **UNKNOWN / not established**.

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

1. Repair and requalify the #207/#208 accounting/release-ordering failures, including #212's missing-usage case. #214 is only a draft candidate until accepted and requalified.
2. Re-run a valid #206 repair-pressure intervention; A4 is BLOCKED because its intended fault was not injected. Preserve A5/A6 negative results rather than treating later experiments as erasure.
3. Continue bounded M6 repair research without promoting #213/#215/#217 into accepted self-maintenance capability; M6-SPEC-003 and -004 both remain retained FAIL results.
4. Retain a fresh exact-current-deployed-revision real-account Puter candidate→verifier→receipt success, or keep live-provider success UNKNOWN.
5. Physically validate the accepted #186 fallback without broadening it into a heavyweight-WebVM reliability claim.
6. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak.
7. Continue #120/#126 WebVM root-cause and long-run reliability work.
8. Resolve the #133/#132 retirement-versus-restoration discrepancy explicitly.
9. Keep #139→ownership-baseline→fresh-qualification→#134 independent.
10. Refresh broader stale candidates such as #152/#177 before current claims use them.
11. Freeze the confirmatory R0–R5 protocol before paper-facing outcome collection.

## Documentation scope

`README.md`, `HARNESS.md`, this status document, the roadmap, research, and evaluation prose are descriptive. `START-HERE.md` remains valid operator guidance and does not make the stale current-main claims corrected here. `implementation-status.yaml` remains accurate as an implementation-presence manifest and is intentionally unchanged.

No documentation-only change may be used to infer qualification beyond retained repository/CI/evidence artifacts.