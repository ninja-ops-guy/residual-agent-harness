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

### Clock-path discriminator

Run **`35123030021`** on exact diagnostic head **`dc4d8d493003005de60e82a1659b12a76be9a453`** separates positive-duration sleep from zero-sleep and direct monotonic clock reads:

- `time.sleep(0.0)` × 400 — **PASS**, including calls 273–275; artifact `10457918798`, SHA-256 `7e957c58f5ae880d02245a7d658dd6f2b39921d97fd1889b2a86dd69a3c09179`;
- `time.monotonic_ns()` × 2000 — **PASS**; artifact `10457773950`, SHA-256 `2754a1a991d6bfb28cba41c588bc32cec2993ce8cf50bd5070af614c93a42a2c`;
- `time.clock_gettime_ns(CLOCK_MONOTONIC)` × 2000 — **PASS**; artifact `10457324344`, SHA-256 `bcac5ce9cec7424d1fae0dc0af507d0670a94eebe0d3b43640cda068d67c42c5`;
- floating `time.clock_gettime(CLOCK_MONOTONIC)` × 2000 — **PASS**; artifact `10457349136`, SHA-256 `454f9ebefdc9ae4aeb86142765d00248b0e800f658d78a4f56fad89386eaefc4`;
- `time.sleep(0.1)` × 320 — **FAIL at call 273** with the same `_PyTime_t` overflow; artifact `10457464261`, SHA-256 `b4487df7440931a3406d8a2351b4b5451f3e817e553ed1a0f5412cd7153f107d`.

Native i386 controls are PASS. This narrows the symptom to the positive-duration sleep/timer-wait path rather than generic monotonic clock reads.

### Process-scope discriminator

Run **`35123647606`** on exact diagnostic head **`439e4b01823e818cda0fa07bcd24b076b9e00e64`** tests whether the positive-sleep boundary is guest-global or process-local. Mission Control is required absent in every arm.

First-attempt results:

- **single-273:** one guest CPython process requests 273 × `time.sleep(0.05)` and **FAILS at call 273** with the same `_PyTime_t` overflow; artifact `10457774977`, SHA-256 `5da071e58fdfe037015c7549a76f6a69a7671d11b8770fe6b69112d7386e1a37`;
- **split-272-2:** process A completes **272/272 PASS** and exits; fresh process B completes **2/2 PASS**; classification `FRESH_PROCESS_RESETS_OR_AVOIDS_SLEEP_BOUNDARY`; artifact `10458028690`, SHA-256 `b6ff7da62f2c67ae9c2f836a991da9f964224b9020fee55006497fb518d85741`;
- **split-200-200:** process A completes **200/200 PASS** and exits; fresh process B completes **200/200 PASS**; same reset/avoidance classification; artifact `10457909703`, SHA-256 `8fc6a97c52dfcd76fee24af09019281a6b1d62612d05c79d1792dbc87e7f0549`.

The paired split/single results materially support a **process-local positive-duration sleep/timer-wait state or budget that resets or is avoided by fresh guest CPython process creation**. They rule out a guest-global accumulated positive-sleep counter that survives process replacement as a necessary explanation for this narrow symptom.

### libc-wrapper and raw-syscall discriminator — current strongest evidence

Exact diagnostic head **`3bca5a7a3d298078d246c2184684137b78422546`** moved the discriminator below Python's public sleep API while keeping Mission Control absent.

Run **`35125002000`** compared direct libc blocking calls with Python `time.sleep()` inside the same published WebVM environment:

- libc `clock_nanosleep(CLOCK_MONOTONIC, relative)` × 300 — **PASS**; artifact `10459685522`, SHA-256 `d08bd5ab79b806993c9588223fa8a70f9b091f42fe4c507e6a156744f3aa1892`;
- libc `clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME)` × 300 — **PASS**; artifact `10459850082`, SHA-256 `e40b6c6816a867cc7f69e8bade2c431c1697f895dca853d0608e87654989c4ab`;
- libc `nanosleep(relative)` × 300 — **PASS**; artifact `10458882606`, SHA-256 `0671ddc434f241eb3d32bd7dfb4fabe3726a231c22a975a75118d87dc05c26d6`;
- Python `time.sleep(0.05)` — **FAIL at call 273** with `OverflowError: timestamp too large to convert to C _PyTime_t`; artifact `10459610467`, SHA-256 `5236f39da50cc19b4aa09acef0f9413b3231d3823505f84d1339ab7be4f191b6`.

