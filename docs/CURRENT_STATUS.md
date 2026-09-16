# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against current `main` at `0580c1e53ddb9163d2423d82c0bca846a6d68ba2`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted review records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The repository contains substantial implementation and qualification evidence for bounded execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

Current `main` is **technically qualified for its observed automated/browser scopes but review-provisional**. Several important current-main-bound candidates are now exact-head green, but no submitted independent approvals are recorded for them. Two other important lanes have retained exact-head failures that remain authoritative and must not be rerun or relabeled merely to obtain green.

The project does **not** claim that the central live-model reliability hypothesis is proven, that WebVM has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that real Puter inference is qualified on the current deployed revision, that blank-machine/recovery qualification is complete, or that elapsed production soak targets have been met.

## Current main — technically qualified, review-provisional

Current `main` is **`0580c1e53ddb9163d2423d82c0bca846a6d68ba2`**, tree **`0bfc9f70b86f58a75fa58a7a95a2e3b027886a0b`**, the merge of PR #147.

Its observed push-triggered workflow set is green. Pages run **`35138502311`** passed generated desktop+narrow browser proof, deployment, published real-guest execution and published narrow Chromium acceptance. M4 run **`35138502603`** retained real capable-runner qualification with no blocked capabilities and zero skips in that qualified scope.

Those facts are exact-revision automated/browser evidence. They do **not** establish independent technical review, every-host M4 capability, live Puter quality, long-run WebVM reliability, blank-environment release qualification, actual host-loss recovery, elapsed soak or live-model research claims.

Merged PRs #145 and #147 have no submitted independent reviews in the retained GitHub review record. Their exact-head CI/browser results remain valid evidence, but current main remains **review-provisional**, not independently accepted.

## Live real-provider boundary

The latest retained real-account provider attempt before #147 remains **FAIL** as `provider_protocol_invalid`; no obligation/artifact was accepted. That failure was correct fail-closed behavior.

PR #147 tightened Puter response transport/conformance. PR **#149** then ported one surviving nested-envelope instruction from closed-unmerged #143 onto exact current main: build output belongs at `updates.build = {summary, files}` inside the exact `updates` + `requests` worker envelope, not at top level.

PR #149 exact head **`2b4c2d094c28e984da6dfc56455acc8f8d5d0af7`** is **8/8 automated/browser workflows PASS**, including Browser VM Demo CI and Pages, with zero submitted reviews recorded.

Current claim discipline is therefore:

- automated provider contract/browser qualification: **PASS** for its tested scope on current main and #149;
- retained pre-#147 real-account provider conformance: **FAIL**;
- post-#147 / post-#149 real-account provider success: **UNKNOWN / NOT YET RETAINED**.

Do not convert SDK-test-double/browser CI into a live-provider-quality claim.

## WebVM reliability boundary

Issues **#120** and **#126** remain open.

Diagnostic PR #133 retains reproducible evidence for a WebVM-specific, process-local positive-duration CPython timed-wait failure surface around call 273. Fresh CPython processes reset or avoid the narrow boundary, while direct monotonic reads and zero-duration sleep do not reproduce it. That supports a narrow characterization of the observed timed-wait symptom, not a proven lower-level root cause and not proof that the broader historical corruption family is eliminated.

Merged #145 avoids that known positive-Python-timed-wait surface in the long-lived browser polling path. Avoidance is not long-run reliability evidence. Keep #120/#126 open until a predefined retained repeated-run campaign or a proven regression-tested root cause supports closure.

## Browser acceptance / onboarding

### PR #140 — post-run control-unlock acceptance race

PR **#140** is refreshed onto current main at exact head **`205257e7b4f83e4a282c4345f73153ad95c5214b`**.

Fresh exact-head qualification is **8/8 PASS**, including Browser VM Demo CI and Pages. The diff remains exactly one acceptance-harness file with the original three-line synchronization repair. No submitted independent review is recorded.

This proves the focused control-unlock harness repair on that exact head. It does not retroactively erase #89's retained historical failure, qualify onboarding, prove production WebVM reliability or establish live-provider quality.

### PR #89 — onboarding / Inspector

PR **#89** is refreshed onto current main at exact head **`e8d25b67707acfe57feb1c36a4e066636336ab2f`** with its expected 11-file onboarding/Inspector surface.

All non-Pages exact-head workflows passed, including the dedicated Inspector/onboarding qualification, Factory runtime evidence, Command Station and controller/provider contracts.

