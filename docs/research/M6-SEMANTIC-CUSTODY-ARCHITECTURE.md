# M6 Semantic Custody Architecture

Status: Proposed
Parent: M6 recursive improvement / Metric Registry
Theme: **separate authorship of meaning from custody of truth**

## 1. Architectural rule

The Host is the sole custodian of verified deterministic state.

Probabilistic components MAY author semantic judgments. They MUST NOT author, copy, transform, or select the deterministic identities that attest those judgments.

A model invocation receives only:

- semantic projections required for its decision;
- invocation-scoped opaque capability handles for evidence it may cite;
- the decision contract.

It MUST NOT receive:

- EvidenceSnapshot hashes;
- Metric Registry hashes/revisions as attestation material;
- receipt hashes;
- verifier revisions;
- human-gate signatures;
- raw sealed-context roots;
- other deterministic identities that the Host can attach itself.

### Important terminology

A model-visible handle is **not** a content hash.

Examples:

- valid model-visible handle: `ev_3`, `claim_2`, or a random invocation-scoped capability token;
- invalid model-visible handle: `fact:0x7a239f...` when the suffix is itself the underlying content hash.

Handles are issued by the Host, scoped to one invocation, and resolvable only if they are present in that invocation's capability set. Guessing another syntactically valid handle gives no authority.

## 2. Sealed Context

The Host maintains an append-only sealed context of verified facts.

Each internal fact contains:

- internal fact ID;
- canonical semantic payload;
- payload SHA-256;
- provenance;
- source receipt references;
- insertion sequence;
- status metadata.

The model-facing projection contains:

- opaque invocation-scoped handle;
- semantic payload or approved semantic projection;
- optional human-readable source class.

It excludes internal hashes and receipt identities.

The Host records a commitment to the exact model-visible projection separately from the model-visible bytes.

### Monotonicity

A fact is never mutated in place.

Corrections and supersessions append new facts and explicit edges. Old receipt chains remain replayable.

## 3. Model-output deterministic-value firewall

The system MUST structurally prevent deterministic identity fields in model-authored schemas.

In addition, the Host MUST reject model-authored free text containing deterministic identities that belong to the sealed context when those identities are not semantically required.

The firewall is defense in depth, not the primary boundary.

The primary boundary is non-disclosure: models do not receive those values.

## 4. Scientist contract: Evidence Curator

The Scientist receives:

- one question;
- semantic evidence projections;
- opaque evidence handles;
- protected semantic invariants stated without attestation identities.

The Scientist emits exactly one:

```
Sufficient {
  evidence_handles: [EvidenceHandle, ...],
  claim: Claim
}

Insufficient {
  evidence_handles: [EvidenceHandle, ...],
  missing_claims: [Claim, ...],
  rationale: str
}
```

The Scientist does not emit snapshot hashes, registry identities, receipt identities, or human-gate state.

The Host resolves every cited handle against the invocation capability set and constructs the provenance envelope.

## 5. Planner contract: Pure Decision Function

The Planner receives the Host-bound Scientist finding plus the semantic metric vocabulary.

It emits exactly one:

```
SelectMetric {
  semantic_selector: MetricSelector
}

DefineMetric {
  proposal: MetricDefinition
}

InsufficientEvidence {
  claim_handle: ClaimHandle,
  rationale: str
}
```

The Planner does not re-author:

- the Scientist observation;
- evidence values;
- protected invariants;
- provenance;
- snapshot identity;
- registry identity;
- human-gate state.

### Metric selection

Metric selection is a semantic decision and MUST be independently justified.

A `MetricSelector` therefore contains structured intent:

- core quantity;
- population;
- aggregation intent;
- unit/dimension;
- applicability constraints;
- rationale for why this lens tests the claim.

The Host resolves the selector against active Metric Registry definitions.

Resolution outcomes:

- EXACT: one compatible active metric;
- AMBIGUOUS: multiple compatible metrics; return candidate semantic projections to Planner for disambiguation;
- NONE: Planner may define a new metric;
- DEPRECATED_ONLY: return active successor/refinement candidates.

