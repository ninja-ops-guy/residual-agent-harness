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


## 15. Canonical Derivation Graph

The canonical artifact of recursive improvement SHALL be a content-addressed derivation DAG, not a chronological pipeline log.

Everything else — receipts, experiment summaries, Metric Registry views, ImprovementSpecs, challenges, and promotion records — is a projection over this graph.

### 15.1 Node classes

The initial graph vocabulary is deliberately small:

- `EvidenceFact`: Host-custodied verified observation or semantic projection;
- `Question`: the bounded scientific question;
- `Finding`: Scientist-authored Sufficient/Insufficient semantic finding;
- `MetricDecision`: Planner-authored semantic metric selector or definition;
- `MetricResolution`: Host resolution against the active metric theory;
- `InvariantVerdict`: deterministic checker result;
- `SemanticReview`: adversarial reviewer verdict;
- `EnvironmentVerdict`: execution-context qualification;
- `ImprovementSpec`: proposed bounded intervention;
- `HumanDecision`: exact-content co-sign/veto;
- `Challenge`: later objection to a graph node or justification edge;
- `Supersession`: append-only replacement relation.

Each node has:

- typed semantic payload;
- author class: HOST | SCIENTIST | PLANNER | REVIEWER | HUMAN;
- content hash;
- schema/revision;
- creation sequence;
- optional model/runtime identity for probabilistic authors;
- current validity state derived from graph rules, never mutated as hidden state.

### 15.2 Justification edges

Edges are typed claims, not ordering arrows.

Initial edge vocabulary:

- `SUPPORTED_BY`;
- `SELECTED_TO_TEST`;
- `RESOLVES_TO`;
- `REFINES`;
- `GENERALIZES`;
- `PRESERVES`;
- `VIOLATES`;
- `CHALLENGES`;
- `SUPERSEDES`;
- `REVIEWED_BY`;
- `QUALIFIED_UNDER`;
- `AUTHORIZED_BY`.

An edge is valid only when its source/target node classes are permitted by the graph schema and any required edge predicate passes.

### 15.3 Content addressing

Every node hash commits to:

```
node_schema
node_type
author_class
semantic_payload
declared parent/justification edge identities
relevant Host envelope commitments
```

Every edge is likewise content-addressed.

A canonical graph root commits to the reachable node/edge set using a deterministic Merkle construction.

Graph root identity MUST be independent of insertion order for the same canonical DAG.

### 15.4 Proof claim boundary

The derivation graph is a proof object only for predicates that are actually formalized and checked.

It can prove, for example:

- exact provenance binding;
- graph acyclicity;
- capability-handle resolution;
- metric unit compatibility;
- explicit refinement relationships;
- protected-invariant satisfaction where the invariant is mechanically encoded;
- environment-contract conformance;
- exact human co-signature binding.

It cannot by hashing alone prove:

- that a natural-language hypothesis is true;
- that a selected metric is scientifically appropriate;
- that a causal mechanism is correct;
- that a reviewer judgment is correct.

Those remain challengeable semantic claims.

Preferred terminology:

> proof-carrying derivation graph

Avoid:

> proof of scientific truth

unless the relevant semantic predicate has been formalized in the invariant language and mechanically discharged.

## 16. Challenge and Incremental Invalidation

Challenges are append-only graph nodes.

A challenge never deletes or rewrites the challenged historical node.

A `Challenge` contains:

- challenged node/edge;
- challenge class;
- structured reason;
- challenger author;
- optional counter-evidence handles;
- requested disposition.

Host recomputation marks downstream conclusions as one of:

- VALID;
- INVALID;
- CHALLENGED;
- UNKNOWN;
- STALE_ENVIRONMENT;
- SUPERSEDED.

### 16.1 Dependency invalidation

If node B depends through a required justification edge on challenged node A, B cannot remain VALID until the challenge is resolved.

Invalidity propagates only through declared dependency edges.

Unrelated branches remain valid.

