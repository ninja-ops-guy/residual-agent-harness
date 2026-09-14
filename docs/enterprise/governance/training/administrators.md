# Training: Administrators (ENT7-R5, ENT7-R6)

Requirement: **ENT7-R5** — role-specific training for Administrators
(configuration, module management, troubleshooting). Requirement:
**ENT7-R6** — hands-on exercises against a **sandboxed Residual instance**
are mandatory.

Tracked via `residual/licensing/training.py` (`TrainingRecord`, role
`administrator`). Required exercises: `configure_station`,
`install_module_with_rollback`, `diagnose_station_failure`.

## Modules

1. **Station configuration** (2h): config layout, versioned backups,
   brake thresholds, HITL policies, engine adapter registration.
2. **Module management** (2h): marketplace, signatures, the
   module-installation runbook (ENT7-R4): validation gates, monitoring,
   rollback.
3. **Licensing administration** (1h): tiers, per-node/per-task/flat
   metering (ENT8-R7), reading `UsageMeter` overage reports.
4. **Troubleshooting** (2h): log/receipt forensics, station-failure
   runbook, failover drill procedure, support-tier escalation (ENT8-R2).

## Hands-On Exercises (Sandbox Required, ENT7-R6)

| Exercise | ID | Task | Pass criteria |
|---|---|---|---|
| Configure a station | `configure_station` | From baseline image, configure brakes, HITL policy, and one engine adapter | Smoke task receipts PASS; config snapshot saved |
| Install and roll back a module | `install_module_with_rollback` | Validate + install a module; trigger the seeded defect; execute the full rollback path | Validation gates documented; rollback restores baseline; receipts verify |
| Diagnose a station failure | `diagnose_station_failure` | Sandbox kills the station process; run failover/restore runbook | Standby promoted or restore completed; chain integrity verified |

## Assessment

All three exercises completed in the sandbox (`sandboxed=True`) mark the
administrator curriculum complete; failover drills repeat quarterly.
