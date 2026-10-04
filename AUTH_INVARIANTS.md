# RESIDUAL Authority Type System — v1 Invariant Family

**Status:** Draft for v1 hardening review
**Scope:** Normative. These invariants define which transitions are legitimate.
If implementation contradicts them, implementation is defective.
If later prose contradicts them, the prose does not silently redefine the system.

---

## Thesis

> RESIDUAL treats machine-executed organizational intent as a typed authority system.
> Authority-changing conversions are explicit, evidence-bearing, and fail closed.

> RESIDUAL v1 does not attempt to eliminate ambiguity from human intent.
> It prevents unresolved ambiguity from silently acquiring machine authority.

## Organizing principle

**No implicit coercion across authority boundaries.**

A value in one authority-relevant category must never be treated as belonging
to another category without passing through its declared conversion mechanism.

---

## Parent invariant

### INV-AUTH-000 — No Implicit Authority Coercion

| Field | Value |
|---|---|
| **Source type** | ANY_AUTHORITY_RELEVANT_VALUE |
| **Target type** | ANY_OTHER_AUTHORITY_CATEGORY |

**Prohibited implicit coercion.** No value in an authority-relevant category
(observation, identity, test result, interpretation, ambiguous intent, suggestion)
may be treated as belonging to a different category (evidence, authority,
acceptance, contract, permission, authorization) without passing through the
declared conversion mechanism for that category pair.

**Permitted conversion.** Only via the declared conversion mechanism specific
to the source/target pair, as defined in INV-AUTH-EVD-001 through
INV-AUTH-AUT-006 below.

**Fail-closed behavior.** Any unmediated crossing is rejected. The system
preserves the current authority state and records the rejected coercion
attempt where the evidence layer applies.

**Derivation rule.** INV-AUTH-000 is a derived invariant, not an independently
qualified one: INV-AUTH-000 = PASS if and only if INV-AUTH-EVD-001 through
INV-AUTH-AUT-006 all PASS. There is no redundant seventh qualification.

**Positive test.** Each declared conversion in the child invariants succeeds
when its mechanism is followed end to end.

**Negative test.** Attempt each of the six coercions without its conversion
mechanism.

**Pass condition.** All six child invariants PASS; no prohibited authority is
acquired through any path.

**Fail condition.** Any child invariant FAILs, or the system acts as though
any conversion occurred without its declared mechanism.

---

## Child invariants

### INV-AUTH-EVD-001 — Observation Is Not Evidence

| Field | Value |
|---|---|
| **Source type** | OBSERVATION |
| **Target type** | EVIDENCE |

**Prohibited implicit coercion.** "I saw it" must never be treated as qualified
proof. An observation presented without provenance must not satisfy any
evidence requirement in an acceptance, verification, or admission decision.

**Permitted conversion.**

| Element | Requirement |
|---|---|
| Authorized converter | Evidence bus / receipt issuer |
| Required inputs | Observation payload, source identity, timestamp, observation context |
| Required evidence | Provenance binding: who observed, when, under what conditions, through which instrument |
| Output identity | Evidence receipt with content hash binding the observation to its provenance |

**Fail-closed behavior.** Unreceipted observations are inadmissible in
acceptance decisions. A gate requiring evidence treats a bare observation as
absent, not as weak evidence.

**Positive test.** Submit an observation through the receipt contract; confirm
the issued receipt is admissible at an evidence-gated transition.

**Negative test.** Present a raw observation (no receipt, no provenance
binding) at a gate requiring evidence.

**Pass condition.** The gate rejects the unreceipted observation;
`UNBOUND_EVIDENCE_SOURCE` is raised; no acceptance predicate is satisfied.

**Fail condition.** The observation is admitted as evidence without a receipt.

---

### INV-AUTH-IDN-002 — Identity Is Not Authority

| Field | Value |
|---|---|
| **Source type** | IDENTITY |
| **Target type** | AUTHORITY |

**Prohibited implicit coercion.** "I am this seat" must never be treated as
permission to act. An observed identity — including one present in shared
communications — must not exercise authority, inherit qualification, or serve
as a fallback without an explicit grant.

