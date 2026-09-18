# Evaluation and reproduction

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

RESIDUAL has two evaluation layers: the original controller benchmark/study path and the frozen reliability-evaluation apparatus under `residual/eval/`. Both are useful, but they answer different questions and must not be mixed into one claim.

## Offline verification

```bash
python3 -m unittest discover -s tests -v
python3 -m residual demo --output runs/demo
python3 -m residual verify-trace runs/demo/trace.jsonl --result runs/demo/result.json
python3 -m residual run examples/incident/task.json --config examples/demo.toml --output runs/incident
```

Transport/contract tests prove the behavior they exercise. They do **not** establish live model quality merely because an adapter or browser workflow is green.

## Original scripted controller experiments

```bash
python3 -m residual benchmark --cases 8 --noise-lines 256 --output docs/benchmark-simulation.json
python3 -m scripts.scale_study
```

The scripted benchmark is useful for deterministic controller/evidence regression. It does not demonstrate that cloud reasoning is necessary, that real models preserve quality, or that simulated request-byte savings predict live billed cost.

Failures, abstentions and missing usage remain in denominators. Missing provider usage remains unknown rather than being reported as zero-cost evidence.

## Frozen reliability evaluation

The research apparatus includes immutable workload definitions, repeated configuration runs, ablations, statistics/comparison reports, fault injection, evidence/report reconstruction and Factory measurement hooks.

Paper-facing metrics include:

- `P(X)` — raw candidate correctness;
- `P(A)` — acceptance coverage;
- `P(X|A)` — accepted correctness;
- Accepted Error Rate (AER);
- accepted-system success / ASSR;
- false acceptance and false rejection;
- verifier rejection / `UNKNOWN` rates;
- throughput and latency;
- orchestration/rework/conflict overhead;
- monetary/token/GPU cost where directly measurable.

A system that rejects nearly everything must not be described as reliable merely because accepted error is low. Report acceptance coverage alongside accepted correctness.

## Current integration evidence is not confirmatory evidence

Current `main` is **`de7d9774cfd63c77ef5645ca43aa0be1a604887f`**, produced by merged #248.

Merged #200 hardens native setup. #205 restores the session-scoped private provider channel after Mission Control reload/remount. #218 applies bounded repair-context transport and the shared five-attempt ceiling. #201 accepts the guided frontend/provider UX. #233 preserves actionable repair failure tails and detects repeated failed patches. #248 adds an explicit credentialless provider-load lifecycle with monotonic generation, `requested → loading → failed|loaded` state, and negative-path proof that a load request actually occurred before an intentionally blocked network failure. These are accepted engineering behaviors, not model-quality or scientific evidence.

Exact merged `main@de7d9774...` has seven ordinary push workflows: six succeeded and **Deploy GitHub Pages run `35363306307` FAILed in published live acceptance**. The generated artifact passed desktop+narrow browser proof and deployment passed. Published desktop acceptance then passed served-artifact identity, guest readiness, real demo verification, warm reload, repository audit, artifact/revision verification, provider transport projection, conversation reload, and guided-provider prompt preservation before timing out because the embedded provider frame's `#signin` remained disabled.

The retained report records `cloud_inference: NOT_RUN`, `REAL_GUEST_WITH_TEST_DOUBLE_SDK_NOT_PAID_INFERENCE`, and `USER_GESTURE_AND_POPUP_CONTRACT_TEST_DOUBLE_NOT_REAL_PUTER_LOGIN`. The retained trace shows the fresh frame's `Load Puter` control was clickable while the frame still said no provider SDK had been loaded; the later terminal snapshot said `Bridge ready. Load Puter when you are ready` while sign-in remained disabled. This supports the focused repository/UI bootstrap-race diagnosis being repaired in open #253. It does **not** establish a Puter outage, real authentication failure, provider/model quality, or paid/live inference result.

Open #253's current exact head has its applicable technical workflows **PASS**, including Browser VM Demo CI and Pages, while the exact-head maintainer approval gate remains **FAIL / pending matching attestation**. That PR is therefore unaccepted. If merged, the resulting main SHA requires its own first production Pages attempt; the `de7d9774...` failure remains retained evidence and must not be rerun away.

Historical exact-revision failures remain in the evidence record even where later revisions pass.

## Real-model development evidence must remain mixed

Draft #202 provides a useful example of why first-attempt and revision binding matter.

An earlier heterogeneous three-task DAG run on exact head `6b30125...` remains **FAIL** with only 1/3 integrated. A later distinct exact-head run on `03c77d12...` is a bounded **PASS** with 3/3 integrated, retained receipts, dependency lineage, rejected fault injections, successful repair, and release export using real local Ollama models.

Evaluation interpretation:

- earlier DAG run: **FAIL on its exact head/configuration**;
- later corrected run: **PASS on its exact head/configuration**;
- general DAG/recovery reliability: **not established**;
- production reliability: **not established**;
- live-provider quality: **not established**, because these experiments used local Ollama rather than Puter.

