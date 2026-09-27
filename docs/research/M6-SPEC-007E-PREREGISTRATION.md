# M6-SPEC-007E Preregistration — Typed Discovery with Mechanical Repair

M6-SPEC-007D proved the representation fix: typed structured output completed quickly and canonically. Its proposal was rejected for a genuine epistemic error: it claimed `provider_timeout_rate` was missing even though the EvidenceSnapshot measured it at 0.2.

## Question

Can RESIDUAL correct a mechanically rejected typed discovery proposal when given the exact verifier finding, without changing the evidence or weakening admission?

## Preserved

- same aggregate EvidenceSnapshot and raw source-evidence hashes as 007D;
- no supplied improvement question, target metric, intervention, or hypothesis;
- same typed response schema;
- same deterministic admission rules;
- same protected invariant vocabulary;
- human approval remains mandatory;
- independent semantic review occurs only after mechanical admission;
- no implementation or promotion authority.

## Repair loop

At most three Scientist calls are allowed.

Attempt 1 receives only the EvidenceSnapshot.
A later attempt receives:
- the same EvidenceSnapshot;
- the previous typed proposal;
- exact deterministic mechanical errors;
- an instruction to correct only those findings without inventing measurements.

## Success

The experiment succeeds only when:
1. a typed proposal has zero mechanical verifier errors;
2. an independent reviewer approves it;
3. RESIDUAL issues a cryptographic admission receipt.

A mechanically admissible but reviewer-rejected proposal remains a failed experiment and must not advance to M6-008.
