# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against current `main` at `f6f9bad84caccf68c7ab35e5788e756d12c55fb7`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted review records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The repository contains substantial implementation and qualification evidence for bounded execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

Current `main` is **technically qualified for its observed automated/browser scopes but review-provisional**. PR #156 materially repairs the real Puter worker-envelope boundary after fresh live-account evidence exposed a protocol-conformance failure. Its exact merged revision passed the observed main-push qualification set, but no submitted independent review exists for #156 and no fresh successful paid/live Puter run is retained on the merged revision.

The project does **not** claim that the central live-model reliability hypothesis is proven, that WebVM has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that real Puter inference is qualified on current main, that blank-machine/recovery qualification is complete, or that elapsed production soak targets have been met.

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

## Live real-provider boundary

The latest retained real-account provider evidence before #156 is authoritative **FAIL** evidence:

- two actual remote calls were made to `openai/gpt-5.4-nano`;
- both returned `provider_protocol_invalid`;
- zero obligations were accepted;
- no candidate reached verification.

The failure is not erased by the repair. PR #156's post-merge provider-contract/browser/Pages qualification is **PASS for its tested automated scope**, but it is not a real-account Puter success.

Therefore:

- automated provider contract/browser qualification on current main: **PASS** for its tested scope;
- retained real-account provider conformance before #156: **FAIL**;
- successful paid/live Puter acceptance on exact `main@f6f9bad8...`: **UNKNOWN / NOT YET RETAINED**.

Do not describe the real-provider path as fixed until a fresh retained real-account build succeeds on the deployed merged revision.

Closed PR #154 and earlier #149 are superseded by #156 and are no longer active provider-integration candidates.

## WebVM reliability boundary

Issues **#120** and **#126** remain open.

Diagnostic work retains reproducible evidence for a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around call 273. Tested direct libc waits continue beyond that narrow boundary, and fresh process creation resets or avoids the observed symptom.

Merged #145 routes long-lived browser polling below that known Python timed-wait surface. Avoiding the trigger is not root-cause proof. The exact CPython/glibc/WebVM mechanism, relationship to earlier `_sha512`/impossible-constructor/allocator-corruption symptoms, and acceptable production recurrence rate remain **UNKNOWN**.

Keep #120/#126 open until a predefined retained repeated-run reliability campaign or a proven regression-tested root cause supports closure.

## Browser acceptance / onboarding

PR #89 retains an authoritative first-attempt narrow-browser **FAIL** caused by an acceptance-observation defect in terminal exit-marker parsing. That failure remains evidence and #89 is **NOT qualified**.

PR #153 consolidates the bounded #140/#150 acceptance-harness repairs and is refreshed onto exact current main at head `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`.

All **eight observed applicable workflows are PASS** on that exact head, including Browser VM Demo CI and Pages/WebVM. Those green results qualify only the focused acceptance-harness repair on that revision; they do not qualify #89, live-provider behavior, long-run WebVM reliability, blank-machine/recovery behavior, elapsed soak or research claims.

The submitted owner-account COMMENT is bound to an earlier head and explicitly does **not** count as independent acceptance. No qualifying genuinely independent approval is bound to current head `35cbf2ba...`. PR #153 is therefore **technically qualified for its tested scope but BLOCKED on independent acceptance before integration**. Only after an accepted #153 integration should #89 be refreshed and requalified; #153 does not erase #89's retained failure or qualify #89 by itself.

## Qualification v1 — PR #152

PR #152 proposes a unified evidence-first qualification layer over the existing repository gates. It adds fail-closed qualification manifests/evidence envelopes, generated lifecycle exploration, RuntimeJournal state-machine testing, DSM fault-matrix binding, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys, bounded process-soak tooling and manual elapsed-soak/live-provider workflows.

Its current head `2a70f38751f843d577ae0492c281262546d6cc43` was also built on `main@f2d58e77...`. PR #156 moved main after that head. Any earlier green or partial workflow evidence remains exact-head history and **does not qualify #152 against current main**.

