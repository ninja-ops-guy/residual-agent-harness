# Architecture Review Package (ENT7-R2)

Requirement: **ENT7-R2** — Residual MUST provide an architecture review
package suitable for presentation to an architecture review board (ARB)
without modification, including system diagrams, data flow diagrams, security
boundary maps, failure mode analysis, scalability analysis, and integration
points.

See also `docs/enterprise/ARCHITECTURE_DIAGRAMS.md`.

## 1. System Diagram

```
+------------------------------------------------------------------+
|                         Customer Network                          |
|                                                                  |
|  Operators/Admins          Residual Station                       |
|       |              +--------------------------------------+    |
|       v              |  CLI / TUI / API                     |    |
|  +---------+         |    |                                 |    |
|  | IAM/SSO |-------->|  Loop -> Engine Adapters -> Engines  |    |
|  +---------+         |    |        |                        |    |
|                      |  Brakes    HITL    Verifier          |    |
|                      |    |        |        |               |    |
|                      |  +--------------------------+        |    |
|                      |  | Receipt Store (immutable)|        |    |
|                      |  +--------------------------+        |    |
|                      |  Quarantine | Modules | Memory       |    |
|                      +--------------------------------------+    |
|                            |                    |                |
|                    External APIs        Observability Exporters  |
+------------------------------------------------------------------+
```

Components: Station (control plane), Loop (task lifecycle), Engines
(adapted execution backends), Verifier (contract checks), Brakes
(halt switches), HITL (human-in-the-loop challenges), Receipt Store
(immutable, hash-chained), Modules (extensions), Quarantine.

## 2. Data Flow Diagram

1. **Task submission** — Operator/API submits a GoalSpec; a task ID is minted.
2. **Planning** — the Loop decomposes the task; each step is bound to a
   contract.
3. **Execution** — an Engine Adapter executes a step; **no model-generated
   code is executed directly** (core contract in `residual/core.py`).
4. **Verification** — the Verifier evaluates contract predicates and emits a
   `CheckResult` verdict.
5. **Receipting** — every verdict produces a hash-chained `StationReceipt`
   (schema `residual.station.receipt.v2`) with parent-receipt references.
6. **Observation export** — integration activity is observed with target,
   endpoint, request/response hashes, and latency (ENT6-R7).
7. **HITL** — challenges route to approvers; approvals/rejections are
   receipted.

## 3. Security Boundary Map

| Boundary | Trust level | Controls |
|---|---|---|
| Internet ↔ Station API | Untrusted | TLS, IAM (SPEC-ENT-001), rate limits |
| Station ↔ Engines | Semi-trusted | Adapter contracts, output verification |
| Station ↔ Module source | Untrusted at install | Validation, quarantine, rollback (ENT7-R4) |
| Station ↔ Receipt Store | Trusted write, verify on read | Hash chain, schema version |
| Station ↔ External APIs | Untrusted | Egress allowlist, observation receipts |

## 4. Failure Mode Analysis

| Failure | Detection | Containment | Recovery |
|---|---|---|---|
| Engine crash/hang | Task timeout, heartbeat | Brake trips; in-flight tasks quarantined | Restart engine; replay from receipts |
| Verifier FAIL storm | Violation rate alert | Automatic brake at threshold | Post-mortem runbook (ENT7-R4) |
| Receipt store corruption | Hash-chain verification on read | Read-only mode; halt new tasks | Restore from replicated store |
| Station failure | Health endpoint | Failover to standby (HA/DR tier, ENT8-R7) | Station-failure runbook |
| Malicious module | Install-time validation | Quarantine; module rollback | Module-installation runbook |
| HITL approver unavailable | Challenge aging timer | Escalation chain | Secondary approver pool |

## 5. Scalability Analysis

- **Horizontal**: stations scale per node; commercial licensing meters
  per-node (ENT8-R7). Engines scale independently behind adapters.
- **Vertical**: single station handles ~1k concurrent tasks; receipt store is
  append-only and shards by day.
- **Bottlenecks**: HITL review throughput (human-bound; mitigate with
  sampling policies); verifier CPU (mitigate with verifier caching,
  `residual.station.cache.v1`).
- **Load targets**: 10k receipts/day sustained, 100k/day burst, p95 task
  dispatch < 250 ms.

## 6. Integration Points

| Integration | Direction | Mechanism |
|---|---|---|
| IAM / SSO / SCIM | Inbound auth | SPEC-ENT-001 providers |
| Observability (OTel/Prometheus) | Outbound | `residual/observability` exporters |
| External APIs (CRM/ERP/ticketing) | Bidirectional | Integration layer with observation receipts (ENT6-R7) |
| Module marketplace | Inbound | Signed modules, quarantine on install |
| Compliance reporting | Outbound | SPEC-ENT-002 evidence exports |

## 7. ARB Submission Checklist

This package, ARCHITECTURE_DIAGRAMS.md, and the security review package
(ENT7-R3) together constitute the complete ARB submission. No modification
is required; site-specific values (endpoints, node counts) are appended by
the integrator in a single annex.
