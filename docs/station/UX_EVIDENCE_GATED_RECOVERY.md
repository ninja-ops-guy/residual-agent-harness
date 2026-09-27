# UX-DOGFOOD-001 — Evidence-gated mission recovery UX

**Source:** OpenClaw Swarm Onboarding R0.1 live RESIDUAL dogfood, 2026-09-26  
**Status:** Findings / implementation proposal  
**Authority:** UI/UX proposal only. This document does not change task, review, integration, or activation authority.

## Observed trajectory

The live mission reached:

- OC-101 / Prepare Anvil: `INTEGRATED`.
- OC-102 / Prepare ForgeV2: `REPAIR_REQUIRED` after multiple attempts.
- OC-103 / Prepare Gateway: `REPAIR_REQUIRED` after multiple attempts.
- later OC-102/OC-103 mechanical checks passed while semantic reviews continued to reject the candidates for missing real-world evidence.
- Run Control opened with 15 passes, 200,000 tokens and a 3,600 second budget, then escalated after one pass with `no_runnable_tasks`, dispatch brake tripped, zero run-control tokens and ~20 ms elapsed.
- deterministic verification recorded acceptance PASS, integration FAIL (`integration_incomplete`), and review SKIPPED (`prior_check_failed`).
- pressing Run task can complete the runner operation while the authoritative task remains `REPAIR_REQUIRED`.
- optional cloud assessment can fail/rate-limit after batch work is already recorded.
- completed draft-spec jobs remain persistently visible in the job tray on the current UI; #470 is the proposed dismissal fix.

## UX problem

The machine state is substantially more informative than the operator-facing state.

Current UI can show:

- `REPAIR REQUIRED`
- `no_runnable_tasks`
- `run-OC-102 completed`
- `ESCALATED`

without presenting a direct operator path for the external evidence that is actually missing.

This creates three ambiguities:

1. **Repair versus evidence:** repeated model/code attempts are visually grouped with blockers that require observations, backups, identity proof or human approval.
2. **Operation completion versus task success:** `run-OC-102 completed` can be read as task success even though the task remains `REPAIR_REQUIRED`.
3. **Escalation without recovery action:** `no_runnable_tasks` explains the scheduler result but not what the human should do next.

## Proposed state taxonomy

Do not replace authoritative workflow states. Add a derived operator-facing blocker classification:

```
REPAIR_REQUIRED
├── MODEL_REPAIRABLE
├── EXTERNAL_EVIDENCE_REQUIRED
├── HUMAN_APPROVAL_REQUIRED
├── DEPENDENCY_BLOCKED
└── ATTEMPT_EXHAUSTED
```

Classification must be derived from retained findings/receipts and must never grant authority.

## Proposed Run Control presentation

When `no_runnable_tasks` occurs, render a decision-oriented panel instead of only the raw reason:

```
RUN CONTROL — EVIDENCE HOLD

2 tasks cannot advance through additional model execution.

ForgeV2
  External evidence required
  • effective runtime/model/fallback identity
  • profile-specific stopped-state proof
  • pre-change backup receipt
  • local fallback qualification
  • stopped bridge validation
  • protected-system unchanged proof
  • human activation approval

Gateway
  External evidence required
  • authoritative target identity

1 pass · 0 run-control tokens · 0.019s
[View required evidence] [Export evidence request]
```

Keep `Open run receipt` available.

## Proposed task-card changes

For evidence-gated tasks:

- retain authoritative `REPAIR_REQUIRED` state;
- add `EXTERNAL EVIDENCE` secondary badge;
- show count of unresolved evidence requirements;
- replace/promote `Run task` with `View required evidence` when another inference attempt cannot satisfy the blockers;
- allow `Run task` only when the scheduler classifies the task as model-repairable or after new admissible evidence changes the classification.

This is a UX guard, not a substitute for scheduler admission.

## Operation-result wording

Replace ambiguous success toast:

`run-OC-102 completed`

with outcome-aware wording such as:

`Attempt completed — OC-102 remains Repair Required`

or, when state advanced:

`Attempt completed — OC-102 advanced to Review Ready`

The toast should use the refreshed authoritative task state, not infer success from job completion.

## Evidence request artifact

Add a deterministic, exportable evidence-request view derived from the latest blocking review:

```json
{
  "schema": "residual.station.evidence-request.v1",
  "project_id": "p-...",
  "task_id": "OC-102",
  "task_state": "repair_required",
  "classification": "external_evidence_required",
  "requirements": [
    {
      "id": "runtime_identity",
      "description": "...",
      "satisfied": false,
      "evidence_refs": []
    }
  ],
  "review_receipt": "...",
  "generated_from_event_seq": 0
}
```

The artifact should be suitable for handing to a human, Shared Comms coordinator, or external evidence collector. Importing returned evidence must remain a separate authenticated operation.

## Evidence admission UX

The dogfood run exposes the missing bridge between:

`external swarm gathers facts`

and

`RESIDUAL can reconsider the task`.

Add an explicit operator flow:

1. **Export evidence request** from a blocked task.
2. External actor performs the requested observation under its own authority.
3. **Attach evidence** to the exact project/task/review requirement.
4. Station records immutable evidence metadata and a new event.
5. Re-run triage/admission.
6. Only if the evidence changes eligibility does Run Control expose runnable work.

Do not accept chat prose as authoritative evidence by default. Evidence admission needs provenance, digest, actor/source and scope.

## GoalSpec / project-spec hash labeling

Dogfood evidence contains two legitimate hashes:

- project/specification hash used by integration criteria;
- GoalSpec/run-control contract hash.

UI and receipts should label them distinctly, e.g.:

- `project_spec_hash`
- `goal_contract_hash`

Avoid displaying both as generic `spec_hash` in adjacent operator surfaces.

## Cloud-assessment separation

Make explicit in UI that:

- deterministic run-control may use zero tokens;
- optional cloud interpretation occurs after/beside authoritative run control;
- a cloud assessment failure does not erase completed batch evidence.

Suggested wording:

`Authoritative run closed with 0 execution tokens. Optional cloud interpretation failed: rate_limit. Recorded work is preserved.`

## Draft-result tray

Current running UI persistently renders completed draft-spec results. #470 proposes:

- explicit dismiss control;
- dismissal persisted client-side by job ID;
- underlying Station job/evidence preserved.

This should remain presentation-only.

## Acceptance tests

1. A task with passing mechanical checks and a blocking review requiring runtime observations renders `EXTERNAL EVIDENCE`.
2. `no_runnable_tasks` with evidence-gated tasks renders actionable evidence requirements.
3. A completed runner job that leaves the task in `repair_required` never emits a success-looking task toast.
4. Evidence request export is deterministic for unchanged task/review/event state.
5. Attaching evidence creates a new event and never mutates historical review receipts.
6. Re-running with unchanged evidence reproduces the same eligibility/disposition.
7. Re-running after admissible evidence may change eligibility, with the causal evidence/event references retained.
8. Cloud assessment failure cannot change deterministic run outcome.
9. Project-spec and GoalSpec hashes are distinctly labeled.
10. Draft dismissal hides presentation only and does not delete the completed job.

## Non-claims

- This proposal does not claim the current scheduler already distinguishes all blocker classes.
- It does not define the final external-evidence trust schema.
- It does not authorize Shared Comms messages as execution evidence.
- It does not alter Station's existing human approval or review authority.