No aggregate Qualification v1 `PASS` is claimed. Virtual-day stress is not elapsed wall-clock soak; a live-provider canary would prove only one bounded adapter execution path, not model quality; 24h/72h/30d evidence does not exist until those wall-clock runs actually complete.

## Other integration candidates after #156

Any candidate last qualified before `f6f9bad8...` must be refreshed/requalified before merge if current-main compatibility is part of its gate.

- **#146** — independent-current-head review enforcement, refreshed onto exact current main at head `c416d408149408ff8668a48d6e73eb1f3bf6347e`. All six observed ordinary repository workflows are **PASS** on that head. The dedicated `Independent review gate` runs its 15 policy regression tests successfully, then correctly reports **BLOCKED** and exits nonzero because no independent human `APPROVED` review from a write-authorized reviewer is bound to the current head. This is expected fail-closed behavior, not a code-qualification PASS and not a defect waiver. #146 remains BLOCKED on the exact review condition it is designed to enforce; platform ruleset enforcement remains a separate maintainer action after accepted integration.
- **#118** — runtime/DSM candidate refreshed onto current main at `ee81051220c616f8a605c948820d972177e19801`; all seven applicable workflows pass, including Pages, but zero reviews exist. Preserve earlier first-attempt failures and require genuine independent acceptance.
- **#115** — release/recovery candidate refreshed onto current main at `27e6e3b790d950ad1e8dd3603569f2eb5090ada4`; all seven applicable workflows pass, including release procedures, but zero reviews exist. Evidence remains procedure/simulation evidence, not true blank-OS, host-loss or elapsed-soak proof.
- **#131** — separate two-file SoakState persistence candidate refreshed onto current main at `0094dd4c27231f8c4f71161b9a82770a27c7aa7b`; all seven applicable workflows pass, including Pages, but zero reviews exist. This is not elapsed-soak evidence.
- **#93** — retains an authoritative runtime-journal concurrency failure/protected dependency from its tested head; it is **NOT qualified** until that blocker is resolved and the lane is rebuilt/requalified.

Do not merge any candidate from stale exact-head evidence.

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

PR #146 is refreshed onto `main@f6f9bad8...` at head `c416d408149408ff8668a48d6e73eb1f3bf6347e`. Six ordinary exact-head workflows are **PASS**. Its policy regression suite passes **15/15**, while the live `independent-review` gate is **BLOCKED** because GitHub records no qualifying independent current-head approval; the Actions job therefore concludes failure by design. This is correct fail-closed enforcement, not a `PASS` and not evidence that the review requirement may be waived.

Platform enforcement is also incomplete: the active repository ruleset must eventually require at least one approving review and the `independent-review` status check. The governance policy does not retroactively rewrite missing review history.

## Research / release non-claims

The project does **not** yet claim that:

- live heterogeneous models materially improve `P(correct | accepted)` over raw worker correctness at useful coverage;
- the gain is worth orchestration cost/latency/throughput;
- current real Puter inference succeeds on `main@f6f9bad8...`;
- the WebVM timed-wait defect or historical corruption family has been root-caused;
- long-run WebVM failure rate is acceptable;
- release/recovery qualification is complete;
- a true blank-machine release installation has passed;
- actual host-loss recovery has passed;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been met;
- bounded self-maintenance evidence proves autonomous recursive self-improvement or merge authority.

## Next production-readiness gates

1. Obtain a genuinely independent post-merge technical review for exact current main / PR #156 and complete #144/#146 enforcement for future merges. #146's ordinary exact-head workflows and policy tests pass; its live review gate remains correctly `BLOCKED` until a qualifying reviewer approves current head `c416d408...`.
2. Run and retain a fresh paid/live Puter acceptance on exact deployed `f6f9bad8...`; preserve `PASS`, `FAIL` or `UNKNOWN` rather than inferring success from automated CI.
3. Obtain genuinely independent exact-head acceptance for technically qualified PR #153 at `35cbf2ba...`; if accepted and integrated, then refresh/requalify #89 while preserving its retained historical Pages failure.
4. Refresh/requalify #152. Do not promote stale-head partial/green evidence into current qualification.
5. Refresh/requalify other stale-base candidates before merge; preserve #93's retained red blocker until its protected dependency is resolved.
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
