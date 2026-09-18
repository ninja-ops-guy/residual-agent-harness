# M6-SPEC-007U Preregistration — Minimal Measurement Planner Envelope

## Motivation

007T proved that host-authored provenance eliminates model hash transcription failures. Its Measurement Planner then re-authored an already verified observation incorrectly.

The Planner does not need authority to restate causal context.

## Independent variable

The Measurement Planner output schema is reduced to:

- `existing_metric_request`: requested registered metric ID + question/reason; or
- `new_metric_proposal`: complete MetricDefinition + reason the current registry is insufficient.

The host carries forward, unchanged, from the mechanically verified Hypothesis Scientist result:

- observed metric/value;
- preservation invariants;
- EvidenceSnapshot hash;
- Metric Registry hash/revision;
- human-gate flag.

The existing Planner verifier remains unchanged and verifies the host-bound request.

## Preserved

All 007T evidence, model, registry, role separation, duplicate/ambiguity gates, independent review, two-cycle bound, and authority restrictions.

## Success

The Planner cannot corrupt the verified Scientist observation because it no longer authors it.

Subsequent outcomes remain open:
- registered evidence request -> host returns exact value;
- duplicate/ambiguous new metric -> fail closed;
- semantically valid new metric -> independent review / MeasurementGap only;
- admitted ImprovementSpec -> M6-008 eligible separately.