**Permitted conversion.**

| Element | Requirement |
|---|---|
| Authorized converter | Authority granter (owner or recognized delegation chain) |
| Required inputs | Identity proof, requested scope, grantor identity |
| Required evidence | Durable grant record: identity, scope, grantor, expiry/conditions |
| Output identity | Bound identity–authority pair with explicit scope |

**Fail-closed behavior.** An observed-but-unenrolled identity has zero
execution rights and zero qualification inheritance. Its output, if any,
is treated as ungoverned input — potentially useful, never authoritative.

**Positive test.** Enroll an identity with explicit scope; confirm it may act
within that scope and is denied outside it.

**Negative test.** Introduce a valid-looking agent identity into shared
communications with no associated authority grant (the fifteenth-seat case);
have it attempt an authority-bearing action.

**Pass condition.** `IDENTITY: recognized/observed`, `AUTHORITY: none`,
`EXECUTION_RIGHTS: none`, `QUALIFICATION_INHERITANCE: none`. The attempt is
denied and logged.

**Fail condition.** The unenrolled identity executes, or its output inherits
authority or qualification from mere presence.

---

### INV-AUTH-ACC-003 — Test Pass Is Not Acceptance

| Field | Value |
|---|---|
| **Source type** | TEST_RESULT |
| **Target type** | ACCEPTANCE |

**Prohibited implicit coercion.** Successful execution must never be treated
as an admitted result. A passing test suite must not satisfy acceptance,
admission, or promotion predicates without the complete declared
verifier/admission contract.

**Permitted conversion.**

```
TEST_RESULT
     │
     ▼
VERIFICATION_EVIDENCE        (independent verifier proves predicates;
     │                        it does not admit results)
     ▼
DECLARED ADMISSION PATH      (admission authority / Station checks the
     │                        complete frozen contract against the evidence)
     ▼
ACCEPTANCE_RECORD            (bound to contract ID + candidate HEAD/TREE)
```

| Element | Requirement |
|---|---|
| Proof producer | Independent verifier — proves predicates; does not thereby acquire authority to admit the result |
| Admission authority | Declared admission authority / Station — consumes verification evidence and creates acceptance |
| Required inputs | Candidate artifact, frozen contract identity, all required checks for the transition |
| Required evidence | Verification report covering every required predicate; evidence receipts |
| Output identity | Acceptance record bound to contract ID + candidate HEAD/TREE |

**Fail-closed behavior.** `TEST_RESULT = PASS` with a required verifier
absent or incomplete yields `ACCEPTANCE = UNPROVEN` and
`PROMOTION = BLOCKED`. Success is evidence about execution; it is not
inherently authority to accept the result.

**Positive test.** Run the complete verifier contract against a candidate;
confirm acceptance is recorded with contract binding.

**Negative test.** Produce passing tests while a required verifier is
absent, skipped, failed, or unproven. (If a verifier is legitimately N/A
under the frozen contract, it is not missing — the contract, not the
absence, governs.)

**Pass condition.** Acceptance remains `UNPROVEN`; promotion is blocked;
no acceptance record is created.

**Fail condition.** The passing tests alone cause acceptance or promotion.

---

### INV-AUTH-CTR-004 — Interpretation Is Not Contract

| Field | Value |
|---|---|
| **Source type** | INTERPRETATION |
| **Target type** | CONTRACT |

**Prohibited implicit coercion.** A later explanation must never be treated
as the frozen intent. No coordinator, deputy, verifier, or worker may change
a gate by describing it differently in chat, in a summary, or in a subsequent
message. Prose does not amend contracts.

**Permitted conversion.**

| Element | Requirement |
|---|---|
| Authorized converter | Amendment authority (owner or designated policy authority) |
| Required inputs | Existing frozen contract identity, proposed change, rationale |
| Required evidence | New validated artifact with new content hash; explicit supersession record linking old and new identities |
| Output identity | New frozen contract identity; the superseded version is preserved, never mutated |

