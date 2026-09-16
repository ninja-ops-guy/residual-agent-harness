# RESIDUAL current status

_Current-state check: 2026-09-16 UTC against accepted `main` at `3a41dc1e84335875537672a62340d9f8c7806417`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests, workflow output, retained machine-readable artifacts and explicit open issues remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator-facing surfaces, browser/WebVM execution, and a bounded self-maintenance/research-bundle experiment.

The repository contains substantial implementation and development evidence for the mechanisms required to test its reliability hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that WebVM reliability has an acceptable long-run recurrence rate, that the historical guest-corruption root cause is established, that release/recovery qualification is complete, that autonomous recursive self-improvement has been demonstrated, or that production soak targets have been met.

## Accepted main

Current accepted `main` is **`3a41dc1e84335875537672a62340d9f8c7806417`**, tree **`8018d6382266b225b0217baab7e345fe28185d1f`**, the merge of PR #136, **Keep Mission Control on one persistent guest Python worker**.

Important accepted milestones include:

- **PR #108 / `0430f2fa...`** — deterministic Factory sandbox-timing and termination repair.
- **PR #121 / `1a52e9a2...`** — provenance-only Factory ownership-anchor finalization.
- **PR #122 / `bc8b783d...`** — Mission Control real-provider reliability/UX hardening.
- **PR #124 / `9d88195a...`** — narrowly scoped WebVM immutable disk-chunk recovery.
- **PR #125 / `70e701d5...`** — provider completion-marker publication.
- **PR #127 / `7cf45ea8...`** — guest-shell dispatch for WebVM workbench missions.
- **PR #109 / `22a5bae5...`** — capable-runner M4 prerequisite/qualification path plus reviewed protected lifecycle CLI-process repair.
- **PR #132 / `f1e62936...`** — protected self-hosting trial, bounded self-maintenance controller and frozen research-bundle tooling.
- **PR #136 / `3a41dc1e...`** — persistent Mission Control guest worker, durable timeout poison/recovery, corruption-class fail-closed termination and related WebVM lifecycle hardening.

Issues #63 and #48 are closed. Their old present-tense blocker language is historical, not the current integration state.

## Current exact-main qualification

All seven observed push-triggered workflows for exact current `main@3a41dc1e...` completed **PASS**:

- Factory ownership gate — run `35101404885`;
- measured-evaluation acceptance binding — run `35101404928`;
- clean-install qualification — run `35101405039`;
- capable-runner M4 qualification/prerequisite workflow — run `35101404956`;
- Command Station checks — run `35101404932`;
- controller/provider contracts — run `35101404949`;
- Deploy GitHub Pages — run `35101404981`.

These results are bound to revision `3a41dc1e...` and their named environments. They do **not** prove every-host capability, long-run production reliability, elapsed soak, live-provider quality or live-model research claims.

### M4 qualification boundary

The retained post-#109 M4 qualification on revision `22a5bae54ec12987ffd7a90d881fb4533c9b4b97` is run `35036589940`: all prerequisite capability checks passed, actual `linux-userns-isolated-v1` execution passed, and the zero-skip M4 suite completed successfully with retained artifact `10423467722` (ZIP SHA-256 `18fbc15c5fb8b6dd2e1984e55a131530f38b0ea96860d1b86ccaf7d5a5812922`).

Current `main@3a41dc1e...` also passed the capable-runner M4 prerequisite/qualification workflow in run `35101404956`. PR #136 did not modify protected Factory/M4 implementation or ownership baselines. The claim remains scoped to the named qualification boundary and environment; namespace-unavailable hosts remain `BLOCKED`/`UNKNOWN`, not PASS.

## PR #136 lifecycle integration and release evidence

PR #136 merged at `3a41dc1e84335875537672a62340d9f8c7806417`. Its earlier candidate heads retained several meaningful **FAIL** results, including unsupported FIFO creation in the real WebVM guest, incompatible DataDevice control-node assumptions, stale source-contract assertions, an obsolete shutdown path that left the worker live, and an unquoted post-worker verifier invocation. Those failures remain historical evidence and are not rewritten as PASS because the repaired head later qualified.

The final PR head `09fb5dc8c60307e3424f6bedc5026ffd6cacdc17` passed all eight applicable exact-head workflows before merge, including generated desktop+narrow browser proof in run `35097645386`.

