# RESIDUAL Documentation

RESIDUAL is now broader than the original verification harness. The repository contains a verification kernel, Command Station operator surface, Factory/Studio multi-worker runtime, adaptive assurance and external-evidence tooling, and an enterprise control layer. The central authority model is unchanged: workers produce proposals; independent policy, evidence, verification, and deterministic integration decide what becomes accepted state.

This page is the current documentation map. **Source, tests, and requirement traceability are authoritative for implementation status. Normative specs may describe work ahead of the implementation.**

## Current status — 2026-09-14

The package reports version **0.5.0** and requires Python 3.11+. The repository has moved materially beyond the older v0.4 Command Station description.

### Implemented surfaces

| Surface | Current role | Primary docs |
| --- | --- | --- |
| Harness | Obligation DAGs, evidence, verification, residual delegation, receipts, budgets and traces | [`architecture.md`](architecture.md), [`research.md`](research.md) |
| Command Station | Self-hosted operator UI, run control, providers, observations, local/cloud execution and packaging | [`station/`](station/) |
| Factory / Studio | Frozen plans, bounded workers, multi-worker execution, evidence flow and deterministic integration | [`factory/`](factory/), [`studio/`](studio/) |
| Assurance / evaluation | Verifier-quality and controlled/external evidence infrastructure | [`assurance-evaluation.md`](assurance-evaluation.md), [`EXTERNAL_ASSURANCE_EVIDENCE.md`](EXTERNAL_ASSURANCE_EVIDENCE.md), [`controlled-evaluation.md`](controlled-evaluation.md) |
| Enterprise | IAM, compliance/audit, tenancy, HA/DR, supply-chain controls, integrations, governance and commercial/licensing controls | [`enterprise/README.md`](enterprise/README.md), [`enterprise/TRACEABILITY.md`](enterprise/TRACEABILITY.md) |

The enterprise implementation maps **SPEC-ENT-001 through SPEC-ENT-008 (62 requirements)** into `residual/iam/`, `residual/compliance/`, `residual/tenancy/`, `residual/hadr/`, `residual/supplychain/`, `residual/integrations/`, and `residual/licensing/`, with requirement-to-test traceability under `docs/enterprise/` and `tests/enterprise/`.

External live assurance tooling is also present so provider-backed execution can be evaluated separately from scripted development fixtures. Treat generated live evidence as experimental evidence tied to its workload, provider, configuration, and commit—not as a universal reliability claim.

### Pending integration

The governed OpenClaw execution adapter is currently in **PR #10**, not `main`. Its intended boundary is: **OpenClaw executes; Residual decides whether the execution counts.** Until that PR lands, do not describe OpenClaw as a main-branch capability. The PR contains `SPEC-OPENCLAW-001`, the adapter, tests, and integration documentation.

## 1. Understand the thesis

Start with [`research.md`](research.md). RESIDUAL's working hypothesis is that useful system-level reliability can emerge from **constraining, observing, verifying, and deterministically integrating** computation that is itself stochastic and imperfect.

The longer IEEE-style manuscript is [`papers/reliability-from-unreliable-computation.md`](papers/reliability-from-unreliable-computation.md). It is a working research paper, not a claim that the hypothesis has already been experimentally established.

## 2. Understand the verification kernel

Read [`architecture.md`](architecture.md) for the obligation-level architecture: ready frontiers, verifier-owned acceptance, evidence negotiation, residual packet compilation, privacy propagation, receipt-bound caching, budgets, and audit limits.

The newer platform layers add execution breadth around this kernel; they do not transfer acceptance authority into workers.

## 3. Run the system

Use [`quickstart.md`](quickstart.md) for the harness and repository-level [`../START-HERE.md`](../START-HERE.md) for Command Station installation and operation.

Station-specific documentation lives under [`station/`](station/), including architecture, run control, modular provider/observation layers, distributed workers, validation, research notes, and specification format.

## 4. Understand Factory and Studio

