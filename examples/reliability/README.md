# Reliability benchmark authoring scaffold

This directory contains templates for Experimental Release 1. It is intentionally **not** a confirmatory benchmark by itself. Confirmatory tasks must be externally authored or independently held out from the system and experiment implementer.

## Target composition

Aim for 60–100 evaluation tasks across at least four families, with enough tasks per family to avoid a result being dominated by one narrow mechanism.

Suggested families:

1. **single_file_repair** — localized defects with executable hidden tests;
2. **multi_file_dependency_repair** — changes whose correctness depends on interactions across files/modules;
3. **constraint_transformation** — objectively gradeable structured transformations where plausible-looking outputs can violate hidden constraints;
4. **adversarial_evidence** — misleading, incomplete, stale, or conflicting evidence designed to test acceptance boundaries;
5. **fault_injection** — runtime/tool/resource/evidence failures with an independently known containment outcome.

Use family-level separation between development and evaluation. Do not derive evaluation variants from development tasks by superficial renaming.

## Required case metadata

For every case preserve, outside the worker-visible environment where appropriate:

- stable case ID and family;
- provenance and author;
- task artifact hash;
- independent grader/test hash;
- whether the task is development or evaluation;
- expected verification mechanism;
- whether a deliberate fault is injected;
- fault type and independently defined containment criterion;
- estimated difficulty and any known dependency on external tools;
- license/source terms when imported from a public benchmark.

## Author separation

The preferred confirmatory process is:

1. A task author creates task inputs and hidden grading material.
2. The experiment operator receives only the runnable suite and provenance manifest.
3. Worker-visible environments cannot read the hidden grader.
4. The suite hash is frozen before model execution.
5. Model IDs, inference settings, verifier revisions, budgets, trial counts, and stopping rules are preregistered.
6. Results are normalized with `scripts/reliability_experiment.py` and analyzed without deleting failed or UNKNOWN trials.

## Study bridge

For obligation-harness experiments, author cases using the existing `residual.study-suite.v1` format and freeze them with `residual study freeze`. After execution, convert the complete run directory:

```bash
python scripts/reliability_experiment.py adapt-study runs/confirmatory-study \
  --map-mode full_cloud=raw \
  --map-mode residual=covd \
  --output runs/reliability/observations.jsonl
```

A mode mapping must reflect the actual experimental semantics. Do not label a controller as `raw`, `contracted`, `cov`, or `covd` merely to fill an ablation table.

## What not to do

- Do not call repository-authored fixture tasks independent evidence.
- Do not expose hidden test answers to the generator or verifier unless that exposure is part of the preregistered condition.
- Do not remove provider failures or blocked runs from the scheduled denominator.
- Do not tune the stopping rule after inspecting outcomes.
- Do not infer Factory candidate correctness from successful execution.
- Do not compare dollar costs using stale or invented provider prices; freeze the source/date for prices used in the study.

The point of the benchmark is to create a credible opportunity for the hypothesis to fail.
