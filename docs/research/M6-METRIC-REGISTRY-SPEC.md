# M6 Discovery Metric Registry — Specification

Status: Proposed
Origin: M6-SPEC-007O post-hoc semantic audit / issue #265

## Purpose

The discovery Metric Registry gives EvidenceSnapshot metrics stable semantics and provides a governed path for proposing new measurable axes.

A metric name alone is not enough to establish identity, comparability, or nonredundancy.

## Trust boundary

The registry is host-owned and versioned.

The Scientist and Measurement Planner may reference registered metrics or propose a new MetricDefinitionProposal. They cannot mutate the active registry during a run.

A registry hash is bound into the EvidenceSnapshot and any discovery-admission receipt.

A valid receipt does not establish semantic adequacy of a metric definition.

## MetricDefinition

Each registered metric MUST bind:

- `metric_id`: canonical lowercase snake_case identifier;
- `description`: concise semantic definition;
- `unit`: canonical unit identifier;
- `aggregation`: aggregation semantics;
- `population`: what observations/runs are included and excluded;
- `valid_domain`: numeric/domain constraints;
- `directionality`: lower_is_better, higher_is_better, target, or contextual;
- `collection_method`: deterministic derivation or observation procedure;
- `implementation_ref`: code/evidence producer identity;
- `revision`: definition revision;
- `definition_sha256`: canonical content hash.

## MetricDefinitionProposal

A proposed new measurable axis MUST contain the same semantic fields except implementation_ref may identify a proposed collector rather than existing code.

It MUST additionally bind:

- originating EvidenceSnapshot hash;
- observed anomaly metric/value;
- reason the existing registry is insufficient;
- preserved invariant IDs;
- human approval required.

## Mechanical gates

MR-R1. Every EvidenceSnapshot metric ID MUST resolve to exactly one registry definition.

MR-R2. Registry definitions MUST canonicalize deterministically and have stable SHA-256 identity.

MR-R3. Metric IDs MUST match `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`.

MR-R4. Definitions with empty description, unit, aggregation, population, domain, collection method, revision, or implementation reference MUST be rejected.

MR-R5. Exact metric-ID duplicates MUST be rejected.

MR-R6. Exact semantic duplicates — identical unit, aggregation, population, domain, and collection method under a different ID — MUST be rejected mechanically.

MR-R7. A MetricDefinitionProposal whose ID differs from an existing ID only by a likely spelling error MUST be classified UNKNOWN and routed to semantic overlap review, not admitted automatically.

MR-R8. A proposed metric MUST NOT be admitted merely because its string ID is absent from the registry.

MR-R9. Missing/ambiguous metric semantics MUST yield UNKNOWN.

MR-R10. Registry revision/hash MUST be included in EvidenceSnapshot identity and discovery admission receipts.

## Semantic overlap review

The independent reviewer receives:

- proposed definition;
- all mechanically similar existing definitions;
- EvidenceSnapshot;
- originating question/observation.

The reviewer determines whether the proposal is:
- genuinely new;
- a refinement requiring a distinct population/aggregation;
- an alias/duplicate;
- ambiguous.

Only genuinely new or explicitly justified refinements may proceed to evidence acquisition.

The reviewer cannot register the metric or grant implementation/promotion authority.

## EvidenceSnapshot integration

EvidenceSnapshot SHALL replace a bare metric catalog with:

```json
{
  "metric_registry_revision": "...",
  "metric_registry_sha256": "...",
  "metrics": {
    "shipping_task_success_rate": 0.6
  }
}
```

The full definitions may be referenced content-addressably rather than repeated in every model prompt.

## Negative-path acceptance tests

1. Reject `mean_wall_clock_s_basline` when a likely intended registered metric is `mean_wall_clock_s` or a semantically overlapping baseline definition exists.
2. Reject a new alias with identical semantics under a different ID.
3. UNKNOWN when population is "normal conditions" without a deterministic inclusion rule.
4. Reject unit mismatch between value and registered definition.
5. Reject changed aggregation semantics under an unchanged metric ID/revision.
6. Reject EvidenceSnapshot whose metric-registry hash does not match the loaded registry.
7. Reject admission receipt whose registry revision/hash differs from the verified proposal context.
8. Preserve a valid genuinely new metric proposal as proposal evidence without automatically registering it.

## M6 sequencing

```text
EvidenceSnapshot + Metric Registry
        ↓
Evidence Scout
        ↓
Hypothesis Scientist
   ├─ ImprovementSpec
   └─ InsufficientEvidence
              ↓
      Measurement Planner
              ↓
       EvidenceResolver
        ├─ existing metric -> exact value
        └─ new dimension -> MetricDefinitionProposal
                               ↓
                       mechanical registry checks
                               ↓
                       semantic overlap review
                               ↓
                       MeasurementGap admission
```

M6-008 remains ineligible until an ImprovementSpec is admitted through the normal mechanical and semantic gates.