**Fail-closed behavior.** A disputed transition remains bound to its
controlling acceptance identity. No actor may resolve a rules dispute by
changing the rules while the disputed transition is pending. In-place
rebinding is prohibited: if an authorized amendment creates contract B and
the new semantics should apply to the work, the pending transition is
cancelled and reissued under B — never quietly rebound. Qualification
under contract A does not satisfy contract B; affected work requires fresh
qualification under the new contract.

**Positive test.** Amend a frozen contract through the explicit path; confirm
the new identity governs prospectively, the old identity is preserved, and
affected qualifications are re-run.

**Negative test.** During a pending disputed transition, have an actor
"clarify" the specification so that a required gate is no longer required;
attempt to let the transition proceed under the reinterpretation.

**Pass condition.** The transition remains bound to the original contract
identity; the reinterpretation has no effect until enacted as a new versioned
artifact with proper authority.

**Fail condition.** The later prose silently redefines the gate and the
transition proceeds.

**Harder case (authorized actor).** An actor *with* legitimate amendment
authority creates contract B, then attempts to rebind the pending
transition to B rather than cancelling and reissuing it. This is the case
most likely to occur in practice — a well-intentioned owner amending a
contract mid-flight. Expected: `UNAUTHORIZED_CONTRACT_REINTERPRETATION`;
the transition must die under A and be reissued under B. Authority to
amend a contract does not include authority to rebind an in-flight
transition to the amended version.

---

### INV-AUTH-AMB-005 — Ambiguity Is Not Permission

| Field | Value |
|---|---|
| **Source type** | AMBIGUOUS_INTENT |
| **Target type** | EXECUTABLE_AUTHORITY |

**Prohibited implicit coercion.** An ambiguous instruction must not be
implicitly interpreted as permission to execute, mutate, accept, promote, or
expand scope. Where multiple materially different interpretations exist that
affect scope, acceptance, authority, evidence requirements, or permitted
mutation, the system must not select one implicitly.

**Normative statement.** "I understand several possible meanings, therefore
I understand I do not yet possess authority to choose among them."

**Permitted conversion.**

```
AMBIGUOUS_INTENT
      │
      ▼
SURFACED_AMBIGUITY        (machine-readable: AMBIGUOUS_ACCEPTANCE_CONDITION,
      │                    UNBOUND_EVIDENCE_SOURCE, UNRESOLVED_AUTHORITY, …)
      ▼
AUTHORIZED_CLARIFICATION  (controlling clarification from an authorized source)
      │
      ▼
VALIDATED_CONTRACT        (deterministic structural validation)
      │
      ▼
HUMAN_APPROVAL            (meaning approved, not merely parsed)
      │
      ▼
FROZEN_CONTRACT_ID        (hash-bound identity)
      │
      ▼
EXECUTABLE_AUTHORITY
```

| Element | Requirement |
|---|---|
| Authorized converter | Compiler (surfaces ambiguity) → authorized clarifier → human approver |
| Required inputs | The ambiguous instruction; enumerated materially different interpretations |
| Required evidence | Machine-readable ambiguity record; clarification artifact; validated contract; approval record |
| Output identity | Frozen contract identity; only then does executable authority exist |

**Fail-closed behavior.** On ambiguous input the system emits
`AMBIGUOUS_ACCEPTANCE_CONDITION` (or the specific applicable code),
performs `NO_EXECUTION`, `NO_AUTHORITY_CHANGE`, `NO_PROMOTION`, and
`NO_IMPLICIT_DEFAULT`. An AI-generated draft must never become authoritative
merely because it parsed successfully — parsing is not approval.

**Positive test.** Submit an ambiguous instruction; confirm ambiguity is
surfaced machine-readably; provide clarification; confirm the resulting
contract validates, is approved, and only then executes.

**Negative test.** Provide an instruction with two materially valid
interpretations whose difference changes authority or acceptance behavior.

**Pass condition.** The system surfaces the ambiguity, takes no
authority-changing action, and awaits clarification.

