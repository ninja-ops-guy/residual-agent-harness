# M6-SPEC-007L Preregistration — Corrected Admitted-Gap Closure

007K failed before model execution due to an apparatus variable-name error in the deterministic metric derivation.

007L changes only that defect and adds an executable preflight.

## Measurement

From the retained non-success runs:

- M6-SHIP-001 first request: 30,606 bytes
- M6-SHIP-003 first request: 32,652 bytes

Therefore:

`context_bytes_non_success_max = 32,652`

The derivation, contributing run IDs/evidence hashes, and originating 007J admission receipt are bound into the enriched EvidenceSnapshot.

## Preserved

All 007K scientific conditions are unchanged:
- no supplied improvement question/target/intervention/hypothesis;
- qwen2.5:7b Scientist/reviewer;
- typed observed-anomaly gap/ImprovementSpec contract;
- deterministic verifier;
- branch-aware semantic review;
- human approval;
- no implementation or promotion authority.

## Preflight

Before installing/running the model, CI imports the experiment module and asserts that the deterministic aggregate function returns exactly `32652` for `context_bytes_non_success_max`.

## Success interpretation

Admitted ImprovementSpec -> M6-008 becomes eligible for a separate preregistered candidate experiment.

Admitted MeasurementGap -> collect the next measurement instead; M6-008 remains blocked.
