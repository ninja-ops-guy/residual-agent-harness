# M6-SPEC-007M Preregistration — Host EvidenceResolver

## Motivation

007L closed the admitted 007J gap and enriched the EvidenceSnapshot with `context_bytes_non_success_max=32652`. The Scientist then asked for `context_bytes_non_success_mean`, which was already present.

This demonstrates that "what evidence do I want?" and "is that evidence missing?" are different responsibilities.

## Architecture

```text
EvidenceSnapshot
      ↓
Scientist
  ├─ ImprovementSpec
  └─ EvidenceRequest
          ↓
     host EvidenceResolver
       ├─ requested metric present
       │      ↓
       │ exact trusted value returned to Scientist
       │      ↓
       │ reassess (bounded)
       │
       └─ requested metric absent
              ↓
         host-classified MeasurementGap
              ↓
         branch-aware semantic review
```

The Scientist no longer declares evidence missing.

## Preserved

- enriched 007L EvidenceSnapshot including the admitted 007J measurement;
- qwen2.5:7b Scientist/reviewer;
- no supplied improvement question, target metric, intervention, or hypothesis;
- typed structured output;
- deterministic grounding of observations;
- branch-aware independent semantic review;
- exact evidence hashes and 007J admission provenance;
- human approval;
- no implementation or promotion authority.

## Bounds

At most three Scientist calls.

If a requested metric is already present, the host returns its exact value. Repeating the same already-resolved request is classified as stagnation.

If a requested metric is absent, only the host may classify the request as a MeasurementGap.

## Success

An admitted ImprovementSpec makes M6-008 eligible.

An admitted host-classified MeasurementGap triggers evidence acquisition and keeps M6-008 blocked.