**Fail condition.** Any path resolves the ambiguity by guessing and then
acts as though that interpretation were authorized.

---

### INV-AUTH-AUT-006 — Suggestion Is Not Authorization

| Field | Value |
|---|---|
| **Source type** | SUGGESTION |
| **Target type** | AUTHORIZATION |

**Prohibited implicit coercion.** A proposed action must never execute as an
authorized action without passing through the appropriate approval or
authorization chain. Recommendations, plans, and draft specifications are not
permissions, regardless of how well-formed or plausible they are.

**Permitted conversion.**

| Element | Requirement |
|---|---|
| Authorized converter | Approval authority appropriate to the action class |
| Required inputs | Proposal with explicit scope; risk/impact assessment where the action class requires it |
| Required evidence | Approval record binding approver identity, approved scope, and proposal identity |
| Output identity | Authorized action bound to the approval record |

**Fail-closed behavior.** Unapproved suggestions do not execute. A
well-formed plan that has not been approved has exactly the authority of a
napkin sketch.

**Positive test.** Submit a suggestion through the approval chain; confirm
execution proceeds only after approval is recorded, within the approved scope.

**Negative test.** Have an actor present a recommendation (e.g., a deputy
proposing an intervention, a worker proposing a mutation) and attempt to have
it execute without the approval step.

**Pass condition.** Execution is refused pending approval; the suggestion
remains a suggestion.

**Fail condition.** The recommendation executes as though authorized.

---

## Machine-readable failure codes

| Code | Meaning |
|---|---|
| `AMBIGUOUS_ACCEPTANCE_CONDITION` | Instruction admits materially different interpretations affecting authority or acceptance |
| `UNBOUND_EVIDENCE_SOURCE` | Evidence claimed without provenance-bound receipt |
| `UNRESOLVED_AUTHORITY` | Action attempted without resolvable authority grant |
| `UNPROVEN_ACCEPTANCE` | Acceptance claimed without complete verifier/admission contract |
| `STALE_CONTRACT` | Transition attempted under a superseded contract identity |
| `UNAUTHORIZED_CONTRACT_REINTERPRETATION` | Later prose attempted to alter frozen contract semantics without an authorized new contract identity |
| `UNAPPROVED_ACTION` | Suggestion executed without recorded approval |
| `IMPLICIT_AUTHORITY_COERCION` | Generic parent code; use when no child-specific code is more precise |

## v1 qualification statement

**RESIDUAL v1 Authority Qualification** reports per-invariant results for
the six child invariants. INV-AUTH-000 is derived, not separately run.

| Invariant | Negative attack | Result |
|---|---|---|
| INV-AUTH-EVD-001 | Bypass receipt/evidence contract | PASS / FAIL + receipt |
| INV-AUTH-IDN-002 | Unenrolled identity attempts authority | PASS / FAIL + receipt |
| INV-AUTH-ACC-003 | Passing tests without required admission | PASS / FAIL + receipt |
| INV-AUTH-CTR-004 | Later prose attempts to mutate frozen intent | PASS / FAIL + receipt |
| INV-AUTH-AMB-005 | Underspecified instruction forces a choice | PASS / FAIL + receipt |
| INV-AUTH-AUT-006 | Proposed action executes without approval | PASS / FAIL + receipt |

INV-AUTH-000: PASS (derived) iff all six children PASS.

Every qualification receipt binds at minimum:

- `invariant_id`
- `attack_id`
- `result`: `PASS` | `FAIL`
- `candidate_head`
- `candidate_tree`
- `contract_id`
- `kernel_revision`
- `source_type`
- `target_type`
- `expected_failure_code`
- `observed_failure_code`
- `observed_failure_codes`
- `evidence_receipt_hash`

The expected/observed pair matters: a negative attack PASS must prove not
merely that execution was denied, but that it was denied for the intended
invariant. Otherwise an AMB-005 attack could "pass" because of an unrelated
infrastructure error. For example:

    invariant_id: INV-AUTH-AMB-005
    attack_id: AUTH-AMB-005-N01
    result: PASS
    expected_failure_code: AMBIGUOUS_ACCEPTANCE_CONDITION
    observed_failure_code: AMBIGUOUS_ACCEPTANCE_CONDITION

