# M6-SPEC-007P Preregistration — Metric Registry Controls

## Purpose

Before allowing the discovery loop to use the new Metric Registry, test the exact semantic failure exposed by 007O plus one exact-duplicate negative control and one genuinely new-axis positive control.

No model is used. This is a deterministic trust-infrastructure experiment.

## Cases

1. **007O replay** — `mean_wall_clock_s_basline` with an undefined "normal operating conditions" population.
   - expected: UNKNOWN
   - must not be admitted as a MeasurementGap.

2. **Exact semantic alias** — a different ID with the same unit, aggregation, population, domain, and collection method as `mean_wall_clock_s`.
   - expected: REJECT.

3. **Well-defined new axis** — `first_call_elapsed_ms_mean`, with explicit unit, aggregation, population, domain, collection method, implementation reference, and revision.
   - expected: SEMANTIC_REVIEW only.
   - this is not metric registration and not evidence acquisition.

## Success

All three classifications must match exactly.

A workflow PASS establishes only the deterministic registry-control behavior. It does not authorize a metric, MeasurementGap, ImprovementSpec, candidate implementation, or promotion.
