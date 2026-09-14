# Pilot Program Framework (ENT7-R1)

Requirement: **ENT7-R1** — Residual MUST provide a pilot program framework
defining evaluation criteria, pilot scope, success metrics, duration
(typically 30–90 days), rollback plan, and graduation criteria to production.

The framework is implemented in code in `residual/licensing/pilot.py`
(`PilotPlan`, `GraduationEvaluation`, `MetricResult`) and governed by this
document.

## 1. Pilot Scope

Every pilot begins with a written scope statement, recorded as the `scope`
field of a `PilotPlan`. Scope MUST enumerate:

- **Teams and business units** participating (e.g. one payments team, one
  platform team). A pilot MUST NOT span more than two teams.
- **Systems and clusters** where Residual stations run (staging first;
  production-adjacent only after week 2 with CAB approval).
- **Task categories** permitted during the pilot (e.g. read-only data
  reconciliation, report generation). Irreversible actions (payments,
  deletions, external sends) are out of scope until graduation.
- **Module allowlist**: only modules validated per the module-installation
  runbook (ENT7-R4) may be installed.

## 2. Duration

Pilots run **30–90 days** (enforced by `PilotPlan` validation:
`MIN_DURATION_DAYS = 30`, `MAX_DURATION_DAYS = 90`). Recommended structure:

| Phase | Days | Activities |
|---|---|---|
| Onboarding | 1–10 | Sandbox setup, operator training (ENT7-R5), baseline metrics |
| Supervised operation | 11–40 | Tasks run with HITL approval on every challenge |
| Reduced supervision | 41–70 | HITL sampling, brake drills, rollback rehearsal |
| Evaluation | 71–90 | Metric scoring, graduation review |

## 3. Success Metrics

Success metrics MUST be measurable and recorded via `MetricResult`. The
standard metric set (pilots may add, never remove):

| Metric | Target | Direction |
|---|---|---|
| Receipt verification rate | >= 99.0% | higher is better |
| Task success rate (verifier PASS) | >= 95.0% | higher is better |
| P1 incidents attributable to Residual | <= 1 | lower is better |
| Mean HITL challenge review time | <= 15 min | lower is better |
| Unplanned rollbacks | 0 | lower is better |

## 4. Evaluation Criteria

Evaluation criteria are the qualitative gates reviewed by the pilot board:

1. **Contract integrity**: no unresolved contract violations; every violation
   has a completed post-mortem (see runbook, ENT7-R4).
2. **Observability**: every task produced a receipt; receipt chain verified
   end-to-end at least weekly by an auditor.
3. **Brake behavior**: at least one live brake drill performed and resolved
   per the brake-tripped runbook.
4. **Operational readiness**: on-call rotation staffed; runbooks exercised.

## 5. Rollback Plan

Every `PilotPlan` MUST name a rollback plan. Standard plan:

1. Freeze new task submissions; drain in-flight tasks.
2. Disable Residual engines via configuration; restore manual workflows.
3. Retain all receipts and quarantine records for audit (immutable).
4. Restore pre-pilot station configuration from versioned config backup.
5. Conduct rollback retrospective within 5 business days.

A rollback rehearsal MUST be executed during the pilot and attested as the
`rollback_rehearsed` graduation criterion.

## 6. Graduation Criteria to Production

Graduation is decided by `GraduationEvaluation.graduated()`, which returns
true only when **all** success metrics pass and **all** graduation criteria
are attested. Standard graduation criteria:

- `security_signoff` — security review package (ENT7-R3) accepted.
- `architecture_signoff` — architecture review (ENT7-R2) accepted.
- `rollback_rehearsed` — rollback executed successfully in a drill.
- `training_complete` — all pilot operators completed hands-on training
  (ENT7-R5, ENT7-R6).
- `support_tier_active` — a support tier (ENT8-R2) is under contract.

Partial passes do not graduate; the pilot is either extended (within the
90-day cap) or rolled back.
