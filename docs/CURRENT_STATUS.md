# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against current `main` at `f6f9bad84caccf68c7ab35e5788e756d12c55fb7`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted review records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The repository contains substantial implementation and qualification evidence for bounded execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

Current `main` is **technically qualified for its observed automated/browser scopes but review-provisional**. PR #156 repaired the real Puter worker-envelope boundary after live-account `provider_protocol_invalid` failures. Its exact merged revision passed the observed main-push qualification set, but no submitted independent review exists for #156.

Fresh post-#156 iPhone/WebKit evidence now provides a newer live product result: the browser reached **`Provider connected`**, but the Linux guest emitted **`RESIDUAL_WORKER_POISONED`** and Mission Control remained at **`GUEST STARTING`** with no supported recovery path. That public-demo attempt is an end-to-end **FAIL** at the guest-recovery/product boundary. It does not prove a provider-model failure, because no valid candidate completed the normal RESIDUAL verifier path; successful paid/live Puter candidate execution remains **UNKNOWN**. The lower-level cause of the poisoned guest also remains **UNKNOWN**.

The project does **not** claim that the central live-model reliability hypothesis is proven, that WebVM has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that end-to-end real Puter execution is qualified on current main, that blank-machine/recovery qualification is complete, or that elapsed production soak targets have been met.

## Current main — technically qualified, review-provisional

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, tree **`9991788c5d59b8ccd3b18b10ad0d4a46098305df`**, the merge of PR #156.

PR #156 followed fresh real-account evidence on the #151 surface where two actual remote calls to `openai/gpt-5.4-nano` both failed closed as `provider_protocol_invalid`, with zero accepted obligations and no candidate reaching verification. The repair:

- removes provider-side `strict: true` structured-output mode from the dynamic obligation-key worker envelope;
- retains the exact tool schema and RESIDUAL's fail-closed local parser/verifier as the acceptance authority;
- restores explicit obligation-key nesting guidance;
- explicitly requires build output under `updates.build = {summary, files}`;
- explicitly requires `requests: []` when no evidence pull is needed;
- preserves grant/model binding, call budget, non-stream transport, progress telemetry, mailbox and verifier semantics.

No Factory/M4 trust-boundary implementation, ownership baseline or shared evidence schema changed in #156.

### Exact merged-main qualification

All **seven observed main-push workflows passed** on exact `main@f6f9bad8...`:

- measured-evaluation acceptance binding — `35158939300` — **PASS**;
- Factory ownership — `35158939411` — **PASS**;
- controller/provider contracts — `35158939242` — **PASS**;
- Command Station — `35158939291` — **PASS**;
- clean install — `35158939243` — **PASS**;
- capable-runner M4 prerequisite/qualification — `35158939207` — **PASS**;
- Pages/WebVM — `35158939226` — **PASS**.

The M4 workflow passed its fail-closed capability probe and zero-skip qualification gate. Pages run `35158939226` completed on **attempt 1**: generated desktop+narrow browser proof passed, deployment passed, published real-guest execution passed, published narrow-Chromium acceptance passed, and live acceptance proof was retained.

These are revision- and environment-bound `PASS` results. They do **not** establish independent technical review, every-host M4 capability, paid/live-provider quality, long-run WebVM reliability, release/recovery qualification, elapsed soak or confirmatory research claims.

GitHub records **zero submitted reviews** for PR #156. Current main therefore remains **review-provisional**. Green CI is not independent acceptance. Missing pre-merge independent acceptance on #136/#145/#147/#151/#156 remains governance debt.

## Live real-provider and production WebVM boundary

### Retained pre-#156 provider failure

The earlier retained real-account provider evidence is authoritative **FAIL** evidence:

- two actual remote calls were made to `openai/gpt-5.4-nano`;
- both returned `provider_protocol_invalid`;
- zero obligations were accepted;
- no candidate reached verification.

That failure is not erased by #156. PR #156's post-merge provider-contract/browser/Pages qualification is **PASS for its tested automated scope**, but automated provider tests are not a real-account Puter success.

### Fresh post-#156 real-device failure

Fresh iPhone/WebKit public-demo evidence after #156 moved the observed failure boundary:

- the provider UI reached **`Provider connected`**;
- the Linux guest emitted **`RESIDUAL_WORKER_POISONED`**;
- Mission Control remained **`GUEST STARTING`**;
- no supported recovery path returned the browser session to a usable guest;
- no valid live candidate completed the normal verifier/receipt path.

The correct classification is:

- current-main automated provider/browser qualification: **PASS** for the tested automated scope;
- earlier real-account provider-envelope result: **FAIL**;
- fresh post-#156 end-to-end public-demo result: **FAIL** at the guest-recovery/product boundary;
- successful paid/live Puter candidate execution and verification on exact current main: **UNKNOWN**;
- lower-level cause of the production guest poison: **UNKNOWN**.

Do not describe the public real-provider demo as fixed from current-main CI alone.

## Poisoned-guest recovery candidates

### PR #158 — clear poison after proven recovery: exact-head FAIL

PR #158 (`ac637711cf9ec5ba3f6283f4484f9823d92b763b`) combines in-console provider setup with a recovery change that removes the poison tombstone after worker death/state cleanup is considered proven.

Exact-head workflow state is **not qualified**:

- clean install — **PASS**;
- measured binding — **PASS**;
- Factory ownership — **PASS**;
- Control Plane — **PASS**;
- Browser VM Demo CI — **PASS**;
- controller/provider contracts — **FAIL** (`35163658277`);
- Command Station — **FAIL** (`35163658222`);
- Pages/WebVM — **FAIL** (`35163658236`).

The authoritative Python 3.11 controller/provider failure ran 1,061 tests and retained **2 failures, 22 skips**. Both failures are directly about durable poison retention:

- `test_recovery_removes_safe_queued_control_after_worker_death` expected the poison file to remain and observed it missing;
- `test_timeout_recovery_kills_worker_recovers_matching_lock_and_fences_restart` failed because the durable timeout poison was not retained.

This is an exact-head **FAIL**. Do not waive it or infer that #158 is safe because some browser-focused jobs are green.

### PR #159 — replace poisoned guest with fresh overlay: technically green, review BLOCKED

PR #159 (`5c33f31d234e3be315a052109fe270d3b70276c5`) preserves the old poisoned guest and its durable fence, then adds recovery by replacing the whole writable WebVM guest overlay:

- host-visible state becomes `starting`, `ready` or `poisoned`;
- poisoned sessions render `GUEST FAILED · RESTART REQUIRED` rather than indefinite `GUEST STARTING`;
- `Restart guest` is available only for a poisoned, idle session;
- the current provider grant/session is ended before restart so a remote call is not replayed;
- a browser-session overlay generation is rotated and the page reloads;
- normal reloads retain the same overlay generation;
- the old poison file is not deleted or interpreted as reusable state.

The changed files are limited to WebVM/demo and a focused regression test; no Factory/M4 protected implementation/test/schema, ownership pin, shared evidence schema, verifier, provider acceptance semantics or qualification threshold changes.

All **eight observed applicable workflows are PASS** on exact head `5c33f31d...`:

- measured binding — `35165844021` — **PASS**;
- Control Plane — `35165843890` — **PASS**;
- Factory ownership — `35165844001` — **PASS**;
- clean install — `35165844069` — **PASS**;
- Browser VM Demo CI — `35165844052` — **PASS**;
- controller/provider contracts — `35165843976` — **PASS**;
- Command Station — `35165844005` — **PASS**;
- Pages/WebVM — `35165843944` — **PASS**.

Pages generated desktop+narrow proof passed. The browser acceptance deliberately reproduces the durable poisoned-worker boundary, requires `GUEST FAILED · RESTART REQUIRED`, rotates to a fresh browser-session overlay, proves poison/PID/control/busy/active-lock state did not carry into the replacement guest, and then completes a real local repository audit.

This is **browser/guest recovery evidence only**. Cloud inference remains test-double coverage and no real Puter success is created by #159.

GitHub records one submitted review on #159: an owner `COMMENTED` handoff explicitly labeled **not independent acceptance**. Therefore #159 is technically green for its tested exact-head scopes but **BLOCKED on genuinely independent technical review**. If independently accepted and merged, the exact merged revision must still pass production Pages and then a fresh real-account iPhone/WebKit build before the public provider demo can be called fixed.