Pages run **`35147627190`** failed on its **first authoritative attempt** in generated desktop+narrow browser proof. Desktop passed. The retained narrow-browser terminal body shows the guest emitted:

`RESIDUAL_E2E_3d6840b33599abaa:0`

but the browser report recorded:

`RESIDUAL_E2E_3d6840b33599abaa:03`

and treated it as exit status 3. Cloud inference was `NOT_RUN`.

Retained artifact: **`webvm-proof-35147627190-1`**, artifact ID **`10467956285`**, SHA-256 **`e9e281a8f642e8dd1cb1a7e82d9dd4efb3f8d66f0804c9773b9df79f711e75c5`**.

The failure is classified as an **acceptance-observation defect**, not evidence that the guest command failed: `browser_smoke.py` removed terminal whitespace and greedily parsed an unterminated decimal exit code, so narrow rendering could concatenate a valid `:0` with an unrelated later digit into synthetic `:03`.

The failed run remains authoritative and is not rerun away. #89 is **NOT qualified**.

### PR #150 — bounded exit-marker parser repair

Focused PR **#150** was opened directly from current main to repair the exact #89 observation defect.

Exact head: **`c47a3d5a2f96cc866378b7acf9db49800107948f`**.

Scope is three files only:

- `demo/vm/browser_smoke.py`;
- new `demo/vm/terminal_proof.py`;
- `tests/test_webvm_deployment_workflow.py`.

The repair adds an explicit nonnumeric `:END` terminator, requires `prefix + digits + :END`, keeps whitespace normalization for terminal wrapping, and adds deterministic regressions proving a real exit `0` cannot absorb a later unrelated digit, wrapped markers still parse and unterminated markers fail closed.

At this status snapshot, **seven of eight observed workflows are PASS** and Pages run **`35148410760`** remains **IN PROGRESS** in the generated desktop+narrow browser proof. No submitted independent review is recorded.

Do not merge #150 until its exact-head Pages proof completes successfully and a genuine independent technical review accepts the exact current head. If #150 later lands, #89 must be refreshed onto the resulting new main and fully requalified; #150 does not qualify #89 by itself.

## Runtime / distributed-state lane — PR #118

PR **#118** is refreshed onto current main at exact head **`a18e8f84f5cbfb148e7dc6a243629a9907cce9cf`**.

Fresh exact-head qualification is **7/7 PASS**, including Pages. The refresh is zero behind current main and preserves only the intended runtime/DSM workflow, documentation, implementation, retained review artifacts and two swarm tests. No current-main WebVM/provider or protected M4 file was replaced.

No submitted independent review is recorded. #118 therefore remains blocked **only on genuine independent technical review** and must not be self-certified or merged from CI alone.

Release/recovery, production worker wiring, host-loss behavior, multi-node consensus, blank-environment qualification and elapsed 24h/72h/30-day soak remain separate unproven gates.

## Release-readiness lane — PR #115

PR **#115** is refreshed onto current main at exact head **`6ebf917516cdc855cfc5bb945b6d66415a54a217`**.

Fresh exact-head qualification is **7/7 applicable workflows PASS**, including the dedicated Release preparation procedures gate. The refresh preserves the intended 18-file release-preparation surface and is zero behind current main.

No submitted independent review is recorded.

The retained two-day rehearsal is still **simulation/procedure evidence only**. It does not establish elapsed soak, a true blank-machine install, production HTTPS release-host success, live Station/provider execution, actual host-loss recovery or production reliability.

## Core soak-state lane — PR #131

PR **#131** is refreshed onto current main at exact head **`818af4142792356884fb53b3b80a86129b3dbda2`**.

Fresh exact-head qualification is **7/7 PASS**, including Pages. The current-main diff remains exactly the two-file SoakState atomic-persistence hardening surface:

- `residual/soak/state.py`;
- `tests/test_soak_state.py`.

No submitted independent review is recorded. The change hardens local resumable state persistence; it is **not elapsed-soak evidence** and remains separate from #115.

## Observability / economics lane — PR #93

PR **#93** is refreshed onto current main at exact head **`7f5e24d958d03b990a8885be5906b82a4f4c2455`**. The refresh is zero behind current main and preserves the original 47-file observability/economics lane diff.

Exact-head PASS scopes include Factory ownership, measured-evaluation binding, clean install, Control Plane, controller/provider contracts, the dedicated Economics and observability qualification, and Pages.

