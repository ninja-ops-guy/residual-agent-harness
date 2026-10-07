# Agentic Harness — Design Documentation

**Status:** Draft v0.1
**Date:** 2026-09-13
**Depends on:** `observation_layer` v0.1, `ai_providers` v0.1
**Source synthesis:** "Harness vs Loop Engineering" (Goyal), "Architecture for Disaggregated LLM Inference: Optimized KV Cache Management"

---

## 1. Problem Statement

Existing infrastructure provides two layers: an immutable observation spine
(`observation_layer`) and a provider-agnostic model routing substrate
(`ai_providers`). Neither constitutes a harness. What is missing is the
control plane: the machinery that defines what "done" means, executes
agent passes against that definition, applies brakes when execution
diverges, and quarantines actions that violate policy before they execute.

This document defines that control plane.

## 2. Architectural Position

Three layers, strict dependency direction, no upward leaks:

```
LOOP LAYER        goal, brakes, completion, escalation
    │ depends on
HARNESS LAYER     gather → act → verify (one pass)
    │ depends on
INFRASTRUCTURE    observation_layer + ai_providers
```

The infrastructure layer is complete. The harness layer is partially
specified (this document). The loop layer is specified here but not yet
implemented.

**Unit of work definitions:**
- Harness pass: one Gather → Act → Verify cycle. Produces a candidate result.
- Loop run: one or more harness passes terminating in a verified final
  response or a brake-triggered escalation. Produces an outcome.

An agent saying "done" is a harness event. A run being done is a loop
decision. These must never be conflated.

## 3. Core Design Decisions

### 3.1 Goal specification is structural, not behavioral

A `GoalSpec` is a frozen, versioned artifact defined before any run opens.
It contains: the objective, success criteria as a ordered list of checks
(mechanical first, judge last), resource budgets, and an amendment rule.
No field is optional. No criterion may reference "the agent thinks."

This is preregistration applied to agent execution: the run does not
define the goal; the goal defines the run.

### 3.2 Verification is ordered and mechanical-first

The `Verifier` evaluates checks in strict order:
1. Mechanical checks (file exists, test passes, schema validates, diff applies)
2. Structural checks (format, length, required sections present)
3. Judge check (LLM evaluation) — only if all prior checks pass

A judge check must never override a failed mechanical check. This ordering
is not a preference; it is a load-bearing constraint. Mechanical checks
are deterministic and replayable. Judge checks are neither.

### 3.3 Brakes are independent state machines

Four brakes, each maintaining independent state, each emitting structured
observations on every transition:

| Brake | Trip condition | State tracked |
|---|---|---|
| Max iteration | pass_count >= spec.max_passes | counter |
| Budget | tokens or wall-clock exceeds spec | running totals |
| No progress | same tool call + same args repeated | call fingerprint history |
| Completion | all GoalSpec checks pass | check results |

A brake trip does not terminate the run. It triggers a `BrakeDecision`:
continue, escalate to human, or abort with partial results. The decision
is itself observed and reasoned.

### 3.4 Actions are quarantined before execution

Every tool call the agent proposes enters a `QuarantineStore` before
execution. Policy evaluation runs against the quarantined action. Denied
actions are:
- **Not executed** — never reach the tool
- **Observed** — emitted as `TOOL_FAILED` with `reason: policy_denied`
- **Not returned to the agent's context** — the agent cannot retry around
  the denial by rephrasing

This resolves the tension between "silent denial is a feature" (the agent
is not handed a refusal it can negotiate with) and fail-visible telemetry
(the denial is fully observed with reason and policy reference).

### 3.5 Context is curated, not accumulated

The `ContextCurator` assembles what enters the Gather zone on each pass.
It does not append; it selects. Selection criteria:
- Relevance to current GoalSpec checks
- Budget compliance (token ceiling per pass)
- Recency and provenance (observed events beat agent claims)

The agent's own outputs from prior passes enter context only through
the observation layer — never through direct injection. This prevents
the agent from laundering its own unverified claims into ground truth.

### 3.6 Sub-agent isolation mirrors ablation discipline

Sub-agents spawned by the harness run with:
- The same GoalSpec (no scope drift)
- The same observation bus (full telemetry)
- Independent context windows (no cross-contamination)
- Strict arm isolation: the spawning agent's tools, seeds, and budgets
  are held constant across sub-agent invocations

A sub-agent is a specialist, not a confidant. It receives a task
description and returns a result. It does not receive the parent's
reasoning.

## 4. Module Map

