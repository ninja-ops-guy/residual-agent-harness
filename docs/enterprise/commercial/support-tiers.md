# Support Tiers (ENT8-R2)

> **COMMERCIAL POLICY TEMPLATE / FUTURE OFFERING.** This file does not create a current RESIDUAL v1 support offering, staffing commitment, contractual SLA, service-credit obligation, dedicated-engineer commitment, or on-site support promise. Commercial availability requires an identified contracting entity and executed agreement.

Target requirement: **ENT8-R2** describes proposed Standard, Premium, and Enterprise support tiers. `residual/licensing/support.py` (`SlaTracker`, `SupportTier`, `Severity`) models timers/compliance mechanics; it does not establish staffing, contractual coverage, actual response capability, or payment of credits.

## Proposed Tier Matrix

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

If adopted in an executed commercial agreement, a service-credit schedule may use the modeled percentages below. No credit obligation exists from this repository document alone.

## Escalation

Proposed enterprise escalation: dedicated engineer → support manager → executive escalation. Proposed Premium/Standard routing uses tier queues/on-call roles. These are policy targets, not evidence of currently staffed roles.
