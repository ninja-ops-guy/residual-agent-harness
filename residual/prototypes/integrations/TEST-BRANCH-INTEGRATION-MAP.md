# Integration Specs → IE Test-Branch Map

This file defines how the integration specs are staged into the inference-engineering test/spec branches. It does not authorize implementation.

All integrations are governed by **INT-000** and remain dormant until their IE prerequisites are qualified.

| IE branch | Integration specs staged for testing/review |
|---|---|
| IE-001 / #160 | INT-000, INT-002, INT-006, INT-008, INT-010, INT-011, INT-014, INT-015, INT-016, INT-017 |
| IE-002 / #161 | INT-000, INT-001, INT-006, INT-014 |
| IE-003 / #162 | INT-000, INT-003, INT-005, INT-007, INT-012 |
| IE-004 / #163 | INT-000, INT-004 |
| IE-005 / #164 | INT-000, INT-004, INT-005, INT-012, INT-013 |
| IE-006 / #166 | INT-000, INT-004, INT-005, INT-007, INT-009, INT-013 |
| IE-007 / #167 | INT-000 plus this map; downstream integrations consume IE-007 diagnostics but none receives new authority from IE-007 |

## Staging rule

Duplicate spec files on multiple branches are intentional planning copies. Before implementation, the accepted/qualified version on then-current `main` is canonical; stale branch copies must be refreshed rather than merged blindly.

## Governance

Normal merge qualification follows the merged solo-maintainer policy (#168): automated qualification appropriate to scope plus exact-head maintainer attestation. Independent/third-party review remains a separate claim when it actually occurs or when a specific research/security claim requires it.
