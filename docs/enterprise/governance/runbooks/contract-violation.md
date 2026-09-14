# Runbook: Contract Violation — Containment and Post-Mortem (ENT7-R4)

Requirement: **ENT7-R4** — runbook template for the "contract violation"
operational scenario.

## Overview

A contract violation occurs when a verifier check returns FAIL — output
fails schema, behavior violates a contract predicate, or an engine
attempts a disallowed action. Violations are containment events, not just
bugs.

## Detection

- Alert: `contract_violation` with task ID, check name, and verifier name
  (`domain:evaluator`).
- Threshold alarm: repeated violations trip a brake automatically —
  coordinate with the brake-tripped runbook.

## Containment (0–15 min)

1. **Park the task**: the violating task is automatically parked; confirm
   it cannot retry.
2. **Quarantine outputs**: any values produced by the failing step move to
   quarantine (`residual/quarantine.py`); downstream tasks consuming them
   are blocked.
3. **Assess blast radius**: walk the receipt graph for parent/child
   dependencies of the violating step; list affected tasks.
4. If the violation indicates active unsafe behavior (data modification,
   external calls), keep the brake engaged until investigated.

## Investigation

1. Retrieve the failing check: contract predicate, expected vs. actual.
2. Classify:
   - **Engine fault** — engine produced malformed output.
   - **Contract defect** — the contract itself is wrong or underspecified.
   - **Module defect** — a module injected invalid behavior.
   - **Adversarial input** — task payload attempted policy bypass
     (treat as a security event; see ENT7-R3 threat model).
3. Verify receipt integrity over the affected window.

## Resolution

- Engine fault: patch/rollback the engine adapter; re-run the task.
- Contract defect: fix the contract via change management (CAB); do not
  weaken a contract merely to pass.
- Module defect: invoke the module-installation runbook rollback path.
- Adversarial input: escalate to security; preserve evidence (receipts,
  quarantined payloads).

## Post-Mortem (within 5 business days)

Template sections:

1. Summary and timeline (receipts cited by hash).
2. Root cause (one of the four classes above, with evidence).
3. Containment effectiveness: did brakes/quarantine hold?
4. Corrective actions with owners and due dates.
5. Detection improvement: new verifier checks or alerts.

## Completion Criteria

Post-mortem approved by engineering + compliance; corrective actions
tracked to closure; unresolved violations block pilot graduation
(ENT7-R1 evaluation criteria).
