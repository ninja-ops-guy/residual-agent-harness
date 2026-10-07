# Training: Auditors (ENT7-R5, ENT7-R6)

Requirement: **ENT7-R5** — role-specific training for Auditors (receipt
verification, compliance reporting). Requirement: **ENT7-R6** — hands-on
exercises against a **sandboxed Residual instance** are mandatory.

Tracked via `residual/licensing/training.py` (`TrainingRecord`, role
`auditor`). Required exercises: `verify_receipt_chain`,
`generate_compliance_report`.

## Modules

1. **Receipt anatomy** (1.5h): `StationReceipt` schema
   (`residual.station.receipt.v2`), hash chains, parent references,
   `CheckResult` verdicts, legacy v1 handling.
2. **Verification practice** (2h): offline chain verification, detecting
   gaps/forgeries, quarantine reconciliation, HITL approval audit
   (bulk-approval and self-approval red flags).
3. **Compliance reporting** (2h): mapping evidence to SOC 2 / ISO 27001 /
   GDPR controls (SPEC-ENT-002), generating evidence bundles, DPA audit
   rights (ENT8-R8).
4. **Support and SLA audit** (1h): reading `SlaTracker.compliance_report()`
   for support-tier adherence (ENT8-R2).

## Hands-On Exercises (Sandbox Required, ENT7-R6)

| Exercise | ID | Task | Pass criteria |
|---|---|---|---|
| Verify a receipt chain | `verify_receipt_chain` | Given a sandbox receipt store with a seeded tampered record, verify the chain and locate the forgery | Tamper detected at correct position; findings documented |
| Generate a compliance report | `generate_compliance_report` | Produce a SOC 2 CC7.2 evidence bundle from sandbox receipts and observations | All sampled actions trace to valid receipts; report maps controls per SPEC-ENT-002 |

## Assessment

Both exercises completed in the sandbox mark the auditor curriculum
complete. Auditors also shadow one pilot evaluation cycle (ENT7-R1)
before signing production evidence.
