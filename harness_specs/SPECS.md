# Agentic Harness — Formal Specifications

**Version:** 0.1.0
**Date:** 2026-09-13
**Normative language:** RFC 2119 (MUST, SHOULD, MAY)

---

## SPEC-001: GoalSpec

### Purpose
Define the frozen, versioned artifact that constitutes a run's objective
and termination conditions.

### Requirements

**SPEC-001-R1.** A `GoalSpec` MUST be immutable after construction.
Mutation MUST be impossible through the public interface.

**SPEC-001-R2.** A `GoalSpec` MUST contain exactly these fields:
`goal_id`, `objective`, `success_criteria`, `max_passes`,
`token_budget`, `wall_clock_budget_s`, `amendment_rule`,
`schema_version`. No field MAY be `None`.

**SPEC-001-R3.** `success_criteria` MUST be an ordered tuple of
`SuccessCriterion`. The tuple MUST be non-empty.

**SPEC-001-R4.** Each `SuccessCriterion` MUST specify:
- `name`: unique within the spec
- `check_type`: one of `mechanical`, `structural`, `judge`
- `description`: what is being verified
- `evaluator`: a reference to the check implementation

**SPEC-001-R5.** `success_criteria` MUST be ordered such that all
`mechanical` checks precede all `structural` checks, which precede all
`judge` checks. This ordering MUST be enforced at construction time.

**SPEC-001-R6.** `amendment_rule` MUST specify:
- `authorized_roles`: who may amend
- `required_reason`: whether a reason is mandatory (always true)
- `max_amendments`: hard cap on amendments per run

**SPEC-001-R7.** Any amendment MUST produce a new `GoalSpec` instance
with an incremented `schema_version` and a mandatory `amendment_reason`
string. The original spec MUST be preserved unmodified.

**SPEC-001-R8.** A `GoalSpec` MUST emit a `checkpoint` observation on
construction containing the spec's content hash and all budget fields.

---

## SPEC-002: Verifier

### Purpose
Evaluate a candidate result against a `GoalSpec` and produce a structured,
ordered verification report.

### Requirements

**SPEC-002-R1.** The `Verifier` MUST evaluate checks in the exact order
defined by `GoalSpec.success_criteria`.

**SPEC-002-R2.** The `Verifier` MUST evaluate all checks regardless of
early failures. Early failures MUST NOT short-circuit evaluation of
subsequent checks.

**SPEC-002-R3.** The overall result MUST be `PASS` if and only if all
checks return `PASS`. Any single `FAIL` produces an overall `FAIL`.

**SPEC-002-R4.** The `VerificationReport` MUST identify the first
failing check (in evaluation order) as the `primary_failure`. This
field MUST be `None` if and only if the overall result is `PASS`.

**SPEC-002-R5.** A `mechanical` check that raises an exception MUST
return `FAIL` with reason `check_error`, not propagate the exception.

**SPEC-002-R6.** A `judge` check MUST NOT be evaluated if any
`mechanical` or `structural` check has failed. Its result MUST be
recorded as `SKIPPED` with reason `prior_check_failed`.

**SPEC-002-R7.** A `judge` check whose evaluator is unavailable MUST
return `FAIL` with reason `judge_unavailable`. It MUST NOT return
`PASS` by default.

**SPEC-002-R8.** Every check evaluation MUST emit a `custom` observation
containing: check name, check type, result, reason, and duration_ms.

---

## SPEC-003: Brakes

### Purpose
Independently monitor execution and trip when defined boundaries are
crossed, without terminating the run directly.

### Requirements

**SPEC-003-R1.** Each brake MUST implement the `Brake` protocol:
`name: str`, `update(event: Observation) -> Optional[BrakeTrip]`,
`reset() -> None`.

**SPEC-003-R2.** Brakes MUST subscribe to the observation bus. They
MUST NOT poll, thread, or maintain independent timers.

**SPEC-003-R3.** A `BrakeTrip` MUST contain: `brake_name`, `trip_reason`,
`triggering_obs_hash`, `recommended_action` (one of `continue`,
`escalate`, `abort`).

**SPEC-003-R4.** The `MaxIterationBrake` MUST trip when the count of
`state.transition` observations with `to_state: "pass_complete"`
reaches `GoalSpec.max_passes`.

**SPEC-003-R5.** The `BudgetBrake` MUST trip when either running token
total (from `llm.response` observations) reaches `token_budget` or
wall-clock elapsed reaches `wall_clock_budget_s`.

**SPEC-003-R6.** The `NoProgressBrake` MUST maintain a history of tool
call fingerprints (tool name + canonical argument hash). It MUST trip
when the same fingerprint appears `spec.no_progress_threshold` times
consecutively. Default threshold: 3.

**SPEC-003-R7.** The `CompletionBrake` MUST trip when a
`VerificationReport` with overall `PASS` is observed.

**SPEC-003-R8.** A brake trip MUST emit a `state.transition` observation
with `from_state: "brake_armed"`, `to_state: "brake_tripped"`, and the
`BrakeTrip` payload.

**SPEC-003-R9.** Brake trips MUST NOT terminate the run. The
`LoopController` MUST evaluate all tripped brakes and produce a single
`BrakeDecision` per pass.

**SPEC-003-R10.** Multiple brakes MAY trip in the same pass. The
`LoopController` MUST prioritize: `abort` > `escalate` > `continue`.

---

## SPEC-004: QuarantineStore

### Purpose
Hold every proposed action for policy evaluation before execution.

### Requirements

**SPEC-004-R1.** Every `ProposedAction` MUST pass through
`QuarantineStore.hold()` before execution. No execution path MAY bypass
the hold.

**SPEC-004-R2.** `QuarantineStore.evaluate()` MUST apply all policies
in the policy tuple and return a `PolicyDecision` of `ALLOW` or `DENY`.

