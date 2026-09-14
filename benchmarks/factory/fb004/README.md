# Frozen Benchmark 004 (FB004)

FB004 is the first Residual Factory benchmark aimed at the product-level claim: **complete a small engineering project, not merely isolated tasks**.

It freezes a 16-requirement, four-stream Python mini-service called TaskFlow. The service includes validation, models, configuration, authorization, persistence, priority scheduling, serialization, metrics, health, API, CLI, and documentation.

## Frozen project

- input commit: `3f692889f78e0cc6dae29cdcda04bd1e9e2a5e5e`
- known-good output: `b6f20aee56f752a20bcd0652837b137c40d588a4`
- requirements/tasks: 16
- functional streams: architecture, backend, service, docs

The task graph contains both broad first-wave parallelism and cross-stream dependencies. `single` uses one worker, `fixed` uses up to four, and `dynamic` uses the ready frontier up to eight workers.

## Completion criterion

A run only succeeds when all 16 tasks are accepted and deterministic integration produces the known-good output commit. Final project verification executes an end-to-end workflow covering submission, owner lookup, priority scheduling, serialization, and health reporting, and requires both documentation artifacts.

Per-task generation is bounded to one file. Candidate Python receives static import/call checks and must expose the required public symbols. Documentation tasks must contain their frozen contract markers. Verified work is canonicalized before final project verification so equivalent worker formatting does not perturb the final Git identity.

FB004 intentionally measures project completion latency, token/GPU cost, verifier rejection, and useful concurrency. It is still a controlled fixture and does not establish performance on arbitrary production repositories.

## Run

```bash
pip install -e '.[factory]'
ollama pull qwen2.5-coder:7b
python benchmarks/factory/fb004/prepare_workload.py --model qwen2.5-coder:7b
residual evaluate \
  --workload benchmarks/factory/fb004/workload.local.json \
  --configs single,fixed,dynamic \
  --runs 3 \
  --station-key benchmarks/factory/fb004/station.local.pem \
  --output runs/fb004
```

Do not publish speedup claims from fixture/simulated runs. Measured claims require a frozen local model digest and repeated measured executions on declared hardware.