### First post-merge release attempt

The exact merged revision then received the required first post-merge public browser acceptance. Pages run **`35101404981`**, attempt **1**, completed **PASS**.

The generated-artifact job passed desktop and narrow browser proof. The deploy job then passed:

- published exact-revision WebVM/guest execution acceptance;
- narrow Chromium acceptance;
- retained live-acceptance proof.

Retained artifacts for the exact merged revision are:

- `webvm-proof-35101404981-1` — artifact **`10448920863`**, SHA-256 **`aa0cd75837464bf11fd7ddd75040288b0837c139816a1ac6c119b0ca14f979af`**;
- `webvm-live-proof-35101404981-1` — artifact **`10448708218`**, SHA-256 **`15f6a982be57c8ecb66f7de7f4ec8949ac2c3c0e3c261b37f4e96f2017b3e79c`**;
- `github-pages-35101404981-1` — artifact **`10449160205`**, SHA-256 **`98864b7669d842a64cbbcec1028b5d9227d7d2cf9ae2d7586830c84c172daf0a`**.

This clears the exact merged revision's first-attempt desktop+narrow release-proof gate. It does **not** prove an acceptable long-run WebVM failure rate, prove the historical guest/interpreter corruption root cause, establish paid/live-provider quality, complete release/recovery qualification, or create elapsed-soak evidence.

### Independent-review evidence gap

PR #136's own qualification checklist required a genuinely independent technical reviewer/account to accept the exact qualified head before merge. The retained review record contains only owner-account `COMMENTED` reviews; the final exact-head audit explicitly stated that it **did not satisfy** the independent-review gate and said not to merge on the strength of that review.

The repository nevertheless records PR #136 as merged. Treat those as two separate facts:

- the merge and post-merge exact-revision browser **PASS** are retained repository/CI evidence;
- genuinely independent technical acceptance before merge is **not recorded** in the retained review evidence.

Do not relabel the successful post-merge CI as independent review or erase the missing-review evidence.

## Mission Control / WebVM reliability boundary

Issue #120 remains open for intermittent Pages/WebVM delivery and guest-runtime failures. Issue #126 remains open/reopened after retained production evidence on earlier accepted revisions showed later fresh guest Python processes failing inside the Python standard library; PR #134 separately retained the same broad failure family as `munmap_chunk(): invalid pointer`.

The persistent-worker integration plus first-attempt post-merge browser PASS is meaningful mitigation/release evidence. The historical root cause remains **UNKNOWN**, and one qualified release attempt does not establish a long-run recurrence rate. Keep #120/#126 open until their own closure criteria are satisfied by retained evidence.

PR #133 now contains reproducible current-main diagnostic evidence for a narrower runtime symptom. In runs `35113634795` and `35120417116`, the persistent `residual.workbench.browser_worker` completed a real audit mission and later crashed at its literal `time.sleep(0.05)` polling call with `OverflowError: timestamp too large to convert to C _PyTime_t`. The subsequently missing `/tmp/residual-workbench.pid` was a secondary cleanup effect, not the primary failure. The first failure is retained in artifact `10454395171` (SHA-256 `6ab6962d7e2fe66fe7fd9e87f0937d78c86374910604eb4f4b3984be89e7abf5`); the second reproduction is retained in artifact `10456069198` (SHA-256 `02467ba1caf40f2b89a4c9d8b4683d33d5ab07aaa215346e5efc0085769db963`). Fresh CPython probes after those worker failures still passed, so these results do not establish a global persistent failure state.

A bounded shell-only discriminator on the same accepted main completed one audit mission and then watched the same worker without launching additional CPython interpreters; no worker failure reproduced in that bounded interval. Artifact `10455949153` (SHA-256 `7f42aec9cfbc3a97d39246d788c385e8addefeff40cda474a578838ebc31826d`) retains that non-reproduction. It is not a reliability PASS.

An independent long-lived sleep canary then reproduced the same overflow outside the worker code path. The initial canary run `35120990540` retained raw evidence that a separate guest CPython process running essentially only repeated `time.sleep(0.05)` failed at iteration **273** while the Mission Control worker remained alive. That run's top-level SUCCESS was **INVALID as classification evidence** because the first harness parser matched literal `PASS` text from the echoed shell command instead of the actual canary status; artifact `10456214799` (SHA-256 `66b4d63256dc13946750b9ba3d3f5dd156fb7ff1ace01d3c8e49e6852ca17f67`) retains the raw failure.