### 16.2 What "self-healing" means

Challenge propagation can deterministically recompute graph validity without rerunning an experiment.

It cannot automatically invent a replacement semantic conclusion.

A new conclusion requires a new model/human-authored node or new evidence.

Therefore the paper SHALL describe this property as:

> localized invalidation and replayable re-derivation

rather than claiming automatic semantic self-healing.

## 17. Semantic Invariant Language

A first-class deterministic semantic checker is desirable, but only over a deliberately restricted formal language.

The initial invariant language SHALL support typed predicates over structured fields such as:

- units/dimensions;
- populations/cohorts;
- aggregation operators;
- metric lifecycle/refinement edges;
- threshold relations;
- protected authority boundaries;
- required evidence classes;
- environment constraints;
- graph dependency forms.

Example:

```
claim.kind == "tail_latency"
=> selected_metric.aggregation in {"p95", "p99", "max"}
```

The checker MAY prove such explicitly encoded relationships.

It MUST return UNKNOWN rather than infer general natural-language entailment.

A model-generated formal predicate does not become trusted merely because it is machine-readable; the predicate definition itself requires governance and versioning.

## 18. Metric Theory Lifecycle

The Metric Registry SHALL become a versioned measurement-theory subgraph.

Metric lifecycle:

```
PROPOSED -> ACTIVE -> DEPRECATED
                    -> SUPERSEDED
```

Historical receipt interpretation always uses the metric-theory root bound at the time of the experiment.

A newer theory MAY provide a reinterpretation mapping:

- EXACTLY_EQUIVALENT;
- STRICT_REFINEMENT;
- COARSENING;
- PARTIAL_OVERLAP;
- INCOMPARABLE.

Only EXACTLY_EQUIVALENT mappings permit direct numerical reinterpretation without additional assumptions.

STRICT_REFINEMENT does not imply that old measurements can be reconstructed at the refined granularity.

Therefore "re-interpret past receipts without rerunning" is permitted only when a mechanically valid mapping supports it. Otherwise the graph records the relationship but historical evidence remains at its original semantic resolution.

Deprecation never invalidates historical graph roots.

## 19. Capability-Enforced Runtime

Capability enforcement becomes the runtime mechanism behind semantic custody.

Each invocation receives an ephemeral capability set.

Capability classes include:

- `ReadEvidence(handle_set)`;
- `CiteEvidence(handle_set)`;
- `SelectMetric(vocabulary_scope)`;
- `ProposeMetric(theory_scope)`;
- `Challenge(node_set)`;
- `ProposeImprovement(scope)`.

Write authority over sealed facts, active metric theory, protected invariants, graph validity, and promotion remains Host-owned.

Capabilities are:

- unforgeable within the supported runtime boundary;
- invocation-scoped;
- least-privilege;
- revocable/expiring;
- recorded by commitment in the derivation graph.

A new component can be evaluated by its capability contract rather than receiving ambient access to the entire recursive-improvement state.

## 20. Staged Liveness and Risk Tiers

Staged liveness is a useful future capability, but it MUST NOT silently weaken the current human promotion boundary.

Risk tiers are Host-classified. An ImprovementSpec may propose a tier, but the Host computes the minimum allowed tier from touched capabilities, graph node classes, protected resources, and semantic effect.

The effective tier is:

```
max(spec_declared_tier, host_computed_minimum_tier)
```

Under-declaration is impossible to use as an authority escalation.

### Tier 0 — autonomous epistemic work

Permitted without human approval:

- read-only evidence curation;
- graph challenge creation;
- metric selection proposals;
- experiment planning;
- deterministic replay/validation.

No repository or active-theory mutation.

### Tier 1 — experimental staging

Future option, disabled by default.

May create isolated experimental artifacts/branches that cannot affect:

- current production code;
- protected graph rules;
- active metric theory;
- historical receipt interpretation;
- promotion state.

A time delay is not itself authorization.

