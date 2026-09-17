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

Current `main` is **`2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`**.

Recent merges include #159 fresh-overlay poisoned-guest recovery, #168 solo-maintainer governance and #153 browser terminal-proof/control-unlock acceptance repair. The final #153 candidate had its observed applicable exact-head workflows green and an exact-head maintainer attestation.

The resulting current-main push is **not fully green**. Retained current-main outcomes include:

- measured-evaluation binding — **PASS** (`35172926292`);
- Command Station — **PASS** (`35172926302`);
- Pages/WebVM — **PASS** (`35172926305`, attempt 1);
- Controller/provider contracts — **FAIL** (`35172926291`).

The Controller/provider failure is in the Python 3.12 full-suite lane on the protected M4 safety test `test_timeout_kills_process_group_not_only_parent`: `/proc/<pid>/status` disappeared between `exists()` and `read_text()`, raising `FileNotFoundError`. Python 3.11 passed; Python 3.13 was cancelled after the matrix failure. The exact main workflow remains **FAIL**. A successful sibling or later candidate must not erase that first observed main result.

This is mechanism/integration evidence. It is **not** a live R0–R5 result, provider/model quality evidence, production-reliability evidence, independent scientific validation or a paper-facing effect size.

## Live-provider boundary

A retained post-#156 iPhone/WebKit public-demo mission reached `Provider connected` but exposed `RESIDUAL_WORKER_POISONED` while Mission Control remained at `GUEST STARTING`. That mission is **FAIL** at the guest-recovery/product boundary. No valid paid/live candidate completed the normal verifier/receipt path.

#159 provides a fresh-overlay recovery path while preserving the poison fence. Its browser proof uses provider test-double coverage and a real local audit; it does not establish real-provider/model quality. The first production Pages run after #159 retained a separate narrow-browser parser failure; #153 repairs that acceptance boundary and current-main Pages is now green.

A successful paid/live Puter mission on exact current main remains **UNKNOWN / not yet established**. If a study depends on the real-provider path, collect and retain fresh exact-revision provider evidence before treating that path as qualified for the study.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM. Merged #145 avoids the known Python timed-wait surface in long-lived browser polling, but the historical guest-corruption root cause and long-run recurrence rate remain **UNKNOWN**. The later poisoned-guest event is additional reliability evidence and has not been proven to share the same cause.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. define a repeated-run reliability campaign in advance;
4. preserve every first-attempt `FAIL`/`UNKNOWN` rather than rerunning it away;
5. report operational failure/missingness separately from model correctness;
6. do not describe a narrow mitigation as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

Issues #63/#48 are closed. M4 remains evidence- and environment-bound rather than universally qualified.

Current-main ordinary CI re-exposes the protected M4 `/proc` observation race. PR #139 is the isolated protected-test repair lane. If a selected evidence path depends on that repair or downstream #134, preserve the complete sequence:

1. evaluate the protected change under the applicable trust-boundary review policy;
2. make any ownership-baseline advancement deliberately, not merely to obtain green;
3. run fresh qualification after a protected pin change;
4. refresh/requalify dependent work against the new accepted revision.

Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification v1 candidate

PR #152 proposes a broader fail-closed qualification methodology, including source-bound evidence manifests, stateful lifecycle exploration, DSM fault evidence, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys and process/elapsed-soak tooling.

Any result from an older base is historical to that exact head and does not constitute current-main qualification. Refresh/requalification is required before integration.

Interpretation boundaries:

- virtual-day stress is fixture stress, not elapsed wall-clock soak;
- planned 24h/72h/30d workflows are not evidence until those runs actually complete;
- a live-provider canary proves at most one bounded adapter execution/evidence path, not provider/model quality;
- the framework does not replace capable-runner M4, ownership or Pages acceptance gates.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance. #146's generic repository-wide independent-human gate was closed unmerged/superseded.

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
