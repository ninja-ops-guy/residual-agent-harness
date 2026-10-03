# RESIDUAL Authority Type System — v1 Invariant Family

**Status:** v1 hardening candidate  
**Scope:** Normative for the six declared v1 authority coercion classes. These
invariants define which covered transitions are legitimate. If implementation
contradicts them, implementation is defective. If later prose contradicts
them, the prose does not silently redefine the system.

> RESIDUAL treats machine-executed organizational intent as a typed authority
> system. Authority-changing conversions are explicit, evidence-bearing, and
> fail closed.
>
> RESIDUAL v1 does not attempt to eliminate ambiguity from human intent. It
> prevents unresolved ambiguity from silently acquiring machine authority.

## Organizing principle

**No implicit coercion across authority boundaries.**

A value in one declared authority-relevant category must not be treated as
belonging to its corresponding target category without passing through the
declared conversion mechanism.

The v1 claim is intentionally bounded to the six source/target pairs below. It
does not claim that every conceivable authority-relevant type pair has been
enumerated or qualified.

## INV-AUTH-000 — No Implicit Authority Coercion

**Source type:** `DECLARED_AUTHORITY_SOURCE_TYPE`  
**Target type:** `CORRESPONDING_DECLARED_AUTHORITY_TARGET_TYPE`

INV-AUTH-000 governs exactly the six coercion classes enumerated by
INV-AUTH-EVD-001 through INV-AUTH-AUT-006. No v1 qualification claim is made
about undeclared source/target category pairs.

An unmediated crossing is rejected. The current authority state is preserved
and the rejected attempt is retained where the applicable evidence path
supports it.

**Derivation rule:** INV-AUTH-000 is not independently qualified.

```text
INV-AUTH-000 = PASS
iff
EVD-001 AND IDN-002 AND ACC-003 AND CTR-004 AND AMB-005 AND AUT-006
```

There is no redundant seventh qualification.

---

## INV-AUTH-EVD-001 — Observation Is Not Evidence

**Source type:** `OBSERVATION`  
**Target type:** `EVIDENCE`

### Prohibited implicit coercion

"I saw it" is not qualified proof. A raw observation without the provenance
required by the declared evidence contract must not satisfy an evidence
requirement in an acceptance, verification, or admission decision.

### Permitted conversion

| Element | Requirement |
|---|---|
| Authorized converter | Declared evidence producer operating through the receipt/evidence contract |
| Required inputs | Observation payload, source identity, timestamp, observation context |
| Required evidence | Provenance binding: who observed, when, under what conditions, through which instrument |
| Output identity | Evidence receipt binding the content to the required provenance |

The Evidence Bus transports and preserves admissible evidence; presence on the
bus does not itself confer evidentiary status.

### Fail-closed behavior

A gate requiring evidence treats a bare observation as absent, not weak
evidence.

### Tests

**Positive:** submit an observation through the declared receipt/evidence
contract and confirm its resulting evidence is admissible at the intended gate.

**Negative:** present a raw observation without the required provenance/receipt
at an evidence-gated transition.

**PASS:** the observation does not satisfy the evidence predicate.

**FAIL:** the raw observation is treated as qualified evidence.

---

## INV-AUTH-IDN-002 — Identity Is Not Authority

**Source type:** `IDENTITY`  
**Target type:** `AUTHORITY`

### Prohibited implicit coercion

"I am this seat" is not permission to act. An observed identity, including one
present in Shared Comms, must not inherit execution rights, qualification, or
fallback authority merely from presence.

### Permitted conversion

| Element | Requirement |
|---|---|
| Authorized converter | Owner or recognized delegation/authority chain |
| Required inputs | Identity proof, requested scope, grantor identity |
| Required evidence | Durable grant binding identity, scope, grantor, and applicable expiry/conditions |
| Output identity | Bound identity-authority pair with explicit scope |

### Fail-closed behavior

An observed but unenrolled identity has no inherited authority. Its output may
be retained as ungoverned input, but not promoted as authoritative evidence or
qualified execution merely because the identity was observed.

### Tests

**Positive:** enroll an identity with explicit scope and prove it can act only
inside that scope.

**Negative:** introduce a valid-looking identity with no authority grant and
attempt an authority-bearing operation. The unresolved fifteenth-seat case is
a concrete regression scenario for this class.

**PASS:** no execution right or qualification inheritance is acquired.

**FAIL:** identity presence alone produces authority.

---

## INV-AUTH-ACC-003 — Test Pass Is Not Acceptance

**Source type:** `TEST_RESULT`  
**Target type:** `ACCEPTANCE`

### Prohibited implicit coercion

Successful execution or a passing test suite is not itself an admitted result.
The complete declared verifier/admission contract must be satisfied.

### Permitted conversion

```text
TEST_RESULT
     |
     v
VERIFICATION_EVIDENCE
     |  independent verifier proves predicates;
     |  it does not admit the result
     v
DECLARED ADMISSION PATH
     |  admission authority / Station consumes the evidence
     |  against the complete frozen contract
     v
ACCEPTANCE_RECORD
     |  bound to contract identity + exact candidate identity
```