After the parser was changed to fail closed using explicit exit codes, dedicated canary run `35121196622` correctly completed **FAIL / `CANARY_FAILED_WORKER_HEALTHY`** at sleep **273** while the first audit mission passed and the Mission Control worker remained alive. Artifact `10457830730` has SHA-256 `1557f510f21414e4b5c7e2a79cd3e01c4f00331acb2ae28c440e140945e96c8c`. A second fail-closed canary job in run `35121196646` independently reproduced the same **FAIL / `CANARY_FAILED_WORKER_HEALTHY`** classification and the same iteration-273 overflow while the worker stayed alive; artifact `10458145353` has SHA-256 `ca8ed4aa2cac3053cc48d738dc83da4d5c0ab4edbec004f897ef47a3f19ab1ff`.

Mission Control was then removed entirely. Exact diagnostic head `d0983b452ed1be23fd588c8b3156cf5ff6c37ae2` ran `35121528538` against the published accepted-main WebVM with `/tmp/residual-workbench.pid` required to remain absent. A **single guest CPython process** executed 400 repetitions of `time.sleep(0.05)`:

- foreground arm: **FAIL / `FOREGROUND_SLEEP_FAILED`** at sleep **273**, artifact `10458480580`, SHA-256 `a84056fbfe474817e075d27fc9fa7814544ddd281a3963ff4c32a4a2008e9652`;
- background arm: **FAIL / `BACKGROUND_SLEEP_FAILED_WITHOUT_MISSION_WORKER`** at sleep **273**, artifact `10457326799`, SHA-256 `b5364b01eb6117b056fc14b11b52b869969c8889482e141a7ef7d764aefb0b49`.

Both arms record the same `OverflowError: timestamp too large to convert to C _PyTime_t`; Mission Control was not started and cloud inference was `NOT_RUN`.

The duration/clock discriminator narrows the symptom further. Run `35122005536` showed WebVM 10 ms and 50 ms sleeps both failing at call 273 despite very different elapsed guest time, while a 100 ms × 200 arm passed after more elapsed time. Exact diagnostic head `bbb34b00094b8e4914b25dcb6fb2c467018b07e0` then extended the matrix in run `35122494248` so every duration crossed call 273. All four WebVM arms **FAIL at call 273** with the same `_PyTime_t` overflow:

- **1 ms:** guest monotonic delta about **0.654 s**; artifact `10457693060`, SHA-256 `b486473f653a19698a2bff416a1c64c674362406c39f076b69d374f7e33ac9b8`;
- **10 ms:** artifact `10457733100`, SHA-256 `e4c26d1b0cf3b55624954b6aebeb46b9f8354962f29cddc957e3a948d2ecf249`;
- **50 ms:** artifact `10457538081`, SHA-256 `096dce402bf1e8ef52f27caad2da5942f92cb7a18b74bbb1d4619f4cebe22e74`;
- **100 ms:** guest monotonic delta about **27.79 s**; artifact `10457942374`, SHA-256 `6e8ba37f8b3217bba77d537bb43917fe5dd7ef1e9fa6d78896007ea38519ae3c`.

The equivalent native `i386/debian:bookworm-slim` CPython control in the same workflow is **PASS** for all four duration/iteration pairs, including 1 ms × 800, 10 ms × 1600, 50 ms × 400 and 100 ms × 400.

For this symptom, retained evidence therefore rules out Mission Control workbench logic, the persistent worker, coexistence with a second long-lived guest CPython interpreter, background execution specifically, a simple elapsed-time/cumulative-sleep threshold, and generic 32-bit CPython behavior in the equivalent native control as **necessary explanations**. Across a **100× sleep-duration range**, the published WebVM guest fails on **the 273rd `time.sleep()` call**, with observed guest monotonic time at failure ranging from about **0.65 s to 27.8 s**. The strongest supported classification is a **WebVM-specific call-count or call-count-correlated runtime-state boundary in the guest CPython `time.sleep()` path**.

