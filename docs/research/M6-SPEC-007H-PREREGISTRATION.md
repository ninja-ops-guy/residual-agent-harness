# M6-SPEC-007H Preregistration — Observed-Anomaly MeasurementGap

## Motivation

M6-SPEC-007D through 007G repeatedly showed a useful but poorly represented epistemic behavior: the Scientist noticed a measured anomaly, then used `missing_metric` to name the anomaly itself while asking for deeper explanatory evidence.

007H changes the MeasurementGap representation so measured evidence and missing evidence are separate fields.

## Independent variable

MeasurementGap contract.

A gap now requires:

- `observation.observed_metric`: a metric present in the EvidenceSnapshot;
- `observation.observed_value`: the exact measured value;
- `missing_metric`: a different measurement absent from the EvidenceSnapshot;
- a substantive question, reason, and mechanically collectible proposed measurement;
- registered preservation invariants;
- exact EvidenceSnapshot hash;
- human approval.

## Preserved

- general `qwen2.5:7b` Scientist/reviewer from 007G;
- same aggregate EvidenceSnapshot and raw source-evidence hashes;
- no supplied improvement question, target metric, intervention, or hypothesis;
- typed structured response;
- deterministic host verification;
- independent semantic review only after mechanical admission;
- no implementation, Git, M4, evaluator, integration, or promotion authority.

## Hypothesis

Separating "I observe X" from "I need Y to explain X" will let the Scientist express legitimate epistemic uncertainty without falsely declaring a measured metric absent.

## Success

Either branch is acceptable:

1. an ImprovementSpec-like proposal that passes mechanical admission and independent semantic review; or
2. a MeasurementGap whose observed anomaly is exactly evidence-bound and whose requested measurement is genuinely absent, mechanically collectible, and semantically approved.

Success produces a cryptographic admission receipt. A successful MeasurementGap advances to instrumentation/measurement work, not directly to candidate implementation.