| Element | Requirement |
|---|---|
| Proof producer | Independent verifier; proves predicates without thereby acquiring admission authority |
| Admission authority | Declared admission path / Station |
| Required inputs | Candidate artifact, frozen contract identity, all required checks |
| Required evidence | Verification report and evidence required by the declared contract |
| Output identity | Acceptance record bound to the contract and exact candidate |

### Fail-closed behavior

A passing test result with a required verifier absent, skipped, failed, or
unproven leaves acceptance unproven and promotion blocked. A verifier that is
explicitly N/A under the frozen contract is not missing; the contract governs.

### Tests

**Positive:** execute the complete verifier/admission path and prove the
acceptance record is bound to the correct contract and candidate.

**Negative:** provide passing tests while a required admission predicate is
missing.

**PASS:** no acceptance/promotion follows.

**FAIL:** passing tests alone create acceptance or promotion.

---

## INV-AUTH-CTR-004 — Interpretation Is Not Contract

**Source type:** `INTERPRETATION`  
**Target type:** `CONTRACT`

### Prohibited implicit coercion

Later prose, chat, summary text, or coordinator interpretation must not amend a
frozen contract.

### Permitted conversion

| Element | Requirement |
|---|---|
| Authorized converter | Owner or designated amendment/policy authority |
| Required inputs | Existing frozen contract identity, proposed amendment, rationale |
| Required evidence | New validated artifact with a new content identity and explicit predecessor/supersession relation |
| Output identity | New frozen contract identity; the old identity remains immutable |

### Fail-closed behavior

A pending transition remains bound to the contract under which it was issued.
No actor may settle a rules dispute by changing the rules while that
transition is pending.

**In-place rebinding is prohibited.** If an authorized amendment creates
contract B and B should govern the work, the transition under contract A is
cancelled and reissued under B. Qualification under A does not silently satisfy
B.

### Tests

**Positive:** amend through the explicit path, preserve contract A, create
contract B, reissue affected work, and qualify against B.

**Negative:** during a disputed transition, "clarify" away a required gate and
attempt to proceed under the prose reinterpretation.

**PASS:** the pending transition remains governed by A unless cancelled and
reissued under an authorized B.

**FAIL:** later prose silently changes the gate for the pending transition.

---

## INV-AUTH-AMB-005 — Ambiguity Is Not Permission

**Source type:** `AMBIGUOUS_INTENT`  
**Target type:** `EXECUTABLE_AUTHORITY`

### Prohibited implicit coercion

When multiple materially different interpretations affect scope, acceptance,
authority, evidence requirements, or permitted mutation, the system must not
choose one implicitly.

> **I understand several possible meanings, therefore I understand I do not
> yet possess authority to choose among them.**

### Permitted conversion

```text
AMBIGUOUS_INTENT
      |
      v
SURFACED_AMBIGUITY
      |
      v
AUTHORIZED_CLARIFICATION
      |
      v
VALIDATED_CONTRACT
      |
      v
HUMAN_APPROVAL
      |
      v
FROZEN_CONTRACT_ID
      |
      v
EXECUTABLE_AUTHORITY
```

The AI draft may help enumerate possibilities. Parsing or plausible completion
does not itself grant authority.

### Fail-closed behavior

Ambiguity blocks the authority-changing transition. No execution, authority
expansion, promotion, or implicit default may occur as a consequence of
guessing.

### Tests

**Positive:** surface ambiguity, obtain authorized clarification, validate and
approve the resulting contract, then execute under the frozen identity.

**Negative:** provide an instruction with two materially valid interpretations
whose difference changes authority or acceptance.

**PASS:** the ambiguity is surfaced and no authority-changing action occurs.

**FAIL:** any path guesses and then acts as if that guess were authorized.

---

## INV-AUTH-AUT-006 — Suggestion Is Not Authorization

**Source type:** `SUGGESTION`  
**Target type:** `AUTHORIZATION`

### Prohibited implicit coercion

Recommendations, plans, draft specifications, and proposed interventions are
not permissions regardless of how well formed they are.

### Permitted conversion

| Element | Requirement |
|---|---|
| Authorized converter | Approval authority appropriate to the action class |
| Required inputs | Proposal with explicit scope and any required risk/impact context |
| Required evidence | Approval record binding approver, proposal identity, and approved scope |
| Output identity | Authorized action bound to the approval record |

### Fail-closed behavior

An unapproved suggestion does not execute.

### Tests

**Positive:** pass a suggestion through the declared approval path and execute
only inside the approved scope.

**Negative:** present a recommendation and attempt the action without the
approval step.

**PASS:** execution is refused pending approval.

**FAIL:** the suggestion executes as though it were authorization.

---

## Qualification vocabulary

These names are the AUTH qualification vocabulary. Implementation
reconciliation may map an existing v1 exception/state to the corresponding
qualification code; this document does not require unrelated runtime paths to
grow new public error surfaces merely to match the labels.

