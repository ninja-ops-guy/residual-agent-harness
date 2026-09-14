# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first orchestration and verification harness for AI-assisted engineering. It treats model output as an untrusted proposal rather than an answer: workers operate inside explicit contracts, actions are observed, outputs are independently checked, and only accepted artifacts cross a deterministic integration boundary.

The central hypothesis is deliberately stronger than “use better models”:

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

RESIDUAL is the applied engineering system used to make that hypothesis testable.

## Why this exists

Most agent systems concentrate capability inside the worker: give a model more context, more tools, more retries, or more autonomy and hope the resulting trajectory is correct. RESIDUAL moves authority out of the worker and into the surrounding system.

A worker may be local or cloud-hosted, weak or strong, deterministic or stochastic. It may fail. What matters is that the harness can bound what it is allowed to do, preserve evidence about what happened, reject unsupported work, escalate only the unresolved residual, and integrate accepted results reproducibly.

That produces a different control loop:

```text
Requirement
    ↓
Frozen contract / execution plan
    ↓
Route + schedule bounded workers
    ↓
Observe execution and collect evidence
    ↓
Independent verification
    ↓
PASS ──→ deterministic acceptance / integration ──→ receipt
  │
  └─ FAIL / UNKNOWN ──→ counterexample or residual packet ──→ retry / escalate
```

The model is a replaceable compute component. The harness owns authority.

## What is implemented

RESIDUAL currently spans three connected layers.

### Residual Harness — verification kernel

The original harness provides obligation DAGs, immutable evidence snapshots, verifier-defined acceptance, counterexample-directed repair, residual delegation, evidence negotiation, receipt-bound caching, disclosure controls, budgets, and tamper-evident traces.

Accepted work is monotonic within an evidence snapshot. `FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider errors, and abstention never silently become success.

### Command Station — operator surface

Command Station exposes the harness as a self-hosted operations console with mission/spec import, run control, local/cloud execution, provider routing, observation traces, model management, HITL hooks, security inspection, downloadable evidence, and source-release packaging.

It supports OpenAI, OpenAI-compatible endpoints, Anthropic, Gemini, Azure, Bedrock, and Ollama routes through bounded adapters. Local-first execution and residual cloud escalation are policy decisions rather than assumptions.

### Factory / Studio — multi-worker execution platform

The newer Factory runtime extends the kernel toward Residual Studio: requirements are compiled into frozen execution plans, bounded workers run in isolated worktrees, observations and evidence are carried across explicit interfaces, and accepted outputs move through deterministic integration rather than free-form agent coordination.

Current platform work includes:

- deterministic requirement compilation and plan freezing;
- worker contracts, bounded swarm runtime, and isolated worktrees;
- evidence/observation plumbing and deterministic integration primitives;
- adaptive assurance with verifier-quality profiles;
- learned orchestration-tax estimates so the system can learn when **not** to swarm;
- verified compute-market selection across heterogeneous engines;
- quorum/authoritative-log boundaries for distributed state;
- engine adapters, async I/O, observability, metrics, and operational integration work;
- CI evidence that preserves exact source, tree identity, and test output for Factory changes.

The long-term Studio direction is a self-hosted engineering platform in which heterogeneous workers can be scheduled for useful parallelism without surrendering verification, provenance, policy, or integration authority.

## Design principles

1. **Workers propose; verifiers decide.** Generation and acceptance are separate authorities.
2. **Unknown is not pass.** Uncertainty remains visible instead of being coerced into success.
3. **Contracts precede execution.** Scope, tools, resources, dependencies, evidence, and checks should be explicit before a worker starts.
4. **Evidence survives handoffs.** Receipts bind accepted results to inputs, verifier revisions, dependencies, and artifacts.
5. **Escalate the residual, not the whole problem.** Preserve accepted independent work and transfer only unresolved obligations and permitted evidence.
6. **Integration is deterministic.** Stochastic workers do not get unilateral authority over accepted state.
7. **Parallelism must earn its cost.** Swarms are evaluated against coordination overhead, latency, rework, rejection, and integration risk—not agent count.
8. **Verifier reliability is itself measured.** Assurance depends on the quality and coverage of the checks, not merely their existence.
9. **Local and cloud compute are interchangeable resources subject to policy.** Capability, cost, privacy, latency, and observed quality can all affect routing.
10. **Claims require evidence.** The repository distinguishes implemented mechanisms, development evidence, hypotheses, and conclusions that still require controlled study.

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher builds the Station environment and serves the UI at `http://localhost:8765`. Model weights are downloaded on demand; this repository is not an offline model distribution.

Native mode requires Python 3.11+ and Git and has no required pip dependencies for the Station path:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md) for installation, GPU options, repositories, storage, and troubleshooting.

### Factory planning

The Factory path is intentionally contract-first. Start with the plan contract and CLI documentation before attaching real workers:

- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/studio/README.md`](docs/studio/README.md)
- [`docs/studio/STUDIO_SPECS.md`](docs/studio/STUDIO_SPECS.md)

## Architecture at a glance

| Layer | Responsibility | Trust boundary |
| --- | --- | --- |
| Requirement / plan | Convert intent into explicit obligations and dependencies | Frozen before execution |
| Router / scheduler | Select direct, verified, swarm, ensemble, local, or remote execution | Policy + observed performance |
| Worker runtime | Produce candidate artifacts under bounded contracts | Untrusted computation |
| Evidence bus | Preserve observations, artifacts, hashes, provenance, and outcomes | Append-oriented evidence |
| Verifier layer | Evaluate candidate acceptance and surface counterexamples/UNKNOWN | Independent authority |
| Integrator | Accept only verified work and resolve ordered state transitions | Deterministic authority |
| Receipt / audit layer | Bind accepted state to the conditions under which it was accepted | Reproducibility + audit |

For the original obligation-level invariants, see [`docs/architecture.md`](docs/architecture.md). For the platform direction, see [`docs/studio/PLATFORM_VISION.md`](docs/studio/PLATFORM_VISION.md).

## Research program

RESIDUAL is both software and a research instrument. The current working paper, **“Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems,”** develops the system-level reliability hypothesis and defines experiments intended to falsify it.

The repository does **not** claim that the hypothesis is already proven. The controlled evaluation framework separates controller behavior from model quality and calls for paired trials, ablations, fault injection, model-degradation studies, hidden grading, external task families, and matched baselines.

Start with:

- [`docs/research.md`](docs/research.md) — research claim, prior art, boundaries, and open questions;
- [`docs/papers/reliability-from-unreliable-computation.md`](docs/papers/reliability-from-unreliable-computation.md) — IEEE-style working manuscript;
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md) — controlled study design;
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation tooling and metrics.

## Documentation map

**Start / operate**
- [`START-HERE.md`](START-HERE.md) — installation and Station setup
- [`docs/quickstart.md`](docs/quickstart.md) — harness quick start
- [`docs/faq.md`](docs/faq.md) — common questions

**Understand the system**
- [`docs/architecture.md`](docs/architecture.md) — core harness architecture and invariants
- [`docs/station/ARCHITECTURE.md`](docs/station/ARCHITECTURE.md) — Command Station architecture
- [`docs/station/RUN-CONTROL.md`](docs/station/RUN-CONTROL.md) — goal contracts, quarantine, and loop controls
- [`docs/station/MODULAR-LAYERS.md`](docs/station/MODULAR-LAYERS.md) — providers, observations, and capability boundaries
- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md) — frozen Factory execution-plan contract

**Build / extend**
- [`docs/extending.md`](docs/extending.md) — extension model
- [`docs/module-tutorial.md`](docs/module-tutorial.md) — module tutorial
- [`docs/station/SPECIFICATION.md`](docs/station/SPECIFICATION.md) — Station specification format
- [`docs/studio/STUDIO_SPECS.md`](docs/studio/STUDIO_SPECS.md) — normative Studio specifications

**Research / validate**
- [`docs/research.md`](docs/research.md) — thesis and prior art
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md) — controlled studies
- [`docs/station/VALIDATION.md`](docs/station/VALIDATION.md) — Station validation evidence
- [`docs/roadmap/README.md`](docs/roadmap/README.md) — implementation roadmap
- [`vendor/ldd-kit/PROVENANCE.md`](vendor/ldd-kit/PROVENANCE.md) — LDD provenance

## Verification

```bash
python3 -m unittest discover -s tests -v
node --check residual/station/static/app.js

# optional browser QA
npm install
npx playwright install chromium
npm run test:ui
```

Factory pull requests additionally preserve exact source, Git tree identity, and test output as CI evidence.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier proves only what its contract and evidence allow it to check. Receipts are evidence of checked acceptance under stated inputs, not certificates of arbitrary truth. Plugins and host integrations remain trusted code. Native project commands are opt-in and are not an OS sandbox. Distributed interfaces define consistency boundaries but do not make every deployment production-ready by default.

Likewise, the project does not currently claim a universally optimal scheduler, universal verifier, new foundation model, guaranteed token savings, guaranteed model-quality preservation, or first-in-literature status. Those are empirical or scholarly questions and are treated as such.

## Project status

The repository is moving from the v0.4 Command Station foundation into the Factory/Studio execution and adaptive-assurance layers. The implementation is intentionally evolving faster than a conventional stable API. Read the specs and tests as the authoritative contract for experimental modules, and pin a commit when reproducing results.

---

**RESIDUAL’s thesis is architectural:** do not require stochastic workers to become trustworthy before they can be useful. Make their authority small, their behavior observable, their outputs checkable, and their accepted effects deterministic.