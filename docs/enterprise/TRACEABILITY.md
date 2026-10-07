# Enterprise Requirement Traceability

Requirement → implementation → tests for SPEC-ENT-001..008.
Normative text: [ENTERPRISE_SPECS.md](ENTERPRISE_SPECS.md).

## SPEC-ENT-001 — Enterprise IAM (package `residual/iam/`, tests `tests/enterprise/test_iam.py`)

| Req | Implementation |
|---|---|
| ENT1-R1 | `residual/iam/saml.py`, `residual/iam/oidc.py`, `residual/iam/crypto.py` |
| ENT1-R2 | `residual/iam/rbac.py` |
| ENT1-R3 | `residual/iam/abac.py` |
| ENT1-R4 | `residual/iam/jit.py` |
| ENT1-R5 | `residual/iam/service_accounts.py` |
| ENT1-R6 | `residual/iam/events.py` |
| ENT1-R7 | `residual/iam/mfa.py` |
| ENT1-R8 | `residual/iam/sessions.py` |

## SPEC-ENT-002 — Compliance & Audit (package `residual/compliance/`, tests `tests/enterprise/test_compliance.py`)

| Req | Implementation |
|---|---|
| ENT2-R1 | `residual/compliance/tagging.py` |
| ENT2-R2 | `residual/compliance/retention.py` |
| ENT2-R3 | `residual/compliance/legal_hold.py` |
| ENT2-R4 | `residual/compliance/residency.py` |
| ENT2-R5 | `residual/compliance/erasure.py` |
| ENT2-R6 | `residual/compliance/reports.py` |
| ENT2-R7 | `residual/compliance/signing.py`, `residual/compliance/reports.py` |
| ENT2-R8 | `residual/compliance/siem.py` |

Foundation: `residual/compliance/log.py` (hash-chained observation log).

## SPEC-ENT-003 — Multi-Tenancy (package `residual/tenancy/`, tests `tests/enterprise/test_tenancy.py`)

| Req | Implementation |
|---|---|
| ENT3-R1 | `residual/tenancy/tenant.py` |
| ENT3-R2 | `residual/tenancy/isolation.py` |
| ENT3-R3 | `residual/tenancy/scheduler.py` |
| ENT3-R4 | `residual/tenancy/delegation.py` |
| ENT3-R5 | `residual/tenancy/policies.py` |
| ENT3-R6 | `residual/tenancy/lifecycle.py` |

## SPEC-ENT-004 — HA / DR (package `residual/hadr/`, tests `tests/enterprise/test_hadr.py`)

| Req | Implementation |
|---|---|
| ENT4-R1 | `residual/hadr/cluster.py` |
| ENT4-R2 | `residual/hadr/replication.py` |
| ENT4-R3 | `residual/hadr/failover.py` |
| ENT4-R4 | `residual/hadr/replication.py`, `residual/hadr/failover.py` |
| ENT4-R5 | `residual/hadr/backup.py` |
| ENT4-R6 | `residual/hadr/restore.py` |
| ENT4-R7 | `residual/hadr/degraded.py` |
| ENT4-R8 | `residual/hadr/events.py` |

Support: `residual/hadr/clock.py`, `residual/hadr/chain.py`.

## SPEC-ENT-005 — Supply Chain Security (package `residual/supplychain/`, tests `tests/enterprise/test_supplychain.py`)

| Req | Implementation |
|---|---|
| ENT5-R1 | `residual/supplychain/signing.py` |
| ENT5-R2 | `residual/supplychain/sbom.py` |
| ENT5-R3 | `residual/supplychain/sbom.py` (vulnerability scanning), `residual/supplychain/audit.py` |
| ENT5-R4 | `residual/supplychain/audit.py` |
| ENT5-R5 | `residual/supplychain/disclosure.py`, `docs/enterprise/supplychain/vulnerability-disclosure-policy.md` |
| ENT5-R6 | `residual/supplychain/pinning.py` |
| ENT5-R7 | `residual/supplychain/sandbox.py` |
| ENT5-R8 | `residual/supplychain/reproducible.py` |

## SPEC-ENT-006 — Integration Hub (package `residual/integrations/`, tests `tests/enterprise/test_integrations.py`)

| Req | Implementation |
|---|---|
| ENT6-R1 | `residual/integrations/itsm.py` |
| ENT6-R2 | `residual/integrations/cicd.py` |
| ENT6-R3 | `residual/integrations/monitoring.py` |
| ENT6-R4 | `residual/integrations/comms.py` |
| ENT6-R5 | `residual/integrations/ticketing.py` |
| ENT6-R6 | `residual/integrations/base.py` (bidirectional API on all connectors) |
| ENT6-R7 | `residual/integrations/base.py` (observed request/response hashes) |

## SPEC-ENT-007 — Change Management & Governance

| Req | Implementation |
|---|---|
| ENT7-R1 | `residual/licensing/pilot.py`, `docs/enterprise/governance/pilot-program.md` |
| ENT7-R2 | `docs/enterprise/governance/architecture-review-package.md` |
| ENT7-R3 | `docs/enterprise/governance/security-review-package.md` |
| ENT7-R4 | `docs/enterprise/governance/runbooks/` |
| ENT7-R5 | `residual/licensing/training.py`, `docs/enterprise/governance/training/` |
| ENT7-R6 | `residual/licensing/training.py` |

Tests: `tests/enterprise/test_licensing.py`.

## SPEC-ENT-008 — Commercial & Legal

| Req | Implementation |
|---|---|
| ENT8-R1 | `docs/enterprise/commercial/entity.md` |
| ENT8-R2 | `residual/licensing/support.py`, `docs/enterprise/commercial/support-tiers.md` |
| ENT8-R3 | `docs/enterprise/commercial/professional-services.md` |
| ENT8-R4 | `docs/enterprise/commercial/ip-indemnification.md` |
| ENT8-R5 | `docs/enterprise/commercial/insurance.md` |
| ENT8-R6 | `docs/enterprise/commercial/financial-stability.md` |
| ENT8-R7 | `residual/licensing/model.py`, `docs/enterprise/commercial/licensing.md` |
| ENT8-R8 | `docs/enterprise/commercial/dpa.md` |
