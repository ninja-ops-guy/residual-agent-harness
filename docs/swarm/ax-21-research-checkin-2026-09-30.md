# AX-21 / RESIDUAL research check-in — 2026-09-30

Status: append-only research maintenance record. This document does not modify frozen AX-21 evidence, authorize deployment, qualify a release, or convert draft/component evidence into whole-system claims.

## Evidence discipline

This check-in separates observed repository/CI evidence, reported-but-not-yet-admitted evidence, interpretation, and proposed follow-up work. Successful checks remain bounded evidence. Negative and inconclusive results are preserved rather than normalized into later PASS states.

## Current release boundary

- Accepted `main` remains `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.
- No formal GitHub release exists at this check-in.
- PR #349 remains draft/open, so there is no new valid P5 after-condition.
- PR #404 remains draft/open and explicitly incomplete for several live mesh qualification dimensions.
- Nothing in this record establishes release readiness, MESH_QUALIFIED, physical F6 success, or whole-system security/autonomy.

## A. Project inference budget vs provider health

Source: PR #492.

Observed during OpenClaw Swarm Onboarding R0.1:

- total model calls: 44 / 100
- cloud model calls: 30 / 30
- request bytes: 213,854 / 5,000,000
- provider/gateway path reported healthy

The blocking condition was a RESIDUAL project cloud-call ceiling, while the prior operator-facing message was generic enough to resemble a provider problem.

### Research result

A local authority/budget failure and a provider-health failure are not interchangeable evidence classes.

### Falsified hypothesis

A generic model-budget exhaustion message is sufficient to infer provider quota or provider unavailability.

### Operator intervention

Increasing the project ceiling is an explicit authenticated operator action and should be counted in human-intervention metrics.

### Candidates

- `RES-UP-BUDGET-FAILURE-PROVENANCE-001`
- `EXP-BUDGET-VS-PROVIDER-01`

## B. Attempt-scoped execution authority lifecycle failure

Source: PR #493.

A DELL qualification attempt admitted an execution budget, later expired without result reconciliation, and recovery retained predecessor budget state. A successor claim obtained fresh task authority but was then blocked by retained predecessor execution-budget state before OpenClaw execution.

The same frozen reproduction failed before the repair and passed after the successor repair.

Measurements retained in #493:

- focused: 22 passed, 22 subtests
- Station: 91 passed
- qualification: 119 passed
- affected suites: 210 passed, 26 subtests
- whole Python suite: 2,009 passed, 37 failed, 413 subtests
- all 37 whole-suite failures reproduced on untouched accepted main and untouched #404
- independent reviewer rerun: 58 passed, no blocking findings
- hosted Qualification-v1 and the major surrounding technical workflows: PASS
- live DELL qualification: still pending
- maintainer exact-head authority: still pending

A preservation limitation is also retained: the original first-run log bytes were lost with the workspace; a historical digest remains, and the frozen test was rerun on untouched source. The later baseline reproduction is not represented as the lost original.

### Research result

Attempt authority is transition-bound, not merely task-bound. Advancing a lease/fence does not automatically advance every related authority object.

The episode also showed that a specific server-side denial can become a generic client/operator failure if typed failure provenance is not preserved end-to-end.

### Non-claims

The repair does not establish provider-side exactly-once execution or fully atomic provider-I/O/result acceptance.

### Candidates

- `RES-UP-ATTEMPT-AUTHORITY-LIFECYCLE-001`
- `RES-UP-FAILURE-CODE-PRESERVATION-001`
- `RES-UP-NEGATIVE-EVIDENCE-DURABILITY-001`
- `EXP-ATTEMPT-BOUNDARY-MATRIX-01`

## C. Dogfood campaign now has a falsifiable autonomy oracle

Source: PR #490.

The preregistered DELL campaign is:

`C0 -> A1 -> A2 -> COMMS1 -> FAIL1 -> REC1 -> DOCTOR1`

It requires a durable runner-qualification receipt before C0, retains a separate owner gate for live-provider degradation, stops on first failure, and forbids retry-until-green.

The core campaign oracle says that after each authoritative parent Station dispatch, Kimi/owner/chat may observe or relay evidence but may not be the mechanism that wakes a claw, advances the workflow, assigns successors, or handles deadlines. The terminal campaign requires zero manual Kimi routing after each parent dispatch.

### Interpretation

This is not evidence that the swarm is autonomous. It is a better measurement contract for a future autonomy claim.

### Candidates

- `RES-UP-OPERATOR-INTERVENTION-LEDGER-001`
- `EXP-OWNER-ABSENCE-01` after the required prerequisites are admitted

## D. Doctor corpus independent review includes a sensitivity control

Source: PR #495 discussion.

Recorded September 30 evidence:

- Scout/DBOX reproduced 57 / 57 checks
- 46 / 46 manifest files reported byte-exact
- two consecutive full runs reported identical output hashes and logical-clock behavior
- a targeted weakening of one forbidden-misclassification assertion produced exactly one expected failure: 56 / 57

The ledger explicitly did not promote the full capability to ready; runtime wiring, scheduler integration, deployment, and live qualification remain open.

### Research result

The targeted mutation provides bounded evidence that the verifier is discriminative for that mutation. It is stronger than replaying PASS alone, but it does not establish comprehensive detector sensitivity.

### Candidates

- `RES-UP-VERIFIER-SENSITIVITY-MATRIX-001`
- `EXP-DOCTOR-MUTATION-SERIES-01`

## E. Reported external review remains distinct from admissible review authority

Source: PR #495.

The integration ledger preserves a reported external review PASS for the #489 candidate and cites review artifacts, while also recording that the original host-bound review bytes/full digests still need local verification and binding before new integration admission.

### Research result

Two different propositions remain separate:

1. absence of a GitHub-native review does not prove that no external review occurred;
2. a reported external PASS does not automatically become admissible evidence for a new integration decision.

### Candidate

- `RES-UP-EXTERNAL-REVIEW-ADMISSION-001`

## F. Secret-scanner fixture repair reached a technically green successor

Source: PR #491.

The prior false-positive class involved the detector's own synthetic fixture. The narrow successor changes the fixture representation while preserving the detector's positive control.

The tracked-secret guard and surrounding major technical workflows are green on the exact successor head. Independent review remains required.

### Interpretation

This closes the narrow fixture-reproduction loop only. It is not evidence that historical credentials never existed or that any historical credential was revoked.

## G. Execution-substrate authority work separates evidence integrity from authority, then exposes a lifecycle inconsistency

Sources: PRs #498, #499, #500.

#498 introduces a post-v1 qualification tuple that binds execution-substrate identity and environment context.

#499 makes a further distinction mechanical: a valid qualification record is evidence, while trusted Station admission is authority. Evidence-only records remain inspectable but do not grant execution capability.

#500 extends the model with freshness, revocation, key rotation, predecessor retirement, distrust, and re-admission. Its current exact head is not qualified: aggregate Qualification-v1, Command Station, and controller/provider workflows are red, while many neighboring gates remain green.

The retained first failure occurs in the key-rotation/re-admission test because the existing admission-bundle uniqueness rule rejects the intended old/new admission pair before lifecycle resolution can occur.

### Falsified hypothesis

The earlier admission uniqueness rule is automatically compatible with later re-admission semantics under key rotation.

### Research result

An invariant can be valid in one lifecycle and become over-constraining when a later lifecycle introduces a legitimate second authority dimension.

This does not establish that the proposed lifecycle model is secure or insecure. It establishes that the current candidate representation and intended lifecycle semantics are inconsistent.

### Candidates

- `RES-UP-AUTH-READMISSION-SEMANTICS-001`
- `RES-UP-INVARIANT-LIFECYCLE-COMPAT-001`
- `EXP-AUTH-ROTATION-READMISSION-01`

## H. Single-Station autonomy remains a specification target, not an observed result

Source: PR #495.

The program-level target now explicitly distinguishes specification, isolated implementation, independent review, integration, bounded deployment, and live qualification.

The proposed end state includes `SINGLE_STATION_AUTONOMY_QUALIFIED` followed by an `OWNER_ABSENT_8H` condition with zero manual interventions and no lost/duplicate accepted work, stale authority acceptance, unexplained runnable-seat idleness, or missed native deadlines.

Those conditions have not been demonstrated in this cycle.

## Comparison with frozen / pre-release AX-21

The older continuity baseline remains a useful control:

- R0 preserved a negative result where an unknown failure-domain route still produced one adapter call despite a persistent quota circuit.
- R2 later passed 215 tests with zero failures/errors/skips but explicitly limited its verdict to sandbox/bootstrap scope, excluding actual WSL/systemd, real-model, production Station, live deployment, and independent security-review claims.

Relative to that baseline, this cycle adds:

- a measured live swarm budget/authority observation;
- a reproduced control-plane attempt-lifecycle failure;
- an independent verifier sensitivity mutation;
- a new authority-lifecycle candidate failure.

These are meaningful extensions of the evidence corpus, but they do not erase the baseline's scope limits.

## Paper-relevant conclusions

1. Local authority/budget failure and provider failure must remain separate evidence classes.
2. Authority is lifecycle- and attempt-bound, not only object-bound.
3. Failure taxonomy is part of the research apparatus; typed causes must survive transport and UI layers.
4. Verifier confidence is stronger when a controlled weakening changes the expected verdict.
5. Evidence integrity and execution authority are distinct properties.
6. Earlier invariants require requalification when the lifecycle acquires new dimensions.
7. Autonomy claims require explicit intervention denominators, not narrative impressions.
8. Negative evidence should remain immutable across repairs and successor generations.

## Non-claims

This check-in does not establish general RESIDUAL security, general alignment/corrigibility, fleet-wide failover correctness, provider-side exactly-once behavior, live provider production reliability, MESH_QUALIFIED, DELL runner qualification, single-Station autonomy, owner-absence success, physical F6 success, P5 operator-friction improvement, release readiness, or sustained autonomous recursive development.

## Research-maintenance queue

Priority candidates:

1. `EXP-ATTEMPT-BOUNDARY-MATRIX-01`
2. `EXP-BUDGET-VS-PROVIDER-01`
3. `EXP-DOCTOR-MUTATION-SERIES-01`
4. `EXP-AUTH-ROTATION-READMISSION-01`
5. `EXP-OWNER-ABSENCE-01` after prerequisites are admitted
6. `RES-UP-OPERATOR-INTERVENTION-LEDGER-001`
7. `RES-UP-EXTERNAL-REVIEW-ADMISSION-001`
8. `RES-UP-NEGATIVE-EVIDENCE-DURABILITY-001`

Material evidence changed, so a new append-only record is warranted. This file is documentation-only and does not approve implementation PRs or transfer their evidence/authority to another exact head.