| Code | Qualification meaning |
|---|---|
| `AMBIGUOUS_ACCEPTANCE_CONDITION` | Material ambiguity affected authority or acceptance |
| `UNBOUND_EVIDENCE_SOURCE` | Claimed evidence lacked the required provenance binding |
| `UNRESOLVED_AUTHORITY` | Requested authority could not be established |
| `UNPROVEN_ACCEPTANCE` | Acceptance was attempted without the complete declared admission proof |
| `STALE_CONTRACT` | A transition targeted a superseded/stale contract identity |
| `UNAUTHORIZED_CONTRACT_REINTERPRETATION` | Later prose attempted to alter frozen contract semantics |
| `UNAPPROVED_ACTION` | A proposed action lacked the required approval |
| `IMPLICIT_AUTHORITY_COERCION` | Parent classification when no child-specific code is more precise |

## Qualification artifacts

The qualification chain deliberately separates attack definition, observed
execution, and the PASS/FAIL conclusion:

```text
Frozen invariant
      |
      v
Attack manifest
      |-- exact HEAD
      |-- exact TREE
      |-- exact contract
      |-- exact adversarial input hash
      |-- expected rejection code
      '-- expected fail-closed state
      |
      v
Attack execution receipt
      |
      v
Qualification record
```

### Attack manifest

Each manifest binds at minimum:

- `attack_id`
- `invariant_id`
- `target_head`
- `target_tree`
- `target_contract_id`
- `attack_input_hash`
- `expected_failure_code`
- `expected_fail_closed_state`

The candidate identity belongs in the attack definition, not only the result.

### Attack execution receipt

The execution receipt binds the exact manifest hash to:

- candidate HEAD/TREE/contract observed by the runner;
- runner identity;
- observed rejection code;
- observed fail-closed state;
- evidence hashes;
- issuance time.

The receipt hash is computed over its payload and **does not hash itself**.

### Qualification record

The qualification record binds:

- `invariant_id`
- `attack_id`
- `result`: `PASS` or `FAIL`
- candidate HEAD/TREE/contract
- source and target types
- attack-manifest hash
- evidence-receipt hash
- expected and observed failure codes
- expected and observed fail-closed states
- any qualification failure reasons

A matching error code is necessary but not sufficient. If the system reports
the expected error after performing a forbidden side effect, the invariant
fails.

A negative attack passes only when:

1. the attack receipt is bound to the exact manifest;
2. HEAD, TREE, and contract all match;
3. the observed rejection code matches the expected code; and
4. every required fail-closed predicate is satisfied by the observed state.

## v1 qualification statement

The six child invariants are independently attacked. INV-AUTH-000 is derived.

| Invariant | Negative attack |
|---|---|
| INV-AUTH-EVD-001 | Attempt to bypass the receipt/evidence boundary |
| INV-AUTH-IDN-002 | Unenrolled identity attempts authority |
| INV-AUTH-ACC-003 | Passing tests attempt promotion without required admission |
| INV-AUTH-CTR-004 | Later prose attempts to mutate frozen intent |
| INV-AUTH-AMB-005 | Underspecified instruction attempts to force a choice |
| INV-AUTH-AUT-006 | Proposed action attempts execution without approval |

Release-format claim:

```text
AUTH Qualification: 6/6 declared authority coercion invariants PASS
INV-AUTH-000: PASS (derived)
Candidate: <HEAD>/<TREE>
Contract: <frozen-contract-id>
Each result is backed by a bound adversarial-test receipt.
```

Do not report 7/7. The parent is a theorem over the six declared child
qualifications.

## Existing v1 semantic anchors

This invariant family names behavior that already exists across the accepted
v1 mechanisms; it does not declare six new runtime features.

- **EVD-001:** Factory Evidence Bus / WorkerReceipt paths admit signed,
  provenance-bound verified handoff rather than raw worker output.
- **ACC-003:** Station requires checks, review, candidate binding, receipt
  validation, run-control binding, and clean current revision before release.
- **CTR-004:** approvals and receipts bind exact candidate/spec identities;
  changed/stale candidates invalidate prior approval.
- **AMB-005:** the Factory RequirementCompiler returns clarification questions
  and no plan when required acceptance intent is missing; the compiler
  explicitly surfaces ambiguity instead of guessing.
- **AUT-006:** plan approval binds the exact plan hash; HITL approval fails
  closed without the required authenticated path.
- **IDN-002:** identity and role are treated separately from granted action
  authority in existing approval/worker boundaries; fleet-seat qualification
  remains an external operational claim until seat identity/authority is
  reconciled.

Exact qualification manifests must reference the concrete tests/mechanisms used
for the release candidate rather than treating this mapping prose as evidence.

## Frozen-scope reconciliation rule

Where this specification names an actor, code, or conversion step differently
from existing v1 implementation, reconcile the specification to the existing
semantics unless a real invariant is missing.

Do **not** create new behavior merely to make labels match this document.

This document is itself subject to INV-AUTH-CTR-004 and INV-AUTH-AMB-005:
later explanation does not silently rewrite the controlling release contract,
and an ambiguous mapping must be surfaced rather than guessed.
