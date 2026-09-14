# Residual Experimental Release 1 — Reliability from Unreliable Computation

This release protocol is the shortest path from an implemented architecture to evidence for—or against—the central Residual hypothesis.

> With worker capability held constant, bounded authority, evidence, independent verification, and deterministic integration reduce the probability that incorrect computation crosses into accepted state.

The protocol intentionally adds **analysis and evidence binding**, not another orchestration stack. Existing Study, Assurance, Factory, and provider runners remain responsible for execution. This layer consumes normalized observations and calculates the paper's primary outcomes.

## Primary endpoint

**Accepted Error Rate (AER)**

```text
incorrect independently graded accepted outputs
------------------------------------------------
                 all accepted outputs
```

AER is undefined when a configuration accepts nothing. The analyzer reports that state as `null` / `UNKNOWN`, not zero error. This prevents a reject-everything controller from appearing perfectly reliable.

AER must always be interpreted beside:

- acceptance rate;
- accepted correctness;
- independent task success;
- Failure Containment Rate (FCR);
- cost per independently correct accepted result;
- latency;
- raw worker correctness when independently measurable.

## Secondary endpoint

**Failure Containment Rate (FCR)**

```text
injected faults detected or contained before accepted state
-----------------------------------------------------------
                    all injected faults
```

A fault can occur without invalidating the architecture. The systems question is whether that fault is allowed to become accepted state.

## Canonical configurations

A confirmatory study SHOULD include these configurations where the task/runtime permits them:

1. `raw` — direct worker/model result, no Residual acceptance architecture.
2. `conventional` — normal agent/tool orchestration with its ordinary completion behavior.
3. `contracted` — explicit contracts and bounded execution, without independent verification.
4. `cov` — constrain + observe + independently verify.
5. `covd` — constrain + observe + verify + deterministic integration.
6. `residual_fixed_swarm` — COVD with a fixed bounded swarm.
7. `residual_market_swarm` — heterogeneous verified-compute selection plus bounded swarm when the orchestration-tax policy chooses it.

Not every study needs every configuration. The preregistered manifest freezes the exact set before result analysis.

## Required studies

### 1. Fixed-model ablation

Hold model identity, task corpus, inference settings, tool surface, and environment constant. Progressively add Residual controls. The primary comparison is AER relative to `raw` and an appropriate conventional baseline.

### 2. Worker-degradation curve

Repeat the same workload with progressively degraded worker reliability. Degradation may use weaker models, controlled context removal, constrained inference budgets, or deterministic fault transformation, but the method must be frozen before evaluation.

The key graph is:

```text
worker correctness  ->  accepted error rate
```

The central hypothesis predicts that accepted-system correctness should degrade more slowly than raw worker correctness when the acceptance boundary is effective.

### 3. Fault injection

Inject reproducible failures such as:

- malformed output;
- forbidden tool attempt;
- resource exhaustion;
- worker termination;
- conflicting edit;
- stale or absent telemetry;
- verifier unavailability;
- evidence tampering;
- verifier-revision mismatch;
- incomplete dependency evidence.

Record `fault_injected=true` and whether the fault was actually contained before accepted state. Never infer containment merely because a test failed later.

### 4. Matched-budget study

Compare a stronger direct model against Residual using weaker/heterogeneous workers under a frozen total budget. Report both reliability at equal cost and cost at equal reliability where the observed points support those comparisons.

Verifier compute belongs in the Residual budget. A useful additional control gives the conventional baseline access to an equivalent verification-compute budget without granting it Residual's acceptance architecture.

## Frozen manifest

`residual.reliability-manifest.v1` binds the study before analysis:

```json
{
  "schema_version": "residual.reliability-manifest.v1",
  "study_id": "rer1-confirmatory-001",
  "suite_sha256": "<frozen-suite-hash>",
  "source_revision": "git:<commit>",
  "preregistered_at": "2026-09-14T08:00:00-04:00",
  "baseline_configuration": "raw",
  "configurations": ["raw", "contracted", "cov", "covd", "residual_fixed_swarm"],
  "primary_metric": "accepted_error_rate",
  "model_bindings": {},
  "verifier_revisions": {},
  "budget": {}
}
```

Use exact model identifiers, inference settings, verifier revisions, environment information, call ceilings, token/cost ceilings, and stopping rules inside the binding objects used by the actual study. Do not alter the manifest after inspecting outcomes; make a new study ID instead.

## Normalized observation

Every `(case, trial, configuration, degradation_level)` produces one observation:

```json
{
  "schema_version": "residual.reliability-observation.v1",
  "case_id": "repair-017",
  "family": "multi_file_repair",
  "trial": 3,
  "configuration": "covd",
  "accepted": true,
  "independently_correct": true,
  "worker_correct": false,
  "fault_injected": false,
  "fault_contained": null,
  "degradation_level": "medium",
  "cost_usd": 0.0831,
  "latency_ms": 4312.0,
  "evidence_hash": "<receipt-or-run-evidence-hash>"
}
```

`worker_correct` is nullable because some workflows do not expose a meaningful pre-verification candidate grade. Missing data stays missing.

## Analyze

```bash
python scripts/reliability_experiment.py check \
  --manifest experiments/reliability/manifest.json \
  --observations runs/reliability/observations.jsonl

python scripts/reliability_experiment.py analyze \
  --manifest experiments/reliability/manifest.json \
  --observations runs/reliability/observations.jsonl \
  --output runs/reliability/release-1
```

The output directory is create-only. Existing results are not overwritten.

Artifacts:

- `results.json` — complete machine-readable analysis;
- `report.md` — paper/release-oriented table and interpretation boundary;
- `evidence-manifest.json` — hashes binding manifest, observations, result, and upstream evidence;
- `plot-data.csv` — raw points for independent plotting;
- `figures/degradation-aer.svg` — dependency-free degradation/AER figure.

## Benchmark design target

For the first confirmatory release, target approximately 60–100 externally authored or independently held-out tasks across at least four task families. Prefer executable or objectively gradeable tasks. Families should include meaningful cases where incorrect output can plausibly look correct to the generator.

Do not place task answers or hidden graders in the worker-visible environment. The existing controlled-evaluation warning still applies: arbitrary-code work needs grader isolation strong enough that a worker cannot read hidden ground truth.

## Statistical interpretation

The analyzer reports Wilson intervals for AER and FCR proportions but does not automatically claim statistical significance or independence. Repeated trials over the same task are clustered observations. Confirmatory analysis should report task/case-family-level uncertainty and use a paired or clustered procedure appropriate to the final design.

A result supports the central hypothesis only when lower AER cannot be explained by rejecting nearly all work, materially larger unreported compute, leakage from the independent grader, or a verifier that effectively contains the answer.

## Release criterion

Call the result **Residual Experimental Release 1** only when all of the following exist:

- frozen external/held-out workload and provenance;
- fixed-model ablation;
- worker-degradation study;
- fault-injection study;
- matched or transparently normalized cost accounting;
- complete normalized observations;
- hash-bound upstream receipts/evidence where available;
- generated release artifacts from this analyzer;
- paper Results section generated from those artifacts rather than manually transcribed example numbers;
- negative, failed, and `UNKNOWN` outcomes retained in the evidence set.

If the experiment does not support H1, publish that result. The purpose of this layer is to make Residual's thesis testable, not to manufacture a favorable conclusion.
