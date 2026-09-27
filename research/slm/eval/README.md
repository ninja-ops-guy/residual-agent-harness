# EXP-M6-SLM evaluation tooling (research/slm/eval)

Pre-freeze tooling for the EXP-M6-SLM research program. Aligned with
`docs/research/EXP-M6-SLM/SLM-00-PROTOCOL.md` and
`docs/research/EXP-M6-SLM/EVALUATION-PROTOCOL.md`
(eval-protocol-v1.0.0). All modules are stdlib-only Python 3 and expose
`--help`.

## Boundary statement

This directory contains **tooling only**:

- **No training.** Nothing here trains, fine-tunes, or updates any model.
- **No holdout access.** Nothing here reads benchmark items, test-split
  labels, or holdout data. Calibration and cost computations operate on
  externally supplied, already-verified records.
- **No model performance inspection.** These tools compute statistics
  over records produced by the evaluation pipeline; they do not run or
  probe models and cannot influence the SLM-00 freeze gate.
- **Separate from production.** The results store is a research
  artifact, explicitly separate from production logs.
- `feature_flags.py` is a pure config/spec module describing the frozen
  SLM-05 condition ladder A-F. It does not modify RESIDUAL runtime;
  harness consumption of the matrix is a separate later change.

## Modules

| File | Purpose |
| --- | --- |
| `calibration.py` | ECE (10 equal-width buckets), Brier score, reliability diagrams (ASCII table or standalone SVG, no matplotlib), escalation threshold sweeps reporting FNER/UER. |
| `failure_costs.py` + `failure-cost-matrix.yaml` | Preregistered failure-cost matrix with the frozen 10:1 FNE:UE asymmetry (w_FNE=10, w_UE=1), explicit per-category overrides, weighted cost per run. Weights are decision-analysis weights only, never mixed into the standalone safety metrics (FNER, AVR). |
| `model_card.py` + `model-card-template.md` | Model-card generator: intended/prohibited use, training data classes, known limitations, benchmark version, qualification status (candidate/staged/qualified/rejected), deployment constraints. |
| `results_store.py` + `results-store.schema.json` | Append-only, digest-chained research results store. Stable run IDs bind model hash, benchmark hash, harness condition (SLM-05 A-F), frozen seed + seed index, hardware, metrics (frozen names), raw outputs. |
| `feature_flags.py` | Feature-addressable harness switches (contracts, epistemic memory, deterministic verification, repair history, full station context) mapping to SLM-05 conditions A-F as a config matrix. |
| `paper_export.py` | Paper artifact pipeline: content-addressed per-run manifests, result tables (CSV/markdown) over frozen metric names, reproducibility metadata from the results store. |

## Usage

Every module is a CLI. Examples:

```bash
python calibration.py ece --input observations.jsonl
python calibration.py reliability --input observations.jsonl --svg rel.svg
python calibration.py sweep --input observations.jsonl --steps 20

python failure_costs.py show --matrix failure-cost-matrix.yaml
python failure_costs.py cost --counts '{"false_non_escalation": 1, "unnecessary_escalation": 4}'

python model_card.py init --output card.json
python model_card.py validate --metadata card.json
python model_card.py render --metadata card.json --template model-card-template.md

python results_store.py init --store runs.jsonl
python results_store.py append --store runs.jsonl --record record.json
python results_store.py verify --store runs.jsonl

python feature_flags.py matrix
python feature_flags.py diff A F

python paper_export.py table --store runs.jsonl --format markdown
python paper_export.py manifest --store runs.jsonl --outdir artifacts/
python paper_export.py repro --store runs.jsonl
```

## Tests

```bash
cd research/slm/eval
python -m unittest discover -s tests -v
```

Tests use toy data only and never touch benchmark content.

## Metric-name alignment

Metric identifiers follow EVALUATION-PROTOCOL.md exactly: VMSR, VSMS/$,
VSMS/W, FNER, AVR, frontier calls avoided, UER (unnecessary escalation
rate), operator-active minutes, latency (median/p95/p99), schema-invalid
output rate, ECE, Brier, throughput. Safety metrics are always reported
standalone and never aggregated into composite scores.