The equivalent native i386 libc/Python control job passed.

Run **`35125001828`** then probed raw i386 sleep syscall surfaces:

- legacy raw `clock_nanosleep` relative — **PASS**;
- legacy raw `clock_nanosleep` absolute — **PASS**;
- raw time64 relative — **UNSUPPORTED**, immediately returning `ENOSYS` (`errno 38`), not a call-273 failure; artifact `10458857388`, SHA-256 `c1e61a7c84662261802a1c5ab833363bf4d0d60dad3bbadba34e08c3eb372b16`;
- raw time64 absolute — **UNSUPPORTED** with the same unavailable-syscall classification; artifact `10458872292`, SHA-256 `e311994b6b9d15f2f974b740f3cb15ce2759bef281593743695f7a9bb155e7c7`;
- native i386 raw controls — **PASS**.

This materially narrows the defect: the tested direct libc sleep wrappers and legacy raw i386 `clock_nanosleep` path do not require the call-273 failure, while this WebVM guest does not expose the raw time64 syscall surface tested by the discriminator. That makes CPython/Python sleep behavior and its ABI/fallback interaction with the WebVM i386 environment a higher-value next target.

It does **not** prove that time64 unavailability causes the Python failure. Direct libc wrappers continue to work, and Python sleep succeeds 272 times before the exception. The exact CPython/glibc/emulation state transition remains **UNKNOWN**.

For the call-273 `_PyTime_t` symptom, retained evidence now rules out as necessary explanations:

- Mission Control/workbench logic;
- the persistent browser worker;
- a second guest interpreter;
- background execution specifically;
- elapsed time or cumulative requested sleep;
- generic 32-bit CPython behavior in the native control;
- zero-duration `time.sleep()` call count;
- direct monotonic clock reads;
- a guest-global positive-sleep count that survives process replacement;
- failure of the tested direct libc `clock_nanosleep`/`nanosleep` wrappers;
- unavailability of the legacy raw i386 `clock_nanosleep` surface.

The strongest supported classification is now a **WebVM-specific, process-local Python positive-duration sleep failure at call 273 that is not reproduced by the tested direct libc sleep wrappers; the raw i386 time64 syscall surface is separately unavailable (`ENOSYS`) while the legacy raw surface works**.

That remains **not root-cause proof**. Whether the unavailable time64 surface participates in a CPython/glibc fallback or accounting defect is **UNKNOWN**. The relationship to the historical `_sha512`, impossible-constructor and `munmap_chunk()` corruption family also remains **UNKNOWN**. Long-run reliability remains unresolved.

The next useful discriminator is to inspect the exact CPython/glibc sleep fallback and ABI behavior around the unavailable time64 surface, retain several sequential fresh-process reproductions, and compare another/minimal WebVM runtime build if available. Do not patch Mission Control merely to hide the symptom and do not retry failures solely to obtain green.

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

## PR #140 — browser-acceptance synchronization repair

PR #140 is a focused one-file, three-line acceptance-harness repair based directly on `main@3a41dc1e...`. It does not change production Mission Control, WebVM runtime, onboarding, provider logic, Factory/M4 controls, evidence schemas or qualification thresholds.

The retained PR #89 Pages/WebVM run `35112465799` still records a generated-artifact browser **FAIL** after the real guest worker completed the build and exposed the expected result. The Playwright trace showed the test sampling post-run navigation state before the UI's separate cleanup/unlock transition completed. PR #140 preserves the active-mission control-lock assertions and adds bounded waiting for the post-run unlock before retaining the existing idle-state assertions.

Exact head **`36c596277b04c019fb9f0c74d8108aafed0e83de`** has all eight observed applicable workflows **PASS**:

