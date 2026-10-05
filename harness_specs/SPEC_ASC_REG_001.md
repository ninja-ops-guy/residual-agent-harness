# SPEC-ASC-REG-001 — Authority Surface Register

Status: research candidate / execution-ready after owner review
Program: ASC-001 (#525)
Normative scope: research qualification only; not normative for v1
Owner gate: CTR-004 / owner adoption of Thesis v2 is separate

## Purpose

Define the versioned, machine-readable register used to enumerate every declared authority-bearing transition inside a frozen qualification boundary.

The register is not a security claim by itself. It is the inventory against which mediation, evidence, bypass attempts, and residual unknowns are tested.

## Core invariant

Every declared authority-bearing transition MUST have exactly one explicit coverage state:

- COVERED
- UNMAPPED
- NOT_TESTED
- OUT_OF_SCOPE

Unknown transitions MUST NOT be coerced into COVERED through taxonomy approximation.

## Definitions

**Authority-bearing transition:** a state change or action that can create, expand, exercise, transfer, persist, or finalize authority over a protected resource or outcome.

**Protected effect:** an externally or durably observable effect whose execution requires authority under the declared policy.

**Mediator:** the typed enforcement point that decides whether a transition is permitted, denied, halted, or requires approval.

**Authority principal:** the actor permitted to authorize the transition. A worker/model identity is not implicitly an authority principal.

## Data model

Implement a versioned `AuthoritySurfaceRegister` with ordered `AuthorityTransition` entries.

Each transition MUST bind at least:

- `transition_id`: stable semantic identifier;
- `schema_version`;
- `semantic_action`;
- `source_state` and `target_state`, when stateful;
- `protected_resource`;
- `protected_effect`;
- `initiator_classes`;
- `authorized_principals`;
- `mediator_id`;
- `mediator_contract_revision`;
- `policy_id` and `policy_digest`;
- `required_evidence_types`;
- `verifier_requirements`;
- `approval_requirement`;
- `failure_semantics`;
- `persistence_semantics`;
- `rollback_semantics`;
- `source_commit` and `source_tree`;
- `eae_digest` from SPEC-ASC-EAE-002;
- `coverage_state`;
- `coverage_reason`;
- `evidence_refs`;
- `known_bypass_classes`;
- `notes`.

## Requirements

- REG-R1: The register MUST have a versioned JSON-serializable schema with canonical serialization.
- REG-R2: `transition_id` MUST be unique and stable across non-semantic refactors. Semantic changes require a new transition revision.
- REG-R3: Every entry MUST have exactly one coverage state.
- REG-R4: COVERED MUST require a declared mediator, policy binding, and EAE digest.
- REG-R5: UNMAPPED MUST preserve the observed transition/path description and why mediation is unresolved.
- REG-R6: NOT_TESTED MUST distinguish known-but-untested from unknown/unmapped.
- REG-R7: OUT_OF_SCOPE MUST include the explicit qualification-boundary rule that excludes it.
- REG-R8: A transition whose protected effect can be reached through multiple routes MUST enumerate each route or bind them to a mechanically justified common mediator.
- REG-R9: A worker/model self-report MUST NOT change coverage state or establish mediation evidence.
- REG-R10: Register generation MUST preserve deterministic ordering and digest stability for identical semantic input.
- REG-R11: Register diffs MUST identify added, removed, changed, and coverage-state-changed transitions.
- REG-R12: Removing a previously COVERED transition MUST require an explicit disposition: retired, merged-equivalent, out-of-scope, or regression.
- REG-R13: Any plausible UNMAPPED path to a protected effect MUST block ASC `PASS_BOUNDED`.
- REG-R14: Evidence references MUST be content-addressed or otherwise candidate-bound; chat assertions are not evidence.
- REG-R15: The register MUST distinguish the authority to REQUEST, ATTEMPT, EXECUTE, ACCEPT, and observe EFFECT where those are separate transitions.
- REG-R16: Transition metadata MUST be sufficient to reconstruct which principal was allowed to authorize the transition and why.
- REG-R17: The schema MUST reject unknown enum values and malformed digests rather than silently normalize them.
- REG-R18: Backward-incompatible schema changes MUST increment schema major version.

## Discovery inputs

The first implementation MUST support register construction from at least:

1. explicit Station/state-machine transitions;
2. controller/service routes that can cause protected effects;
3. adapter/harness actions that cross an authority boundary;
4. approval/HITL transitions;
5. integration/export/publish transitions;
6. recovery/restart paths that can restore or replay authority-bearing state.

Discovery MAY begin partially manual, but the resulting register MUST be machine-readable and independently reviewable.

## Tests

At minimum:

- duplicate transition ID rejection;
- invalid coverage state rejection;
- COVERED entry missing mediator rejection;
- COVERED entry missing EAE rejection;
- UNMAPPED preservation without force-fit;
- deterministic canonical digest;
- semantic change changes digest;
- non-semantic key ordering does not change digest;
- removal requires disposition;
- multi-route transition fixture;
- REQUEST vs EXECUTE vs ACCEPT separation fixture;
- worker-asserted acceptance does not mutate authoritative coverage.

## Seeded fixture

Create a deterministic fixture with:
- at least 6 legitimate transitions;
- at least 2 protected effects;
- one alternate route to a protected effect;
- one intentionally UNMAPPED transition;
- one known but NOT_TESTED transition;
- one OUT_OF_SCOPE transition.

The fixture MUST have hidden expected inventory metadata for SPEC-ASC-QUAL-003 independent challenge tests.

## Acceptance

REG-A1: Schema validation and canonical serialization pass.
REG-A2: Identical semantic register input produces identical digest.
REG-A3: Seeded UNMAPPED transition remains UNMAPPED and blocks bounded pass.
REG-A4: Independent enumeration can detect the intentionally omitted/alternate route.
REG-A5: Register diff identifies an authority-relevant transition addition.
REG-A6: Worker/model assertions cannot create or upgrade authoritative coverage.

## Deliverables

- register schema;
- Python/domain types;
- canonical serializer + digest;
- diff utility;
- deterministic seeded fixture;
- unit tests;
- short operator/reviewer documentation.

Dependencies: existing Station authority contracts; SPEC-ASC-EAE-002 for final COVERED qualification binding.
