# Factory Benchmark Corpus — FB001–FB004

This directory turns the four frozen Factory benchmarks into one controlled, signed experiment.

The corpus is intended to answer a narrower question than a general software benchmark:

> On the same host and frozen local model, how do serial, fixed-swarm, and dynamic-swarm execution change completion time, coordination cost, rework, and project success as workload structure becomes harder?

## Included workloads

| Benchmark | Primary variable |
|---|---|
| FB001 | Independent parallel work / scheduling ceiling |
| FB002 | Multi-file implementation with DAG dependencies |
| FB003 | Shared-artifact stale-base integration pressure |
| FB004 | Whole mini-project completion |

## Corpus invariants

A measured corpus is signed only when all of the following remain true for the entire FB001–FB004 run:

- one exact Residual source commit;
- one host hardware fingerprint;
- one Ollama model name and exact model digest;
- the same `single,fixed,dynamic` configurations;
- at least three repetitions per configuration;
- provider-reported measured provenance (no simulation);
- valid Station signatures on every child ComparisonReport;
- exact frozen output commits required by each benchmark.

If the source revision, hardware fingerprint, model digest, child report signature, workload hash, or provenance changes, corpus generation fails closed.

## Run

Install Ollama and the Factory dependencies, pull one model, and run:

```bash
pip install -e '.[factory]'
ollama pull qwen2.5-coder:7b

python benchmarks/factory/corpus/run_corpus.py \
  --model qwen2.5-coder:7b \
  --runs 3 \
  --output runs/factory-corpus
```

Use a fresh/empty output directory. A full corpus performs four benchmarks × three configurations × at least three repetitions, so it is intentionally more expensive than the deterministic CI checks.

## Outputs

A successful corpus contains:

```text
runs/factory-corpus/
├── host.json
├── source-commit.txt
├── station-public-key.hex
├── corpus-manifest.json
├── corpus-summary.json
├── fb001/
│   ├── workload.json
│   └── results/
│       ├── observations.jsonl
│       └── comparison-report.json
├── fb002/...
├── fb003/...
└── fb004/...
```

`corpus-manifest.json` is the authoritative aggregate artifact. It binds the source revision, host fingerprint, model identity, workload hashes, child report hashes, run count, simulation state, and Station key identity under a domain-separated Ed25519 signature.

`corpus-summary.json` is a convenience projection for plotting/analysis. It is intentionally not the trust root; regenerate or cross-check it against the signed child reports for publication.

The local private signing key is used only while generating the corpus. Do not publish it. The public key is sufficient for verification.

## Verify

```bash
python benchmarks/factory/corpus/verify_corpus.py runs/factory-corpus
```

To additionally require that verification is occurring on the same hardware fingerprint captured by the experiment:

```bash
python benchmarks/factory/corpus/verify_corpus.py \
  runs/factory-corpus \
  --require-current-host
```

Verification checks the aggregate manifest signature, every child ComparisonReport signature, every workload/report hash binding, model identity consistency, simulation status, and the signed corpus entries.

## Interpreting the corpus

The expected research shape is not simply “dynamic is fastest.” The useful result is the transition across workload classes:

- FB001 estimates the parallelism ceiling.
- FB002 shows the cost of dependency waves.
- FB003 exposes integration tax as swarm width grows.
- FB004 tests whether those effects survive all the way to whole-project completion.

A dynamic swarm that wins FB001 but loses FB003 or FB004 is an important result: it identifies where scheduler policy must account for contention, critical path length, or verifier/integration pressure.

## Claim boundary

This corpus is a controlled systems experiment over four frozen workloads. It does not establish superiority over arbitrary repositories, developers, IDEs, or model providers. Publish measured results with the source commit, host fingerprint, exact model digest, run count, signed manifest hash, and child ComparisonReports so claims remain auditable.