## WebVM reliability boundary

Issues **#120** and **#126** remain open.

Diagnostic work retains reproducible evidence for a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around call 273. Tested direct libc waits continue beyond that narrow boundary, and fresh process creation resets or avoids the observed symptom.

Merged #145 routes long-lived browser polling below that known Python timed-wait surface. Avoiding the trigger is not root-cause proof. The exact CPython/glibc/WebVM mechanism, relationship to earlier `_sha512`/impossible-constructor/allocator-corruption symptoms, and acceptable production recurrence rate remain **UNKNOWN**.

The fresh poisoned-guest event is additional production reliability evidence. It has **not** been shown to share the timed-wait root cause, so that relationship remains **UNKNOWN**.

Keep #120/#126 open until a predefined retained repeated-run reliability campaign or a proven regression-tested root cause supports closure.

## Browser acceptance / onboarding

PR #89 retains an authoritative first-attempt narrow-browser **FAIL** caused by an acceptance-observation defect in terminal exit-marker parsing. That failure remains evidence and #89 is **NOT qualified**.

PR #153 consolidates the bounded #140/#150 acceptance-harness repairs and is refreshed onto exact current main at head `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`.

All **eight observed applicable workflows are PASS** on that exact head, including Browser VM Demo CI and Pages/WebVM. Those green results qualify only the focused acceptance-harness repair on that revision; they do not qualify #89, live-provider behavior, long-run WebVM reliability, blank-machine/recovery behavior, elapsed soak or research claims.

No qualifying genuinely independent approval is bound to current head `35cbf2ba...`. PR #153 is therefore **technically qualified for its tested scope but BLOCKED on independent acceptance before integration**. Only after an accepted #153 integration should #89 be refreshed and requalified; #153 does not erase #89's retained failure or qualify #89 by itself.

## Qualification v1 — PR #152

PR #152 proposes a unified evidence-first qualification layer over the existing repository gates. It adds fail-closed qualification manifests/evidence envelopes, generated lifecycle exploration, RuntimeJournal state-machine testing, DSM fault-matrix binding, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys, bounded process-soak tooling and manual elapsed-soak/live-provider workflows.

Its current head `2a70f38751f843d577ae0492c281262546d6cc43` was built on pre-#156 main. Any earlier green or partial workflow evidence remains exact-head history and **does not qualify #152 against current main**.

No aggregate Qualification v1 `PASS` is claimed. Virtual-day stress is not elapsed wall-clock soak; a live-provider canary would prove only one bounded adapter execution path, not model quality; 24h/72h/30d evidence does not exist until those wall-clock runs actually complete.

## Other integration candidates after #156

- **#146** — independent-current-head review enforcement at `c416d408149408ff8668a48d6e73eb1f3bf6347e`. Six observed ordinary repository workflows are **PASS**. Its 15 policy regressions pass, while the live independent-review gate correctly reports **BLOCKED** because no qualifying independent current-head approval exists. This is expected fail-closed behavior, not a code-qualification waiver. Platform ruleset enforcement remains a separate maintainer action after accepted integration.
- **#118** — runtime/DSM candidate at `ee81051220c616f8a605c948820d972177e19801`; applicable exact-head workflows pass, but zero reviews exist. Preserve earlier first-attempt failures and require genuine independent acceptance.
- **#115** — release/recovery candidate at `27e6e3b790d950ad1e8dd3603569f2eb5090ada4`; applicable exact-head workflows pass, but zero reviews exist. Evidence remains procedure/simulation evidence, not true blank-OS, host-loss or elapsed-soak proof.
- **#131** — separate two-file SoakState persistence candidate at `0094dd4c27231f8c4f71161b9a82770a27c7aa7b`; applicable exact-head workflows pass, but zero reviews exist. This is not elapsed-soak evidence.
- **#93** — retains an authoritative runtime-journal concurrency failure/protected dependency from its tested head; it is **NOT qualified** until that blocker is resolved and the lane is rebuilt/requalified.