**SPEC-004-R3.** A denied action MUST NOT be returned to the agent's
context window. The agent MUST observe only the absence of a result.

**SPEC-004-R4.** A denied action MUST emit a `tool.failed` observation
with `reason: policy_denied`, the policy name, and the action fingerprint.

**SPEC-004-R5.** An allowed action MUST be released via
`QuarantineStore.release()` and executed. The result MUST be observed
as `tool.completed`.

**SPEC-004-R6.** The `QuarantineStore` MUST maintain an append-only log
of all held actions, their evaluation results, and their final
dispositions. This log MUST be queryable by action fingerprint.

**SPEC-004-R7.** Policy evaluation MUST be side-effect-free. A policy
MUST NOT execute the action, modify state, or emit observations.

---

## SPEC-005: ContextCurator

### Purpose
Assemble the context window for each harness pass under budget.

### Requirements

**SPEC-005-R1.** The `ContextCurator` MUST produce a context assembly
for each pass. It MUST NOT accumulate context across passes without
selection.

**SPEC-005-R2.** Context selection MUST prioritize, in order:
1. The current `GoalSpec` objective and success criteria
2. Observed events from the current run (via observation layer)
3. Results of prior passes (only verified results; unverified agent
   claims MUST be excluded)

**SPEC-005-R3.** The assembled context MUST NOT exceed the per-pass
token budget. If selection exceeds budget, the curator MUST drop lowest
priority items until compliant.

**SPEC-005-R4.** The curator MUST NOT include any content that has not
passed through the observation layer. Agent-generated text enters
context only as an observed event, never as direct injection.

**SPEC-005-R5.** The curator MUST emit a `custom` observation per pass
containing: item count, total tokens, items included (by reference),
items dropped (by reference and reason).

---

## SPEC-006: SubAgentPool

### Purpose
Spawn, monitor, and terminate sub-agents with strict isolation.

### Requirements

**SPEC-006-R1.** A sub-agent MUST be spawned with a `SpawnSpec`
containing: `task_description`, `goal_spec` (same as parent's),
`tool_subset`, `token_budget`, `max_passes`.

**SPEC-006-R2.** A sub-agent MUST NOT receive the parent agent's
reasoning, prior context, or unverified claims. It receives only the
task description and its own curated context.

**SPEC-006-R3.** A sub-agent MUST emit observations to the same
observation bus as the parent. Its events MUST be tagged with
`agent_id` and `parent_id`.

**SPEC-006-R4.** A sub-agent that exceeds its `token_budget` or
`max_passes` MUST be terminated by the pool. Termination MUST emit
`agent.terminated` with reason `budget_exceeded` or `max_passes_exceeded`.

**SPEC-006-R5.** A sub-agent's result MUST be verified before entering
the parent's context. Unverified sub-agent output MUST be held in the
quarantine store until verified.

**SPEC-006-R6.** Arm isolation: sub-agent invocations with the same
`SpawnSpec` MUST receive identical tools, seeds, and budgets. The pool
MUST enforce this by construction, not by convention.

---

## SPEC-007: LoopController

### Purpose
Orchestrate one complete run: multiple harness passes, brake evaluation,
escalation, and termination.

### Requirements

**SPEC-007-R1.** `LoopController.run()` MUST accept a `GoalSpec` and a
`HarnessPass` and return a `RunOutcome`.

**SPEC-007-R2.** `RunOutcome` MUST be exactly one of: `SUCCESS`,
`ESCALATED`, `ABORTED`, `AMENDED`. No other value is valid.

**SPEC-007-R3.** The controller MUST run harness passes until either:
- A `VerificationReport` with overall `PASS` is observed (`SUCCESS`)
- A brake trip recommends `abort` (`ABORTED`)
- A brake trip recommends `escalate` and no authorized amendment
  resolves it (`ESCALATED`)
- The `GoalSpec` is amended and the run restarts under the new spec
  (`AMENDED`)

**SPEC-007-R4.** After each pass, the controller MUST evaluate all
brake trips and produce a single `BrakeDecision`. The decision and its
reasoning MUST be observed.

**SPEC-007-R5.** On `SUCCESS`, the controller MUST emit a `checkpoint`
observation containing: total passes, total tokens, wall-clock duration,
and the content hash of the final verified result.

**SPEC-007-R6.** On `ABORTED` or `ESCALATED`, the controller MUST emit
a `checkpoint` observation containing the same fields plus the tripped
brake name(s) and trip reason(s).

**SPEC-007-R7.** The controller MUST flush the observation bus before
returning any `RunOutcome`.

**SPEC-007-R8.** The controller MUST NOT catch exceptions from the
observation layer. Observation failures MUST propagate.

---

## SPEC-008: HarnessPass

### Purpose
Execute one Gather → Act → Verify cycle.

### Requirements

**SPEC-008-R1.** A harness pass MUST execute exactly three phases in
order: Gather, Act, Verify. No phase MAY be skipped or reordered.

**SPEC-008-R2.** The Gather phase MUST call `ContextCurator.assemble()`
and produce a context assembly under budget.

**SPEC-008-R3.** The Act phase MUST send the assembled context to the
model via `ai_providers.Router` and receive a response. All proposed
tool calls in the response MUST enter the `QuarantineStore`.

**SPEC-008-R4.** The Verify phase MUST call `Verifier.verify()` with
the candidate result and the current `GoalSpec`.

**SPEC-008-R5.** Each phase transition MUST emit a `state.transition`
observation: `gather_complete`, `act_complete`, `verify_complete`.

**SPEC-008-R6.** A harness pass MUST NOT emit a final response to the
caller. It produces a `CandidateResult`. The `LoopController` decides
whether the run is complete.
