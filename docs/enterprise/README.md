# Enterprise Implementation

This directory contains the enterprise-layer implementation of the
Residual Command Station, covering SPEC-ENT-001 through SPEC-ENT-008
(62 requirements). The normative spec text is in
[ENTERPRISE_SPECS.md](ENTERPRISE_SPECS.md).

| Spec | Title | Implementation |
|---|---|---|
| SPEC-ENT-001 | Enterprise IAM | `residual/iam/` |
| SPEC-ENT-002 | Compliance & Audit | `residual/compliance/` |
| SPEC-ENT-003 | Multi-Tenancy | `residual/tenancy/` |
| SPEC-ENT-004 | HA / DR | `residual/hadr/` |
| SPEC-ENT-005 | Supply Chain Security | `residual/supplychain/` + `docs/enterprise/supplychain/` |
| SPEC-ENT-006 | Enterprise Integration Hub | `residual/integrations/` |
| SPEC-ENT-007 | Change Management & Governance | `residual/licensing/` (pilot evaluator) + `docs/enterprise/governance/` |
| SPEC-ENT-008 | Commercial & Legal | `residual/licensing/` + `docs/enterprise/commercial/` |

Every requirement ID (ENTx-Ry) is referenced verbatim in the
implementing module or document. See [TRACEABILITY.md](TRACEABILITY.md)
for the full requirement → implementation → test mapping.

Tests live in `tests/enterprise/` and run with the standard suite:
`python3 -m pytest tests/ -q`.
