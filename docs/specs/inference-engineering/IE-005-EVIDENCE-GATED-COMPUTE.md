# IE-005 — Evidence-Gated Compute Ladder and Speculative Escalation

Status: proposed implementation contract  
Prerequisites: qualified IE-001 prototype / #160; accepted IE-002 telemetry / #161; IE-003 pressure controls SHOULD be available before default-on rollout

## 1. Objective

Formalize RESIDUAL's existing local-solver/local-model/expert progression into an explicit evidence-gated compute ladder so expensive computation is invoked only when cheaper bounded computation fails to produce independently acceptable work.

The model remains proposal compute. Verifier/host acceptance remains authority.

## 2. Existing architecture preserved

RESIDUAL already supports local solving, bounded local-model work, residual delegation to an expert, verifier feedback, budgets and provider routing.

IE-005 SHALL turn that progression into an explicit policy/state machine. It MUST NOT create a second verifier, bypass residual delegation, or allow a model tier to self-certify success.

## 3. Tier model

A deployment MAY configure a subset of tiers such as:

- Tier 0 — deterministic/tool/local solver;
- Tier 1 — cheap/local model;
- Tier 2 — bounded remote or stronger model;
- Tier 3 — pair/ensemble/swarm topology;
- Tier 4 — human/HITL escalation.

Tier names are configuration labels, not universal capability rankings.

Each tier definition SHALL bind:

- eligible task/assurance classes;
- engine/provider selector or topology policy;
- placement/privacy requirements;
- max attempts;
- per-attempt and cumulative budgets;
- deadline/latency policy;
- escalation conditions;
- whether speculative prelaunch is permitted.

## 4. Acceptance rule

Only the existing independent verifier/acceptance path can terminate an obligation as accepted.

Tier outcomes map as follows:

- verifier PASS → accept through normal authority; stop sequential escalation;
- verifier FAIL → preserve counterexample; escalate only if policy/budget permits;
- verifier UNKNOWN → preserve UNKNOWN/evidence gap; escalate only if policy permits;
- malformed/provider/transport failure → typed failure; may escalate according to policy but never becomes PASS;
- abstention → unresolved; may escalate according to policy.

Escalation MUST preserve accepted independent work and transfer only the unresolved residual/evidence needed by the next tier.

## 5. Sequential mode

Sequential escalation SHALL be the default v1 policy.

The next tier MUST NOT dispatch until the previous tier reaches a policy-recognized terminal/unresolved condition.

If a cheaper tier receives verifier PASS, more expensive tiers MUST NOT be started merely to seek a "better" answer.

## 6. Speculative mode

Optional speculative prelaunch MAY be enabled for explicitly latency-sensitive policies after sequential mode is qualified.

Speculative mode MUST define:

- which later tier may prelaunch;
- delay/trigger before prelaunch;
- budget reservation before every provider dispatch;
- cancellation behavior when an earlier candidate is accepted;
- late-result handling;
- accounting for work already dispatched even if later canceled.

Cancellation MUST NOT be assumed to eliminate provider cost. Failed/canceled calls retain whatever budget/accounting semantics the provider path already requires.

## 7. Race and late-result semantics

Parallel candidates MUST NOT race for integration authority.

Once an obligation is accepted through the normal verifier/receipt path:

- outstanding later-tier work SHOULD be canceled where safe;
- a late candidate may be retained as diagnostic evidence if policy allows;
- it MUST NOT overwrite accepted state merely because it arrived later or came from a stronger model;
- duplicate integration/receipt issuance is forbidden.

If two candidates complete before acceptance is committed, candidate evaluation order MUST be deterministic or explicitly policy-defined and replayable.

## 8. Privacy and placement

Escalation cannot broaden disclosure authority.

A remote tier is ineligible when the obligation, any required artifact or transitive dependency is local-only under existing policy.

The controller MUST distinguish:

- no eligible next tier because of privacy/placement;
- no eligible next tier because of budget;
- no eligible next tier because of deadline/cancellation;
- true terminal failure/UNKNOWN.

These are not interchangeable reasons.

