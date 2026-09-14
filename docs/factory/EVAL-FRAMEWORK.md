# Factory Evaluation Framework

`SPEC-EVAL-001` compares the same frozen engineering workload under `single`, `fixed`, and `dynamic` execution configurations. The framework is evidence-oriented: it records provenance, rejects engine drift, signs the final report, and labels fixture/simulated runs so they cannot be presented as measured Factory speedup.

## Frozen workload

A workload fixes:

- requirement IDs and task dependency graph;
- task acceptance criteria;
- input Git commit and expected output Git commit;
- engine name and version;
- temperature `0` and an optional seed;
- an explicit driver argv used to execute one configuration/run.

The workload hash excludes the driver command so transport/runner wiring does not redefine the research workload.

Example shape:

```json
{
  "schema_version": "factory-evaluation-v1",
  "workload_id": "factory-bench-001",
  "requirements": ["R1", "R2"],
  "tasks": [
    {"task_id": "t1", "requirement_ids": ["R1"], "depends_on": [], "acceptance": ["tests"]},
    {"task_id": "t2", "requirement_ids": ["R2"], "depends_on": ["t1"], "acceptance": ["tests"]}
  ],
  "input_commit": "<full git object id>",
  "expected_output_commit": "<full git object id>",
  "engine": {"name": "model-name", "version": "model-revision", "temperature": 0, "seed": 7},
  "driver_argv": ["python", "run_eval.py", "{config}", "{run}", "{output}"]
}
```

The command driver is invoked without a shell. It must write one `RunMeasurement` JSON document to `{output}`. The framework rejects a returned configuration/run identity mismatch, engine/version drift, malformed measurements, and—on real measured runs—an output commit different from the frozen expected commit.

## Measured engine-backed driver

`residual.factory.eval_driver.EngineBackedEvaluationDriver` executes the frozen task DAG through a real Residual `ExecutionEngine`.

Configuration semantics are fixed for comparability:

- `single`: exactly one active worker;
- `fixed`: a configured fixed worker pool;
- `dynamic`: expands/contracts to the currently ready dependency frontier up to a configured maximum.

A measured engine result must provide an integer `token_usage` and `raw_metadata.provenance == "measured"`. Missing usage or ambiguous provenance fails the run rather than being interpreted as zero. Optional provider-reported `gpu_time_ms` and `api_cost_usd` are consumed directly; explicit configured rates can account for GPU and infrastructure time.

The driver records observed peak concurrent workers in each `RunMeasurement`. `parallel_efficiency` is therefore computed from measured speedup divided by measured worker capacity, not inferred circularly from speedup.

SDK engine adapters preserve explicit usage/provenance metadata returned by their callback, allowing live Claude/OpenAI-style adapters to participate without parsing model text for accounting data.

The finalizer must bind the run to a concrete Git output commit and final-test counts. The evaluation framework then verifies that a non-simulated output commit exactly matches the workload's frozen expected output commit.

## CLI

```bash
residual evaluate \
  --workload spec.json \
  --configs single,fixed,dynamic \
  --runs 3 \
  --station-key station-ed25519.pem \
  --output runs/factory-evaluation
```

At least three runs per configuration are required.

## Metrics

Each run records the normative SPEC-EVAL metrics:

- elapsed time;
- accepted tasks/hour;
- total LLM tokens;
- GPU inference time;
- coordination overhead;
- rework rate;
- merge conflicts;
- verifier rejection rate;
- final test pass rate;
- API, GPU, infrastructure, total, and per-accepted-task cost;
- observed peak worker concurrency.

The ComparisonReport reports mean, median, and sample standard deviation for every metric. Pairwise differences use Mann-Whitney U: exact permutation for small samples and a tie-corrected normal approximation for larger samples.

## Evidence and signing

Every evaluation event is written to a hash-chained JSONL observation log. The signed ComparisonReport binds:

- frozen workload hash;
- run count;
- aggregated configuration metrics;
- pairwise significance results;
- observation-log root;
- whether any input run was simulated;
- Station key identity and report timestamp.

Reports are signed with the Station Ed25519 identity under a signature domain distinct from WorkerReceipt and IntegrationReceipt domains.

## Simulation boundary

A driver may set `simulation=true` for framework/CI fixtures. If any run is simulated, the ComparisonReport is marked `simulation=true`.

A simulated report demonstrates that the evaluation machinery works. It does **not** establish model quality, real speedup, token savings, GPU efficiency, or cost reduction. Those claims require measured runs from the actual engine-backed Factory execution path.

## Current boundary

The repository now contains both the evaluation contract and the measured execution driver. CI validates the measured driver with deterministic fake engines, while real benchmark claims still require an explicitly configured live model engine, frozen Git workload, and repeated runs on declared hardware. Cluster-scale physical testing remains a separate deployment/evaluation activity.
