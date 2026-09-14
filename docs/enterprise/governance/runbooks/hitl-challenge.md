# Runbook: HITL Challenge — Review and Approval Workflow (ENT7-R4)

Requirement: **ENT7-R4** — runbook template for the "HITL challenge"
operational scenario.

## Overview

A HITL (human-in-the-loop) challenge pauses a task until a human approves
or rejects it. Challenges arise from policy (sensitive actions), low
verifier confidence, or contract requirements.

## Detection

- Notification to the approver pool (UI badge + email per IAM routing).
- Metric: `hitl_pending_challenges` > 0; aging alert at 15 minutes.

## Review Workflow

1. **Triage**: open the challenge; read the task summary, the step being
   challenged, the triggering policy, and the verifier context.
2. **Inspect evidence**: pull the task's receipt chain; confirm prior
   steps verified cleanly. Check the exact action payload — approvers MUST
   review the actual parameters, not the summary.
3. **Decide**:
   - **Approve** when the action matches the task's approved scope and
     parameters are correct.
   - **Reject** when scope is exceeded, parameters are wrong, or intent
     is unclear. Rejection MUST include a reason (recorded in the receipt).
   - **Escalate** when the action needs security/legal review; route per
     the escalation chain.
4. **Record**: approval/rejection produces a receipt bound to the task ID
   and challenge nonce. Verbal approvals are invalid — only receipted
   decisions count.

## SLAs

| Tier (ENT8-R2) | Challenge response target |
|---|---|
| Standard | 1 business day |
| Premium | 4 hours |
| Enterprise | 1 hour (P1 challenges) |

## Stuck / Expired Challenges

- Challenge aging past its expiry: task auto-parks (never auto-approves).
- Approver unavailable: escalation chain engages the secondary pool.
- Repeated challenges from one task (>3): treat as a contract-violation
  precursor; open the contract-violation runbook.

## Anti-Patterns (Audit Findings)

- Bulk-approving without parameter review (flagged in auditor reviews,
  ENT7-R5 auditor curriculum).
- Approving own tasks (separation of duties enforced by IAM).
- Using rejection to silently drop work — every rejection needs a reason.

## Post-Action

Approved actions resume execution under the verifier; monitor the next
verdict. Rejected tasks close with a terminal receipt.
