# Enterprise Implementation

This directory documents the enterprise control layer for RESIDUAL, covering **SPEC-ENT-001 through SPEC-ENT-008 (62 requirements)**. The normative specification is [`ENTERPRISE_SPECS.md`](ENTERPRISE_SPECS.md); [`TRACEABILITY.md`](TRACEABILITY.md) maps requirements to implementation and tests.

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

Every requirement ID (`ENTx-Ry`) should remain traceable to implementation/documentation and test evidence. Use [`TRACEABILITY.md`](TRACEABILITY.md) for the detailed mapping rather than inferring completeness from package names.

## Validation

Enterprise tests live under `tests/enterprise/` and are included in the repository's standard unittest discovery path:

```bash
python3 -m unittest discover -s tests -v
```

The repository also carries verifier/acceptance material for the enterprise requirement set. When preserving evidence, record the exact commit and do not rely only on a passing aggregate command; inspect requirement coverage and relevant test output.

## Status semantics

“Implemented” here means mechanisms and requirement mappings exist in the repository. It does **not** mean every supported-looking external system has been exercised against a live production tenant, that every HA/DR topology has been failure-tested, or that the project has received independent regulatory/security certification.

Deployment readiness must be evaluated for the actual identity provider, tenancy model, storage/backup topology, compliance obligations, integrations, secrets infrastructure, and operational environment.