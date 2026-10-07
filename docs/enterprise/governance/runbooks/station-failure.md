# Runbook: Station Failure — Failover and Recovery (ENT7-R4)

Requirement: **ENT7-R4** — runbook template for the "station failure"
operational scenario.

## Overview

A station failure is loss of the Residual control plane (process crash,
host failure, network partition). HA/DR deployments (commercial tier,
ENT8-R7) run a standby station; single-node deployments follow the
restore path.

## Detection

- Health endpoint failure (`/healthz` non-200 for 30s).
- Watchdog alert: no receipts emitted for > 5 minutes during active work.
- Infrastructure alerts (host down, disk full, OOM).

## Failover (HA/DR, target RTO 15 min / RPO 5 min)

1. Confirm primary is truly down (avoid split-brain): check host, network,
   and process from out-of-band monitoring.
2. Fence the primary: revoke its receipt-store write credentials.
3. Promote the standby: `residual station promote --standby <id>`.
   Promotion is receipted.
4. Standby replays the replicated receipt store and rebuilds queue state;
   in-flight tasks resume from their last receipted step.
5. Redirect operator/API traffic (DNS or load balancer).
6. Verify: submit a smoke task; confirm receipt chain continuity (the
   first post-failover receipt's parent must be the last primary receipt).

## Single-Node Restore

1. Provision replacement host from the baseline image.
2. Restore station configuration from the versioned config backup.
3. Restore/re-attach the receipt store; run full chain verification
   before accepting tasks.
4. Start the station in read-only mode; auditors verify integrity; then
   enable execution.

## Data Integrity Checks (Mandatory)

- Receipt hash chain verifies with zero gaps.
- Quarantine store reconciled (no orphaned references).
- HITL pending challenges re-surfaced to approvers.

## Post-Recovery

1. Declare recovery complete only after the integrity checks pass.
2. Record downtime against the support SLA (ENT8-R2) and, for pilots,
   against pilot metrics (ENT7-R1).
3. Post-mortem if downtime exceeded the tier target.

## Prevention

- HA/DR tier with standby replication (ENT8-R7 feature `ha_dr`).
- Quarterly failover drill (attested in training records, ENT7-R6).
