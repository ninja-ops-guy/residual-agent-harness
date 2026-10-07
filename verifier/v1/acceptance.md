# Verifier v1 — Acceptance Criteria

Objective: Implement all specs (SPEC-ENT-001..008, 62 requirements) in residual-agent-harness.

Checks (verifier/v1/check.sh):
1. Requirement coverage: each ID ENTx-Ry listed in docs/enterprise/ENTERPRISE_SPECS.md
   must appear in at least one file under residual/ or docs/enterprise/ (excluding the spec itself).
2. Mapping doc docs/enterprise/TRACEABILITY.md exists and every referenced file path exists.
3. All new packages import: residual.iam, residual.compliance, residual.tenancy,
   residual.hadr, residual.supplychain, residual.integrations, residual.licensing.
4. Full pytest suite passes (baseline 328 + new enterprise tests).
