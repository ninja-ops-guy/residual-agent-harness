# RESIDUAL

**Reliable AI systems without assuming reliable AI workers.**

RESIDUAL is an evidence-first orchestration, verification, and integration harness for AI-assisted engineering. Models are treated as untrusted compute: they can propose work, but they do not get to decide whether that work is correct or whether it should become accepted state.

The core idea is simple:

> **Reliability can come from the system around the model — by constraining execution, preserving evidence, independently verifying outputs, and integrating accepted work deterministically.**

That is the project thesis and the engineering target.

## What problem RESIDUAL is trying to solve

Agent systems are getting more capable, but capability and trustworthiness are not the same thing. A stronger model can still hallucinate, overwrite correct work, misuse tools, leak context, produce inconsistent patches, or confidently pass bad state downstream.

RESIDUAL takes the opposite approach from “just trust the agent more.” It keeps authority outside the worker.

A worker can be:

- local or cloud-hosted;
- cheap or expensive;
- deterministic or stochastic;
- weak, strong, specialized, or unreliable.

The harness decides what the worker is allowed to touch, what evidence it can see, how its output is checked, whether it is accepted, and how accepted state is integrated.

## The control loop

```text
Intent
  ↓
Frozen plan / contract
  ↓
Route work to bounded workers
  ↓
Observe execution + preserve evidence
  ↓
Independent verification
  ↓
PASS ───────────────→ deterministic integration ─→ receipt
  │
  └─ FAIL / UNKNOWN → counterexample / residual ─→ retry or escalate
```

The important boundary is this:

**workers generate candidates; the harness owns acceptance.**

## What makes it different

RESIDUAL is not mainly a prompt framework and it is not trying to maximize agent count.

It is built around a few harder boundaries:

- **Verifier-owned acceptance** — workers cannot approve their own output.
- **UNKNOWN stays UNKNOWN** — uncertainty is not coerced into success.
- **Residual escalation** — preserve accepted work and escalate only what remains unresolved.
- **Evidence-bound receipts** — accepted outputs are tied to inputs, dependencies, verifier revisions, and artifacts.
- **Deterministic integration** — stochastic workers do not directly own accepted state transitions.
- **Measured orchestration** — swarms must justify their coordination overhead.
- **Verifier quality tracking** — the assurance layer itself is measured instead of assumed trustworthy.
- **Policy-aware compute routing** — local/cloud engines can be selected by capability, cost, privacy, latency, and observed quality.

The result is closer to a control plane for unreliable computation than a conventional autonomous-agent loop.

## Current architecture

RESIDUAL has three connected layers.

### 1. Harness — verification kernel

The original harness provides obligation DAGs, immutable evidence snapshots, verifier-defined acceptance, counterexample-directed repair, evidence negotiation, residual delegation, disclosure policy, receipt-bound caching, budgets, and tamper-evident traces.

This is where the core trust model lives.

### 2. Command Station — operator surface

Command Station turns the harness into a self-hosted operations console for running specs, managing local/cloud models, observing execution, reviewing evidence, handling HITL boundaries, and exporting verified artifacts.

Current provider routes include OpenAI, OpenAI-compatible endpoints, Anthropic, Gemini, Azure, Bedrock, and Ollama.

### 3. Factory / Studio — multi-worker execution layer

Factory is the current implementation path toward Residual Studio.

It adds:

- deterministic requirement compilation and plan freezing;
- worker contracts and bounded runtime execution;
- isolated Git worktrees;
- evidence and observation plumbing;
- deterministic integration primitives;
- verifier-quality profiles;
- orchestration-tax learning;
- compute-market selection across heterogeneous engines;
- quorum-aware distributed-state boundaries;
- engine adapters, async I/O, metrics, and operational integrations.

The goal is not “more agents.” The goal is **useful parallelism under verification and control**.

## Adaptive assurance

The newer assurance layer lets RESIDUAL reason about the reliability and cost of its own execution strategies.

For example:

- `VerifierQualityProfile` tracks how trustworthy a verifier has actually been.
- `OrchestrationTaxController` learns whether direct execution, strong verification, swarming, or ensembles are worth the added overhead for a task class.
- `VerifiedComputeMarket` ranks eligible engines using capability, quality evidence, privacy, latency, and cost.
- quorum-aware interfaces prevent authoritative state from being treated as valid when the required consistency boundary is unavailable.

This is an important part of the broader research question: **can reliability emerge from the architecture even when the underlying workers remain imperfect?**

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

Native mode:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md) for installation, GPU options, model setup, storage, and troubleshooting.

### Factory / Studio

Start with the execution-plan contract and Studio overview:

- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/studio/README.md`](docs/studio/README.md)
- [`docs/studio/STUDIO_SPECS.md`](docs/studio/STUDIO_SPECS.md)

## Research

RESIDUAL is also a research instrument. The working hypothesis is explored in:

- [`docs/research.md`](docs/research.md) — claim boundaries, prior art, and open questions;
- [`docs/papers/reliability-from-unreliable-computation.md`](docs/papers/reliability-from-unreliable-computation.md) — IEEE-style working paper;
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md) — controlled study design;
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation tooling and metrics.

The project does **not** claim that the hypothesis is already proven. Development fixtures can show that the controller behaves as intended; they do not establish real-model quality preservation, universal cost savings, production readiness, or first-in-literature status.

## Documentation

Start with [`docs/README.md`](docs/README.md).

A few key references:

- [`docs/architecture.md`](docs/architecture.md) — core harness architecture and invariants
- [`docs/station/ARCHITECTURE.md`](docs/station/ARCHITECTURE.md) — Command Station architecture
- [`docs/station/RUN-CONTROL.md`](docs/station/RUN-CONTROL.md) — run-control and safety boundaries
- [`docs/station/MODULAR-LAYERS.md`](docs/station/MODULAR-LAYERS.md) — provider and observation layers
- [`docs/studio/PLATFORM_VISION.md`](docs/studio/PLATFORM_VISION.md) — Studio platform direction
- [`docs/studio/STUDIO_SPECS.md`](docs/studio/STUDIO_SPECS.md) — normative Studio specifications
- [`docs/roadmap/README.md`](docs/roadmap/README.md) — roadmap and implementation tracks

## Verify

```bash
python3 -m unittest discover -s tests -v
node --check residual/station/static/app.js

# optional browser QA
npm install
npx playwright install chromium
npm run test:ui
```

Factory-related CI also preserves exact source identity and test evidence for the run.

## Status

RESIDUAL is active R&D. The Command Station foundation is usable; Factory, Studio, and adaptive-assurance interfaces are still evolving. For experimental modules, treat source, tests, and normative specs as the authority for the commit you are using.

## Scope

RESIDUAL is not a universal proof system. A verifier is only as strong as its contract, implementation, and evidence. Receipts prove checked acceptance under stated conditions; they do not certify arbitrary truth. Plugins and host integrations remain trusted code, and not every runtime boundary is an OS sandbox.

---

**The project is built around one constraint: unreliable workers can be useful, but they should never be the sole authority for deciding that their own work is correct.**