However, Command Station run **`35147825425`** is authoritatively **FAIL**. Python 3.11 job **`104968277918`** failed `test_readiness_polling_survives_concurrent_writer` with runtime status `AUDIT_FAILED`, reason `OperationalError`; Python 3.12 and 3.13 passed the same suite.

The failing test exists specifically to prove that readiness polling cannot destabilize runtime writes. This is therefore treated as a repository-level runtime-journal concurrency defect/nondeterminism, not an ordinary namespace skip and not an observability-fixture result to waive.

`residual/factory/runtime_journal.py` is part of the protected Factory/M4 ownership surface. The #93 lane stopped at that dependency rather than modifying protected runtime bytes, tests, schemas or ownership pins for green CI.

#93 is **NOT exact-head qualified** and must not merge. Its retained observability/economics results remain development-fixture evidence only, not live-model SLO, production-reliability or research evidence.

PRs #93 and #118 both touch `tests/swarm`; if either eventually integrates first, the other must be refreshed and requalified against the resulting new main before later integration.

## Factory / M4 protected boundary

M2/M3/M4 are implemented. Current M4 claims remain environment-bound: capable-runner qualification is not every-host qualification, and namespace/capability-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not `PASS`.

### PR #139 — protected test repair

PR #139 head **`2d8855274ba3fe1d6af3296140d4a382680db3a7`** changes protected `tests/test_factory_m4_safety.py` to close a `/proc/<pid>/status` observation race without weakening the termination property.

Ownership/dependent gates correctly fail closed while the baseline still pins the prior protected test blob. A same-author/owner COMMENT is not independent acceptance.

Required sequence:

1. genuinely independent review of the exact protected head;
2. deliberate ownership-baseline decision if accepted;
3. fresh qualification after any protected pin change;
4. only then refresh/requalify downstream #134 against the resulting current main.

No protected byte, ownership pin, evidence schema or qualification threshold is weakened by this status work.

## Provider-adapter lane — PR #134

PR #134 remains held on the protected #139 dependency and is behind current main. Its retained first-attempt Command Station failure remains evidence; adapter-specific tests passing in that run do not convert the full workflow into `PASS`.

Do not advance #134 until #139 completes the independent protected-byte sequence. If #139 is accepted, #134 still requires current-main refresh and exact-head requalification before integration or a new real-provider test request.

## Governance / independent review

Issue **#144** remains open.

PR **#146** implements a repository-side independent-current-head review gate, but it is not integration-ready on its current head. Its own policy correctly rejects self-review, bot review, stale-head approval, COMMENT-only review, missing review evidence and green CI alone.

No current critical lane should use the repository owner's own review as a substitute for genuine independent acceptance.

Current technically green but review-blocked candidates include **#118, #115, #131, #140 and #149**. #150 may join that set only if its still-running Pages workflow completes successfully on the exact current head.

## Research / release non-claims

The project does **not** yet claim that:

- live heterogeneous models show materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- acceptance coverage remains useful while achieving that gain;
- the gain is worth orchestration cost/latency/throughput;
- current real Puter inference succeeds after #147 or #149;
- the WebVM timed-wait defect or historical corruption family has been root-caused;
- long-run WebVM failure rate is acceptable;
- release/recovery qualification is complete;
- a true blank-machine release installation has passed;
- actual host-loss recovery has passed;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been met;
- bounded self-maintenance evidence proves autonomous recursive self-improvement or merge authority.

## Next production-readiness gates

1. Complete #150's exact-head Pages/browser proof. Preserve any first-attempt failure if one occurs. If the exact head becomes fully green, obtain independent technical review before integration.
2. After any #150 integration, refresh #89 onto the new main and fully requalify onboarding/Inspector; do not inherit #150's result as #89 evidence.
3. Obtain genuine independent exact-head acceptance for technically green #118, #115, #131, #140 and #149. Recheck live main immediately before any merge and requalify a candidate if main moved materially.
4. Resolve #93's protected runtime-journal dependency through the protected M4 ownership/review process rather than editing protected runtime or tests inside #93.
5. Resolve #139 through independent protected-byte review → deliberate baseline handling → fresh qualification; only then refresh #134.
6. Complete #144/#146 platform enforcement so future merges cannot bypass the independent-review rule.
7. Quantify WebVM reliability with a predefined retained repeated-run campaign; keep #120/#126 open until evidence supports closure.
8. Complete true blank-environment release/recovery qualification without converting rehearsal/simulation evidence into release `PASS`.
9. Freeze the live evaluation workload, evidence path, model/configuration, verifier policy, metrics and analysis before confirmatory outcome access.
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
