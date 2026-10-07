# Residual Agent Harness — Specification Set

**Status:** Complete canonical set (v0.1.0 → v2.0.0 roadmap)
**Normative language:** RFC 2119
**Last updated:** 2026-09-14

This folder is the single source of truth for all Residual Command
Station / Residual Agent Harness specifications. Documents are ordered
by dependency; each lists its own `Depends on:` header.

## Reading Order

| # | Document | Scope | Target |
|---|---|---|---|
| 1 | [DESIGN.md](DESIGN.md) | Harness design rationale, loop layers | v0.1 |
| 2 | [SPECS.md](SPECS.md) | SPEC-001..008: GoalSpec, Verifier, Brakes, Quarantine, Loop | v0.1 |
| 3 | [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | v0.2.0 gap analysis against SPECS | v0.2.0 |
| 4 | [NETOPS_SECOPS_SPECS.md](NETOPS_SECOPS_SPECS.md) | NetOps/SecOps station modules | v0.3.0 |
| 5 | [WORLD_CLASS_SPECS.md](WORLD_CLASS_SPECS.md) | Verifier-receipt binding, registry, memory, HITL, TUI, trajectory | v0.3.0 → v1.0.0 |
| 6 | [V040_ASSESSMENT.md](V040_ASSESSMENT.md) | Honest v0.4.0 repo assessment | v0.4.0 |
| 7 | [GAP_CLOSURE_SPECS.md](GAP_CLOSURE_SPECS.md) | GAP1..GAP6 closure requirements | v0.4.0 → v0.5.0 |
| 8 | [PHASE_4_5_SPECS.md](PHASE_4_5_SPECS.md) | ECO (ecosystem) + PROD (production) specs | v0.4.0 → v1.0.0 |
| 9 | [RESILIENCE_SPECS.md](RESILIENCE_SPECS.md) | APC, FED, FMV, MAI, PQC resilience layers | v1.0.0 → v2.0.0 |
| 10 | [MESH_SPECS.md](MESH_SPECS.md) | Federated group-chat mesh | v1.0.0+ |
| 11 | [STUDIO_SPECS.md](STUDIO_SPECS.md) | Residual Studio multi-swarm platform ("The Factory") | v1.0.0+ |
| 12 | [M2_M3_M4_SPECS.md](M2_M3_M4_SPECS.md) | Studio milestones M2/M3/M4 + EVAL | v1.0.0+ |
| 13 | [CONTROL_PLANE_SPECS.md](CONTROL_PLANE_SPECS.md) | World-class control plane (CP-R1..R19) | v1.0.0+ |
| 14 | [PATH_TO_10_SPECS.md](PATH_TO_10_SPECS.md) | SPEC-NINE (28 reqs) + SPEC-TEN (20 reqs) | v1.0.0 → v2.0.0 |
| 15 | [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md) | Binding conflict resolutions; supersedes conflicting language | all |
| 16 | [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) | System diagrams (source: main @ e3d4b9c) | reference |

## Milestone Summary

- **v0.5.0** — Gap closure (GAP_CLOSURE_SPECS.md)
- **v1.0.0 ("9.5 rating")** — Engine adapters, production soak, async I/O,
  cluster layer, documentation (PATH_TO_10_SPECS.md, SPEC-NINE). ~12 weeks.
- **v2.0.0 ("10 rating")** — Published research, production at scale,
  ecosystem growth, TEE integration, formal verification
  (PATH_TO_10_SPECS.md, SPEC-TEN). ~52 weeks.

## Conventions

- Requirement IDs are stable once published. Amendments add new IDs;
  they never renumber existing ones.
- `MUST`/`MUST NOT` are normative; `SHOULD`/`MAY` are advisory
  (RFC 2119).
- Where documents disagree, CONFLICT_RESOLUTIONS.md governs.
