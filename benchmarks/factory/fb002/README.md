# Frozen Benchmark 002 — bounded multi-file implementation

FB002 measures the Factory runtime on a real multi-file software implementation workload while preserving deterministic evaluation. It follows FB001's pure scheduling benchmark and introduces code generation, semantic acceptance tests, dependency blocking, canonical integration, and project-level verification.

## Workload

The fixture is a small Python `service` package containing six unimplemented helpers:

- `text` — `slugify`
- `retry` — exponential backoff
- `paths` — safe path joining
- `config` — boolean parsing
- `summary` — depends on `text` + `config`
- `banner` — depends on `retry` + `paths`

The initial ready frontier is four tasks. The second wave contains the two dependent helpers. Files do not overlap, so FB002 measures dependency scheduling and verified multi-file integration without intentionally manufacturing merge conflicts.

Frozen Git objects:

- input: `35d17ee0aa7cf39f405baf12e3a71e211111787f`
- known-good output: `efbe57071650782261916655e90205cff0278ba9`

Git author, committer, timestamp, commit messages, file names, and canonical output bytes are pinned by the fixture generator.

## Why canonical integration?

Unlike FB001, the model writes source code. Different correct implementations can satisfy the same task, so requiring the model's raw bytes to equal one reference implementation would turn the benchmark into a formatting/memorization test.

FB002 instead:

1. validates each candidate's AST and import boundary;
2. executes task-specific semantic tests;
3. rejects failed candidates;
4. records the accepted implementation as the worker result;
5. normalizes every verified task to the benchmark's canonical reference bytes during final integration;
6. runs all six project checks;
7. requires the deterministic known-good Git commit.

The normalization step means the timing/quality question is: **did the agent produce a semantically correct bounded patch?** It does not reward incidental formatting differences.

## Measured configurations

- `single`: one model worker;
- `fixed`: four workers;
- `dynamic`: expands to the current DAG-ready frontier, capped at six.

The same frozen Ollama model digest, temperature `0`, and seed are used for every configuration. The live runner requires provider-reported token counts and marks results as measured provenance.

## Prepare

```bash
pip install -e '.[factory]'
ollama pull qwen2.5-coder:7b
python benchmarks/factory/fb002/prepare_workload.py --model qwen2.5-coder:7b
```

`prepare_workload.py` verifies both deterministic fixture commits, freezes the installed Ollama model digest, writes `workload.local.json`, and creates a local Station Ed25519 key when needed.

## Run

```bash
residual evaluate \
  --workload benchmarks/factory/fb002/workload.local.json \
  --configs single,fixed,dynamic \
  --runs 3 \
  --station-key benchmarks/factory/fb002/station.local.pem \
  --output runs/fb002
```

A run fails rather than contributing misleading data when the model identity drifts, token usage is absent, a task fails semantic verification, the project checks fail, or the final commit differs from the frozen output.

## Claim boundary

FB002 is still a controlled benchmark. It supports claims about bounded multi-file code generation, dependency-aware parallelism, semantic acceptance, and deterministic integration for this workload. It does **not** establish general superiority over IDE agents or prove performance on large repositories. A later conflict-bearing benchmark should measure rework and deterministic conflict handling separately.
