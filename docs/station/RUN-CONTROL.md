# Goal contracts and bounded mission runs

The merged control layer now runs the station's real implementation batches. The coordinator imports and triages the Markdown specification locally, creates an immutable `GoalSpec`, and runs dependency waves through `LoopController`. Each wave may dispatch several workers, check their proposals locally, obtain revision-bound review and integrate accepted work. The existing LDD state machine remains the authority for task transitions.

A batch produces `RUN-CONTROL.md`: JSON inside a Markdown fence containing the full goal contract, its hash, pass count, reported tokens, elapsed time, ordered check results and brake decisions. Open it from **Mission board → Run control → Open run receipt** or the evidence list. Project Markdown also contains the latest run summary. Control observations appear in Diagnostics; they are not replayed as model prompts.

## Controls in the interface

Under **Model workshop → Mission loop limits**, set maximum passes, reported token budget and elapsed-time budget. Defaults are 30 waves, 200,000 reported tokens and one hour. The wave count is further bounded by three times the task count. Per-task implementation attempts still stop at three, and the existing project call/byte reservations apply to every provider attempt, including failover.

Token and time brakes are **cooperative checks between waves**. A running wave can exceed these values before its calls and local checks return. They are not a hard spending cap or an OS watchdog. Provider timeouts and project reservations operate separately. The controller will not start another wave after its limit is reached. Unknown or invalid usage aborts further waves and is recorded as `null`, never as zero. Training missions execute no model calls, so their total is zero.

## Pre-dispatch budget admission

Because the controller's brakes only engage between passes, Station mirrors the same run-level budget/deadline accounting inside the pass through a host-owned **admission gate** (`BudgetAdmission` in `residual/station/control.py`). The invariant is: no action capable of producing an accepted or releasable successor may begin unless the run has sufficient admissible budget/deadline authority for that dispatch.

* **Admission before dispatch.** Every runner and reviewer provider dispatch must be admitted by the gate first. Admission is refused when the run's recorded usage plus outstanding reservations reach the token budget, when the wall-clock deadline has elapsed, or when usage is unknown.
* **Reserved-then-recheck.** Where bounded cost is knowable it is reserved before dispatch: the reservation unit is the worst per-call usage observed so far in the run (one token before any observation), held while the call is in flight and reconciled against the durable `usage.recorded` receipt on completion. Run authority is re-checked after the runner wave, before each review, after each review and before each integration, so a budget trip racing an in-flight dispatch still blocks every subsequent authority-bearing effect.
* **Unknown usage is conservative.** An unknown or invalid usage receipt admits no further dispatch and permits no review/integration effect, matching the controller's abort on unknown usage. Denied admissions are recorded as durable `project.note` events with the reason and stage.
* **Export requires a bound run-control receipt.** `station.export()` requires the last run-control result to be a success bound to the exact current integrated head (`project_head`) and project spec hash (`project_spec_hash`), not merely integrated task state. An aborted run cannot produce a releasable successor even when candidate checks and review passed.

Automatic cloud assessment runs after an eligible non-aborted live batch. Its calls have separate receipts and count against the project-wide reservations; they are outside the implementation batch's run receipt. Aborted batches do not automatically invoke the cloud assessment.

## Verification order and decisions

| Check | Station evidence | Inference added by control check |
|---|---|---|
| Mechanical | Every task has passing local acceptance receipts | None |
| Structural | Original specification hash and task IDs match; all tasks are integrated | None |
| Judge | Existing reviewer approvals match the integrated task commits | None; reuses the recorded review |

The reviewer itself can use the configured local or cloud provider during a wave. A failed mechanical or structural check skips the judge check. Missing evaluators, exceptions and malformed results fail closed. Brakes decide in the order abort, escalate, continue. A successful final allowed pass can complete; a token or time abort takes precedence. Paused dispatch and exhausted runnable tasks produce a structured escalation rather than an indefinite loop.

The controller generates its own pass and verification events. Worker-supplied lifecycle, token and completion observations cannot change control counters. A host-computed fingerprint of task states and revisions detects repeated waves without copying tool arguments or source into observations.

## Provider quarantine

Station model operations are held, evaluated for the mission's cloud-sharing permission, then released once. The router still checks authoritative project reservations and permissions for each actual provider attempt. The quarantine record contains a packet digest, provider/model IDs and output limit; it does not contain source or credentials.

`QuarantineStore` binds each hold to the store that created it. Release requires a completed allow decision. Denied, foreign, fabricated and already consumed holds cannot execute. Evaluation is cached, policy exceptions deny, and proposal budgets reserve once even under concurrent callers. Executor failures remain observable; the station and provider wrapper propagate the original error instead of returning an apparent empty success.

Quarantine is a host-level action gate, not an OS sandbox. Its in-memory log is local to the operation; station execution/denial observations are durable when recording is enabled. File-write policies reject lexical path escapes, while the station's existing workspace executor checks writable scope and resolved symlink paths. Native command checks still require a trusted project and explicit command execution opt-in.

## Public Python interface

```python
from residual import (
    AmendmentRule, CheckResult, CheckType, GoalSpec,
    LoopController, SuccessCriterion, Verifier,
)

spec = GoalSpec(
    goal_id="repair-health", objective="Produce a tested health function",
    success_criteria=(SuccessCriterion(
        "tests", CheckType.MECHANICAL, "Behavioral tests pass", "tests"),),
    max_passes=3, token_budget=20_000, wall_clock_budget_s=300,
    amendment_rule=AmendmentRule(("operator",)),
)

class Runner:
    def run_pass(self, spec, pass_number):
        # Host code implements the proposal and executes the declared tests.
        # Replace this small deterministic example with your own runner.
        return {"candidate": {"tests_passed": True}, "tokens_used": 0,
                "observations": []}

verifier = Verifier({"tests": lambda candidate, params: (
    CheckResult.PASS if candidate["tests_passed"] else CheckResult.FAIL,
    "host_test_result",
)})
result = LoopController(spec, verifier, Runner()).run()
print(result.outcome.value, result.spec_hash)
```

`tokens_used` must come from host/provider receipts for all calls performed by that pass. A missing value stops the loop. Custom executors and evaluators are trusted host code; the controller cannot preempt a hung Python function or discover unreported external calls. Inference-based custom evaluators must enforce their own dispatch budgets and report their usage through the host integration.

For the original obligation harness, wrap a configured provider with `QuarantinedProvider(provider, store, policies)` before constructing `Harness`. Station model calls already use quarantine. Optional observation adapters count delivery failures without stopping a request; a direct, authoritative `LoopController.emit` callback propagates exceptions. This keeps optional diagnostics distinct from host enforcement.

## Goal amendments

Parameters and role lists are detached immutable values. Goal hashes bind criterion descriptions, evaluator identities, parameters, budgets, amendment authority and lineage. A hash identifies the declared contract; it does not fingerprint the Python evaluator implementation or authenticate a person.

`spec.amend(..., amended_by="operator", amendment_reason="...")` returns a new contract with a parent hash and increased amendment count/version. It rejects missing reasons, roles outside the host-declared list and exhausted amendment allowances. The old contract remains unchanged. The host is responsible for authenticating the caller before assigning a role. Amendments are explicit new runs; the controller never expands its own goal or budget automatically. `RunOutcome.AMENDED` is reserved and is not currently emitted.
