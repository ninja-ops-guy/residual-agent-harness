# Evaluation and reproduction

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

RESIDUAL has two evaluation layers: the original controller benchmark/study path and the newer frozen reliability-evaluation apparatus under `residual/eval/`. Both are useful, but they answer different questions and must not be mixed into one claim.

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

The scripted benchmark remains useful for deterministic controller/evidence regression. It does not demonstrate that cloud reasoning is necessary, that real models preserve quality, or that simulated request-byte savings predict live billed cost.

Failures, abstentions and missing usage remain in denominators. Missing provider usage remains unknown rather than being reported as zero-cost evidence.

## Frozen reliability evaluation

The current research apparatus includes immutable workload definitions, repeated configuration runs, ablations, statistics/comparison reports, fault injection, evidence/report reconstruction and Factory measurement hooks.

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

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, the merge of PR #156. Its seven observed main-push qualification workflows are **PASS** for their named exact-revision scopes. The capable-runner M4 workflow passed its fail-closed capability and zero-skip gate. Pages run `35158939226` passed on attempt 1 through generated desktop+narrow proof, deployment, published real-guest execution and published narrow-Chromium acceptance.

This is useful mechanism/integration evidence. It is **not** independent approval, a live R0–R5 result, model-quality evidence, production-reliability evidence or a paper-facing effect size.

PR #156 has zero submitted reviews, so current main is **review-provisional** despite green automated evidence.

The latest retained real-account provider evidence before #156 is **FAIL** as `provider_protocol_invalid`: two real `openai/gpt-5.4-nano` calls produced zero accepted obligations and no candidate reached verification. PR #156 repairs the identified worker-envelope conformance regression, but green post-merge contract/browser CI is not a real-account provider success. Successful paid/live provider inference on exact current main remains **UNKNOWN / not yet retained**.

If a study depends on the real-provider path, collect and retain fresh exact-revision provider evidence before treating that path as qualified for the study.

## WebVM-dependent evaluation gate

Issues #120 and #126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM. Merged #145 avoids the known Python timed-wait surface in long-lived browser polling, but the historical guest-corruption root cause and long-run recurrence rate remain **UNKNOWN**.

For any confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. define a repeated-run reliability campaign in advance;
4. preserve every first-attempt `FAIL`/`UNKNOWN` rather than rerunning it away;
5. report operational failure/missingness separately from model correctness;
6. do not describe a narrow mitigation as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Current acceptance-harness gate

PR #89 retains an authoritative first-attempt narrow-browser `FAIL` caused by an observation/parser defect. PR #153 consolidates the bounded #140/#150 repairs, but its current head is based on pre-#156 main.

Therefore #153's previous exact-head workflow results remain historical evidence only. It must refresh onto current main, run its complete qualification set again, preserve any first-attempt failure, and obtain genuinely independent exact-head review before integration. After an accepted #153 merge, #89 must itself be refreshed/requalified; #153 does not qualify #89 by inheritance.

## Protected Factory/M4 evidence path

Issues #63 and #48 are closed, so the old evaluation gate that treated them as present-tense blockers is obsolete. M4 remains evidence- and environment-bound rather than universally qualified.

PR #139 is a protected-test repair lane. If a selected evidence path depends on that repair or downstream #134, require the complete sequence:

1. independent exact-head technical review;
2. deliberate ownership-baseline decision;
3. fresh qualification after any protected pin change;
4. refresh/requalification of dependent work against current main.

Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification v1 candidate

PR #152 proposes a broader fail-closed qualification methodology, including source-bound evidence manifests, stateful lifecycle exploration, DSM fault evidence, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys and process/elapsed-soak tooling.

Its current head was built before #156. Any prior green or partial workflow evidence remains bound to that exact head and does not constitute current-main qualification. Refresh/requalification is required before integration.

Important interpretation boundaries remain:

- virtual-day stress is fixture stress, not elapsed wall-clock soak;
- planned 24h/72h/30d workflows are not evidence until those runs actually complete;
- a live-provider canary proves at most one bounded adapter execution/evidence path, not provider/model quality;
- the framework does not replace existing capable-runner M4, ownership or Pages acceptance gates.

## Governance / independent-review gate

Issue #144 tracks the independent-review enforcement gap. PR #146 implements a fail-closed exact-current-head review checker, but its current head predates #156 and must refresh/requalify before integration. Platform ruleset enforcement still requires a maintainer change after #146 itself is independently accepted.

Merged #156 has no submitted review. Its automated qualification remains valid evidence but must not be labeled independent acceptance. For release/paper evidence that requires independent technical acceptance, retain that evidence explicitly.

## Live confirmatory evaluation gate

Before paper-facing R0–R5 outcome collection:

1. freeze exact source commit/tree and execution environment;
2. freeze the selected evidence/execution adapter and task mapping;
3. freeze workload hashes, model/version, inference settings and prompts;
4. freeze verifier revisions, policies and acceptance boundary;
5. freeze metrics, missingness handling, statistical tests and analysis code;
6. independently qualify the selected evidence path;
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
