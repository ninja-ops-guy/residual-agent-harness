# RESIDUAL Documentation

This directory covers the full project: the original verification harness, Command Station, Factory, Residual Studio, evaluation tooling, and the research program behind them.

The easiest way to understand the repository is to read it in layers.

## Start here

If you only read five documents, use this order:

1. [`../README.md`](../README.md) — what RESIDUAL is and why it exists.
2. [`architecture.md`](architecture.md) — the verification kernel and trust model.
3. [`studio/README.md`](studio/README.md) — how Factory/Studio extend that kernel.
4. [`research.md`](research.md) — the research claim, prior art, and non-claims.
5. [`controlled-evaluation.md`](controlled-evaluation.md) — how the hypothesis is meant to be tested.

## By goal

| I want to... | Read |
| --- | --- |
| Install and run Command Station | [`../START-HERE.md`](../START-HERE.md) |
| Understand the core architecture | [`architecture.md`](architecture.md) |
| Understand Station internals | [`station/ARCHITECTURE.md`](station/ARCHITECTURE.md) |
| Understand run-control boundaries | [`station/RUN-CONTROL.md`](station/RUN-CONTROL.md) |
| Understand provider / observation layers | [`station/MODULAR-LAYERS.md`](station/MODULAR-LAYERS.md) |
| Understand Factory execution plans | [`factory/PLAN-CONTRACT.md`](factory/PLAN-CONTRACT.md) |
| Understand the Studio direction | [`studio/README.md`](studio/README.md) and [`studio/PLATFORM_VISION.md`](studio/PLATFORM_VISION.md) |
| Read normative Studio requirements | [`studio/STUDIO_SPECS.md`](studio/STUDIO_SPECS.md) |
| Extend the harness | [`extending.md`](extending.md) |
| Build a module | [`module-tutorial.md`](module-tutorial.md) |
| Review validation evidence | [`station/VALIDATION.md`](station/VALIDATION.md) |
| Review research claims | [`research.md`](research.md) |
| Read the working paper | [`papers/reliability-from-unreliable-computation.md`](papers/reliability-from-unreliable-computation.md) |
| Understand experiments and metrics | [`controlled-evaluation.md`](controlled-evaluation.md) and [`evaluation.md`](evaluation.md) |
| Follow implementation direction | [`roadmap/README.md`](roadmap/README.md) |

## Project layers

### Harness

The verification kernel. This layer defines obligations, evidence boundaries, verifier-owned acceptance, residual escalation, disclosure policy, receipts, caching, budgets, and trace integrity.

### Command Station

The operator-facing surface. It adds mission/spec workflows, local and remote model routing, observation, HITL hooks, run control, evidence export, model management, and operational UX.

### Factory

The current headless implementation path for multi-worker engineering. It introduces frozen execution plans, worker contracts, bounded runtimes, isolated worktrees, evidence flow, and deterministic integration.

### Residual Studio

The broader platform direction. Studio adds orchestration across heterogeneous workers, adaptive assurance, multi-swarm scheduling, compute selection, distributed-state boundaries, and a future engineering workspace around the same verification kernel.

## Core invariants

These ideas should remain true even as individual APIs change:

- workers propose; verifiers decide;
- `FAIL` and `UNKNOWN` do not become success;
- a worker cannot redefine the check that judges its own output;
- evidence and dependency provenance survive acceptance;
- privacy restrictions propagate with the data they protect;
- accepted state is owned by the integration layer;
- parallelism is justified by measured utility, not agent count;
- verifier quality is part of the assurance model;
- claims stay narrower than the implementation's ambitions.

## How to read maturity

Some documents describe current implementation while others describe target architecture. Keep the distinction explicit:

| Label | Meaning |
| --- | --- |
| **Implemented** | Present in source and expected to be covered by tests/contracts |
| **Demonstrated** | Exercised by repository fixtures, CI, or controlled development runs |
| **Hypothesized** | A system property that still requires stronger evaluation |
| **Established** | Reserved for conclusions supported by appropriate evidence |

A normative specification may intentionally lead implementation. For experimental modules, current source and tests are the best description of what exists in a particular commit.

## Research discipline

RESIDUAL is both software and a research instrument. The repository intentionally separates mechanism from conclusion.

For example, implementing residual delegation demonstrates that the mechanism exists. A scripted benchmark can demonstrate that the controller routes a known case correctly. Neither result proves that the approach reduces cost or preserves quality across real models and workloads.

That distinction is central to the project, not a disclaimer added afterward.

## Reproducibility

The project is moving quickly. Pin a commit when reproducing experiments, keep the relevant verifier/configuration revisions with the run, and prefer preserved CI/source evidence over assumptions about `main` at a later date.
