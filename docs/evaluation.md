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

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`** and includes merged #183 on top of the accepted #179 browser build-output path.

#179 provides the bounded 8192-token browser build ceiling/default while retaining 1536 for non-build/source-grounded live mode and explicit fail-closed truncation classification. #183 adds bounded mobile provider-session lifecycle recovery without changing model-call budgets, verifier authority, Factory/M4 boundaries or evidence schemas. Its exact final head completed all observed PR workflows **PASS** and received exact-head maintainer attestation before merge.

Exact merged-main integration evidence is **mixed**, not all-green. Six of seven observed `push` workflows completed **PASS**. **Command Station checks** run `35219212073` completed **FAIL** on attempt 1 in the Python 3.11 full-unittest step; browser, Docker, Python 3.12 and Python 3.13 jobs passed. The exact failing test/cause is **UNKNOWN** from retained workflow metadata currently available. **Deploy GitHub Pages** run `35219212133` completed **PASS** on attempt 1.

This is mechanism/integration/browser evidence. It is **not** a live R0–R5 result, paid/live provider/model quality evidence, physical iPhone/WebKit reliability evidence, long-run production-reliability evidence, independent scientific validation or a paper-facing effect size. Preserve the exact-current-main Command Station failure in any qualification package; a green sibling lane or pre-merge candidate does not erase it.

The earlier `main@2b7cb626...` retained a protected M4 `/proc/<pid>/status` observation-race **FAIL**. That exact-revision failure also remains in the evidence record. Later green workflows do not establish root cause or protected repair.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both separately counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary (`candidate_rejections=0`, `verification_elapsed_ms=0`). Candidate correctness and semantic verification therefore remain **UNKNOWN**.

The historical mission used a 1536-token browser-build provider-output bound. #179 changed the bounded build path and truncation classification but did not prove truncation caused the historical failures. Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses the provider protocol boundary and proceeds through normal verifier/receipt handling.

Merged #183 addresses provider-session follow-up/reload lifecycle behavior, but accepted implementation and automated CI do not by themselves constitute post-merge physical-device provider-session `PASS`. Retain that real-device outcome separately if the evaluation depends on it.

If a study depends on the real-provider path, do not substitute green provider-contract or Pages/browser CI for fresh exact-revision provider evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM. Merged #145 avoids the known Python timed-wait surface in long-lived browser polling; merged #159 provides fresh-overlay poison recovery; merged #169 improves local triage evidence; merged #179 changes the bounded build-output path; merged #183 changes provider-session lifecycle handling. None proves the historical guest-corruption root cause or an acceptable long-run recurrence rate.

Fresh physical-device evidence from predecessor `main@250494f2...` reports desktop success while iPhone/WebKit crashes on the heavyweight WebVM path. No retained typed iPhone crash artifact is available, so the exact internal failure mechanism remains **UNKNOWN**.

Open #182 is the bounded iOS safe-mode candidate. Its current exact head has all observed technical workflows **PASS**, including dedicated WebKit preflight and Pages, but its maintainer approval gate is **FAIL/BLOCKED** and the branch predates #183. It must be refreshed/requalified, then if accepted followed by first-attempt production Pages and a physical iPhone retest before device reliability can become `PASS`.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. resolve or explicitly scope the exact-current-main Command Station `FAIL` before selecting the evidence path;
4. define a repeated-run reliability campaign in advance;
5. preserve every first-attempt `FAIL`/`UNKNOWN` rather than rerunning it away;
6. report operational failure/missingness separately from model correctness;
7. do not describe a safe fallback, provider-session repair, narrow mitigation or added telemetry as proof that the broader corruption family is fixed.

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

PR #152 proposes a broader fail-closed qualification methodology. Any result from an older base is historical to that exact head and does not constitute current-main qualification.

Interpretation boundaries:

- virtual-day stress is fixture stress, not elapsed wall-clock soak;
- planned 24h/72h/30d workflows are not evidence until those runs actually complete;
- a live-provider canary proves at most one bounded adapter execution/evidence path, not provider/model quality;
- the framework does not replace capable-runner M4, ownership or Pages acceptance gates;
- a current-main workflow `FAIL` must be represented as `FAIL`, not hidden by aggregate sibling success.

Draft #177 is the development-only IE-001 prototype qualification candidate. The branch reports 203 focused prototype tests passing plus Q1–Q10/exact-head repository and maintainer-governance evidence, but Q11 genuinely independent current-head technical review remains pending. It is not final IE-001 qualification, production runtime evidence, a real-provider/GPU benchmark or a paper-facing result. The branch predates current main, so current-main qualification is not inherited.

Draft #178 is documentation-only follow-on implementation backlog for IE-002 through IE-007 and makes no speedup/cost/routing/GPU/paper claim. Draft #175 remains specification-only OpenViking/context-provider planning.

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
6. resolve or explicitly bound the exact-current-main Command Station `FAIL` for the selected evidence path;
7. independently qualify the selected evidence path to the degree required by the scientific claim;
8. retain any WebVM/provider/release qualification required by that selected path;
9. preserve negative, rejected, `UNKNOWN`, missing and failed cells in the evidence package.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Recommended qualification ladder

1. **Clean install** — installed package/import/asset/CLI checks on the exact revision.
2. **Exact-main regression state** — preserve and explain any current exact-revision `FAIL` before promoting broader qualification.
3. **Selected backend/evidence path** — prove execution identity, anti-replay, workload mapping, evidence completeness and verifier boundary.
4. **Environment-specific runtime qualification** — WebVM/provider/cluster path only if the study uses it.
5. **Frozen R0–R5 study** — one fixed model under the preregistered schedule.
6. **Model degradation** — progressively weaker workers, unchanged acceptance policy.
7. **Heterogeneous routing** — mixed local/remote/cheap/strong workers under the same evidence boundary.
8. **Fault campaign** — worker termination, stale telemetry, network interruption, invalid receipts, verifier failure and recovery cases.
9. **24-hour soak** — only after shorter qualification is clean.
10. **72-hour soak** — only after the 24-hour run is clean.
11. **30-day soak** — long-duration operational evidence after shorter gates are stable.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- Never compare scripted-worker latency with live provider/network latency as the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer physical iOS reliability from narrow Chromium.
- Do not infer production readiness from fixture CI.
- Do not inherit qualification from a predecessor branch after `main` materially moves.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository has strong development evidence for mechanisms and exact-revision integration, plus a retained current-main regression that must remain visible. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.
