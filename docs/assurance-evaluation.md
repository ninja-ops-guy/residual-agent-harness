# Adaptive Assurance Evaluation

This document defines the evidence boundary for the Path-to-10 adaptive assurance layer.

## What is measured

The deterministic assurance fixture evaluates two separate questions:

1. **Orchestration and compute allocation:** can a learned policy select between direct and swarm-style strategies, and between heterogeneous engines, more efficiently than fixed routing policies on a mixed workload?
2. **Verifier quality:** can known defects expose false acceptance, false rejection, defect recall, calibration and posterior uncertainty rather than treating verifier PASS as ground truth?

The implementation lives in `residual/assurance/evaluation.py`; `scripts/assurance_eval.py` emits the reproducible evidence artifact used by CI.

## Frozen workload

`FrozenAssuranceWorkload.sha256` binds the workload name, seed and all case fields. Any change to task class, expected outcomes, cost, latency, assurance class, engine outcome, preferred engine or split changes the workload hash.

Each case is explicitly assigned to either `training` or `evaluation`. The controller is trained **only** from training cases. Evaluation cases are rejected if their task class has no frozen training observations. This prevents the evaluation harness from learning directly from the outcomes it later scores.

The current bundled workload is synthetic. It exists to validate experiment mechanics and the adaptive control loop; it is not evidence that any live model, provider or swarm is superior in production.

## Baselines

The adaptive policy is compared against:

- always `DIRECT`
- always `DYNAMIC_SWARM`

For each policy the report records successes, success rate, total cost, cost per success and total latency. The adaptive policy additionally records whether compute-market selections match the case's known preferred engine.

The synthetic fixture is designed to contain multiple granularities: small tasks where orchestration overhead is wasteful, broader tasks where decomposition is beneficial, and high-assurance tasks where stronger compute is required.

## Verifier campaign

`VerifierDefect` provides an independently labeled pair:

- whether the artifact is actually acceptable
- whether the verifier passed it

The verifier-quality framework then measures:

- false acceptances
- false rejections
- defect recall
- false-accept rate
- Bayesian posterior mean
- lower credible bound
- whether the resulting quality profile requires HITL escalation

A verifier's own decision never labels itself as correct. Quality updates require the independent outcome label supplied by the campaign (or, in production, delayed ground truth such as human review, incident feedback, stronger verification, or known-answer benchmarks).

## CI evidence

The controller workflow runs:

```bash
python scripts/assurance_eval.py --output runs/ci-assurance-evidence.json
```

The resulting JSON artifact is retained alongside the existing controlled-study evidence on Python 3.11, 3.12 and 3.13.

## Claim boundary

Passing this fixture establishes that:

- workload identity is frozen and hash-bound;
- training and evaluation outcomes are separated;
- adaptive and fixed policies are measured under the same evaluation cases;
- known verifier defects produce measurable quality statistics;
- evidence generation is reproducible and exercised in CI.

It does **not** establish:

- production reliability;
- superiority over a specific model/provider;
- real-world dollar savings;
- independence of synthetic task families;
- correctness of an unavailable M2 swarm implementation;
- distributed consensus guarantees beyond the DSM interface contracts.

The next evidence level is a separately authored or externally sourced FrozenWorkload executed through live engines and the real M2 swarm runtime once that runtime is present on `main`.