```
harness/
├── goalspec.py        GoalSpec, SuccessCriterion, AmendmentRule
├── verifier.py        Verifier protocol, OrderedVerifier, CheckResult
├── brakes.py          Brake protocol, four brake implementations, BrakeDecision
├── quarantine.py      QuarantineStore, Policy, PolicyDecision
├── curator.py         ContextCurator, SelectionStrategy
├── subagents.py       SubAgentPool, SpawnSpec, isolation enforcement
├── loop.py            LoopController, RunOutcome, EscalationPath
└── harness.py         HarnessPass — the Gather→Act→Verify pipeline
```

## 5. Interface Contracts

### 5.1 GoalSpec

```python
@dataclass(frozen=True)
class GoalSpec:
    goal_id: str
    objective: str
    success_criteria: tuple[SuccessCriterion, ...]  # ordered, mechanical first
    max_passes: int
    token_budget: int
    wall_clock_budget_s: float
    amendment_rule: AmendmentRule  # who may modify, under what conditions
    schema_version: str
```

Frozen at construction. Amendments produce a new `GoalSpec` with an
incremented version and a mandatory `amendment_reason` observed on the bus.

### 5.2 Verifier

```python
class Verifier(Protocol):
    def verify(self, candidate: CandidateResult, spec: GoalSpec) -> VerificationReport: ...
```

`VerificationReport` contains per-check results in evaluation order,
an overall pass/fail, and the check that failed first (if any). The
first failure is the report's primary finding; subsequent checks are
evaluated for telemetry but do not affect the pass/fail outcome.

### 5.3 Brakes

```python
class Brake(Protocol):
    name: str
    def update(self, event: Observation) -> Optional[BrakeTrip]: ...
    def reset(self) -> None: ...
```

Brakes subscribe to the observation bus. They do not poll. A `BrakeTrip`
contains the brake name, the trip reason, the triggering observation's
hash, and a recommended action (continue / escalate / abort).

### 5.4 QuarantineStore

```python
class QuarantineStore:
    def hold(self, action: ProposedAction) -> HeldAction: ...
    def evaluate(self, held: HeldAction, policies: tuple[Policy, ...]) -> PolicyDecision: ...
    def release(self, held: HeldAction) -> ExecutedAction: ...
    def deny(self, held: HeldAction, reason: str) -> DeniedAction: ...
```

`ProposedAction` → `HeldAction` → (`ExecutedAction` | `DeniedAction`).
No path skips the hold. No path executes without evaluation.

### 5.5 LoopController

```python
class LoopController:
    def run(self, spec: GoalSpec, harness: HarnessPass) -> RunOutcome: ...
```

`RunOutcome` is a closed enum: `SUCCESS` (all checks passed),
`ESCALATED` (brake tripped, human decision required), `ABORTED`
(budget exhausted or unrecoverable error), `AMENDED` (GoalSpec amended
mid-run, run restarted under new spec).

## 6. Observation Integration

Every state transition in every module emits through the observation
layer. Event kinds already defined in `observation_layer` are reused;
new kinds are added only where no existing kind fits:

| Event | Kind | Payload |
|---|---|---|
| Run opened | `checkpoint` | goal_id, spec hash, budgets |
| Pass started | `state.transition` | pass_number, context size |
| Action quarantined | `state.transition` | action fingerprint, policy set |
| Action denied | `tool.failed` | reason: policy_denied, policy ref |
| Action executed | `tool.completed` | duration, result hash |
| Check evaluated | `custom` | check name, result, duration |
| Brake tripped | `state.transition` | brake name, trip reason, obs hash |
| Brake decision | `custom` | decision, reasoning |
| Run closed | `checkpoint` | outcome, total passes, total tokens |
| Spec amended | `custom` | old hash, new hash, reason |

## 7. Failure Modes and Responses

| Failure | Detection | Response |
|---|---|---|
| Agent claims done, checks fail | Verifier | Continue loop; failed checks feed ContextCurator |
| Same tool call repeated | NoProgressBrake | Trip brake; decision: continue with warning or escalate |
| Token budget exhausted | BudgetBrake | Abort with partial results; all observations flushed |
| Policy violation proposed | QuarantineStore | Deny silently to agent; observe fully |
| Judge check unavailable | Verifier | Fail closed: judge check returns FAIL with reason `judge_unavailable` |
| Sub-agent exceeds scope | SubAgentPool | Terminate sub-agent; observe; escalate |
| Spec amendment without authorization | AmendmentRule | Reject amendment; observe rejection; run continues under original spec |

## 8. What This Document Does Not Specify

- Concrete policy implementations (these are deployment-specific)
- Judge prompt construction (a separate spec; judge checks are the
  least reliable layer and must be replaceable)
- Multi-run orchestration (the loop layer handles one run; scheduling
  across runs is out of scope)
- Persistence format for GoalSpec artifacts (the observation layer's
  JSONL sinks suffice; a dedicated artifact store is future work)
