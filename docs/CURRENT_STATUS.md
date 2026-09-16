# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against accepted `main` at `3a41dc1e84335875537672a62340d9f8c7806417`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests, workflow output, retained machine-readable artifacts and explicit open issues remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform includes requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution, and bounded self-maintenance/research-bundle experiments.

The repository contains substantial implementation and qualification evidence for its mechanisms. It does **not** yet claim that the central reliability hypothesis is proven on live heterogeneous models, that WebVM reliability has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that release/recovery qualification is complete, that autonomous recursive self-improvement has been demonstrated, or that production soak targets have been met.

## Accepted main

Accepted `main` is **`3a41dc1e84335875537672a62340d9f8c7806417`**, tree **`8018d6382266b225b0217baab7e345fe28185d1f`**, the merge of PR #136.

Important accepted milestones include:

- **#108 / `0430f2fa...`** — deterministic Factory sandbox-timing and termination repair.
- **#121 / `1a52e9a2...`** — provenance-only Factory ownership-anchor finalization.
- **#122 / `bc8b783d...`** — Mission Control real-provider reliability/UX hardening.
- **#124 / `9d88195a...`** — narrowly scoped WebVM immutable disk-chunk recovery.
- **#125 / `70e701d5...`** — provider completion-marker publication.
- **#127 / `7cf45ea8...`** — guest-shell dispatch for WebVM workbench missions.
- **#109 / `22a5bae5...`** — capable-runner M4 prerequisite/qualification path plus reviewed protected lifecycle CLI-process repair.
- **#132 / `f1e62936...`** — protected self-hosting trial, bounded self-maintenance controller and frozen research-bundle tooling.
- **#136 / `3a41dc1e...`** — persistent Mission Control guest worker, durable timeout poison/recovery and corruption-class fail-closed lifecycle handling.

Issues #63 and #48 are closed. Their former blocker language is historical rather than current.

## Exact-main qualification

All seven observed push-triggered workflows for exact current `main@3a41dc1e...` completed **PASS**:

- Factory ownership — `35101404885`;
- measured-evaluation binding — `35101404928`;
- clean install — `35101405039`;
- capable-runner M4 qualification — `35101404956`;
- Command Station — `35101404932`;
- controller/provider contracts — `35101404949`;
- Pages/WebVM — `35101404981`.

These results are revision- and environment-bound. They do **not** establish every-host capability, long-run WebVM reliability, release/recovery qualification, elapsed soak, live-provider quality or live-model research claims.

### M4 boundary

Accepted-main capable-runner M4 qualification remains a **PASS** on the named environment. Namespace-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not PASS. PR #136 did not modify protected Factory/M4 implementation or ownership baselines.

## PR #136 release evidence and review gap

The final #136 candidate passed all applicable exact-head workflows before merge. Exact merged revision `3a41dc1e...` then passed its first public desktop+narrow Pages/WebVM acceptance on **attempt 1** in run `35101404981`.

That is meaningful exact-revision release evidence, but it does **not** establish a long-run recurrence rate, paid/live-provider quality, blank-environment release qualification, host-loss recovery or elapsed soak.

The retained #136 review record also does not contain a genuinely independent pre-merge technical acceptance satisfying the PR's own stated review gate. Successful CI is not retroactive independent review. Keep that evidence gap explicit.

## WebVM reliability boundary

Issues #120 and #126 remain open. Earlier accepted revisions retained standard-library and guest-runtime corruption symptoms, including `_sha512` failure; PR #134 separately retained `munmap_chunk(): invalid pointer`. Their common root cause remains **UNKNOWN**.

PR #133 is diagnostic-only and remains unmerged. It exercises the already-published accepted `main@3a41dc1e...`; it does not promote diagnostic branch code into production evidence.

### From worker symptom to guest-runtime reproduction

Current-main diagnostics first showed the persistent `residual.workbench.browser_worker` completing a real audit mission and later failing at literal `time.sleep(0.05)` with:

`OverflowError: timestamp too large to convert to C _PyTime_t`

The later missing worker PID was a secondary cleanup effect. Runs `35113634795` and `35120417116` retain those worker failures.

A shell-only bounded worker watch did not reproduce the failure, but an independent long-lived guest CPython canary then reproduced the same `_PyTime_t` overflow at sleep **273** while the Mission Control worker stayed healthy. The first canary harness falsely labeled raw failure evidence green because it parsed echoed literal text; that workflow-level PASS is **INVALID as classification evidence**. Repaired fail-closed canaries independently produced **FAIL / `CANARY_FAILED_WORKER_HEALTHY`** at sleep 273.

