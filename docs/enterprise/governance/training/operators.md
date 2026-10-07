# Training: Operators (ENT7-R5, ENT7-R6)

Requirement: **ENT7-R5** — role-specific training for Operators (task
execution, HITL approval, brake response). Requirement: **ENT7-R6** — all
training MUST include hands-on exercises run against a **sandboxed Residual
instance**; video-only or document-only training is insufficient.

Progress is tracked in code: `residual/licensing/training.py`
(`TrainingRecord`, role `operator`). Completion requires all three
hands-on exercises: `execute_task`, `approve_hitl_challenge`,
`respond_to_brake`.

## Modules

1. **Residual fundamentals** (1h): stations, tasks, contracts, receipts.
2. **Task execution** (2h): submitting GoalSpecs, monitoring, reading
   verifier verdicts.
3. **HITL approvals** (2h): challenge anatomy, evidence review,
   approve/reject/escalate, approval SLAs (ENT8-R2).
4. **Brake response** (1.5h): brake types, the brake-tripped runbook
   (ENT7-R4), safe re-arm procedure.

## Hands-On Exercises (Sandbox Required, ENT7-R6)

| Exercise | ID | Task | Pass criteria |
|---|---|---|---|
| Execute a task end-to-end | `execute_task` | Submit a reconciliation task in the sandbox; verify its receipt | Receipt chain verifies; verdict PASS |
| Approve a HITL challenge | `approve_hitl_challenge` | Review a seeded challenge with a deliberate parameter error; reject with reason; approve the corrected resubmission | Rejection reason recorded; approval receipt bound to task |
| Respond to a tripped brake | `respond_to_brake` | Sandbox trips a verifier-threshold brake; follow the runbook to investigate and re-arm | Correct trigger identified; re-arm receipted |

## Assessment

Exercises auto-recorded via `TrainingRecord.record_exercise(...,
sandboxed=True)`. Non-sandboxed completion is rejected by the code.
Completion attests `training_complete` for pilot graduation (ENT7-R1).
