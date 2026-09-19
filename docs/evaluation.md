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

Current `main` is **`e7b72ad18df5729f16d36771971c8a8828d71a10`**.

Merged #275 repairs exact-head maintainer-approval status publication. Merged #276 closes #267 by ensuring every merged-main SHA receives a non-cancelling authoritative production Pages attempt. These are accepted engineering/qualification changes, not model-quality or scientific evidence.

The first production Pages attempt for exact current main is **run `35410875305`, attempt 1, FAIL**. Generated desktop+narrow proof and deployment passed; published live guest verification failed and the subsequent published narrow acceptance was skipped. This is exact-revision production qualification evidence. It does **not** establish paid/live Puter failure, model quality, every-host M4 qualification, or a scientific effect size. The exact lower-level cause is **UNKNOWN from the currently inspected retained metadata**.

Controller/provider, Command Station and Factory ownership have retained exact-main PASS results in their named automated scopes. Those results do not override the production Pages FAIL. Historical exact-revision failures remain evidence even where later revisions pass.

## Real-model development evidence must remain mixed

Draft #202 provides a useful example of why first-attempt and revision binding matter.

An earlier heterogeneous three-task DAG run on exact head `6b30125...` remains **FAIL** with only 1/3 integrated. A later distinct exact-head run on `03c77d12...` is a bounded **PASS** with 3/3 integrated, retained receipts, dependency lineage, rejected fault injections, successful repair and release export using real local Ollama models.

Evaluation interpretation:

- earlier DAG run: **FAIL on its exact head/configuration**;
- later corrected run: **PASS on its exact head/configuration**;
- general DAG/recovery reliability: **not established**;
- production reliability: **not established**;
- live-provider quality: **not established**, because these experiments used local Ollama rather than Puter.

Do not average away or overwrite the earlier negative cell because a later experiment succeeded.

The M6 self-host sequence is similarly mixed: #203/#204/#215/#217 retain authoritative **FAIL** cells, while #220/M6-SPEC-006 retains one bounded corrected-path **PASS**. That PASS does not establish general autonomous self-maintenance.

## M6.2 discovery evaluation boundary

The autonomous-discovery series must be evaluated as a matrix of scoped outcomes rather than one aggregate success claim.

Key retained cells include:

- #244/#246: execution **FAIL** before a valid proposal;
- #249: bounded discovery **FAIL** after malformed/repeated/truncated proposals;
- #250/#251/#252/#254: deterministic admission **FAIL** for requests of already-measured evidence;
- #255: semantic-review **FAIL**;
- #257: bounded **PASS at formal MeasurementGap admission**, receipt `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`;
- #259/#262/#263: evidence-use/resolver/query **FAIL** cells;
- #264: workflow/receipt integrity succeeded, but scientific conclusion **UNKNOWN** because metric identity/semantics were ambiguous;
- #274: bounded **PASS** for registry/receipt semantic binding;
- #273/#277: provenance/Planner **FAIL** cells, with #277 retaining positive host-owned provenance evidence inside an overall failed trial.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. M6-008 remains **BLOCKED** pending its declared semantic/derivation admission gates. Unmerged derivation-graph and M7 work is research apparatus, not production capability.

## Deterministic stress evidence and governance ordering

Draft #206 Campaign A has completed its authoritative corrected exact-head runs. Workflow-level success means the scenario executed and retained artifacts; it is not a scenario-level PASS.

Its retained outcomes include:

- **STRESS-A4 — BLOCKED / invalid for repair-pressure qualification:** the intended intervention never validly executed.
- **STRESS-A5 — FAIL / incomplete:** 3/6 DAG tasks integrated before escalation, no release.
- **STRESS-A6 — FAIL in scope:** three frozen Qwen2.5-Coder 7B trials produced 0 successes.

Draft #207 Campaign B intentionally probes conditions that a stronger fail-closed claim must survive:

- **STRESS-B1 — FAIL:** final token-budget exhaustion was observed after accepted integration/release had already occurred.
- **STRESS-B2 — scoped PASS:** the early-convergence control completed without the target trips.
- **STRESS-B3 — FAIL:** terminal verifier failure aborted with 0 integrated, but a non-empty release materialized afterward.
- **STRESS-B4 — containment PASS / recovery FAIL:** injected corrupt candidates were rejected and none integrated, but the task did not recover to successful completion within the frozen pass budget.

Draft #212 Campaign C adds:

- malformed runner JSON: bounded **PASS for fail-closed containment**;
- invalid reviewer schema: bounded **PASS for fail-closed containment**;
- reviewer denial then approval: bounded **PASS for recovery**;
- transient HTTP 500: retry/failover success **UNKNOWN / not established**;
- missing usage: **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` abort.

Until a repair is accepted and these affected scenarios are requalified, do not make a stronger blanket claim that budget exhaustion, unknown usage or terminal verifier failure always prevents later accepted-state/release materialization.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling.

Do not substitute green provider-contract, browser, Pages-build or lifecycle CI for fresh exact-revision provider evidence. Likewise, the current production Pages FAIL at published guest verification is not enough to infer a provider/model-quality failure.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Bounded mitigations, diagnostics and individual green runs do not establish an acceptable long-run recurrence rate or a complete root cause.

The #186 fallback is accepted. It establishes only that the unsupported/unqualified iOS WebKit profile is routed to the lightweight walkthrough before heavyweight guest/disk boot. That result must **not** be reported as physical heavyweight-WebVM reliability.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. preserve first-attempt `FAIL`/`UNKNOWN` evidence rather than rerunning it away;
4. define a repeated-run reliability campaign in advance;
5. report operational failure/missingness separately from model correctness;
6. do not describe a safe fallback, provider-session repair, publication-boundary fix or added telemetry as proof that the broader reliability family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent. Qualification-v1 work on the separate testing branch, including #303/#312, is branch evidence only until its own governed acceptance path is completed.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance.

For release or paper claims that require independent technical/scientific validation, retain that validation separately. Repository merge permission is not a substitute for external evidence required by a claim.

Issue #305 remains open for Actions queue saturation. Queue pressure can make a required result `BLOCKED`/missing/queued, but never PASS. Open #307 is an unmerged candidate fan-out repair and does not alter current evidence until accepted.

## Live confirmatory evaluation gate

Before paper-facing R0–R5 outcome collection:

1. freeze exact source commit/tree and execution environment;
2. freeze the selected evidence/execution adapter and task mapping;
3. freeze workload hashes, model/version, inference settings and prompts;
4. freeze verifier revisions, policies and acceptance boundary;
5. freeze metrics, missingness handling, statistical tests and analysis code;
6. preserve and explicitly scope retained exact-revision failures, blocked interventions and mixed cells for the selected evidence path;
7. repair/requalify any #207/#208/#212 governance-ordering defect required by that path;
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
- Do not inherit qualification from a predecessor branch after `main` materially moves.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository has strong development evidence for mechanisms and exact-revision integration, plus useful positive and negative real-model/stress evidence. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.