The Host MUST NOT silently choose among ambiguous candidates.

## 6. Metric Registry as a constrained semantic lattice

The Metric Registry evolves from a flat set into a versioned partial order over structured metric semantics.

Each metric definition adds:

- `core_quantity`;
- `population_spec`;
- `aggregation_spec`;
- `unit_dimension`;
- `applicability`;
- `refines`;
- `generalizes`;
- lifecycle state: ACTIVE | DEPRECATED;
- optional `superseded_by`.

### Deterministic boundary

General natural-language semantic subsumption is not deterministically decidable.

Therefore deterministic lattice checks apply only to normalized structured dimensions and explicit refinement edges.

The Host MAY deterministically establish:

- exact structured equivalence;
- explicit strict refinement;
- lifecycle validity;
- unit compatibility;
- graph acyclicity;
- successor/deprecation validity.

Potential semantic overlap not established by those rules is UNKNOWN and requires adversarial semantic review. It MUST NOT be converted to PASS by fuzzy-string similarity alone.

### Deprecation

Deprecation never invalidates historical receipts.

New experiments default to ACTIVE metrics.

A deprecated metric may be used only when:

- replaying historical work; or
- the experiment explicitly preregisters why no active successor is appropriate.

## 7. Adversarial Semantic Reviewer

The Reviewer is a judgment component, not an attestation verifier.

It receives:

- the same semantic question;
- the same semantic evidence projections/handles;
- Scientist finding;
- Planner metric-selection rationale or new MetricDefinition;
- ImprovementSpec semantic content when applicable.

It does not receive receipt hashes, registry hashes, sealed-context roots, verifier revisions, or signatures.

It emits:

```
Valid { rationale: str }
Invalid { challenged_claim: ClaimRef, reason: str }
Challenge { challenged_claim: ClaimRef, requested_evidence: str, reason: str }
```

The Reviewer MUST answer the semantic question:

> Is the reasoning and framing justified by the evidence, and is the selected metric an appropriate lens for the claim?

A deterministic verifier separately answers:

> Is the attestation internally consistent and bound to the exact Host context?

Neither answer substitutes for the other.

## 8. Badly framed experiment gate

A well-formed receipt for a badly framed experiment MUST NOT become an admissible ImprovementSpec.

Before ImprovementSpec admission, the Host requires:

1. Scientist sufficiency finding bound to cited evidence;
2. Planner metric-selection rationale;
3. deterministic metric resolution or independently reviewed new metric;
4. adversarial Reviewer verdict VALID;
5. falsifiable predicted effect;
6. preregistered acceptance and preservation criteria;
7. rollback plan;
8. protected-invariant check;
9. environment qualification;
10. exact-content human co-signature.

A Reviewer CHALLENGE returns to evidence acquisition. INVALID terminates the candidate.

## 9. ImprovementSpec admission protocol

An ImprovementSpec is admissible only when all of the following exist:

- `intent`: structural deficiency being addressed;
- `mechanism`: bounded proposed change;
- `predicted_effects`: metric-linked falsifiable predictions;
- `verification_plan`: preregistered experiment;
- `preservation_criteria`: metrics/invariants that must not regress;
- `rollback_plan`: deterministic reversal path;
- `evidence_handles`: Host-resolvable supporting evidence;
- `semantic_review`: VALID;
- `host_invariant_verdict`: PASS;
- `environment_contract`: qualified;
- `human_cosignature`: exact content-addressed spec head.

Admission authority belongs to the Human gate. Models may originate and challenge; they may not admit.

M6-008 remains blocked until a candidate satisfies this protocol.

## 10. Environment Contract

Experiment claims are conditional on an explicit execution environment.

The Host records:

- repository commit/tree identity;
- workflow identity;
- runner OS/image label and available immutable image metadata;
- Python/runtime versions;
- resolved dependency lock/wheel hashes where available;
- model name and immutable model digest where available;
- provider/runtime version;
- queue latency;
- experiment start/end time;
- concurrency declaration;
- environment variables allowlist hash;
- input artifact hashes.