## 9. Budget semantics

Every tier dispatch MUST pass existing pre-I/O budget reservation/authorization.

The ladder SHOULD support cumulative mission/obligation ceilings for:

- calls;
- expert/remote calls;
- request bytes/tokens where existing accounting supports them;
- declared/authoritative cost where the underlying runner supports it;
- wall-clock deadline.

Budget exhaustion MUST produce a typed unresolved/budget result and cannot be relabeled as model failure.

## 10. Escalation evidence

IE-002 observations SHALL record at minimum:

- tier entered;
- reason entered;
- engine/topology chosen;
- dispatch/cancel timestamps;
- verifier outcome;
- escalation reason;
- budget before/after where authoritative;
- residual/counterexample identity hash;
- whether dispatch was sequential or speculative.

Raw sensitive prompt/evidence data need not be retained for this controller.

## 11. Required tests

### T1 — cheap PASS stops escalation

Tier 1 produces a candidate that independently verifies PASS. No Tier 2/3 dispatch occurs in sequential mode.

### T2 — FAIL escalates residual

Tier 1 FAIL retains its counterexample and only unresolved obligation/evidence is transferred to the next eligible tier.

### T3 — UNKNOWN stays UNKNOWN until resolved

UNKNOWN triggers policy-allowed escalation but is never converted to PASS merely because a stronger tier is attempted.

### T4 — provider failure

A provider/transport error can trigger fallback/escalation but remains visible as its typed event.

### T5 — privacy block

A local-only obligation cannot escalate into a remote tier. The terminal reason identifies placement/privacy ineligibility.

### T6 — budget block

A later tier requiring more budget than remains is not dispatched. No provider call occurs before successful reservation.

### T7 — speculative cancellation

A later tier is prelaunched; an earlier candidate verifies PASS; later work is canceled where safe; late responses cannot overwrite accepted state.

### T8 — cost accounting after cancel

Speculatively dispatched/canceled work is not assumed free. Accounting remains conservative/authoritative according to existing provider semantics.

### T9 — duplicate acceptance race

Concurrent candidate completion cannot create duplicate receipts/integration or nondeterministic accepted state.

### T10 — deterministic candidate ordering

When multiple candidates are simultaneously eligible for verification before acceptance, ordering/selection is deterministic and replayable.

### T11 — pressure integration

With IE-003 active, speculative work counts against configured in-flight capacity and cannot bypass backpressure.

### T12 — disabled-mode equivalence

With the ladder feature disabled, existing local/expert execution behavior remains equivalent to accepted baseline.

### T13 — exact-head regression

All applicable existing CI remains green. No protected M4 file/test/pin/shared evidence schema changes without explicit dependency stop.

## 12. Qualification experiment

Use one fixed workload/model set to compare:

- existing baseline execution;
- explicit sequential ladder;
- speculative ladder only if sequential is already qualified.

Report:

- accepted/integrated goodput;
- acceptance coverage;
- escalation frequency;
- tier distribution;
- latency;
- provider calls/tokens/cost when authoritative;
- cancellations;
- rejection/UNKNOWN;
- orchestration tax.

Do not claim savings unless the measured workload/environment actually demonstrates them.

## 13. Rollout

Recommended rollout:

1. sequential ladder opt-in;
2. exact-head qualification + independent review;
3. engineering comparison;
4. sequential policy eligible for default only after evidence supports it;
5. speculative mode remains separately gated/opt-in until its race, budget and cancellation evidence is qualified.

## 14. Exit criteria

IE-005 exits when:

- the IE-001 escalation model is qualified;
- sequential policy passes T1–T13;
- privacy/budget/cancellation terminal reasons are explicit;
- no model/tier gains acceptance authority;
- disabled-mode equivalence is demonstrated;
- independent current-head review accepts the implementation.

## 15. Non-goals

This PR does not:

- guarantee cheap models are sufficient;
- define a universal model ranking;
- treat stronger models as verifiers;
- weaken provider budget rules;
- overwrite accepted state with late speculative output;
- make adaptive engine/topology predictions — IE-006 owns that policy.
