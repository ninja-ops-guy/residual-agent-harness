# Support Tiers (ENT8-R2)

Requirement: **ENT8-R2** — Residual MUST offer Standard, Premium, and
Enterprise support tiers. SLAs are enforced in code by
`residual/licensing/support.py` (`SlaTracker`, `SupportTier`, `Severity`),
including the 1-hour P1 response timer.

## Tier Matrix

| | **Standard** | **Premium** | **Enterprise** |
|---|---|---|---|
| Coverage hours | Business hours (9×5) | 24/7 | 24/7 |
| Response SLA | 24 hours | 4 hours | **1 hour for P1** (4h P2, 8h P3) |
| Channels | Email only | Email + phone | Email + phone + on-site option |
| Dedicated support engineer | — | — | Yes |
| On-site support | — | — | Optional (annual on-site included) |
| Runbook co-development | — | — | Quarterly review of customer runbooks (ENT7-R4) |

## Severity Definitions

- **P1** — production execution halted (brake engaged system-wide,
  station down without failover, data integrity at risk).
- **P2** — degraded operation (single engine down, elevated violation
  rate, HITL backlog).
- **P3** — questions, cosmetic issues, feature requests.

## SLA Mechanics (implemented in `SlaTracker`)

- Case opened via an allowed channel for the tier (channel enforcement in
  code: Standard rejects phone, Premium rejects on-site).
- First response measured from `opened_at` to `first_response_at`;
  `breached()` reports SLA violations; `overdue(now)` flags unanswered
  cases past their timer (e.g. 3600s for Enterprise P1).
- `compliance_report()` produces per-tier adherence reports for quarterly
  business reviews and auditor review (ENT7-R5 auditor curriculum).

## SLA Credits

Missed response SLAs accrue service credits: 5% of the monthly support fee
per breached P1, capped at 50% per month, claimed against the next invoice.

## Escalation

Enterprise: dedicated engineer → support manager → VP Engineering
(30-minute P1 cadence). Premium/Standard: tier queue → on-call engineer
per severity timer.
