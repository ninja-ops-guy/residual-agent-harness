# M6-SPEC-007O Preregistration — Split Hypothesis Scientist and Measurement Planner

## Motivation

007N made evidence inspection explicit, but the combined Scientist still repeatedly chose the lower-commitment EvidenceRequest branch.

007O separates two epistemic roles.

## Protocol

1. Evidence Scout selects 2–5 metric IDs from the trusted catalog.
2. Host returns exact values.
3. Hypothesis Scientist may return only:
   - `ImprovementSpec`, or
   - `InsufficientEvidence`.
4. Only after `InsufficientEvidence`, a separate Measurement Planner may request one metric.
5. Host EvidenceResolver decides whether that metric is already available.
6. Present evidence is added for one more hypothesis cycle; absent evidence becomes a host-classified MeasurementGap.
7. Mechanical admission and branch-aware semantic review remain external.

## Preserved

- enriched snapshot and 007J measurement provenance;
- qwen2.5:7b for all model roles;
- no supplied improvement question, target metric, intervention, or hypothesis;
- deterministic host evidence authority;
- independent semantic review;
- human approval;
- no implementation or promotion authority.

## Bounds

At most:
- one evidence-scout call;
- two Hypothesis Scientist cycles;
- two Measurement Planner calls;
- one semantic review.

## Success

Admitted ImprovementSpec -> M6-008 eligible.

Admitted host-classified MeasurementGap -> evidence acquisition; M6-008 blocked.

Insufficient/repeated already-inspected evidence -> fail closed.
