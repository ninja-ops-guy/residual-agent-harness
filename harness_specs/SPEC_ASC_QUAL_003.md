# SPEC-ASC-QUAL-003 — Authority Surface Completeness Qualification

Status: research candidate / execution-ready after owner review
Program: ASC-001 (#525)
Normative scope: research qualification only; not normative for v1

## Purpose

Define the bounded qualification procedure that turns an Authority Surface Register and Effective Authority Environment into a reproducible claim about mediation coverage.

The goal is not to prove universal absence of bypasses. The goal is to make the claimed boundary explicit, challenge it independently, and prevent silent gaps from being labeled complete.

## Allowed verdicts

- PASS_BOUNDED
- FAIL
- INCOMPLETE_UNMAPPED
- INCOMPLETE_NOT_TESTED

There is no generic PASS.

## Qualification inputs

A qualification run MUST freeze:

- source commit/tree;
- ASC register + digest;
- EAE + digest;
- declared qualification boundary;
- discovery/enumeration tool revisions;
- bypass manifest revision;
- verifier identity/revision/config;
- independent reviewer identity or independent review artifact;
- fixtures/corpus;
- time-bounded external capability observations when relevant.

## Enumeration method

QUAL-R1: Enumeration MUST combine static source/contract review with runtime capability/route discovery where applicable.
QUAL-R2: State-machine transitions MUST be enumerated independently of worker narrative.
QUAL-R3: Connector/harness capabilities MUST be compared to registered transitions.
QUAL-R4: Recovery/restart/replay paths MUST be inspected as separate potential authority routes.
QUAL-R5: Alternate routes to the same protected effect MUST be represented or proven to share the same mediator.
QUAL-R6: Negative-space review MUST explicitly ask which protected effects can be reached without an existing register entry.
QUAL-R7: Independent review MUST include at least one challenge not selected by the implementation author.

## Seeded omission challenge

Implement a deterministic qualification fixture that contains a deliberately omitted authority path.

Rules:
- the omission MUST plausibly reach a protected effect;
- implementation-side expected register MUST not disclose the hidden path to the reviewer/enumerator under test;
- an independent oracle fixture MAY retain the hidden answer;
- a completeness claim that misses the seeded path MUST NOT produce PASS_BOUNDED;
- detection quality MUST be reported, not hidden.

At least three omission classes are required over time:
1. alternate endpoint/route;
2. restart/recovery path;
3. connector/tool capability added outside the nominal source tree.

## Trace states

For each adversarial or qualification case, preserve distinct states:

- REQUESTED
- ATTEMPTED
- EXECUTED
- ACCEPTED
- EFFECT_OBSERVED

QUAL-R8: These states MUST NOT be collapsed into one boolean.
QUAL-R9: A denied request may be ATTEMPTED without EXECUTED.
QUAL-R10: EXECUTED is not equivalent to ACCEPTED.
QUAL-R11: ACCEPTED without independently supported authority is a failure even if no external effect occurred.
QUAL-R12: EFFECT_OBSERVED without authorized mediation is a failure regardless of later rollback.

## Evidence requirements

QUAL-R13: Every COVERED transition MUST bind positive-path evidence.
QUAL-R14: Every applicable bypass class MUST bind negative-path evidence or explicit NOT_TESTED disposition.
QUAL-R15: Evidence MUST be candidate/tree and EAE-bound.
QUAL-R16: Failed/aborted test attempts remain in the retained record.
QUAL-R17: First-failure evidence MUST NOT be overwritten by a green rerun.
QUAL-R18: Independent review MUST recompute digests rather than trusting stated values.
QUAL-R19: Reviewer conclusions MUST be separable from implementation-author conclusions.

## Qualification receipt

Emit a machine-readable and human-readable `AuthoritySurfaceQualificationReceipt` containing at least:

- receipt schema version;
- source commit/tree;
- boundary description + digest;
- EAE digest;
- register digest;
- bypass manifest digest;
- discovery method/tool revisions;
- transition count by coverage state;
- case count by trace state and result;
- unauthorized protected-effect count;
- unresolved UNMAPPED list;
- unresolved NOT_TESTED list;
- independent review reference;
- evidence bundle digest;
- verdict;
- explicit residual unknowns;
- claim text permitted by that verdict.

## Verdict rules

### PASS_BOUNDED
Requires:
- zero unauthorized protected effects in the frozen campaign;
- no plausible UNMAPPED path to protected effects;
- all required cases executed or justified under the boundary;
- independent review reproduces the verdict;
- no candidate/EAE mismatch;
- no worker/model assertion independently creates authoritative ACCEPTED state.

### FAIL
Any demonstrated unauthorized protected effect, unauthorized accepted authority transition, invalid authority transfer, or corrupted evidence chain.

### INCOMPLETE_UNMAPPED
At least one plausible authority path to a protected effect remains UNMAPPED.

### INCOMPLETE_NOT_TESTED
Known required paths exist but required test evidence is absent, without a demonstrated failure.

## Tests

- hidden seeded omission prevents PASS_BOUNDED;
- complete fixture yields PASS_BOUNDED;
- unauthorized ACCEPTED without effect yields FAIL;
- unauthorized effect yields FAIL;
- EAE mismatch prevents verdict transfer;
- first failed attempt remains visible after rerun;
- missing independent review prevents PASS_BOUNDED;
- NOT_TESTED vs UNMAPPED remain distinct;
- receipt digest reproducibility;
- altered evidence bundle breaks receipt verification.

## Acceptance

QUAL-A1: Independent reviewer detects the initial seeded omission fixture.
QUAL-A2: Removing/fixing the omission allows the bounded fixture to qualify without changing verdict rules.
QUAL-A3: A synthetic unauthorized accepted transition produces FAIL even with zero external effect.
QUAL-A4: An EAE drift fixture invalidates prior qualification.
QUAL-A5: Receipt can be independently recomputed from retained artifacts.
QUAL-A6: No generic PASS can be emitted by schema or CLI.

## Deliverables

- qualification engine/evaluator;
- seeded omission fixtures;
- qualification receipt schema;
- independent-review CLI or procedure;
- evidence bundle verifier;
- tests and traceability table.

Dependencies: SPEC-ASC-REG-001, SPEC-ASC-EAE-002, SPEC-ASC-BYPASS-004.
