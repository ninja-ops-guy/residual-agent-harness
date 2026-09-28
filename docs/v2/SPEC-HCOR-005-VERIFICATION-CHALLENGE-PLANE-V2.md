# HCOR-005 — Independent Verification & Challenge Plane

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000

## Objective

Institutionalize the Piston-style pattern: implementation claims never self-close; independent verification and adversarial challenge are separately scheduled, evidence-bound roles.

## Verification requirement

A mission may specify:
- min verifier count;
- independent host/provider/model/harness requirements;
- clean-room reproduction;
- adversarial profile;
- exact-byte artifact transport;
- negative matrix;
- sensitivity controls;
- required receipt schemas.

Scheduler enforces these constraints.

## Candidate admission

A candidate becomes verifiable only after:
- exact artifact bytes received;
- sender digest and recipient digest agree;
- controlling spec/acceptance identities available;
- author checkpoint/receipt preserved;
- candidate generation frozen.

Transport corruption stops verification; verifier never reconstructs guessed source.

## Verifier role

Verifier independently recomputes claims, executes author tests where admissible, adds challenge tests, preserves first failure, and never patches the candidate. A fix is a successor candidate with new digests and fresh verification.

## Challenge coordinator

Optional challenge role asks:
- which PASS depends on self-report?
- what assumptions are untested?
- are paths trusted instead of identities?
- what if host/provider/coordinator dies?
- can artifact transport corrupt?
- can stale authority/results regain control?
- can UI/projection diverge from evidence?

Challenge output creates findings, not direct candidate mutations.

## Adjudication

Station accepts/rejects candidate state based on verifier receipts and mission acceptance contract. Coordinator cannot override a failed required verifier.

## Artifact transport invariant

`CREATED -> SENDER_HASHED -> TRANSPORTED -> RECIPIENT_HASHED -> BYTE_EXACT_VERIFIED -> ADMISSIBLE`.

Semantic/canonical identity may layer above exact-byte evidence but cannot replace transport integrity.

## Negative qualification

Corrupted paste, same-semantic/different-byte artifact, forged verifier receipt, verifier using author workspace, author edits during verification, self-verifier assignment, conflicting verifier results, missing sensitivity control, verifier crash, stale candidate generation, and candidate B overwriting candidate A.

## Qualification target

Run implementation and verification swarms on separate hosts/providers. Inject a plausible false PASS and transport corruption. Both must be caught while valid candidates progress.

**Terminal:** `VERIFICATION_CHALLENGE_PLANE_QUALIFIED`.