Mission Control was then removed entirely. No-worker foreground and background single-CPython arms both failed at sleep **273** with the same exception. That rules out Mission Control, the persistent worker, a second guest interpreter and background execution as necessary conditions for this narrow symptom.

### Duration discriminator

Run `35122494248` showed positive-duration WebVM sleeps failing on the same call count across a **100× duration range**:

- 1 ms — **FAIL at call 273**;
- 10 ms — **FAIL at call 273**;
- 50 ms — **FAIL at call 273**;
- 100 ms — **FAIL at call 273**.

Observed guest monotonic time at failure ranged from about **0.65 s to 27.8 s**. The equivalent native 32-bit Linux CPython control passed all tested duration/iteration pairs. This rules out a simple elapsed-time/cumulative-requested-sleep threshold and weakens a generic 32-bit CPython explanation.

### Clock-path discriminator — current strongest evidence

Run **`35123030021`** on exact diagnostic head **`dc4d8d493003005de60e82a1659b12a76be9a453`** separates positive-duration sleep from zero-sleep and direct monotonic clock reads:

- `time.sleep(0.0)` × 400 — **PASS**, including calls 273–275; artifact `10457918798`, SHA-256 `7e957c58f5ae880d02245a7d658dd6f2b39921d97fd1889b2a86dd69a3c09179`;
- `time.monotonic_ns()` × 2000 — **PASS**; artifact `10457773950`, SHA-256 `2754a1a991d6bfb28cba41c588bc32cec2993ce8cf50bd5070af614c93a42a2c`;
- `time.clock_gettime_ns(CLOCK_MONOTONIC)` × 2000 — **PASS**; artifact `10457324344`, SHA-256 `bcac5ce9cec7424d1fae0dc0af507d0670a94eebe0d3b43640cda068d67c42c5`;
- floating `time.clock_gettime(CLOCK_MONOTONIC)` × 2000 — **PASS**; artifact `10457349136`, SHA-256 `454f9ebefdc9ae4aeb86142765d00248b0e800f658d78a4f56fad89386eaefc4`;
- `time.sleep(0.1)` × 320 — **FAIL at call 273** with the same `_PyTime_t` overflow; artifact `10457464261`, SHA-256 `b4487df7440931a3406d8a2351b4b5451f3e817e553ed1a0f5412cd7153f107d`.

Native i386 controls are PASS.

For this narrow symptom, retained evidence therefore rules out as necessary explanations:

- Mission Control/workbench logic;
- the persistent browser worker;
- a second guest interpreter;
- background execution specifically;
- elapsed time or cumulative requested sleep;
- generic 32-bit CPython behavior in the native control;
- zero-duration `time.sleep()` call count;
- direct monotonic clock reads, including nanosecond-returning clock paths.

The strongest supported classification is now a **WebVM-specific positive-duration `time.sleep()` / timer-wait path defect with a deterministic call-273 boundary under the published guest environment**.

That is still **not root-cause proof**. The underlying timer/wait resource, emulation mechanism or accounting state responsible for the 273 boundary remains **UNKNOWN**. The relationship to the historical `_sha512`, impossible-constructor and `munmap_chunk()` corruption family also remains **UNKNOWN**. Long-run reliability remains unresolved.

The next useful discriminator is below the Python application layer: determine whether fresh sequential processes independently reset the ~272-successful-positive-sleep budget, compare positive sleep with alternate blocking/wait primitives, inspect any exposed timer/resource state around calls 272–273, and compare another/minimal WebVM runtime build if available. Do not patch Mission Control merely to hide the symptom and do not retry failures solely to obtain green.

## Protected M4 test-race repair — PR #139

PR #139 isolates the protected `/proc/<pid>/status` observation-race repair at exact head `2d8855274ba3fe1d6af3296140d4a382680db3a7`.

- capable-runner M4 qualification: **PASS** (`35111486331`);
- Factory ownership and dependent qualification workflows: **FAIL closed** because the ownership baseline still pins the prior protected test blob.

This is intentional trust-boundary behavior. Required sequence remains:

1. genuinely independent review of exact `2d885527...`;
2. deliberate ownership-baseline advancement only if accepted;
3. fresh qualification after that protected pin change;
4. only then refresh/requalify PR #134.

This documentation branch does not modify the pin, protected bytes, Factory/M4 implementation or evidence schemas.

## PR #134 — provider-adapter boundary

PR #134 is rebuilt directly on current main, but its first exact-head qualification attempt remains **FAIL** because Command Station run `35109573754` hit the protected `/proc/<pid>/status` observation race. Its browser-mailbox tests and separate controller/provider lane passing does not convert the full workflow into PASS.

PR #134 remains held behind #139 acceptance/integration, refresh/requalification, independent adapter review and then fresh real-provider iPhone evidence.