The lower-level mechanism remains **UNKNOWN**. Current evidence does not establish which timer/syscall/runtime state is exhausted or corrupted at or before call 273, whether the defect resides in guest CPython, WebVM timer/syscall emulation or another integration layer, or whether the historical `_sha512`, impossible-constructor and `munmap_chunk()` failures share this cause. Their relationship remains **UNKNOWN**.

PR #133 should therefore continue below application-level code rather than patching Mission Control to hide the symptom. The next useful discriminator is whether call 273 is specific to `time.sleep()` or follows a shared timer/resource primitive: compare zero/near-zero sleeps and alternate waits where available, inspect resource/accounting state around calls 272–273, verify whether a fresh process resets the boundary, and compare alternate/minimal WebVM runtime builds if available. These diagnostics are not accepted-main qualification gates; first-attempt results must remain retained without retry-to-green substitution.

PR #134 is now rebuilt directly on current `main@3a41dc1e...`, but its first exact-head qualification attempt remains **FAIL** because Command Station run `35109573754` hit a `FileNotFoundError` observation race in protected `tests/test_factory_m4_safety.py` while reading `/proc/<pid>/status`. Its browser-mailbox tests passed in that failing job and the separate controller/provider lane passed; this does not convert the full workflow into PASS. PR #134 remains held behind the protected-test repair/requalification sequence before any fresh real-provider iPhone result can be treated as evidence for that adapter lane.

## Protected M4 test-race repair — PR #139

PR #139 isolates the protected one-file repair for the `/proc/<pid>/status` observation race at exact head `2d8855274ba3fe1d6af3296140d4a382680db3a7`. The test now reads the status once and treats `FileNotFoundError` as the child already being gone; otherwise the existing bounded loop still requires zombie-or-disappeared state. The timeout, loop bound and process-group assertion are unchanged.

The capable-runner M4 prerequisite/qualification workflow on that head is **PASS** (`35111486331`), but Factory ownership (`35111486366`) and dependent clean-install, controller/provider, Command Station and measured-binding workflows are **FAIL** because the ownership baseline still pins the prior protected test blob. That is intentional fail-closed trust-boundary behavior, not a reason to weaken or silently advance the pin.

Required sequence remains: genuinely independent review of exact `2d885527...` → deliberate protected ownership-baseline advancement if accepted → fresh qualification after that protected pin change → only then refresh/requalify PR #134. No ownership baseline or protected-byte claim is changed by this documentation update.

## Protected self-hosting / research-bundle milestone

PR #132 remains a meaningful research milestone, but its evidence is deliberately narrower than “RESIDUAL builds itself.”

The retained trial used exactly **one live external GPT-5.6 Sol interactive worker** to author a four-file research-bundle candidate against frozen base `22a5bae...`. RESIDUAL reconstructed the candidate and evaluated it through deterministic predicates. The final evidence records one live external-model-authored candidate, classification **PR_READY**, `merge_authorized=false`, zero protected paths touched, 6/6 visible feature tests, and hidden freeze/verify/tamper acceptance PASS including rejection of mutated frozen source.

The retained 100-generation, 1,000-fault, and 200-document-policy campaigns are controller/policy stress experiments. They are **not** repeated live model-authored generations, autonomous recursive self-modification attempts, or independent trust-domain qualification. The final protected-self-hosting workflow was run `35045986860`, with retained artifact `10427205992` and ZIP SHA-256 `09b627315255ea19f5be767634315929c5763f07d59eddbb8df3807ef6f41b31`.