Do not average away or overwrite the earlier negative cell because a later experiment succeeded.

Draft #203/#204/#215/#217 M6 self-maintenance trials remain **FAIL** in their exact scopes. Their negative evidence informed later repair changes but is not retroactively relabeled.

### M6-SPEC-006 corrected-runtime evidence

Draft #220 is the first bounded positive M6 repair-loop result on the accepted #218 runtime. Its authoritative exact-head workflow ran at `7971a05798fbc77f7be344dd15f920adf1fad03c` using local Qwen2.5-Coder 7B and retained:

- attempt 1: rejected by the frozen ImprovementSpec checks;
- attempt 2: rejected by the frozen ImprovementSpec checks;
- attempt 3: **PASS 2/2 checks**;
- independent Station review: approved;
- integration: 1/1 task;
- verification receipt: present;
- release export: present;
- run-control outcome: success after three passes.

Workflow run `35334715201` retained artifact `m6-spec-006-corrected-runtime-evidence` (`10543236401`, digest `sha256:ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61`).

Evaluation interpretation:

- exact M6-SPEC-006 trial: **PASS**;
- prior #203/#204/#215/#217 trials: **remain FAIL**;
- accepted #218 runtime mechanism: current engineering behavior, not itself a scientific effect size;
- repeated-seed/task/model repair reliability: **UNKNOWN / not established**;
- autonomous problem discovery: **not tested by this fixed-spec trial**;
- autonomous merge authority: **not granted**;
- general recursive/self-improvement claim: **not established**.

## M6.2 discovery evidence: execution, representation, and evidence grounding are distinct

The autonomous-discovery sequence must be interpreted at the layer actually exercised:

- **#244 / 007:** provider timeout before proposal — **FAIL in experiment-execution scope / discovery not reached**.
- **#246 / 007B:** smaller request, same provider timeout before proposal — **FAIL in experiment-execution scope / discovery not reached**.
- **#249 / 007C:** provider completed, but free-form proposals were malformed/repeated/truncated and exhausted the five-pass budget — **FAIL in bounded discovery qualification scope**.
- **#250 / 007D:** typed output eliminated malformed JSON, but deterministic admission rejected a MeasurementGap claiming already-measured `provider_timeout_rate` was missing — **FAIL in mechanical-admission scope**.
- **#251 / 007E:** three typed repair attempts received exact verifier feedback and repeated the same invalid already-measured-metric MeasurementGap — **FAIL in bounded typed-repair scope**.
- **#252 / 007F:** evidence-aware typed schema still produced an already-measured metric as a MeasurementGap — **FAIL in evidence-aware admission scope**.
- **#254 / 007G:** substituting general `qwen2.5:7b` for the coder model produced the same failure class with already-measured `context_bytes_non_success_mean` — **FAIL in that alternate-model cell**.

None of #250/#251/#252/#254 produced semantic review approval or an admission receipt. Their value is diagnostic: structured output can solve syntax while leaving epistemic grounding unsolved, and the deterministic checker correctly prevents an evidence-contradicted proposal from becoming accepted because it is well formed.

General autonomous improvement discovery remains **UNKNOWN / not established**. A future single PASS would also remain bounded until repeated under frozen champion/challenger evaluation.

### #231 research shipment versus #243 production candidate

#231 remains a bounded **PASS** for self-shipping the first ImprovementSpec implementation against exact prior main. Production #243 imports that generated implementation but now contains deliberate maintainer hardening for deep immutability and stable canonical identity after review found mutable nested `acceptance` state. Therefore the current #243 head **is not byte-identical to the generated #231 source**.

#243's applicable technical exact-head workflows currently pass, including Pages; the exact-head maintainer approval gate remains **FAIL / pending matching attestation**. Until accepted, production ImprovementSpec behavior remains **UNKNOWN / unaccepted**. Do not attribute the current hardened bytes solely to autonomous generation.

## Deterministic stress evidence and governance ordering

Draft #206 Campaign A completed its authoritative corrected exact-head runs against frozen baseline `699e286...`. Workflow-level `success` means the scenario executed and evidence was retained; it is not a scenario-level PASS.

Its retained outcomes include:

- **STRESS-A4 — BLOCKED / invalid for repair-pressure qualification:** 0 faults were injected; the intended intervention never executed.
- **STRESS-A5 — FAIL / incomplete:** 3/6 DAG tasks integrated before `no_runnable_tasks` escalation; downstream tasks did not complete and no release export was attempted.
- **STRESS-A6 — FAIL in scope:** three frozen Qwen2.5-Coder 7B trials produced 0 successes and accepted rate 0.0.

Draft #207 Campaign B intentionally probes conditions that a stronger fail-closed claim must survive:

