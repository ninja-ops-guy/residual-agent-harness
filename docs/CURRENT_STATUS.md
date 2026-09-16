# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against current `main` at `f2d58e779ad589fe1d08842c9efc40ec5214a213`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted review records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The repository contains substantial implementation and qualification evidence for bounded execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

Current `main` is **technically qualified for its observed automated/browser scopes but review-provisional**. PR #151 materially advanced the Mission Control live execution surface and provider transport, and the exact merged revision passed its main-push qualification set. No submitted independent review exists for #151, and no fresh successful paid/live Puter run is retained on that revision.

The project does **not** claim that the central live-model reliability hypothesis is proven, that WebVM has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that real Puter inference is qualified on current main, that blank-machine/recovery qualification is complete, or that elapsed production soak targets have been met.

## Current main — technically qualified, review-provisional

Current `main` is **`f2d58e779ad589fe1d08842c9efc40ec5214a213`**, tree **`c62cf2a5d8c4234edcd7e53e0faa8edeb94a1571`**, the merge of PR #151.

PR #151 adds:

- an event-backed `LIVE PIPELINE` projection in Mission Control Chat;
- bounded provider-stage telemetry correlated to the pending mission/request;
- explicit non-streaming Puter inference presentation rather than invented stream activity;
- stricter `residual_submit` response transport while preserving exact raw JSON as compatibility fallback;
- exact requested-model handling without silent model substitution;
- the visible default model `openai/gpt-5.4-nano`.

The change does not modify protected Factory/M4 implementation or shared evidence schemas.

### Exact merged-main qualification

The exact #151 candidate head passed all eight observed applicable pull-request workflows. After merge, all **seven observed main-push workflows passed** on exact `main@f2d58e77...`.

Important retained evidence:

- capable-runner M4 — run **`35149837820`**: real `linux-userns-isolated-v1`, `blocked_capabilities: []`, **142 tests + 84 subtests, zero skips**;
- Pages/WebVM — run **`35149837756`**: **PASS on first attempt** for generated desktop+narrow proof plus published desktop+narrow acceptance;
- live proof artifact — **`10468668615`**, SHA-256 **`5105cdda5d63eae0b97ed5953989cf8ce1616af6a28fa103940b0e4e28be2a1f`**.

These are revision- and environment-bound `PASS` results. They do **not** establish independent technical review, every-host M4 capability, paid/live-provider quality, long-run WebVM reliability, release/recovery qualification, elapsed soak or confirmatory research claims.

GitHub records **zero submitted reviews and zero review threads** for PR #151. Current main therefore remains **review-provisional**. Green CI is not independent acceptance. Missing pre-merge independent acceptance on #136/#145/#147/#151 remains governance debt.

An external Vercel deployment status also failed because the free deployment quota was rate-limited. That external rate-limit failure is retained separately and is not converted into a repository qualification PASS or treated as evidence that GitHub Pages qualification failed.

## Live real-provider boundary

The latest retained real-account provider path remains negative. Real Puter responses previously failed closed as `provider_protocol_invalid`; no obligation or artifact was accepted.

PR #151 tightens provider transport and makes the real pipeline more observable, but its post-merge browser proof explicitly records **`cloud_inference: NOT_RUN`** and uses the SDK test double. Therefore:

- automated provider contract/browser qualification on current main: **PASS** for its tested scope;
- retained real-account provider conformance before the latest transport work: **FAIL**;
- successful paid/live Puter acceptance on exact `main@f2d58e77...`: **UNKNOWN / NOT YET RETAINED**.

PR #149 carries additional nested `updates.build = {summary, files}` guidance, but it is still based on pre-#151 `main@0580c1e5...`. Its earlier green exact-head evidence is historical to that head. It must be refreshed/requalified before it can support a current-main integration claim.

## WebVM reliability boundary

Issues **#120** and **#126** remain open.

Diagnostic PR #133 retains reproducible evidence for a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around call 273. Tested direct libc waits continue beyond that narrow boundary. Fresh process creation resets or avoids the observed symptom.

Merged #145 routes long-lived browser polling below that known Python timed-wait surface. Avoiding the trigger is not root-cause proof. The exact CPython/glibc/WebVM mechanism, relationship to earlier `_sha512`/impossible-constructor/allocator-corruption symptoms, and acceptable production recurrence rate remain **UNKNOWN**.

Keep #120/#126 open until a predefined retained repeated-run reliability campaign or a proven regression-tested root cause supports closure.

## Browser acceptance / onboarding

### PR #89 — retained authoritative failure

PR #89 retains a first-attempt narrow-browser **FAIL** from Pages run `35147627190`. Desktop passed. The terminal body shows a guest exit marker ending in `:0`, while the report parsed `:03` after whitespace normalization allowed an unrelated later digit to extend the unterminated decimal marker.

This is classified as an **acceptance-observation defect**, not evidence that the guest command failed. The failure remains authoritative; #89 is **NOT qualified**.

### PR #153 — current-main consolidated harness repair

Closed-unmerged PRs #140 and #150 carried separate repairs for:

1. post-run control-unlock synchronization; and
2. bounded terminal-proof marker parsing.

Those repairs are now consolidated on PR **#153**, built directly from current `main@f2d58e77...`.

Current exact head: **`ee3e8f5b78d7e273fbd61dd110dbebb824ed960c`**.

Scope is four acceptance-harness files only:

- `demo/vm/browser_smoke.py`;
- `demo/vm/mission_smoke.py`;
- `demo/vm/terminal_proof.py`;
- `tests/test_webvm_deployment_workflow.py`.

