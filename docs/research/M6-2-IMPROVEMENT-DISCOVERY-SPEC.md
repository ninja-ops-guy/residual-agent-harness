# M6.2 Evidence-Driven Improvement Discovery — Foundation Spec

Status: Proposed implementation
Parent: #222

## Purpose

RESIDUAL has demonstrated bounded recursive development in M6-SPEC-006. This specification adds the smallest trustworthy layer required for RESIDUAL to discover an improvement hypothesis from its own evidence without granting recursive authority.

## New package

`residual/improvement/`

### spec.py

First-class immutable `ImprovementSpec` contract. Required fields:

- improvement_id
- observation
- hypothesis
- target_metrics
- preserve_metrics
- protected_invariants
- acceptance
- human_approval_required=True

Requirements are the frozen behavioral contract proven in M6-SPEC-006. Canonical JSON and SHA-256 identity are mandatory.

### evidence.py

Define immutable `EvidenceSnapshot`.

Required properties:
- schema_version
- baseline_commit
- source_evidence: tuple of content hashes / receipt hashes
- metrics: mapping of mechanically computed metric names to finite numeric values
- sample_count
- window_start / window_end when applicable
- metric_definition_hash

The snapshot MUST canonicalize deterministically and expose a SHA-256 identity.

Reject:
- missing/invalid SHA-256 evidence IDs;
- non-finite metrics;
- zero/negative sample count;
- missing baseline identity;
- unversioned schema.

### scientist.py

The Scientist is analysis-only.

Input:
- EvidenceSnapshot
- bounded model proposal callback

Output:
- ImprovementSpec candidate; or
- MeasurementGap proposal when the available evidence cannot support a defensible hypothesis.

The prompt/contract MUST distinguish measured observations from hypotheses. Every numeric baseline statement used by an ImprovementSpec MUST be present in EvidenceSnapshot.metrics.

### measurement_gap.py

Define an immutable `MeasurementGap` contract for missing evidence dimensions.

Required fields:
- gap_id
- question
- missing_metric
- why_needed
- proposed_measurement
- preserve_invariants
- evidence_snapshot_hash
- human_approval_required=True

A MeasurementGap is **not** evidence that a defect exists. It is a falsifiable request to improve observability so that a later hypothesis can be tested.

The Scientist MAY emit a MeasurementGap only when:
- the requested metric is absent from EvidenceSnapshot;
- the question cannot be answered from existing measured dimensions;
- the proposed measurement is mechanically collectible;
- the proposal does not require modifying evaluator/M4/promotion authority.

MeasurementGap proposals MUST enter the experiment ledger and require external approval before instrumentation changes.

The Scientist MUST have no repository writer, Git, verifier mutation, integration, promotion, shell, or network capability except the explicitly injected model proposal callback.

### verifier.py

Mechanically validate an ImprovementSpec against EvidenceSnapshot.

Reject if:
- no evidence binding;
- target/preserve/protected sets are empty;
- acceptance criteria are not mechanically representable;
- a claimed baseline metric is absent;
- protected paths/capabilities include evaluator, M4, receipt, qualification, promotion, or evidence-integrity mutation;
- human approval is disabled.

Return a structured pass/fail result and deterministic reason codes.

The verifier MUST additionally enforce lessons from M6-EPI-001:
- acceptance criteria use a structured, mechanically evaluable schema rather than free-form prose;
- protected invariants come from a versioned closed vocabulary or registered invariant IDs, not arbitrary metric names;
- MeasurementGap.preserve_invariants is non-empty and uses the same invariant vocabulary;
- evidence_snapshot_hash exactly matches the snapshot under analysis;
- ImprovementSpec target/preserve metrics exist in the snapshot or are explicitly identified as post-intervention metrics with a defined measurement source.

### ledger.py

Append-only experiment ledger linking hashes:

`EvidenceSnapshot -> ImprovementSpec -> experiment -> candidate -> checks -> review -> receipt`

No record may be mutated in place. Later records may supersede earlier records by hash.

## Authority boundary

The M6.2 foundation MUST NOT:
- merge a PR;
- modify protected evaluator/qualification/M4 code;
- change acceptance checks;
- delete evidence;
- promote/deploy a candidate.

## Acceptance

1. Unit tests cover canonical identity and negative paths for every contract.
2. Same EvidenceSnapshot + same ImprovementSpec produces the same validation identity.
3. Scientist cannot create a valid spec with an unmeasured baseline claim.
4. When a required axis is absent, Scientist can emit a MeasurementGap instead of fabricating a baseline.
5. MeasurementGap cannot be converted into an ImprovementSpec until the requested metric has been mechanically collected.
6. Free-form prose acceptance criteria fail validation; acceptance must be mechanically evaluable.
7. Empty or unknown protected-invariant identifiers fail validation.
8. Protected-target attempts fail mechanically before implementation.
9. Ledger tampering or broken hash lineage fails verification.
10. Existing Station/Controller/provider qualification remains green.

## Next experiment

M6-SPEC-007 will use this foundation to give RESIDUAL a hash-bound corpus of its own M6-001..006 research evidence and ask the Scientist to autonomously identify one measurable improvement opportunity. The resulting hypothesis must be recorded before any implementation is authorized.
