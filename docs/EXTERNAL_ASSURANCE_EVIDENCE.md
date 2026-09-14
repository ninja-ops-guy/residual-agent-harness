# External Assurance Evidence

This protocol is the next evidence tier after the bundled synthetic assurance fixtures.
It is designed for **independently authored workloads** and **real heterogeneous provider engines**.

## What it establishes

A run can show, for the frozen supplied suite and configured engines/models:

- per-engine independently graded train/evaluation success;
- Verified Compute Market selection using only train evidence before evaluation decisions;
- repeated live trials with a fresh market trained independently inside each trial;
- Wilson 95% confidence intervals for market, oracle, cheapest-policy, and fixed-engine success rates;
- market success against both a cheapest-eligible-engine baseline and each fixed engine;
- market success versus an oracle that asks whether any tested engine could solve each evaluation case;
- observed latency/token usage from the normalized provider adapters;
- a content hash binding workload cases and declared provenance;
- a preregistration hash binding hypotheses, suite, engine configuration, trial count, stopping rule, budget ceiling, and runner revision before provider execution;
- an evidence-bundle hash binding the preregistration to the final report.

It does **not** establish universal model superiority, production safety, provider independence, or authorship authenticity.
`externally_authored` is an attestation supplied by the evaluator. Residual binds that assertion into the suite hash but cannot prove who authored a file.

## Suite format

```json
{
  "schema_version": "residual.external-suite.v1",
  "name": "independent-suite-name",
  "provenance": {
    "evidence_level": "externally_authored",
    "author": "independent evaluator or organization",
    "source_uri": "immutable source reference",
    "authored_at": "2026-09-13T00:00:00Z"
  },
  "cases": [
    {
      "id": "train-001",
      "split": "train",
      "capability": "text",
      "assurance": "routine",
      "required_pass_rate": 0.9,
      "prompt": "...",
      "grader": {"kind": "exact_text", "expected": "..."}
    },
    {
      "id": "eval-001",
      "split": "evaluation",
      "capability": "text",
      "assurance": "important",
      "required_pass_rate": 0.95,
      "prompt": "...",
      "grader": {"kind": "contains_all", "values": ["..."]}
    }
  ]
}
```

Supported declarative graders are `exact_text`, `contains_all`, `json_exact`, and `regex`. Arbitrary executable graders are intentionally excluded from this live evidence boundary.

Both train and evaluation splits are mandatory. Evaluation outcomes are not applied to market profiles until after each corresponding market decision has been recorded. For repeated studies, each trial creates a fresh market and trains it only on that trial's train outputs before evaluating that trial's evaluation split.

## Importing a public benchmark

For public JSONL datasets with scalar exact answers, use the deterministic adapter rather than rewriting cases by hand:

```bash
python scripts/import_external_jsonl.py \
  --input evaluator-dataset.jsonl \
  --output external-suite.json \
  --name evaluator-suite \
  --author "Independent Evaluator" \
  --source-uri "https://immutable.example/dataset" \
  --authored-at "2026-09-01T00:00:00Z" \
  --split-salt "published-before-execution" \
  --train-percent 20
```

The adapter hashes the original source file and appends that digest to `source_uri`. Split assignment is deterministic from `(case_id, split_salt)`, so the same source and salt reproduce the same train/evaluation partition. The adapter is only a format converter; external authorship remains an evaluator-supplied provenance assertion.

## Engine config

```json
{
  "schema_version": "residual.external-engines.v1",
  "engines": [
    {
      "provider": "openai",
      "model": "MODEL_NAME",
      "capabilities": ["text"],
      "locality": "cloud",
      "cost_per_task": 0.01,
      "privacy_class": 1,
      "location": "cloud"
    },
    {
      "provider": "ollama",
      "model": "LOCAL_MODEL_NAME",
      "capabilities": ["text"],
      "locality": "local",
      "cost_per_task": 0.0,
      "privacy_class": 0,
      "location": "local"
    }
  ]
}
```

