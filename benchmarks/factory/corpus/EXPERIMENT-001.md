# Factory Corpus Experiment 001

Status: FROZEN FOR PHYSICAL MEASUREMENT

## Frozen source

- Residual source commit: `793d629c483502b8d4e61e058f2e69980f583623`
- Experiment branch: `experiment/factory-corpus-exp1`
- Benchmarks: FB001, FB002, FB003, FB004
- Configurations: `single`, `fixed`, `dynamic`
- Minimum repetitions: 3 per configuration
- Intended local model: `qwen2.5-coder:7b`
- Exact Ollama model digest: resolved and recorded by the preparation/corpus tooling on the physical test host.
- Temperature: 0
- Seed: 7

## Qualification before freeze

The frozen source head completed the repository software preflight before this experiment branch was cut:

- Factory runtime evidence: PASS
- Factory OS execution evidence: PASS
- Controller/provider contracts: PASS
- Command Station checks: PASS
- fresh wheel build/install: PASS
- installed-wheel `residual doctor`: PASS
- scripted real OS sandbox execution: PASS

No performance result is implied by those checks.

## Physical-test sequence

From this experiment branch:

```bash
ollama pull qwen2.5-coder:7b
bash scripts/setup_factory.sh qwen2.5-coder:7b
```

Then perform the non-performance dry run:

```bash
python benchmarks/factory/corpus/run_corpus.py \
  --model qwen2.5-coder:7b \
  --runs 3 \
  --dry-run \
  --output runs/factory-corpus-dry-run
```

Only if the preflight and dry run succeed, execute the measured corpus:

```bash
python benchmarks/factory/corpus/run_corpus.py \
  --model qwen2.5-coder:7b \
  --runs 3 \
  --output runs/factory-corpus
```

If interrupted, resume only through the corpus runner's strict `--resume` path.

## Evidence to retain

Retain the complete `runs/factory-corpus/` directory, including:

- `corpus-manifest.json`
- `corpus-summary.json`
- `corpus-state.json`
- `host.json`
- `source-commit.txt`
- `station-public-key.hex`
- all four frozen workload files
- all observation logs
- all signed child ComparisonReports

Do not publish or retain the private Station signing key after successful aggregate signing.

## Abort / invalidation rules

Do not treat the run as Experiment 001 evidence if any of the following occurs:

- source revision changes during the corpus;
- host fingerprint changes;
- Ollama model digest changes;
- a child report is simulated;
- a workload/output binding fails;
- a required child signature fails;
- the corpus runner refuses resume because experiment identity changed.

Fixes discovered during physical testing belong on a new source revision and therefore a new experiment identifier. Do not patch this frozen experiment branch in place and continue calling the results Experiment 001.

## Claim boundary

Experiment 001 measures these four controlled workloads on one declared host/model configuration. It does not establish general superiority over arbitrary repositories, developers, IDEs, providers, or hardware.
