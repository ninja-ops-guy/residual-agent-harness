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

Current `main` is **`160c01a1b1933ee10c82dcf30b1674a17f7560ff`** and includes merged #169 after the accepted provider-transport path through #173.

#169 adds privacy-safe local diagnostics and sanitized triage bundles without changing authoritative guest trace/`verify-trace` evidence, provider routing, mission authority or qualification semantics. Its exact final head completed qualification and received a maintainer attestation before merge.

All seven observed exact-current-main `push` workflows completed **PASS**. Pages/WebVM run `35182396521` passed on attempt 1 through provider/publication contracts, generated desktop+narrow real-browser proof, deployment, published real-guest execution, published narrow-Chromium acceptance and retained live-acceptance proof.

This is mechanism/integration/browser evidence. It is **not** a live R0–R5 result, paid/live provider/model quality evidence, long-run production-reliability evidence, independent scientific validation or a paper-facing effect size.

The earlier `main@2b7cb626...` retained Controller/provider run `35172926291` as **FAIL** in Python 3.12 on the protected M4 `/proc/<pid>/status` observation race. That exact-revision failure remains in the evidence record. A later green workflow does not erase it or establish root cause.

## Live-provider boundary

Fresh retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both separately counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary (`candidate_rejections=0`, `verification_elapsed_ms=0`). Candidate correctness and semantic verification therefore remain **UNKNOWN**.

The retained mission also shows a 1536-token provider-output limit for a browser build that required the complete generated file bundle. That observation does not establish truncation as the sole cause of the invalid protocol responses.

PR #176 proposes a bounded build-only ceiling/default of 8192 while retaining 1536 for non-build/source-grounded live mode and classifying normalized `finish_reason=length` as `provider_protocol_invalid / response_truncated`. Its current head is diverged from current main, so its existing exact-head CI and maintainer attestation are historical to that candidate. Refresh/current-main qualification is required before integration, and a new retained real-account iPhone/WebKit mission is required after any accepted merge before successful paid/live Puter execution can become `PASS`.

If a study depends on the real-provider path, do not substitute green provider-contract or Pages/browser CI for fresh exact-revision provider evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM. Merged #145 avoids the known Python timed-wait surface in long-lived browser polling; merged #169 improves local triage evidence, but the historical guest-corruption root cause and long-run recurrence rate remain **UNKNOWN**. The later poisoned-guest event is additional reliability evidence and has not been proven to share the same cause.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. define a repeated-run reliability campaign in advance;
4. preserve every first-attempt `FAIL`/`UNKNOWN` rather than rerunning it away;
5. report operational failure/missingness separately from model correctness;
6. do not describe a narrow mitigation or added telemetry as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

Issues #63/#48 are closed. M4 remains evidence- and environment-bound rather than universally qualified.

The historical `2b7cb626...` Controller/provider failure re-exposed the protected M4 `/proc` observation race. PR #139 is the isolated protected-test repair lane. If a selected evidence path depends on that repair or downstream #134, preserve the complete sequence:

1. evaluate the protected change under the applicable trust-boundary review policy;
2. make any ownership-baseline advancement deliberately, not merely to obtain green;
3. run fresh qualification after a protected pin change;
4. refresh/requalify dependent work against the new accepted revision.

Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification v1 and inference-economics candidates

PR #152 proposes a broader fail-closed qualification methodology, including source-bound evidence manifests, stateful lifecycle exploration, DSM fault evidence, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys and process/elapsed-soak tooling. Any result from an older base is historical to that exact head and does not constitute current-main qualification.

Interpretation boundaries:

- virtual-day stress is fixture stress, not elapsed wall-clock soak;
- planned 24h/72h/30d workflows are not evidence until those runs actually complete;
- a live-provider canary proves at most one bounded adapter execution/evidence path, not provider/model quality;
- the framework does not replace capable-runner M4, ownership or Pages acceptance gates.

Draft #177 is the development-only IE-001 prototype qualification candidate. The branch reports 203 focused prototype tests passing plus Q1–Q10/exact-head repository and maintainer-governance evidence, but Q11 genuinely independent current-head technical review remains pending. It is not final IE-001 qualification, production runtime evidence, a real-provider/GPU benchmark or a paper-facing result. The branch also predates current #169 main, so current-main qualification is not inherited.

Draft #178 is documentation-only follow-on implementation backlog for IE-002 through IE-007. It explicitly distinguishes prototype evidence from production qualification and makes no speedup/cost/routing/GPU/paper claim. Draft #175 remains specification-only OpenViking/context-provider planning.

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
6. independently qualify the selected evidence path to the degree required by the scientific claim;
7. retain any WebVM/provider/release qualification required by that selected path;
8. preserve negative, rejected, `UNKNOWN`, missing and failed cells in the evidence package.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Recommended qualification ladder

1. **Clean install** — installed package/import/asset/CLI checks on the exact revision.
2. **Selected backend/evidence path** — prove execution identity, anti-replay, workload mapping, evidence completeness and verifier boundary.
3. **Environment-specific runtime qualification** — WebVM/provider/cluster path only if the study uses it.
4. **Frozen R0–R5 study** — one fixed model under the preregistered schedule.
5. **Model degradation** — progressively weaker workers, unchanged acceptance policy.
6. **Heterogeneous routing** — mixed local/remote/cheap/strong workers under the same evidence boundary.
7. **Fault campaign** — worker termination, stale telemetry, network interruption, invalid receipts, verifier failure and recovery cases.
8. **24-hour soak** — only after shorter qualification is clean.
9. **72-hour soak** — only after the 24-hour run is clean.
10. **30-day soak** — long-duration operational evidence after shorter gates are stable.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- Never compare scripted-worker latency with live provider/network latency as the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer production readiness from fixture CI.
- Do not inherit qualification from a predecessor branch after `main` materially moves.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository has strong development evidence for mechanisms and exact-revision integration. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.
