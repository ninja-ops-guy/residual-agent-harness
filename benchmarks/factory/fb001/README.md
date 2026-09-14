# Frozen Benchmark 001 — Service Policy Parallelism

FB001 is the first measured Residual Factory benchmark. It is intentionally narrow: six independent, exactly verifiable policy-synthesis tasks produce one canonical `policy.json`. Its purpose is to measure the **parallelism ceiling and orchestration tax** of `single`, `fixed`, and `dynamic` execution without allowing subjective code-quality differences to dominate the result.

It is not a claim that six small policy questions represent a full software project. Harder coding workloads should follow as FB002+.

## Frozen fixture

Git author, committer, timestamps, messages, and bytes are pinned. A healthy checkout reproduces:

- input commit: `921c7d728fe9901ec5c5251509084917b9bd1b4b`
- known-good output commit: `beb95402f45815a9b68c06933dd419c476d0f132`

The runner refuses to continue if either deterministic commit drifts.

## Prerequisites

- Python 3.11+
- `pip install -e '.[factory]'`
- Git
- a running Ollama instance
- one installed model that reports token usage through Ollama's `/api/chat`

Example:

```bash
ollama pull qwen2.5-coder:7b
```

## 1. Freeze the local workload

This resolves the installed model's Ollama digest and generates a local Station signing key if one does not already exist.

```bash
python benchmarks/factory/fb001/prepare_workload.py \
  --model qwen2.5-coder:7b \
  --output benchmarks/factory/fb001/workload.local.json \
  --station-key benchmarks/factory/fb001/station.local.pem
```

Do not commit `workload.local.json` or `station.local.pem`. The workload contains the exact model digest used for the experiment.

## 2. Run the repeated comparison

```bash
residual evaluate \
  --workload benchmarks/factory/fb001/workload.local.json \
  --configs single,fixed,dynamic \
  --runs 3 \
  --station-key benchmarks/factory/fb001/station.local.pem \
  --output runs/fb001
```

The configurations mean:

- `single`: one concurrent model task;
- `fixed`: four concurrent workers;
- `dynamic`: expands to the ready DAG frontier, up to six workers.

All three configurations receive the same six frozen tasks, model identity, temperature (`0`), seed (`7`), acceptance rules, input commit, and expected output commit.

## What counts as measured

A run is rejected unless:

1. Ollama reports integer token usage for every model call;
2. the runner marks the provider result as measured provenance;
3. every task answer exactly satisfies its acceptance rule;
4. the deterministic finalizer produces the frozen expected Git commit;
5. the final policy checks pass.

No scripted response or fixture is marked as a measured result.

## Metrics and interpretation

The signed ComparisonReport includes elapsed time, accepted tasks/hour, tokens, coordination overhead, verifier rejection, rework, conflicts, final pass rate, costs, observed peak workers, speedup, parallel efficiency, and significance tests.

FB001 is primarily a **scheduler/parallelism benchmark**. Because all six tasks are independent, it approximates the upper bound on useful concurrency for a small batch. A result such as `dynamic > fixed > single` supports only the claim that Residual can exploit independent work under this frozen workload/model/hardware combination. It does not establish general software-engineering superiority.

Record the hardware, Ollama version, model digest, and whether inference ran CPU-only, GPU-only, or hybrid alongside any published report. Ollama currently provides inference durations and token counts, but FB001 does not infer GPU occupancy from those durations; GPU-time should remain unclaimed unless measured independently.