- Command Station — `35122315857`;
- clean install — `35122315999`;
- controller/provider contracts — `35122315909`;
- Browser VM Demo CI — `35122316013`;
- Control Plane — `35122315891`;
- Factory ownership — `35122315921`;
- measured-evaluation binding — `35122315912`;
- Pages/WebVM — `35122316061`.

No submitted PR review is recorded on #140. The green candidate therefore supports that the focused synchronization repair passes its exact-head qualification, but it does **not** erase #89's retained failure, qualify #89 itself, establish WebVM long-run reliability, or satisfy the required independent technical acceptance gate.

## Protected self-hosting / research-bundle milestone

PR #132 remains a bounded research milestone rather than evidence that RESIDUAL autonomously builds or merges itself.

The retained trial used one live external GPT-5.6 Sol interactive worker to author one four-file research-bundle candidate against a frozen base. The candidate reached **PR_READY** while `merge_authorized=false`, touched no protected paths and passed the retained freeze/verify/tamper acceptance sequence.

The larger 100-generation, 1,000-fault and 200-document-policy campaigns are controller/policy stress experiments, not repeated live model-authored generations or recursive autonomous self-modification evidence.

## Current implementation map

| Area | State | Qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, receipts, cache binding, trace/audit and provider routing exist. |
| Command Station | Implemented research/operations surface | Operational controls exist; deployment-specific production readiness remains separate. |
| Mission Control / WebVM | Implemented product/demo surface; **reliability gate open** | #136 merged and passed first release attempt. #133 now shows a process-local Python positive-duration `time.sleep()` failure at call 273, direct libc sleep wrappers PASS, legacy raw i386 sleep PASS, and raw time64 syscall probes UNSUPPORTED/`ENOSYS`; the causal mechanism and historical-family link remain `UNKNOWN`. |
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
- **#133** — diagnostic-only; Python positive sleep fails at call 273 in one process while fresh-process splits pass; direct libc sleep wrappers and legacy raw i386 `clock_nanosleep` pass, while raw time64 syscall probes are UNSUPPORTED with `ENOSYS`. This narrows the next investigation but does not prove the causal mechanism, which remains `UNKNOWN`.
- **#140** — exact-head synchronization-repair workflows PASS, including Pages/WebVM and Browser VM Demo CI; no submitted independent review is recorded. It does not qualify #89 or erase #89's retained failure.
- **#89** — onboarding/Inspector candidate retains Pages/WebVM **FAIL** run `35112465799`; refresh/requalification remains required after any accepted #140 integration. No browser qualification PASS is claimed for #89.
- **#118** — observed exact-head workflow set PASS; genuinely independent technical acceptance remains required.
- **#115** — observed exact-head workflow set PASS; procedure/simulation evidence is not bare-OS, actual recovery or elapsed-soak evidence; independent acceptance remains required.
- **#131** — observed exact-head workflow set PASS; local SoakState persistence is not elapsed-soak evidence; independent acceptance remains required.
- **#93** — observed exact-head workflows PASS; economics/observability outputs remain development-fixture evidence; independent acceptance remains required.

## Research non-claims

The project does **not** yet claim that:

- live heterogeneous models show materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax;
- the WebVM process-local Python sleep defect, its relationship to the unavailable raw time64 surface, or the historical corruption family has been root-caused;
- PR #132 proves autonomous recursive self-improvement or merge authority;
- PR #136 had recorded genuinely independent technical acceptance before merge;
- release/recovery qualification is complete;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been met.

## Next gates

1. Resolve #139 without weakening the ownership gate: independent review → deliberate baseline advancement if accepted → fresh protected-state qualification.
2. Refresh/requalify #134 afterward, then require independent adapter review before fresh live-provider evidence.
3. Obtain genuinely independent exact-head review for green PR #140; if accepted, integrate it and then refresh/requalify #89 while preserving the retained `35112465799` failure as historical evidence.
4. Obtain independent acceptance for green current-main candidates #118, #115, #131 and #93.
5. Continue #133 below Python `time.sleep()`: inspect CPython/glibc ABI and fallback behavior around the unavailable raw time64 syscall surface, repeat the fresh-process reset over several sequential processes, and compare alternate/minimal WebVM runtime builds while keeping causality and the historical-family relationship `UNKNOWN` until proven.
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