## Protected self-hosting / research-bundle milestone

PR #132 remains a bounded research milestone rather than evidence that RESIDUAL autonomously builds or merges itself.

The retained trial used one live external GPT-5.6 Sol interactive worker to author one four-file research-bundle candidate against a frozen base. The candidate reached **PR_READY** while `merge_authorized=false`, touched no protected paths and passed the retained freeze/verify/tamper acceptance sequence.

The larger 100-generation, 1,000-fault and 200-document-policy campaigns are controller/policy stress experiments, not repeated live model-authored generations or recursive autonomous self-modification evidence.

## Current implementation map

| Area | State | Qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, receipts, cache binding, trace/audit and provider routing exist. |
| Command Station | Implemented research/operations surface | Operational controls exist; deployment-specific production readiness remains separate. |
| Mission Control / WebVM | Implemented product/demo surface; **reliability gate open** | #136 merged and passed first release attempt. #133 now isolates a deterministic positive-duration guest `time.sleep()` failure at call 273; lower mechanism and historical-family link remain `UNKNOWN`. |
| Factory M2 | Implemented | Worker contracts, bounded runtime, isolated worktrees, journaled observations and host-owned termination exist. |
| Factory M3 | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and integrity checks exist. |
| Factory M4 | Implemented; capable-runner qualified | Not every-host or production qualification. Protected #139 review/baseline sequence remains open. |
| Evaluation | Implemented development/research apparatus | CI binding is not live-model empirical evidence. |
| Self-maintenance | Experimental | #132 is bounded PR-ready proposal evidence with no merge authority. |
| Cluster/distributed | Implemented development surface | Production distributed guarantees remain narrower than fixtures. |
| Lifecycle/gateway | Implemented | Release/recovery qualification remains downstream. |
| Research/reproducibility | Active | Live R0–R5 and elapsed soak remain future evidence gates. |

## Open integration/release gates

- **#139** — capable-runner M4 PASS; ownership/dependent gates intentionally FAIL closed pending independent protected-byte review and deliberate baseline handling.
- **#134** — held behind #139, then refresh/requalification and independent provider-adapter review.
- **#133** — diagnostic-only; positive-duration sleep fails at call 273 while zero-sleep and direct monotonic reads pass. Lower timer/wait mechanism remains `UNKNOWN`.
- **#89** — onboarding/Inspector candidate has a retained Pages/WebVM **FAIL** in run `35112465799`; no browser PASS claim.
- **#118** — observed exact-head workflow set PASS; genuinely independent technical acceptance remains required.
- **#115** — observed exact-head workflow set PASS; procedure/simulation evidence is not bare-OS, actual recovery or elapsed-soak evidence; independent acceptance remains required.
- **#131** — observed exact-head workflow set PASS; local SoakState persistence is not elapsed-soak evidence; independent acceptance remains required.
- **#93** — observed exact-head workflows PASS; economics/observability outputs remain development-fixture evidence; independent acceptance remains required.

## Research non-claims

The project does **not** yet claim that:

- live heterogeneous models show materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax;
- the WebVM positive-sleep/timer-wait defect or historical corruption family has been root-caused;
- PR #132 proves autonomous recursive self-improvement or merge authority;
- PR #136 had recorded genuinely independent technical acceptance before merge;
- release/recovery qualification is complete;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been met.

## Next gates

1. Resolve #139 without weakening the ownership gate: independent review → deliberate baseline advancement if accepted → fresh protected-state qualification.
2. Refresh/requalify #134 afterward, then require independent adapter review before fresh live-provider evidence.
3. Resolve #89's retained Pages/WebVM FAIL without weakening the browser gate.
4. Obtain independent acceptance for green current-main candidates #118, #115, #131 and #93.
5. Continue #133 below Mission Control: discriminate fresh-process reset, alternate wait primitives and timer/resource state around positive sleep calls 272–273 while keeping deeper cause `UNKNOWN` until proven.
6. Quantify WebVM reliability with a defined retained repeated-run campaign; keep #120/#126 open.
7. Execute true release/recovery qualification without converting rehearsal/simulation evidence into release PASS.
8. Freeze live-evaluation workload, evidence path, metrics and analysis choices before confirmatory model results.
9. Run fixed-model R0–R5, degradation and heterogeneous-routing studies.
10. Progress through elapsed 24h → 72h → 30-day soak only after shorter gates are clean.
11. Update the paper from frozen retained artifacts only.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. tests, workflow output and retained machine-readable artifacts for that exact revision;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and generated implementation summary for implementation traceability;
6. historical specs/snapshots for design intent, not current implementation claims.

RESIDUAL's strongest research claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.