Do not merge any candidate from stale or incomplete exact-head evidence.

## Factory / M4 protected boundary

M2/M3/M4 are implemented. Issues #63 and #48 are closed. Current M4 claims remain environment-bound: capable-runner qualification is not every-host qualification, and namespace/capability-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not `PASS`.

### PR #139 — protected test repair

PR #139 changes protected `tests/test_factory_m4_safety.py` to close a `/proc/<pid>/status` observation race without weakening the termination property.

Ownership/dependent gates correctly fail closed while the baseline pins the prior protected test blob. A same-author/owner COMMENT is not independent acceptance.

Required sequence remains:

1. genuinely independent review of the exact protected head;
2. deliberate ownership-baseline decision if accepted;
3. fresh qualification after any protected pin change;
4. only then refresh/requalify downstream #134 against the resulting current main.

This documentation update changes no protected byte, ownership pin, qualification anchor, evidence schema or qualification threshold.

### PR #134 — provider-adapter lane

PR #134 remains downstream of #139 and behind current main. Its retained first-attempt failure remains evidence. Adapter-specific tests passing in that run do not turn the full workflow into `PASS`.

Do not advance #134 until #139 completes the independent protected-byte sequence, then refresh/requalify #134 against current main before any integration or new live-provider acceptance request.

## Governance / independent review

Issue **#144** remains open.

PR #146 codifies a fail-closed repository-side independent-current-head review check. The intended gate accepts only a human, non-author reviewer with write/admin permission who approved the exact current PR head and has not subsequently invalidated that approval.

Self/owner approval, bots, COMMENT-only review, stale-head approval, read-only review, missing permission evidence and green CI alone do not qualify.

Platform enforcement is incomplete: the active repository ruleset must eventually require at least one approving review and the `independent-review` status check. The governance policy does not retroactively rewrite missing review history.

## Research / release non-claims

The project does **not** yet claim that:

- live heterogeneous models materially improve `P(correct | accepted)` over raw worker correctness at useful coverage;
- the gain is worth orchestration cost/latency/throughput;
- current end-to-end real Puter execution succeeds on `main@f6f9bad8...`;
- the production poisoned-guest cause is known;
- the WebVM timed-wait defect or historical corruption family has been root-caused;
- long-run WebVM failure rate is acceptable;
- release/recovery qualification is complete;
- a true blank-machine release installation has passed;
- actual host-loss recovery has passed;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been met;
- bounded self-maintenance evidence proves autonomous recursive self-improvement or merge authority.

## Next production-readiness gates

1. Obtain genuinely independent exact-head technical review for #159. If accepted, integrate without weakening the durable poison boundary, then require first-attempt production Pages and a fresh real-account iPhone/WebKit mission before claiming the public provider demo recovered.
2. Preserve #158 as exact-head **FAIL** evidence unless materially revised and fully requalified; do not waive its durable-poison regressions.
3. Retain independent post-merge technical review for exact current main / PR #156 and complete #144/#146 enforcement for future merges.
4. Obtain genuinely independent exact-head acceptance for #153; if accepted and integrated, refresh/requalify #89 while preserving its retained historical Pages failure.
5. Refresh/requalify #152. Do not promote stale-head partial/green evidence into current qualification.
6. Resolve #139 through independent protected-byte review → deliberate baseline handling → fresh qualification; only then refresh #134.
7. Quantify WebVM reliability with a predefined retained repeated-run campaign; keep #120/#126 open until evidence supports closure.
8. Complete true blank-environment release/recovery qualification without converting rehearsal/simulation into release `PASS`.
9. Freeze live-evaluation source, workload, model/configuration, evidence path, verifier policy, metrics and analysis before confirmatory outcome access.
10. Progress through elapsed 24h → 72h → 30-day soak only after shorter gates are clean.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head tests, workflow output and retained machine-readable artifacts;
3. submitted exact-head review records and open qualification/security/reliability/governance issues;
4. this current-status document;
5. `implementation-status.yaml` and its generated implementation summary for implementation-presence traceability;
6. historical specs/snapshots for design intent, not current qualification claims.

RESIDUAL's strongest research claim remains architectural until confirmatory live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.
