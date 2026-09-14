# Frozen Benchmark 003 (FB003)

FB003 measures the **parallelism vs integration-pressure tradeoff** for the headless Residual Factory runtime.

Unlike FB001 (independent policy synthesis) and FB002 (non-overlapping multi-file coding), every FB003 task modifies the same `service/policy.py` file. Workers in the same execution batch receive the same base revision. This deliberately creates valid stale-base overlap without manufacturing invalid model answers.

## Workload

Six bounded changes:

- connect timeout: `2 -> 3`
- read timeout: `5 -> 8`
- retry count: `2 -> 4`
- retry backoff: `0.25 -> 0.5`
- log level: `INFO -> DEBUG`
- structured logging: `False -> True`

Frozen Git states:

- input commit: `be7c9a644502333a8066460633e3d0bd5fae4b47`
- known-good output commit: `53c78e92932bb15d2e51e2b668cfadc249ecc41a`

## Configuration semantics

- `single`: one worker/edit at a time. Every subsequent worker sees the already-integrated policy. Expected overlap rework: `0`.
- `fixed`: batches up to four workers from the same base. On this workload the conflict-work upper bound is `4` extra stale-base edits.
- `dynamic`: all six ready workers may execute from the same base. On this workload the conflict-work upper bound is `5` extra stale-base edits.

`merge_conflicts` and `rework_tasks` count extra verified stale-base edits that cannot be applied as independent whole-file changes and therefore require deterministic composition/resolution.

The runner also records the number of resolution groups in its raw measurement JSON as `fb003_resolution_groups`. The normative `RunMeasurement` ignores this extra field for compatibility with SPEC-EVAL-001.

## Safety / acceptance boundary

The model returns the complete `service/policy.py` source under a strict JSON schema. Candidate source is **not executed**. The verifier parses Python AST and permits only:

1. `from __future__ import annotations`;
2. one literal `POLICY` assignment with the frozen schema; and
3. `def policy() -> dict: return POLICY`.

The verifier then confirms that the candidate differs from its batch baseline at exactly the one key assigned to that task. Arbitrary code, imports, calls, extra policy changes, or structural changes are rejected.

After all candidates in a batch verify, the benchmark's frozen resolution rule composes only their approved key-level deltas. This deliberately excludes human decision latency: FB003 measures **conflict detection/resolution work**, not how long a person takes to approve a conflict.

## Prepare

```bash
pip install -e '.[factory]'
ollama pull qwen2.5-coder:7b
python benchmarks/factory/fb003/prepare_workload.py --model qwen2.5-coder:7b
```

Preparation freezes the installed Ollama model digest and checks both deterministic fixture commits.

## Run

```bash
residual evaluate \
  --workload benchmarks/factory/fb003/workload.local.json \
  --configs single,fixed,dynamic \
  --runs 3 \
  --station-key benchmarks/factory/fb003/station.local.pem \
  --output runs/fb003
```

A measured run fails if model identity drifts, Ollama does not report token usage, any candidate changes more than its assigned key, or final integration does not reproduce the known-good output commit.

## Claim boundary

FB003 does **not** establish general merge-conflict behavior for arbitrary software repositories. It isolates one specific systems question: how widening a swarm can reduce model wall-clock time while increasing stale-base integration work when logically independent requirements share a physical artifact.

The benchmark intentionally uses a frozen automatic resolution rule so repeated measurements are possible. A later HITL benchmark should measure actual human-resolution latency separately.