- **STRESS-B1 — FAIL:** final token-budget exhaustion was observed after accepted integration/release had already occurred.
- **STRESS-B2 — scoped PASS:** the early-convergence control completed 2/2 without the budget/max-iteration trips under study.
- **STRESS-B3 — FAIL:** terminal verifier failure aborted with 0 integrated, but a non-empty release was materialized afterward.
- **STRESS-B4 — containment PASS / recovery FAIL:** injected corrupt candidates were rejected and none integrated, but the task did not recover to successful completion within the frozen pass budget.

Draft #212 Campaign C extends this with deterministic failure/recovery cases:

- malformed runner JSON: **PASS for fail-closed containment** in that exact scenario;
- invalid reviewer schema: **PASS for fail-closed containment** in that exact scenario;
- reviewer denial then approval: **PASS for the bounded recovery path**, integrating on attempt 2;
- transient HTTP 500: no integration, but retry/failover success remains **UNKNOWN / not established**;
- missing usage: **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` host abort, corroborating the #207 ordering defect family.

A workflow-level `success` for a research campaign means the experiment executed and retained its evidence. It does **not** mean each stress scenario passed.

Until a repair is accepted and the affected #207/#212 scenarios are requalified, do not make a stronger blanket claim that budget exhaustion, unknown usage, or terminal verifier failure always prevents later accepted-state/release materialization across the tested control surface.

## Frontend/provider evaluation boundary

Accepted #201 and #248 change the browser/user-experience/provider-lifecycle path, not the scientific evidence boundary. Green browser/provider contract tests prove only their declared contracts.

Exact current main's first Pages run `35363306307` is a **FAIL** in published live acceptance despite successful generated artifact proof and deployment. The failure is bound to a browser/provider bootstrap sequence; `cloud_inference` was not run. Therefore it is neither a live model-quality PASS nor a live model-quality FAIL.

The inline provider flow may use Puter's secure authorization popup; keeping RESIDUAL-side setup within Mission Control is not equivalent to successful provider inference. Likewise, command animation, guided proof, provider lifecycle state, and negative-network qualification improve or verify onboarding/control behavior but are not model-quality or reliability measurements.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

#179, #183, #189, #205, #201 and #248 repair or improve bounded build-output, provider-session, publication, reload-recovery, guided setup and provider-load behavior. None itself constitutes live semantic acceptance evidence.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling. If a study depends on the real-provider path, do not substitute green provider-contract, browser, Pages or lifecycle CI for fresh exact-revision provider evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM, but the lower-level cause and long-run recurrence rate remain unresolved.

The #186 fallback is accepted. It establishes only that the unsupported/unqualified iOS WebKit profile is routed to the lightweight walkthrough before heavyweight guest/disk boot. That result must **not** be reported as physical heavyweight-WebVM reliability.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. preserve first-attempt `FAIL`/`UNKNOWN` evidence rather than rerunning it away;
4. define a repeated-run reliability campaign in advance;
5. report operational failure/missingness separately from model correctness;
6. do not describe a safe fallback, provider-session repair, publication-boundary fix, inline provider UX, provider-lifecycle fix or added telemetry as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent. If a selected evidence path depends on those candidates, preserve the complete protected review/pin/requalification sequence. Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance.

For release or paper claims that require independent technical/scientific validation, retain that validation separately. Repository merge permission is not a substitute for external evidence required by a claim.

## Live confirmatory evaluation gate

Before paper-facing R0–R5 outcome collection:

1. freeze exact source commit/tree and execution environment;
2. freeze the selected evidence/execution adapter and task mapping;
3. freeze workload hashes, model/version, inference settings and prompts;
4. freeze verifier revisions, policies and acceptance boundary;
5. freeze metrics, missingness handling, statistical tests and analysis code;
6. preserve and explicitly scope retained exact-revision failures, blocked interventions, bounded PASS cells, and mixed discovery cells for the selected evidence path;
7. repair/requalify any #207/#212 governance-ordering defect required by that path;
8. independently qualify the selected evidence path to the degree required by the scientific claim;
9. retain any WebVM/provider/release qualification required by that selected path;
10. preserve negative, rejected, `UNKNOWN`, `BLOCKED`, missing and failed cells in the evidence package.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job, rerun or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- A research workflow may PASS because it successfully captured a scenario-level FAIL; distinguish experiment execution from hypothesis outcome.
- Never compare scripted-worker latency with live provider/network latency as the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer physical iOS reliability from browser preflight alone.
- Do not infer production readiness from fixture CI.
- Do not inherit qualification from a predecessor branch or PR head after `main` materially moves.
- A well-formed typed proposal is not evidence-grounded merely because schema validation passes.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository now has bounded positive M6 repair/self-shipping evidence alongside earlier negative M6 cells, mixed DAG/stress evidence, and a sequence of autonomous-discovery failures that increasingly isolate the problem from provider execution to representation and then evidence grounding. It still does **not** have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax, repeated evidence that M6 repair succeeds reliably across tasks/models/seeds, or a retained verifier-accepted autonomous discovery result from evidence without a supplied hypothesis. Those remain major scientific milestones.