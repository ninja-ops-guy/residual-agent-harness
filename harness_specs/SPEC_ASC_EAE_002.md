# SPEC-ASC-EAE-002 — Effective Authority Environment

Status: research candidate / execution-ready after owner review
Program: ASC-001 (#525)
Normative scope: research qualification only; not normative for v1

## Purpose

Define a canonical identity for the authority-relevant environment in which a candidate executes.

A source HEAD/TREE pin is insufficient when connector capabilities, permissions, policy, approval semantics, adapters, or protected endpoints can change independently of source.

## Core invariant

**The authority surface qualified is the authority surface to which the verdict applies.**

An authority-relevant environment change MUST either:
1. change the EAE identity; or
2. be covered by an explicit, testable normalization rule proving the change is non-semantic for authority.

Qualification MUST NOT transfer automatically across a changed EAE.

## Data model

Implement versioned `EffectiveAuthorityEnvironment` with canonical serialization and digest.

Required components:

- `schema_version`;
- RESIDUAL source commit/tree;
- runtime/harness identity + version/revision;
- adapter identities + revisions;
- tool/connector capability inventory;
- tool/connector schema digests;
- granted scopes/permissions;
- protected endpoint/action inventory;
- policy identifiers + digests;
- approval/HITL configuration;
- isolation backend identity/config digest;
- verifier identity/revision/config digest;
- Station/control-plane authority contract revision;
- relevant recovery/restart authority configuration;
- environment normalization policy revision;
- collection timestamp as non-identity metadata unless explicitly justified.

## Requirements

- EAE-R1: EAE serialization MUST be canonical and deterministic.
- EAE-R2: Authority-relevant connector/tool schema changes MUST change the digest.
- EAE-R3: Scope/permission expansion or reduction MUST change the digest.
- EAE-R4: Approval policy/semantics changes MUST change the digest.
- EAE-R5: Adapter revision changes MUST change the digest unless an explicit normalization contract proves authority equivalence.
- EAE-R6: Verifier identity or authority-relevant configuration changes MUST change the digest.
- EAE-R7: Protected endpoint/action inventory changes MUST change the digest.
- EAE-R8: Purely observational/non-authority metadata MAY be normalized away only by named normalization rules.
- EAE-R9: Every normalization rule MUST be versioned, testable, and included in the EAE record.
- EAE-R10: Unknown connector/tool capabilities MUST be represented explicitly; omission MUST NOT be treated as absence.
- EAE-R11: Discovery failure MUST yield INCOMPLETE/UNKNOWN state, not a valid complete EAE.
- EAE-R12: Secrets MUST NOT enter the EAE artifact; bind secret source/type/slot metadata without credential material.
- EAE-R13: EAE capture MUST distinguish declared capability from observed reachable capability when both are available.
- EAE-R14: A mismatch between declared and observed authority capabilities MUST be retained as evidence and prevent silent qualification transfer.
- EAE-R15: EAE diff MUST classify changes as authority-relevant, authority-irrelevant by explicit normalization, or unresolved.
- EAE-R16: Unresolved changes MUST invalidate automatic transfer.
- EAE-R17: The EAE MUST be bindable into receipts/register entries without circular hashing.
- EAE-R18: Historical EAE artifacts MUST remain immutable and replay-verifiable.

## Connector-drift fixture

Provide a deterministic fixture with C1 and C2 environments.

C1:
- read-only tool A;
- write tool B disabled;
- scope set S1;
- approval required for protected action P.

C2 introduces at least:
- one new write capability or endpoint;
- one scope change;
- one tool-schema change.

Required behavior:
- C1 digest != C2 digest;
- prior C1 qualification does not transfer to C2;
- diff identifies the exact authority-relevant reasons.

Also provide C1' with a benign metadata-only difference that canonical normalization proves authority-equivalent.

## Tests

- deterministic digest;
- ordering-insensitive canonicalization;
- schema change modifies digest;
- permission change modifies digest;
- connector action addition modifies digest;
- approval policy change modifies digest;
- verifier substitution modifies digest;
- benign metadata normalization leaves identity unchanged;
- unknown capability state cannot be serialized as complete;
- secret values are absent from retained EAE;
- declared/observed mismatch is surfaced;
- diff classification is reproducible.

## Acceptance

EAE-A1: C1 vs C2 authority drift changes identity.
EAE-A2: C1 vs C1' benign normalized variation preserves identity.
EAE-A3: Prior qualification is mechanically rejected for mismatched EAE.
EAE-A4: Unknown discovery prevents a complete EAE claim.
EAE-A5: EAE artifacts contain no secret material.
EAE-A6: Independent recomputation from the frozen inputs yields the same digest.

## Deliverables

- EAE schema and domain types;
- canonical serializer/digest;
- collector interface;
- connector/tool capability normalizer;
- diff/classification utility;
- C1/C1'/C2 deterministic fixture;
- tests;
- reviewer documentation.

Dependencies: existing exact-head/revision discipline; connector/harness inventory sources. Consumers: SPEC-ASC-REG-001, SPEC-ASC-QUAL-003, SPEC-ASC-BYPASS-004.