Do not place credentials, bearer tokens, headers, endpoints, or secret-bearing URLs in this file. The preregistration loader rejects common secret-bearing fields. The existing `ai_providers` registry resolves credentials and endpoints from the environment. Supported provider names currently include OpenAI, Anthropic, Google, Azure OpenAI, Bedrock, Ollama, and OpenAI-compatible endpoints.

`cost_per_task` is a declared study input. Residual uses it for market policy and preregistration budget projection; it is not claimed to be provider billing truth unless the evaluator has derived it from current provider pricing.

## Preregister, verify, then run

The preferred flow freezes the study before any provider call. New preregistrations use `residual.external-preregistration.v2`; v1 manifests remain readable and represent exactly one trial.

First create a manifest. For nondeterministic cloud models, use repeated trials and ensure the frozen budget covers every engine on every case for every trial:

```bash
python scripts/external_assurance_eval.py preregister \
  --suite external-suite.json \
  --engines external-engines.json \
  --study-id residual-live-001 \
  --registered-at 2026-09-14T03:30:00-04:00 \
  --hypothesis "VCM improves evaluation success over a fixed cheapest-engine policy." \
  --primary-metric market_success_rate \
  --secondary-metric market_vs_cheapest_delta \
  --secondary-metric oracle_gap \
  --trials 10 \
  --maximum-budget-usd 250 \
  --runner-revision git:<COMMIT_SHA> \
  --output preregistration.json
```

Then verify it independently:

```bash
python scripts/external_assurance_eval.py verify \
  --manifest preregistration.json \
  --suite external-suite.json \
  --engines external-engines.json
```

Finally execute the live providers:

```bash
python scripts/external_assurance_eval.py run \
  --manifest preregistration.json \
  --suite external-suite.json \
  --engines external-engines.json \
  --output runs/external-assurance/evidence-bundle.json
```

The run aborts before provider execution if the suite or engine configuration differs from the preregistration, if the planned provider-call count violates a preregistered call ceiling, or if declared projected cost exceeds the frozen budget. The trial count comes from the manifest and cannot be changed at run time.

The resulting report includes:

- `market.success_rate` and `market.success_ci95`;
- `market.oracle_success_rate`, its confidence interval, and `oracle_gap`;
- `baselines.cheapest_eligible`, including success, confidence interval, declared evaluation cost, and market success delta;
- `baselines.fixed_engine` for each configured engine;
- per-engine repeated evaluation success rates and confidence intervals;
- one evaluation row per `(trial, case)` with the market and cheapest-policy choices/outcomes.

Fixed baselines reuse the same provider outputs gathered for the market study, so computing those comparisons does not introduce extra provider calls or different samples.

The evidence bundle includes the full preregistration payload, preregistration hash, suite hash, engine-config hash, trial count, projected declared spend, projected call count, report, and bundle hash.

The legacy `hash --suite ...` command remains available for inspecting the canonical suite hash, but a bare expected-suite hash is not the preferred live-run gate because it does not freeze engines, hypotheses, trials, stopping rules, or budget.

## Statistical interpretation

The reported 95% intervals are Wilson score intervals over evaluation attempts. They are more informative than a bare success percentage, especially for smaller sample counts, but they do not remove dependence created by repeated use of the same benchmark cases. Treat them as uncertainty over observed Bernoulli attempts, not proof that the workload is an iid sample from all possible tasks.

For stronger publication claims, preregister enough independent cases and trials, report case-level as well as attempt-level analysis, retain normalized receipts, and consider cluster/bootstrap analysis by case family when the suite contains related tasks. Do not choose the number of trials after observing intermediate results.

## Interpretation

Treat this evidence as a scoped experiment. For publication-quality claims, use an evaluator-controlled repository or immutable release for the suite, publish the preregistration before execution, record exact engine/model identifiers and pricing, retain normalized receipts, and report both effect sizes and uncertainty rather than relying on a single success percentage.

M2 swarm evidence remains separate. Until a concrete `SwarmRuntime`/`WorkerContract` implementation lands on `main`, this external runner evaluates heterogeneous engine selection with direct execution only; it does not pretend to provide live swarm evidence.