At this snapshot, Factory ownership and Control Plane are **PASS**. Browser VM Demo CI and Pages are **IN PROGRESS**; Command Station, controller/provider, clean install and measured binding are still **QUEUED**. No submitted independent review is recorded.

Therefore #153 is **NOT yet exact-head qualified**. Historical green results from #140/#150 do not qualify this current-main consolidation. After any accepted #153 integration, #89 must be refreshed onto the resulting main and fully requalified; #153 does not qualify #89 by itself.

## Qualification v1 — draft PR #152

Draft PR **#152** proposes a unified evidence-first qualification layer over the existing repository gates. It adds fail-closed qualification manifests/evidence envelopes, generated lifecycle exploration, RuntimeJournal state-machine testing, DSM fault-matrix binding, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys, bounded process-soak tooling and manual elapsed-soak/live-provider workflows.

Current exact head: **`2a70f38751f843d577ae0492c281262546d6cc43`**.

Observed status at this snapshot is partial:

- Browser VM Demo CI — **PASS**;
- Factory OS execution evidence — **PASS**;
- Factory ownership — **PASS**;
- Control Plane — **PASS**;
- measured-evaluation binding — **PASS**;
- Pages — **IN PROGRESS**;
- Factory runtime evidence — **IN PROGRESS**;
- Command Station, controller/provider, clean install and the new `RESIDUAL Qualification v1` workflow — **QUEUED**.

No aggregate qualification `PASS` is claimed. Virtual-day stress is not elapsed wall-clock soak; a live-provider canary would prove only one bounded adapter execution path, not model quality; 24h/72h/30d evidence does not exist until those wall-clock runs actually complete.

## Open integration candidates after #151

PRs **#118**, **#115**, **#131**, **#93** and **#149** were last refreshed/qualified against `main@0580c1e5...`, before PR #151 merged. Their retained exact-head outcomes remain valid historical evidence for those heads but are **not current-main qualification**.

- **#118** — prior exact head `a18e8f84...` had 7/7 PASS; independent acceptance remained open. It must refresh/requalify after #151 before merge.
- **#115** — prior exact head `6ebf9175...` had its applicable workflows PASS; procedure/simulation evidence still was not bare-OS, actual recovery or elapsed-soak evidence. It must refresh/requalify after #151.
- **#131** — prior exact head `818af414...` had 7/7 PASS; local SoakState persistence is not elapsed-soak evidence. It must refresh/requalify after #151.
- **#93** — prior exact head `7f5e24d9...` retained an authoritative Command Station **FAIL** in `test_readiness_polling_survives_concurrent_writer` with `AUDIT_FAILED/OperationalError`. The affected runtime-journal path is protected Factory/M4 surface. #93 remains **NOT qualified**; #151 does not change that retained blocker.
- **#149** — prior exact head `2b4c2d09...` had 8/8 PASS on the pre-#151 base but zero submitted reviews and no live-provider success. Refresh/requalification is required.

Do not merge any of these from stale exact-head evidence.

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

This documentation update changes no protected byte, ownership pin, evidence schema or qualification threshold.

### PR #134 — provider-adapter lane

PR #134 remains downstream of #139 and behind current main. Its retained first-attempt failure remains evidence. Adapter-specific tests passing in that run do not turn the full workflow into `PASS`.

Do not advance #134 until #139 completes the independent protected-byte sequence, then refresh/requalify #134 against current main before any integration or new live-provider acceptance request.

## Governance / independent review

Issue **#144** remains open.

PR **#146** is now rebuilt directly from `main@f2d58e77...` at head **`e620bb22e5023fa842063e1db7e7e9cf7f490f40`**. It codifies a fail-closed repository-side independent-current-head review check. The gate accepts only a human, non-author reviewer with write/admin permission who approved the exact current PR head and has not subsequently invalidated that approval.

Self/owner approval, bots, COMMENT-only review, stale-head approval, read-only review, missing permission evidence and green CI alone do not qualify.

Platform enforcement is still incomplete: the active repository ruleset must eventually require at least one approving review and the new `independent-review` status check. Do not merge #146 itself without genuinely independent exact-head acceptance and its ordinary qualification gates.

## Research / release non-claims

The project does **not** yet claim that:

- live heterogeneous models materially improve `P(correct | accepted)` over raw worker correctness at useful coverage;
- the gain is worth orchestration cost/latency/throughput;
- current real Puter inference succeeds on `main@f2d58e77...`;
- the WebVM timed-wait defect or historical corruption family has been root-caused;
- long-run WebVM failure rate is acceptable;
- release/recovery qualification is complete;
- a true blank-machine release installation has passed;
- actual host-loss recovery has passed;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been met;
- bounded self-maintenance evidence proves autonomous recursive self-improvement or merge authority.

## Next production-readiness gates

1. Obtain a genuinely independent post-merge technical review for exact current main / PR #151 and complete #144/#146 enforcement for future merges.
2. Run and retain a fresh paid/live Puter acceptance on exact deployed `f2d58e77...`; preserve `PASS`, `FAIL` or `UNKNOWN` rather than inferring success from SDK-test-double CI.
3. Complete #153 exact-head CI. Preserve any first-attempt failure. If fully green, require independent technical review before integration, then refresh/requalify #89.
4. Finish #152 only through its own fail-closed aggregate qualification; do not promote partial workflow success, virtual-day stress or planned elapsed-soak workflows into release evidence.
5. Refresh/requalify stale-base integration candidates #118/#115/#131/#149 against current main. Preserve #93's retained red blocker until its protected dependency is resolved.
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