[`factory/PLAN-CONTRACT.md`](factory/PLAN-CONTRACT.md) documents the frozen execution-plan boundary. [`studio/README.md`](studio/README.md) relates Factory to the broader Studio architecture, [`studio/PLATFORM_VISION.md`](studio/PLATFORM_VISION.md) describes direction, and [`studio/STUDIO_SPECS.md`](studio/STUDIO_SPECS.md) contains normative design material.

Current Factory/Studio work includes bounded worker contracts, isolated worktrees, deterministic scheduling/integration, evidence and receipt plumbing, heterogeneous engine routing, orchestration-tax and verifier-quality work, distributed-state boundaries, async/observability infrastructure, and CI evidence preservation. Verify individual mechanisms against source/tests before relying on experimental APIs.

## 5. Understand enterprise controls

Read [`enterprise/README.md`](enterprise/README.md) first, then [`enterprise/TRACEABILITY.md`](enterprise/TRACEABILITY.md) when auditing requirement coverage. The normative source is [`enterprise/ENTERPRISE_SPECS.md`](enterprise/ENTERPRISE_SPECS.md).

Enterprise implementation covers eight specification families and 62 requirements. This means the mechanisms exist in the repository and have mapped tests/traceability; it does **not** by itself mean every external identity provider, HA topology, regulatory regime, integration endpoint, or production deployment has received independent certification or production validation.

## 6. Evaluate claims

Use [`controlled-evaluation.md`](controlled-evaluation.md) for controlled study design, [`evaluation.md`](evaluation.md) and [`assurance-evaluation.md`](assurance-evaluation.md) for evaluation tooling, and [`EXTERNAL_ASSURANCE_EVIDENCE.md`](EXTERNAL_ASSURANCE_EVIDENCE.md) for provider-backed external evidence.

Development fixtures demonstrate controller behavior. External runs improve ecological validity but remain bounded observations. Neither alone proves universal model-quality preservation, cost reduction, verifier completeness, or system-level reliability.

| Level | Meaning |
| --- | --- |
| Implemented | Mechanism exists in source and is expected to have tests/contracts |
| Demonstrated | Behavior has been exercised by repository fixtures, CI, or recorded evidence |
| Externally exercised | Behavior has been run against provider-backed/external workloads under recorded conditions |
| Hypothesized | Expected system property that still requires controlled evaluation |
| Established | Reserved for conclusions supported by appropriate reproducible experimental evidence |

## 7. Extend the system

Use [`extending.md`](extending.md) for the extension model and [`module-tutorial.md`](module-tutorial.md) for a small module walkthrough. New execution engines, verifiers, integrations, worker runtimes, or enterprise adapters should preserve the authority boundaries: workers propose, verifiers decide, evidence remains attributable, and accepted state crosses a deterministic integration boundary.

## Core invariants

- `FAIL` and `UNKNOWN` never silently accept work.
- A worker cannot redefine the verifier that judges its own output.
- Evidence and dependency provenance survive acceptance through receipts/hashes.
- Sensitive evidence does not become remotely eligible merely because a downstream value depends on it.
- Accepted state is an integration-layer decision, not an agent-side effect.
- Parallelism is justified by measured utility, not agent count.
- Verifier quality is part of the assurance model.
- Runtime/provider controls are defense in depth; they do not replace Residual verification authority.
- Enterprise mechanisms must remain traceable to requirements and tests.
- Research claims remain narrower than the implementation's ambitions.

## Verification

The repository's standard no-credential contract path is:

```bash
python3 -m compileall -q residual
python3 -m unittest discover -s tests -v
```

Additional Station/browser, Factory, enterprise, and external-evidence checks have their own documented prerequisites. Pin the exact commit when preserving experimental evidence.

## Status discipline

RESIDUAL is an active research/engineering project with a rapidly changing implementation. Avoid using old version labels as shorthand for repository capability. For a current claim, check in this order:

1. implementation source;
2. tests and CI/evidence artifacts;
3. requirement traceability;
4. implementation guides;
5. normative/future specs and roadmap material.

That ordering keeps the documentation honest as the implementation advances faster than long-form narrative docs.