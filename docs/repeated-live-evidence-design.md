# Repeated Live Evidence Design

This note records the experimental invariants behind repeated external assurance runs.

1. The preregistration freezes the exact suite hash, engine-config hash, trial count, hypotheses, metrics, budget ceiling, stopping rule, and runner revision before provider calls.
2. Every configured engine is executed for every train and evaluation case in every trial. Baseline comparisons reuse those observations and make no additional provider calls.
3. Each trial creates a fresh `VerifiedComputeMarket`. Only that trial's train outcomes update the market before evaluation. Evaluation outcomes update the market only after each corresponding decision is recorded.
4. The cheapest-eligible baseline selects by declared `cost_per_task`, then engine id for deterministic tie-breaking, subject to capability compatibility.
5. Fixed-engine baselines report each engine's observed evaluation outcomes over the same trial/case attempts.
6. Wilson 95% intervals are reported for Bernoulli success proportions. These intervals describe observed attempt-level uncertainty; repeated use of the same benchmark cases means they must not be interpreted as an iid sample of all possible tasks.
7. v1 preregistration manifests remain supported as exactly one trial. New manifests use v2 and explicitly bind `trials`.
8. Declared cost is an experimental input for policy/budget comparison, not a claim about authoritative provider billing unless the evaluator has independently sourced current pricing.
