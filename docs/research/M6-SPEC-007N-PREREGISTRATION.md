# M6-SPEC-007N Preregistration — Active Evidence Query

## Motivation

007M proved that host-side EvidenceResolver can prevent false missing-evidence claims, but the Scientist still repeated requests for values already present in passive context.

007N changes evidence consumption from passive reading to an explicit typed query phase.

## Protocol

```text
trusted metric catalog (names only)
        ↓
Scientist selects 2–5 metrics to inspect
        ↓
host returns exact values
        ↓
Scientist proposes ImprovementSpec or EvidenceRequest
        ↓
host EvidenceResolver
   ├─ requested evidence present -> exact value added, bounded reassessment
   └─ requested evidence absent  -> host-classified MeasurementGap
        ↓
deterministic admission + branch-aware review
```

## Preserved

- enriched snapshot including `context_bytes_non_success_max=32652`;
- source evidence hashes and 007J admission provenance;
- qwen2.5:7b;
- no supplied improvement question, target, intervention, or hypothesis;
- host authority over evidence truth/missingness;
- deterministic verification;
- independent semantic review;
- human approval;
- no implementation or promotion authority.

## Additional grounding rule

ImprovementSpec observations/target/preserve metrics must come from evidence the Scientist actively selected or that the host subsequently resolved into the active evidence set.

## Success

Admitted ImprovementSpec -> M6-008 becomes eligible.

Admitted host-classified MeasurementGap -> acquire evidence; M6-008 remains blocked.

Repeated already-resolved evidence requests -> stagnation, not success.