Issue #35 remains open because the broader reproducibility program still includes claim-to-evidence maintenance, bibliography provenance, frozen statistical analysis choices, negative/`UNKNOWN` publication, unified manifests, artifact-derived paper tables and threats-to-validity work.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing exist. |
| Command Station | Implemented research/operations surface | Run control, provider/model management, observations, HITL hooks, evidence export and operational UI exist. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface; **long-run reliability gate open** | PR #136 is integrated and exact merged revision `3a41dc1e...` passed its first public desktop+narrow release attempt. Current-main diagnostics reproduce a WebVM-specific `_PyTime_t` overflow on the 273rd `time.sleep()` call from 1 ms through 100 ms with Mission Control absent, while the native i386 CPython control passes. #120/#126 remain open; the lower-level mechanism and historical corruption-family relationship remain `UNKNOWN`. |
| Factory M2 | Implemented | Worker contracts, bounded runtime, isolated worktrees, journaled observations and host-owned termination exist. |
| Factory M3 | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and integrity checks exist. |
| Factory M4 | Implemented; capable-runner qualified on named environments | Closed #63 implementation gaps, #108 timing repair, fail-closed prerequisite probing and zero-skip qualification path exist. Not every-host or production qualification. |
| Evaluation | Implemented development/research apparatus | Frozen workloads, repeated runs, ablations, statistics, fault injection and measured Factory hooks exist. CI binding is not live research evidence. |
| Self-maintenance / research bundles | Implemented experimental surface | PR #132 demonstrates bounded PR-ready proposal evaluation with no merge authority. One live authored candidate is evidence of one bounded trial, not recursive autonomy. |
| Cluster / distributed execution | Implemented development surface | Versioned schema, authenticated membership, heartbeats, reassignment and local-first routing exist. Distributed guarantees remain narrower than fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway and recovery mechanisms exist. Release/recovery qualification remains downstream. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O exist. |
| Research / reproducibility | Active | Controlled-evaluation framework, exact-tree evidence practice, frozen research bundles and working paper exist. Live R0–R5 and soak remain future evidence gates. |

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is the machine-readable implementation manifest and its generated summary is traceability evidence for implementation presence. It must not be read as production/research qualification.

The old documentation that described issue #63 as an open M4 closure gate is stale. Current claim discipline is: M4 implementation closure is accepted and capable-runner qualification exists; every-host, release/recovery, reliability, soak and live-model research claims remain separate.

## Open integration and release gates

Accepted `main` remains `3a41dc1e...`. Several open candidates have now been rebuilt on that exact base, but candidate qualification does not become accepted-main evidence until integration and any required post-merge gates are satisfied.

- **PR #139 — protected M4 test-race repair.** Exact head `2d885527...` has capable-runner M4 **PASS**, while ownership and dependent qualification checks **FAIL closed** because the protected-byte baseline has not been advanced. Independent exact-head review and deliberate baseline/qualification handling are mandatory before merge.
- **PR #134 — real browser provider-adapter boundary.** Current head `5006d441...` is directly based on current main but remains **BLOCKED/FAIL** on its first exact-head full-workflow attempt because of the protected test race above. Do not rerun merely to erase that retained failure; repair #139 must be accepted/integrated first, then #134 must be refreshed/requalified and independently reviewed before fresh live-provider iPhone evidence.
- **PR #133 — WebVM runtime diagnostics.** The diagnostic lane targets published `main@3a41dc1e...` and remains unmerged. No-worker foreground/background arms and the 1/10/50/100 ms duration matrix all reproduce `OverflowError: timestamp too large to convert to C _PyTime_t` on the **273rd `time.sleep()` call** with Mission Control absent; failure elapsed time spans ~0.65–27.8 s while the equivalent native i386 CPython control passes. The strongest current classification is a WebVM-specific call-count or call-count-correlated guest sleep-runtime boundary. The exact mechanism and historical corruption-family relationship remain `UNKNOWN`.
- **PR #89 — onboarding/Inspector.** Current head `2a4ce5dc...` has eight observed workflows **PASS**, including Inspector/onboarding qualification and Factory runtime evidence, but Pages/WebVM run `35112465799` is **FAIL** at generated desktop browser proof after substantial earlier stages passed. Failure artifact `10453083802` has ZIP SHA-256 `8128c1c5d7a676cc486e0e9ab6ac9af718a6cb8aca0fadca963cdb8842198988`. No Pages/browser PASS is claimed for this candidate.
- **PR #118 — runtime/DSM closure.** Current head `e0f042c6...` has all seven observed exact-head workflows **PASS**, including Pages/WebVM. Retained first-attempt failures stay in the record. Fresh genuinely independent technical acceptance remains required. Cross-process/multi-host serialization, production process wiring, host-loss behavior, release/recovery and elapsed soak remain separate non-claims.
- **PR #115 — release preparation.** Current head `f1862e15...` has all seven observed exact-head workflows **PASS**, including Release preparation procedures. Its offline recovery fixtures and two-simulated-day soak rehearsal are procedure/simulation evidence only. True bare-OS install, production HTTPS release-host, actual host-loss recovery and elapsed soak remain unproven; independent acceptance remains required.
- **PR #131 — core SoakState persistence hardening.** Current head `1c416970...` has all seven observed exact-head workflows **PASS**, including Pages/WebVM. The change hardens local resumable-state persistence only; it does not establish elapsed soak or release readiness. Independent acceptance remains required.
- **PR #93 — orchestration economics/observability.** Current head `17189262...` has all eight applicable workflows **PASS**, including Economics and observability qualification and Pages/WebVM. Its retained/generated results remain **development-fixture evidence** and do not establish live SLOs, real-model economics, production reliability, confirmatory research or release readiness. Independent acceptance remains required.

