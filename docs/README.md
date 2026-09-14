# RESIDUAL Documentation

This repo now spans a verification kernel, an operator-facing Station, a headless Factory runtime, adaptive assurance, and an expanding Studio/swarm platform. The documentation is easier to follow if you read it by **system boundary** instead of by file age.

## Start here

If you only read five documents, use this order:

1. [`../README.md`](../README.md) — what RESIDUAL is now.
2. [`architecture.md`](architecture.md) — original verification kernel and invariants.
3. [`factory/M2-EXECUTION.md`](factory/M2-EXECUTION.md) — bounded worker execution and quarantine boundary.
4. [`factory/M3-EVIDENCE-BUS.md`](factory/M3-EVIDENCE-BUS.md) — Station-signed receipts and trusted evidence handoff.
5. [`research.md`](research.md) — research claims, prior art, limits, and what remains to be proven.

## System map

### Verification kernel

Read [`architecture.md`](architecture.md) for obligation DAGs, ready frontiers, residual packet compilation, evidence negotiation, privacy propagation, verifier-owned acceptance, caching, budgets, and audit limits.

This is the trust model the rest of the project builds around.

### Command Station

Use [`../START-HERE.md`](../START-HERE.md) to run it.

Station-specific design material lives under [`station/`](station/), including:

- architecture and lifecycle;
- run control and quarantine;
- providers and observations;
- HITL and distributed adapters;
- specification format;
- validation evidence.

### Factory

Factory is no longer only a plan compiler. Current `main` contains concrete worker execution and evidence layers.

Read:

- [`factory/PLAN-CONTRACT.md`](factory/PLAN-CONTRACT.md) — deterministic plan freeze and approval binding;
- [`factory/M2-EXECUTION.md`](factory/M2-EXECUTION.md) — Linux sandboxed workers, worktrees, resource bounds, journals, cancellation, quarantine;
- [`factory/M2-IMPLEMENTATION-STATUS.md`](factory/M2-IMPLEMENTATION-STATUS.md) — exact M2 implementation boundary and known limits;
- [`factory/M3-EVIDENCE-BUS.md`](factory/M3-EVIDENCE-BUS.md) — Station signing, accepted artifacts, receipt chain, dependency admission.

The key Factory invariant is that **candidate completion is not acceptance**. Worker output stays untrusted until trusted Station-side checks accept it.

### Studio / swarm platform

[`studio/README.md`](studio/README.md) is the best entry point for the current platform direction.

The repository also now contains implementation paths for sandbox hardening, red-team tests, cluster and orchestration primitives, evaluation/soak infrastructure, gateway/lifecycle glue, crypto abstractions, connector conformance, Studio frontend development surfaces, and onboarding examples.

The broader target remains documented in:

- [`studio/PLATFORM_VISION.md`](studio/PLATFORM_VISION.md)
- [`studio/STUDIO_SPECS.md`](studio/STUDIO_SPECS.md)

Normative specs can lead implementation. Do not infer production completeness from the presence of a spec alone.

### Adaptive assurance

The assurance layer measures parts of the control plane that ordinary agent frameworks often treat as fixed assumptions:

- verifier quality;
- orchestration overhead;
- compute-engine quality/cost tradeoffs;
- uncertainty and escalation;
- authority/quorum boundaries.

These mechanisms support a system that can learn when **not** to swarm and can fail toward stronger verification or HITL when confidence is insufficient.

## Research and evaluation

Start with [`research.md`](research.md), then use:

- [`papers/reliability-from-unreliable-computation.md`](papers/reliability-from-unreliable-computation.md) — working paper;
- [`controlled-evaluation.md`](controlled-evaluation.md) — controlled study design;
- [`evaluation.md`](evaluation.md) — evaluation tooling;
- swarm/reliability specs and evidence docs under [`swarm/`](swarm/) where present.

The project intentionally separates four claim levels:

| Level | Meaning |
| --- | --- |
| Implemented | mechanism exists in source |
| Demonstrated | tests/fixtures/CI exercise it |
| Hypothesized | system property still under evaluation |
| Established | supported by suitable controlled/external evidence |

A green test suite can establish implementation behavior. It cannot by itself establish universal model quality, cost savings, safety, or scientific novelty.

## Verification evidence

The repo now has layered verification:

```bash
python3 -m unittest discover -s tests -v
python3 verifier/v2/check_specs.py
python3 verifier/v3/check_swarm.py
```

The v3 swarm verifier checks required deliverables, protects owned runtime/evidence/integration boundaries against accidental overlap, runs the full pytest suite, and requires the earlier spec verifier to stay green.

The newest retained merged-tree evidence reports **1,033 pytest tests + 166 subtests passing**.

## Implementation status

[`status/IMPLEMENTATION_STATUS.md`](status/IMPLEMENTATION_STATUS.md) is generated from `implementation-status.yaml`, not hand-authored.

Because the project is currently merging large parallel work streams quickly, the generated status view can temporarily lag the newest source tree. When there is a disagreement, prefer:

1. current source;
2. current tests;
3. component-specific implementation docs;
4. retained verifier evidence;
5. generated status prose.

The manifest/status tooling exists specifically to reduce this drift over time.

## Extend the system

Use [`extending.md`](extending.md) and [`module-tutorial.md`](module-tutorial.md) for extension patterns.

New workers, engines, verifiers, modules, connectors, or UI surfaces should preserve the same authority split:

- workers can generate;
- providers can advise;
- verifiers decide acceptance;
- HITL is explicit;
- evidence binds handoffs;
- the harness owns accepted state.

## Stable invariants

Even while APIs are evolving, these should remain true:

- `FAIL` and `UNKNOWN` never silently accept work.
- A worker cannot redefine its own verifier.
- Successful process exit is not equivalent to accepted output.
- Evidence/provenance survives trusted handoffs.
- Private inputs do not become remotely eligible through derivation alone.
- Accepted state is controlled outside stochastic workers.
- Parallelism must justify its coordination tax.
- Verifier quality is measurable and can affect escalation.
- Research claims stay narrower than implementation ambition.

## Status

RESIDUAL is moving quickly. Pin commits for reproducible experiments and use exact component docs/tests when depending on experimental interfaces.