A preregistration states which fields are:

- REQUIRED_EXACT;
- REQUIRED_COMPATIBLE;
- OBSERVATIONAL.

Any REQUIRED_EXACT deviation prevents admission.

A REQUIRED_COMPATIBLE deviation requires a recorded compatibility verdict.

Queue latency is evidence, not automatically a failure condition.

## 11. Receipt: proof-carrying separation record

The receipt commits to:

- sealed-context Merkle root;
- exact model-visible semantic input projections;
- opaque-handle issuance map commitment;
- model-output content hashes;
- Host resolution actions;
- deterministic verifier results;
- adversarial semantic-review verdict;
- environment contract/verdict;
- human co-signature when applicable.

### Claim boundary

A receipt can provide cryptographic evidence of the bytes the Host says it supplied to each model and the resolution actions it performed.

A receipt alone cannot mathematically prove the negative claim that a model had no side channel to hidden state.

The stronger statement "the model could not access sealed deterministic state" requires an attested execution/isolation boundary in addition to the receipt.

Until such attestation exists, the paper SHALL claim:

> RESIDUAL's declared model input channel excludes Host-custodied deterministic identities, and the receipt commits to that declared information flow.

It SHALL NOT claim cryptographic proof of total non-access.

## 12. Scientific framing

The architecture does not make models more reliable.

It reduces the amount of deterministic correctness delegated to probabilistic components.

Preferred paper language:

> RESIDUAL progressively reduces the deterministic load borne by models by moving identity, provenance, verified-state custody, and attestation into Host-owned contracts. Model errors remain possible in semantic judgment; those judgments are isolated, challenged independently, and prevented from silently rewriting verified state.

Avoid:

> The models become reliable because transcription errors are eliminated.

## 13. Required experiments

### SC-001 — sealed-context non-disclosure

Assert that model-visible invocation payloads contain no known sealed hashes, receipt hashes, registry hashes, verifier revisions, or signatures.

Negative control: inject one prohibited identity into the semantic projection and require the invocation builder to reject it.

### SC-002 — capability scope

Issue handles to invocation A.

Assert:

- A resolves its issued handles;
- B cannot resolve A's handles;
- guessed syntactically valid handles fail;
- expired invocation handles fail.

### MS-001 — metric-selection adversarial control

Provide a claim about tail latency with candidate metrics for mean, p95, and p99.

Planner selection must include structured rationale.

Independent Reviewer must reject a mean-only lens when the claim is explicitly about tail latency.

### ML-001 — lattice lifecycle

Test exact equivalence, strict refinement, incomparable axes, ambiguous overlap, deprecation, successor resolution, and cycle rejection.

### RV-001 — badly framed experiment

Construct a mechanically valid proposal whose metric and receipt are valid but whose experiment cannot falsify its causal claim.

Deterministic attestation should PASS; semantic Reviewer should INVALID/CHALLENGE; ImprovementSpec admission must remain blocked.

### ENV-001 — delayed-run environment drift

Preregister an environment contract, then vary one REQUIRED_EXACT field and one OBSERVATIONAL field.

Exact-field drift must block admission. Observational drift must be retained without automatically changing the scientific verdict.

### IS-001 — ImprovementSpec positive protocol

Use a synthetic, bounded candidate to exercise all admission steps through the Human co-signature boundary without implementing or promoting the candidate.

## 14. Migration

1. Land sealed-context and capability-handle contracts behind experimental APIs.
2. Move Scientist to Evidence Curator contract.
3. Move Planner to pure decision contract.
4. Add structured metric selector and lattice lifecycle metadata.
5. Add adversarial semantic Reviewer contract.
6. Add Environment Contract.
7. Add typed ImprovementSpec admission protocol.
8. Extend receipts with separation-record commitments in a new schema version only after compatibility review.
9. Run SC/MS/ML/RV/ENV/IS experiments.
10. Only then reconsider M6-008.

No existing StationReceipt schema is modified by this specification.