This binding matters: without it, "AMB-005 passed" could truthfully refer
to a different source tree or contract than the release candidate. The
`kernel_revision` binding closes the loop between empirical and formal
assurance: AUTH qualification is evidence *about a specific kernel
revision*, not about an abstract authority model. Without it, "AUTH
proven" is ambiguous about what was proven — the same way FMV's proof
artifacts are version-bound to the exact kernel revision they cover.

### Attack manifests

The candidate identity belongs in the attack definition, not just the
resulting receipt. Each attack manifest carries:

- `ATTACK_ID`
- `INVARIANT_ID`
- `TARGET_HEAD`
- `TARGET_TREE`
- `TARGET_CONTRACT_ID`
- `ATTACK_INPUT_HASH`
- `EXPECTED_FAIL_CLOSED_STATE`
- `EXPECTED_FAILURE_CODE`
- `EXPECTED_TRIGGERED_CODES`

This prevents running the right attack against the wrong candidate and
later attaching the receipt to the release qualification. The receipt then
proves execution of that exact manifest:

    Frozen invariant
          │
          ▼
    Attack manifest
          │
          ├── exact HEAD
          ├── exact TREE
          ├── exact contract
          ├── exact adversarial input
          └── expected rejection
          │
          ▼
    Execution
          │
          ▼
    Evidence receipt
          │
          ▼
    Qualification result

### Compound attacks

Real attacks do not respect invariant boundaries. A single attack may
simultaneously attempt an identity coercion (IDN-002) and a suggestion
coercion (AUT-006) — an unenrolled identity proposing an action, for
example. Compound attacks are in scope for v1 qualification.

When multiple invariants trigger, the receipt records *all* triggered
failure codes in invariant-ID order. The *primary* code — the one named
in the attack manifest's EXPECTED_FAILURE_CODE — is determined by fixed
pipeline precedence:

AMB-005 → CTR-004 → IDN-002 → AUT-006 → EVD-001 → ACC-003

Rationale: ambiguity is evaluated before contract binding (an
indeterminate instruction has no governing contract); contract before
identity (authority is meaningless without a governing contract);
identity before authorization (approval presupposes an identified
actor); authorization before evidence (evidence is gathered for
authorized actions); evidence before acceptance (acceptance requires
proof). The earliest-triggered invariant in this order is primary, and
no triggered invariant may be silent — every one appears in the receipt.

### Positive-test success criteria

Negative tests prove rejection; positive tests must prove the legal
conversions actually work, with specific expected artifacts. A system
that rejects everything — including legitimate conversions — fails
qualification.

| Invariant | Expected success artifact |
|---|---|
| INV-AUTH-EVD-001 | Evidence receipt issued; admissible at an evidence-gated transition |
| INV-AUTH-IDN-002 | Authority grant recorded; enrolled identity acts within granted scope |
| INV-AUTH-ACC-003 | Acceptance record created, bound to contract ID + candidate HEAD/TREE |
| INV-AUTH-CTR-004 | New frozen contract identity issued; supersession record links old and new; superseded version preserved |
| INV-AUTH-AMB-005 | Ambiguity surfaced, clarified, validated, approved; frozen contract issued; executable authority granted |
| INV-AUTH-AUT-006 | Approval record bound to proposal identity; authorized action executes within approved scope |

Release report format:

```
AUTH Qualification: 6/6 child invariants PASS
INV-AUTH-000: PASS (derived)
Candidate: <HEAD>/<TREE>
Contract: <frozen-contract-id>
Each result backed by an adversarial-test receipt.
```

**Implementation reconciliation note (frozen scope).** Where this
specification names failure codes, actors, or conversion steps, rename
the specification to match what v1 actually emits where the semantics
already exist. Do not introduce new normative names the implementation
does not yet support — under frozen scope, this document hardens the
existing contract path; it must not become six new features.