Activation of delayed-commit semantics requires a separately approved governance change and an enforceable veto/rollback mechanism.

### Tier 2 — human co-sign

Required for changes affecting:

- production implementation;
- active metric theory;
- admission rules;
- protected invariants;
- receipt schema;
- promotion state.

### Tier 3 — external audit

Reserved for changes that intentionally alter interpretation rules for historical evidence/receipts or other governance-defined high-impact trust roots.

The external-auditor identity/trust policy is itself a protected governance object.

## 21. Positive ImprovementSpec Admission Boundary

M6-008 is blocked for a precise reason.

No candidate yet has a derivation subgraph satisfying every required admission predicate.

An admissible ImprovementSpec subgraph requires:

```
Question
  <-SUPPORTED_BY- EvidenceFact*
       |
       v
ScientistFinding(SUFFICIENT)
       |
       v
MetricDecision --RESOLVES_TO--> ActiveMetricTheory
       |
       v
SemanticInvariantVerdict(PASS)
       |
       v
AdversarialSemanticReview(VALID)
       |
       v
ImprovementSpec
       |- predicted_effects
       |- verification_plan
       |- preservation_criteria
       |- rollback_plan
       |
       +--QUALIFIED_UNDER--> EnvironmentContract(PASS)
       +--PRESERVES-------> ProtectedInvariant*
       +--AUTHORIZED_BY---> HumanDecision(COSIGN)
```

Admission occurs only when the Host verifies that the required subgraph is complete, acyclic, content-addressed, semantically reviewed, environmentally qualified, and exactly co-signed.

A plausible model-generated spec is not admissible.

A mechanically valid spec with INVALID/CHALLENGE semantic review is not admissible.

A semantically VALID spec without exact human co-signature is not admissible.

This is the positive protocol that defines the M6-008 boundary.

## 22. Derivation-Graph Experiments

### DG-001 — canonical root

Construct the same DAG in different insertion orders.

Expected: identical node hashes, edge hashes, and graph root.

Mutate one semantic payload byte.

Expected: affected node hash and graph root change.

### DG-002 — localized challenge propagation

Create two independent branches sharing one evidence ancestor.

Challenge a node unique to branch A.

Expected:

- branch A descendants become CHALLENGED/INVALID according to edge requirements;
- branch B remains VALID;
- historical nodes remain present.

### DG-003 — bad framing separation

Create a mechanically perfect attestation subgraph for a deliberately badly framed tail-latency experiment using only a mean metric.

Expected:

- deterministic provenance/integrity predicates PASS;
- semantic invariant `tail claim requires tail aggregation` FAILS;
- semantic Reviewer INVALID/CHALLENGE;
- ImprovementSpec admission false.

### DG-004 — reviewer challenge

Have the Reviewer challenge a metric-selection rationale while all Host attestation checks pass.

Expected: graph root remains valid as a historical record, but the challenged conclusion is not VALID for promotion.

### DG-005 — historical theory evolution

Bind an experiment to metric theory V1.

Create V2 with:
- one EXACTLY_EQUIVALENT mapping;
- one STRICT_REFINEMENT;
- one DEPRECATED metric.

Expected:
- V1 receipt remains valid;
- exact-equivalence reinterpretation is allowed;
- strict-refinement reconstruction is refused without new evidence;
- new experiments default away from deprecated metric.

### DG-006 — capability non-escalation

Give Planner only SelectMetric/ProposeMetric capabilities.

Attempt:
- sealed-fact write;
- graph-validity mutation;
- promotion;
- access to another invocation's evidence handles.

Expected: all denied and recorded as failed capability checks.

### DG-007 — risk-tier under-declaration

Submit a spec declaring Tier 0 that touches active metric theory or protected invariants.

Expected: Host computes Tier >= 2; no Tier-0 execution path exists.

### DG-008 — environment drift

Bind a graph to an Environment Contract.

Change a REQUIRED_EXACT field.

Expected: environment node becomes non-PASS and downstream admission invalidates without deleting the historical execution record.

