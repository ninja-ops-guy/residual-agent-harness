# External Assurance Evidence

This protocol is the next evidence tier after the bundled synthetic assurance fixtures.
It is designed for **independently authored workloads** and **real heterogeneous provider engines**.

## What it establishes

A run can show, for the frozen supplied suite and configured engines/models:

- per-engine independently graded train/evaluation success;
- Verified Compute Market selection using only train evidence before evaluation decisions;
- market success versus an oracle that asks whether any tested engine could solve each evaluation case;
- observed latency/token usage from the normalized provider adapters;
- a content hash binding workload cases and declared provenance.

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

Both train and evaluation splits are mandatory. Evaluation outcomes are not applied to market profiles until after each corresponding market decision has been recorded.

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

Do not place credentials, bearer tokens, headers, or secret-bearing URLs in this file. The existing `ai_providers` registry resolves credentials from the environment. Supported provider names currently include OpenAI, Anthropic, Google, Azure OpenAI, Bedrock, Ollama, and OpenAI-compatible endpoints.

## Precommit, then run

First compute and record the suite hash before any provider calls:

```bash
python scripts/external_assurance_eval.py hash --suite external-suite.json
```

Then execute with that exact hash:

```bash
python scripts/external_assurance_eval.py run \
  --suite external-suite.json \
  --expected-suite-sha256 <RECORDED_HASH> \
  --engines external-engines.json \
  --output runs/external-assurance/report.json
```

The run aborts before provider execution if the suite has changed since precommitment.

## Interpretation

Treat this evidence as a scoped experiment. A stronger publication-quality study should additionally use an evaluator-controlled repository or immutable release for the suite, pre-register engine versions and pricing, run repeated trials where provider sampling is nondeterministic, retain raw normalized receipts, and report confidence intervals rather than relying on a single success percentage.

M2 swarm evidence remains separate. Until a concrete `SwarmRuntime`/`WorkerContract` implementation lands on `main`, this external runner evaluates heterogeneous engine selection with direct execution only; it does not pretend to provide live swarm evidence.
