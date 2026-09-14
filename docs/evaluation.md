# Evaluation and reproduction

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

RESIDUAL now has two evaluation layers: the original controller benchmark/study path and the newer `residual/eval/` package used for frozen reliability experiments over the Factory/runtime stack. Both remain useful, but they answer different questions.

## Offline verification

```bash
python3 -m unittest discover -s tests -v
python3 -m residual demo --output runs/demo
python3 -m residual verify-trace runs/demo/trace.jsonl --result runs/demo/result.json
python3 -m residual run examples/incident/task.json --config examples/demo.toml --output runs/incident
python3 -m examples.python_api
```

HTTP contract tests exercise native Ollama/OpenAI-compatible transport behavior including framing, output caps, usage parsing, redirect refusal, malformed responses, header-confined credentials and missing usage. They do **not** establish live model quality merely because transport tests pass.

## Original scripted controller experiments

```bash
python3 -m residual benchmark --cases 8 --noise-lines 256 --output docs/benchmark-simulation.json
python3 -m scripts.scale_study
```

The scripted benchmark remains useful for deterministic controller/evidence behavior. It does not demonstrate that cloud reasoning is necessary, that real models preserve quality, or that simulated request-byte savings predict live billed cost.

| Mode | Local tools/model | Expert evidence | Purpose |
| --- | --- | --- | --- |
| `local_only` | Enabled | No expert | Establish local fixture baseline |
| `full_cloud` | Disabled | All permitted task evidence | Isolate broad expert processing |
| `cascade` | Enabled | All permitted task evidence | Simple fallback after local attempts |
| `residual_fixed` | Enabled | Failed frontier + fixed evidence capsule/pulls | Isolate residual transfer |
| `residual` | Enabled | Failed frontier + adaptive packet/pulls | Default residual design |
| `no_pull` | Enabled | Seed evidence only | Missing-evidence ablation |

Failures, abstentions and missing usage remain in denominators. Missing provider usage must remain unknown rather than being reported as zero-cost evidence.

## Frozen reliability evaluation (`residual/eval/`)

The current research path is the hash-locked evaluation package under `residual/eval/`. It includes:

- immutable `FrozenWorkload` task sets;
- repeated configuration runs;
- ablation definitions;
- statistics and comparison reports;
- fault injection;
- evidence/report reconstruction from retained observations;
- measured Factory evaluation hooks.

The central reliability experiment holds worker/model capability constant while progressively changing the surrounding acceptance architecture. The paper-facing metrics are:

- `P(X)` — raw worker/candidate correctness;
- `P(A)` — acceptance coverage;
- `P(X|A)` — accepted correctness;
- Accepted Error Rate (AER);
- accepted-system success / ASSR;
- false acceptance and false rejection;
- verifier rejection / `UNKNOWN` rates;
- throughput and latency;
- orchestration overhead and rework/conflict cost;
- monetary/token/GPU cost where directly measurable.

A system that rejects almost everything must not be described as reliable merely because accepted error is low. Reliability results must always be interpreted with acceptance coverage and efficiency.

## Live evaluation gate

Do **not** start paper-facing live R0–R5 evaluation from current `main` until the following are closed or explicitly scoped out:

1. **Issue #63 — current M4 qualification:** accepted-tree binding, filesystem/link safety, verifier-execution isolation and Git-evidence `UNKNOWN` semantics.
2. **Issue #48 — traceability reconciliation:** M2/M3/M4/EVAL are implemented in code but still shown as `not_started` in the stale generated implementation-status view.
3. **Factory OS reproducibility classification:** timing-sensitive tests have exhibited a fail-then-pass-unchanged run and need root-cause classification.

Once those gates are clean, freeze the exact commit, workload hash, model/version, inference settings, verifier revisions, policies, prompts and analysis code before collecting confirmatory data.

## Recommended qualification ladder

1. **Clean-install qualification** — build/install wheel in an isolated environment, `pip check`, import-origin checks, packaged assets, installed CLI smoke and full source verifier gate.
2. **Single live backend qualification** — run a known backend through the evaluation path and verify usage/latency/evidence completeness.
3. **Frozen R0–R5 study** — same worker/model across configurations; at least three repeats per configuration/task grouping as specified by the research protocol.
4. **Model degradation** — repeat with progressively weaker workers while preserving the same acceptance boundary.
5. **Heterogeneous routing** — test local/remote/cheap/strong engines under the same verifier policy.
6. **Fault campaign** — worker termination, stale telemetry, network interruption, cluster reassignment, invalid receipts, verifier failure and restart/recovery cases.
7. **24-hour soak** — resource growth, queue behavior, recovery, evidence completeness and state drift.
8. **72-hour soak** — only after the 24-hour run is clean.
9. **30-day soak** — long-duration operational evidence after shorter gates are stable.

## Live benchmark example

For the original benchmark CLI, edit a model configuration and supply credential environment variables. The harness does not silently fall back to a scripted model after a live-provider failure.

```bash
python3 -m residual benchmark --config config.local.toml \
  --task-suite examples/suite.json --modes cascade residual_fixed residual \
  --repeats 3 --output runs/live-benchmark.json
```

Each task/mode/repeat has its own budget. Provider prices are supplied by configuration and are not treated as timeless constants. Cost-per-success must include unsuccessful runs, and cost remains unknown when required usage/price data are incomplete.

## Interpretation rules

- Never compare scripted-worker latency with live network/model latency as if they were the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer production readiness from fixture CI.
- Preserve `FAIL`, `UNKNOWN`, rejected and abstained runs in denominators.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` can be estimated separately.
- Retain exact commit/tree identity, workload hash, model/config identifiers and raw observations for every paper-facing result.
- Negative or null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository has strong development evidence for mechanisms and controlled fixture behavior. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That is the next major scientific milestone.