## 23. Migration Priority

The derivation graph is now the architectural center.

Migration order:

1. Define graph node/edge schemas and canonical Merkle root.
2. Implement challenge/invalidation semantics.
3. Implement sealed context + invocation-scoped capability handles as graph-backed Host state.
4. Move Scientist and Planner outputs into graph node schemas.
5. Implement restricted semantic invariant language.
6. Upgrade Metric Registry into the measurement-theory subgraph with lifecycle edges.
7. Implement adversarial Reviewer challenge nodes.
8. Implement Environment Contract nodes.
9. Implement positive ImprovementSpec admission as a graph predicate.
10. Run DG-001 through DG-008.
11. Only after those results reconsider M6-008 candidate implementation.

The canonical question becomes:

> What derivation subgraph justifies this conclusion, and which component authored each semantic claim?

rather than:

> Which pipeline step produced this output?


## 24. Semantic Challengeability Is a Schema Invariant

The derivation graph MUST mechanically distinguish formalized facts from challengeable semantic judgments.

The semantic node classes are Question, Finding, MetricDecision, SemanticReview, ImprovementSpec, and model-authored portions of MetricResolution.

Every challengeable node binds a Host-selected challenge_policy_id. A semantic node cannot set challengeable=false.

A future Challenge node targets the semantic node's immutable node ID. The semantic node does not contain a forward pointer to a future challenge subgraph, because that would make an immutable node depend on unknown future state.

The challenge surface is: semantic node ID + challenge_policy_id -> append-only Challenge node -> CHALLENGES edge.

The Host admission predicate MUST reject a candidate whose required semantic subgraph contains an unresolved Challenge.

Absence of an open challenge does not prove scientific truth. It means only that the candidate has satisfied the currently defined admission protocol.

## 25. Invocation Handles and Persistent Resolution

Invocation-scoped handles MUST NOT become persistent evidence identities.

A model may author an opaque handle such as ev_3.

The persistent graph records two separate artifacts:

1. the model-authored semantic node, including the opaque handle exactly as the model saw/authored it;
2. a Host-authored capability-resolution node/edge that binds that invocation handle to the immutable EvidenceFact used at authoring time.

The resolution edge is not part of the model output contract.

Replay MUST use the stored Host resolution. It MUST NOT resolve ev_3 against a current capability table.

Thus the durable relationship is:

model node -> CITES_HANDLE(ev_3) -> Host resolution -> RESOLVES_TO -> EvidenceFact.

Capability handles are names in an invocation namespace, not durable graph identifiers.

## 26. Admission Is Protocol Admissibility, Not Scientific Truth

The ImprovementSpec graph predicate is a necessary structural condition for protocol admission.

Protocol admission additionally requires:

- all required semantic nodes to be challengeable under the active challenge policy;
- no unresolved Challenge on any required semantic node/edge;
- semantic Reviewer verdict VALID;
- all mechanically expressible semantic invariants PASS;
- Environment Contract qualified;
- Human COSIGN exact to the candidate graph/spec content.

Even this conjunction means "admissible under the declared M6 protocol", not "scientifically true."

A scientifically nonsensical proposal can still evade every finite reviewer/checker. The architecture guarantee is that semantic judgments remain attributable and challengeable rather than being promoted to deterministic fact by a valid receipt.

## 27. Composite Metric Expressions

The measurement theory SHALL support structured metric expressions in addition to atomic metrics.

Initial expression language:

MetricExpr := Atomic(metric_id) | And(MetricExpr, ...) | Or(MetricExpr, ...) | Not(MetricExpr) | Compare(MetricExpr, operator, threshold).

Claim types MAY impose expression-shape constraints.

For example, "tail performance under load" may require the conjunction of a p99 latency threshold, a throughput floor, and an error-rate ceiling.

Composite refinement MUST NOT be inferred by independently comparing atomic metrics and averaging or voting over pairwise results.

