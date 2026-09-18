# DG-001..003 Preregistration — Canonical Derivation Controls

## DG-001 — canonical root

Construct semantically identical DAGs in different insertion orders.

Expected:
- identical node IDs;
- identical edge IDs;
- identical graph root.

Change one semantic payload byte.

Expected:
- changed node ID;
- changed graph root.

## DG-002 — localized challenge propagation

Construct two findings sharing one evidence ancestor.

Challenge only branch A's semantic-review node.

Expected:
- challenged review becomes CHALLENGED;
- branch A dependent finding becomes CHALLENGED;
- branch B remains VALID;
- shared evidence remains VALID;
- historical nodes remain present.

## DG-003 — badly framed experiment

Construct an ImprovementSpec that is mechanically complete and human co-signed but claims p99 tail-latency improvement while verifying only a mean metric.

Expected:
- deterministic graph/provenance structure remains valid as a historical record;
- semantic invariant/reviewer nodes fail;
- ImprovementSpec admission predicate returns false.

Positive control:
- a complete p99-grounded synthetic ImprovementSpec with PASS invariant/environment, VALID semantic review, and exact Human COSIGN satisfies the admission predicate.

## Claim boundary

These controls test formal graph predicates and admission logic only. They do not establish scientific truth or model reliability.
