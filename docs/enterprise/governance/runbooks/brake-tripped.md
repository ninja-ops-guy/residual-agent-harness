# Runbook: Brake Tripped — Investigation and Resolution (ENT7-R4)

Requirement: **ENT7-R4** — runbook template for the "brake tripped"
operational scenario.

## Overview

A brake is Residual's automatic halt switch. When a brake trips, task
execution stops safely. This runbook covers investigation and resolution.
**Severity default: P2** (P1 if production execution is fully halted).

## Detection

- Alert: `brake_tripped` event in observability exporter.
- Symptom: new tasks refused; in-flight tasks parked; station status
  shows `BRAKED`.

## Immediate Actions (0–15 min)

1. **Do not reset the brake.** Identify which brake tripped and why:
   `residual brakes status` — record brake ID, trigger condition, and the
   task ID that caused the trip.
2. Confirm containment: verify no tasks are executing (queue depth zero,
   engine processes idle).
3. Notify the on-call channel; escalate to P1 per support tier SLA
   (ENT8-R2) if business-critical workloads are halted.

## Investigation (15–60 min)

1. Pull the receipt chain for the triggering task; verify hashes end-to-end.
2. Identify the trigger class:
   - **Verifier FAIL threshold** — inspect failing checks; see the
     contract-violation runbook.
   - **Rate/volume brake** — check for task floods or retry storms.
   - **Manual brake** — identify the operator; review their justification.
3. Determine whether the trip was a true positive (unsafe behavior
   correctly stopped) or a false positive (misconfigured threshold).

## Resolution

- **True positive**: remediate the underlying cause first (bad module,
  contract bug, engine fault). Only then re-arm.
- **False positive**: adjust brake threshold via configuration change
  (CAB-approved in production), then re-arm.
- Re-arm: `residual brakes reset <brake-id>` — requires operator +
  approver (HITL) confirmation; the reset is receipted.
- Resume the task queue gradually; watch verifier verdicts for 30 min.

## Post-Incident

1. Complete the incident record: trigger, root cause, time-to-resolve,
   receipts referenced.
2. If thresholds changed, update the configuration baseline.
3. Feed lessons learned into training exercises (ENT7-R5/R6).

## Rollback / Escalation

If the station cannot be safely re-armed, keep the brake engaged and
follow the station-failure runbook for failover.