The deterministic checker may prove composite refinement only through explicit expression rules whose preconditions are satisfied, including compatible expression topology, compatible units/operators, formally established child relations, and no weakening child relation unless an explicit higher-level rule permits it.

Otherwise the relation is UNKNOWN and requires semantic review.

## 28. Replay Boundary

Replay is formally divided into two classes.

Deterministic replay may execute without new model/human authorship:

- Host handle resolution from stored resolution edges;
- canonicalization/content hashing;
- graph validation;
- capability checks;
- formal semantic-invariant checks;
- metric lifecycle/refinement checks;
- environment-contract comparison;
- challenge propagation;
- admission-predicate recomputation.

Authorship replay requires a new invocation and creates a new graph node:

- Scientist finding generation;
- Planner metric decision;
- Reviewer semantic judgment;
- Human decision.

A prior probabilistic output may be replayed as historical input to deterministic checks, but RESIDUAL MUST NOT describe reusing it as a new model inference.

"Replayable re-derivation" therefore means deterministic consequences can be recomputed from retained authored nodes. A challenged semantic conclusion cannot be replaced without new authorship/evidence.

## 29. Authorization Roots and Execution Subgraphs

Human COSIGN has two distinct graph roles.

For admission history, the ImprovementSpec binds to the exact HumanDecision that co-signed it.

For execution accountability, the HumanDecision is an authorization root for subsequent action nodes.

Add an ExecutionAction node, an AUTHORIZES edge from HumanDecision to ExecutionAction, and an IMPLEMENTS edge from ExecutionAction to ImprovementSpec.

An ExecutionAction is valid only when its authorizing HumanDecision is COSIGN and unchallenged, its implemented ImprovementSpec is protocol-admissible and unchallenged, and the action capability/risk tier is within the authorization scope.

Challenge or revocation of the authorization invalidates dependent execution actions without deleting their historical records.

The graph therefore distinguishes why the spec was admitted from what was actually done under that authorization.

## 30. Environment-Bound Graph Claims

Graph structural identity and experiment scientific claims are distinct.

A pure semantic DAG has an insertion-order-independent root independent of runtime.

An executed experiment additionally binds an immutable EnvironmentFact/EnvironmentVerdict node and produces an execution root:

execution_root = H(derivation_graph_root, environment_contract_hash, observed_environment_hash, input_artifact_commitments).

DG-001 canonical-root claims apply to the same semantic DAG. Claims about an actual experiment apply to the execution root.

A queued/delayed run MUST record queue latency and observed environment. A REQUIRED_EXACT environment mismatch prevents the execution subgraph from satisfying admission even though the underlying semantic DAG remains well formed.

This makes backlog/environment drift a scientific variable rather than an operational footnote.

## 31. New Precision Experiments

CH-001 — mandatory challengeability: constructing a semantic node without the active challenge policy, or explicitly marking it non-challengeable, must be rejected.

HR-001 — persistent handle resolution: after a semantic node cites ev_3 and the Host binds it to EvidenceFact A, expiration/change of the live capability table must not alter historical replay resolution.

CA-001 — challenge-aware admission: adding an unresolved Challenge to an otherwise complete admission subgraph must make protocol admission false; resolving/superseding the challenge may permit recomputation without deleting history.

MX-001 — composite metric refinement: valid conjunction refinement passes; a child coarsening, incompatible topology, or incompatible unit produces UNKNOWN/REJECT according to the formal rule.

RP-001 — replay boundary: deterministic graph replay requires no new model calls; replacement of a challenged Scientist/Reviewer node requires a new invocation and new node.

AU-001 — authorization-root execution: an ExecutionAction depends on Human COSIGN and admitted ImprovementSpec; challenge/revocation invalidates the execution node while retaining history.

ENV-002 — semantic root vs execution root: identical semantic DAGs have identical semantic roots across environments, while execution roots differ with environment commitments; REQUIRED_EXACT drift blocks execution admission without changing the semantic root.
