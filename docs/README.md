# RESIDUAL Documentation

This directory documents three related surfaces of the same project: the original verification harness, the operator-facing Command Station, and the emerging Factory/Studio multi-worker platform.

If you are new to the repository, read the documents in the order below rather than treating every spec as equally mature.

## 1. Understand the thesis

Start with [`research.md`](research.md). RESIDUAL's working hypothesis is that useful system-level reliability can emerge from **constraining, observing, verifying, and deterministically integrating** computation that is itself stochastic and imperfect.

The longer IEEE-style manuscript is [`papers/reliability-from-unreliable-computation.md`](papers/reliability-from-unreliable-computation.md). It is a working research paper, not a claim that the hypothesis has already been experimentally established.

## 2. Understand the verification kernel

Read [`architecture.md`](architecture.md) for the original obligation-level architecture: ready frontiers, verifier-owned acceptance, evidence negotiation, residual packet compilation, privacy propagation, receipt-bound caching, budgets, and audit limits.

This is the conceptual kernel that the newer platform layers build around.

## 3. Run the system

Use [`quickstart.md`](quickstart.md) for the harness and the repository-level [`../START-HERE.md`](../START-HERE.md) for Command Station installation and operation.

Station-specific documentation lives under [`station/`](station/), including architecture, run control, modular provider/observation layers, distributed workers, validation, research notes, and the specification format.

## 4. Understand Factory and Studio

[`factory/PLAN-CONTRACT.md`](factory/PLAN-CONTRACT.md) describes the concrete frozen execution-plan boundary used by the current Factory implementation.

[`studio/README.md`](studio/README.md) explains how Factory relates to the broader Residual Studio direction. [`studio/PLATFORM_VISION.md`](studio/PLATFORM_VISION.md) is the product/architecture vision, while [`studio/STUDIO_SPECS.md`](studio/STUDIO_SPECS.md) is normative design material.

**Important:** normative specifications can lead implementation. Treat tests and current source as the authority for what is implemented today.

## 5. Evaluate claims

Use [`controlled-evaluation.md`](controlled-evaluation.md) for the controlled study design and [`evaluation.md`](evaluation.md) for evaluation tooling/metrics. Development fixtures demonstrate controller behavior; they do not prove that a real model preserves quality, reduces cost, or makes cloud reasoning necessary.

[`cic-integration.md`](cic-integration.md) documents the opt-in structural grouping
and bounded CIC feasibility checks in the original obligation harness, including
receipt semantics, model limits, and the three-arm scripted comparison.

The project intentionally distinguishes:

| Level | Meaning |
| --- | --- |
| Implemented | Mechanism exists in source and should be covered by tests/contracts |
| Demonstrated | Behavior has been exercised by repository fixtures or CI evidence |
| Hypothesized | Expected system property that still requires controlled evaluation |
| Established | Reserved for conclusions supported by appropriate experimental evidence |

## 6. Extend the system

Use [`extending.md`](extending.md) for the extension model and [`module-tutorial.md`](module-tutorial.md) for a small module walkthrough. New execution engines, verifiers, integrations, or worker runtimes should preserve the project's authority boundaries: workers propose, verifiers decide, and the harness integrates accepted state.

## Core invariants

Across the repository, the following ideas should remain stable even as individual APIs evolve:

- `FAIL` and `UNKNOWN` never silently accept work.
- A worker cannot redefine the verifier that judges its own output.
- Evidence and dependency provenance survive acceptance through receipts/hashes.
- Sensitive evidence does not become remotely eligible merely because a downstream value depends on it.
- Accepted state is an integration-layer decision, not an agent-side effect.
- Parallelism is justified by measured utility, not by maximizing agent count.
- Verifier quality is part of the assurance model.
- Research claims remain narrower than the implementation's ambitions.

## Status

RESIDUAL is an active research/engineering project. The Command Station foundation is usable, while Factory/Studio and adaptive-assurance components are evolving rapidly. Pin commits for reproducible experiments and read module tests/specifications before depending on experimental interfaces.