## Research status

### Supported today

- Generation authority is separated from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms.
- Accepted main has current push-level Factory ownership, measured binding, clean-install, Station, controller/provider, capable-runner M4 and Pages workflow **PASS** results.
- The integrated persistent-worker WebVM revision passed its first qualified public desktop+narrow browser release attempt on attempt 1.
- Frozen research-bundle tooling can bind manuscript metrics to exact retained artifact bytes and reproduce them without model credentials.
- One bounded external-model self-maintenance trial produced a PR-ready candidate while preserving `merge_authorized=false`.

### Not yet supported

The project does not yet claim that:

- live heterogeneous models demonstrate materially higher `P(correct | accepted)` than raw worker correctness under matched capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax;
- the WebVM guest sleep/timer fault or historical lifecycle corruption has been root-caused or shown to have an acceptable recurrence rate;
- PR #132 proves autonomous recursive self-improvement, independent trust-domain qualification or autonomous merge authority;
- PR #136 had a recorded genuinely independent technical acceptance before merge;
- release/recovery qualification is complete;
- 24-hour, 72-hour or 30-day elapsed production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Resolve the protected #139 gate without weakening it.** Obtain genuinely independent review of exact `2d885527...`; if accepted, deliberately advance the ownership baseline and requalify the resulting protected state. Do not change the pin merely to make CI green.
2. **Refresh/requalify PR #134 after the protected repair is accepted.** Require exact-head provider/mailbox tests, full CI, generated desktop+narrow browser proof and production desktop+narrow proof before any fresh real-provider iPhone run.
3. **Resolve PR #89's current Pages/WebVM FAIL.** Preserve retained artifact `10453083802`; diagnose the generated-browser failure without converting prior passed stages into overall PASS or weakening the browser gate.
4. **Obtain independent acceptance for green current-main candidates.** #118, #115, #131 and #93 have green observed exact-head workflow sets but still require genuinely independent technical acceptance before integration.
5. **Move the reproducible call-273 `_PyTime_t` investigation one layer lower.** Preserve every first-attempt worker, canary, no-worker and duration-matrix result. Test whether a fresh process resets the boundary, whether zero/near-zero or alternate waits share it, and whether WebVM exposes timer/syscall/accounting state around calls 272–273. Keep both the lower-level mechanism and the historical `_sha512`/heap-corruption relationship `UNKNOWN` until evidence establishes them.
6. **Quantify WebVM reliability.** Keep #120/#126 open, retain every failure, and run a defined repeated-run campaign; one successful first release attempt is not a long-run production failure rate.
7. **Execute release/recovery qualification.** Exercise blank-environment setup, actual recovery and retained-evidence procedures without converting rehearsal/simulation evidence into release PASS.
8. **Complete remaining reproducibility preparation.** Continue #35 work, freeze the live workload/evidence path/metrics/analysis choices before confirmatory model results, and publish negative/`UNKNOWN` outcomes.
9. **Run fixed-model R0–R5**, followed by degradation and heterogeneous-routing studies.
10. **Progress through elapsed 24h → 72h → 30-day soak** only after shorter gates are clean.
11. **Update the paper only from frozen retained artifacts.**

## Documentation authority

Use this order when determining current truth:

1. exact code at the commit being discussed;
2. tests, workflow output and retained machine-readable artifacts for that exact commit;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and generated implementation summary for traceability;
6. historical specs/snapshots for design intent, not current implementation claims.

RESIDUAL’s strongest research claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.