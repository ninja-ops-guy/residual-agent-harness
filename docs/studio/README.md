# Residual Studio / Factory

Residual Studio is the platform direction built around RESIDUAL's verification kernel. **Factory** is the current headless implementation path toward that platform.

The goal is not to create the largest possible agent swarm. It is to make heterogeneous, potentially unreliable compute useful under a system that retains authority over scope, evidence, verification, scheduling, and integration.

## Architectural thesis

```text
Untrusted workers
      ↓
bounded contracts
      ↓
observable execution
      ↓
independent verification
      ↓
deterministic integration
      ↓
auditable accepted state
```

A worker can be wrong without automatically making the system wrong. Reliability is pursued at the orchestration boundary rather than assumed inside the model.

## Current implementation path

Factory is being built in stages:

1. **Requirement compiler / plan freezing** — turn requested work into a deterministic execution plan with explicit dependencies and approval state.
2. **Worker contract + runtime** — execute bounded workers against isolated worktrees and terminate contract violations rather than treating constraints as prompt conventions.
3. **Evidence and receipts** — carry observations and acceptance evidence across worker and integration boundaries.
4. **Deterministic integration** — make acceptance and state transition an authoritative harness operation, not a worker privilege.
5. **Adaptive assurance** — measure verifier quality, orchestration overhead, compute quality/cost, and distributed-state availability so execution strategy can adapt from evidence.

The repository also contains the broader normative Studio specifications. A specification describes the intended contract; its presence does not by itself mean every requirement is production-complete.

## Adaptive assurance

Recent work adds primitives for a system that can reason about the reliability of its own control plane:

- `VerifierQualityProfile` records verifier outcomes and quality evidence instead of assuming every checker is equally trustworthy.
- `OrchestrationTaxController` learns observed success, cost, and latency by strategy so a swarm must justify its coordination overhead.
- `VerifiedComputeMarket` selects eligible engines using capability, privacy, latency, cost, observed quality, and uncertainty.
- quorum-aware authoritative-log interfaces define a CP-oriented boundary for state that must not be accepted during loss of authoritative consensus.
- assurance execution receipts make the selected strategy and outcome inspectable.

These mechanisms support the larger research question: **can system-level assurance improve even when the underlying workers remain stochastic and individually imperfect?**

## Documents

- [`PLATFORM_VISION.md`](PLATFORM_VISION.md) — product thesis, architecture, operating model, and research questions.
- [`STUDIO_SPECS.md`](STUDIO_SPECS.md) — normative RFC-2119 requirements for the platform architecture, requirement compiler, swarm runtime, evidence bus, parallel metrics, cluster, IDE, and deterministic integration.
- [`../factory/PLAN-CONTRACT.md`](../factory/PLAN-CONTRACT.md) — concrete frozen-plan contract used by the Factory implementation.
- [`../research.md`](../research.md) — research boundaries and prior art.
- [`../papers/reliability-from-unreliable-computation.md`](../papers/reliability-from-unreliable-computation.md) — working paper for the reliability hypothesis.
- [`../controlled-evaluation.md`](../controlled-evaluation.md) — experimental design used to separate architecture claims from model-quality claims.

## Relationship to Command Station

Command Station remains the operator-facing verification and safety kernel. Studio/Factory extends it rather than replacing its core invariants:

- workers do not self-approve;
- `UNKNOWN` does not become success;
- evidence and verifier revisions remain part of acceptance provenance;
- remote disclosure remains policy-controlled;
- HITL remains an explicit boundary;
- accepted state is integrated by the harness.

## What success looks like

Studio is successful if it can make additional compute useful **without making additional autonomy equivalent to additional trust**. The important metrics are therefore not raw worker count. They are verified task success, useful parallel speedup, orchestration tax, verifier false-accept behavior, rework, integration conflicts, disclosure, cost, latency, and the reproducibility of accepted state.
