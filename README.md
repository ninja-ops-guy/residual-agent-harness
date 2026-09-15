# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. It treats model output as an untrusted proposal rather than an answer: workers operate inside explicit contracts, execution is observed, outputs are independently checked, and only accepted artifacts are allowed to cross controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

RESIDUAL is the applied engineering system used to make that hypothesis testable.

**Current-state documentation:** [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Why this exists

Most agent systems concentrate capability and authority inside the worker: give a model more context, tools, retries or autonomy and hope the resulting trajectory is correct. RESIDUAL separates capability from authority.

A worker may be local or cloud-hosted, weak or strong, deterministic or stochastic. It may fail. The surrounding system is responsible for bounding what it can do, preserving evidence about what happened, independently deciding whether work is acceptable, and controlling what becomes durable system state.

```text
Requirement / intent
        ↓
Frozen plan + worker contracts
        ↓
Route / schedule bounded workers
        ↓
Observe execution + collect evidence
        ↓
Independent verification
        ↓
PASS ──→ controlled deterministic integration ──→ receipt / audit
  │
  └─ FAIL / UNKNOWN ──→ counterexample / residual ──→ retry / escalate
```

The model is replaceable compute. The harness owns acceptance authority.

## What is implemented

RESIDUAL now spans a connected platform rather than a single harness.

### Core harness

The original harness provides obligation DAGs, immutable evidence snapshots, verifier-defined acceptance, counterexample-directed repair, residual delegation, evidence negotiation, receipt-bound caching, disclosure controls, budgets and tamper-evident traces.

`FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider errors and abstention never silently become success.

### Command Station

Command Station exposes the harness as a self-hosted operations console with mission/spec import, run control, local/cloud execution, provider routing, observation traces, model management, HITL hooks, security inspection, downloadable evidence and source-release packaging.

Provider paths include OpenAI, OpenAI-compatible endpoints, Anthropic, Gemini, Azure, Bedrock and Ollama through bounded adapters. Local-first execution and cloud escalation are policy decisions rather than architectural assumptions.

### Factory / Studio runtime

The Factory runtime extends RESIDUAL into multi-worker execution:

- deterministic requirement compilation and frozen execution plans;
- immutable worker contracts and isolated worktrees;
- bounded runtime, host-owned termination and journaled observations;
- Station-issued receipts and evidence/artifact binding;
- evidence-bus handoff and trusted-consumption checks;
- deterministic integration and scheduler machinery;
- verifier-quality/adaptive-assurance components;
- orchestration-tax learning and routing research interfaces;
- cluster execution, lifecycle recovery and side-effect gateways;
- sandbox/red-team, crypto, connector-conformance, SLO/alert and observability layers;
- Studio/operator surfaces and executable onboarding paths.

M2/M3/M4 are no longer paper-only concepts: the canonical implementations live under `residual/factory/` and related platform packages. However, **current M4 is not yet fully qualified for live/paper-facing claims**; issue #63 tracks accepted-tree binding, filesystem/link safety, verifier execution isolation and Git-evidence semantics that must be closed first.

### Evaluation and soak infrastructure

`residual/eval/` now provides the main frozen reliability-evaluation apparatus:

- immutable hash-locked `FrozenWorkload` sets;
- repeated configuration runs;
- ablations;
- statistics and comparison reports;
- fault injection;
- report/evidence reconstruction from retained observations;
- measured Factory evaluation hooks.

The project also contains soak infrastructure, but long-duration live qualification is still a future evidence gate rather than a completed claim.

## Design principles

1. **Workers propose; acceptance is independent.** Generation and acceptance are separate authorities.
2. **Unknown is not pass.** Missing or incomparable evidence remains visible.
3. **Contracts precede execution.** Scope, tools, resources, dependencies, evidence and checks should be explicit before work starts.
4. **Evidence survives handoffs.** Receipts bind accepted results to artifacts, dependencies, verifier revisions and relevant identities.
5. **Escalate the residual, not the whole problem.** Preserve accepted independent work and transfer only unresolved obligations/evidence.
6. **Integration is deterministic.** Stochastic workers do not get unilateral authority over accepted state.
7. **Parallelism must earn its cost.** Swarms are evaluated against coordination tax, latency, rework, rejection and integration risk.
8. **Verifier reliability is itself measured.** Assurance depends on verifier precision/recall/coverage, not merely verifier existence.
9. **Local and cloud compute are interchangeable resources subject to policy.** Capability, cost, privacy, latency and observed quality all affect routing.
10. **Claims require exact-tree evidence.** A passing historical commit does not automatically qualify later code.

## Current status and qualification boundary

A major integrated milestone at `412b66c35f7c0e1ac479fe60a5b7d33d5510e3af` recorded **1,033 tests plus 166 subtests green** with verifier v2 green and protected-path ownership checks. That evidence applies to that exact tree.

Current `main` has advanced beyond that point. Before starting paper-facing live reliability evaluation, the priority gates are:

1. close **#63** — harden/qualify the current M4 trust boundary;
2. close **#48** — reconcile stale `implementation-status.yaml` and regenerate the generated status document;
3. classify the retained timing-sensitive Factory OS fail-then-pass behavior;
4. freeze the live evaluation protocol before observing model results;
5. run one fixed live model across R0–R5 and measure raw correctness, acceptance coverage, accepted correctness, AER/ASSR, latency, throughput and cost;
6. only then progress to model-degradation, heterogeneous-routing and 24h → 72h → 30-day soak studies.

See [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md) for the detailed current-state map and claim boundaries.

## Important traceability note

`implementation-status.yaml` and `docs/status/IMPLEMENTATION_STATUS.md` currently contain stale pre-merge entries that still mark M2, M3, M4 and EVAL as `not_started`. That documentation drift is tracked by issue #48. Until it is reconciled, do **not** use those four generated rows as current-state evidence; use the exact code/tests, open qualification issues and [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher builds the Station environment and serves the UI at `http://localhost:8765`. Model weights are downloaded on demand; this repository is not an offline model distribution.

Native mode requires Python 3.11+ and Git:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md) for installation, GPU options, repositories, storage and troubleshooting.

### Factory planning

The Factory path is contract-first. Start with:

- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/factory/M2-EXECUTION.md`](docs/factory/M2-EXECUTION.md)
- [`docs/factory/M3-EVIDENCE-BUS.md`](docs/factory/M3-EVIDENCE-BUS.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Architecture at a glance

| Layer | Responsibility | Trust boundary |
| --- | --- | --- |
| Requirement / plan | Convert intent into explicit obligations and dependencies | Frozen before execution |
| Router / scheduler | Select direct, verified, swarm, ensemble, local or remote execution | Policy + observed performance |
| Worker runtime | Produce candidate artifacts under bounded contracts | Untrusted computation |
| Evidence bus | Preserve observations, artifacts, hashes, provenance and outcomes | Evidence/admission boundary |
| Verifier layer | Evaluate candidate acceptance and surface counterexamples/`UNKNOWN` | Independent authority |
| Integrator | Apply only eligible work and control ordered state transitions | Deterministic authority |
| Receipt / audit | Bind accepted state to evidence, identities and revisions | Reproducibility + audit |
| Evaluation | Measure component correctness vs accepted-state correctness | Independent research boundary |

## Research program

The working paper, **“Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems,”** develops the system-level reliability hypothesis and defines experiments intended to falsify it.

The repository does **not** claim the hypothesis is already proven. The key live experiment must compare, under fixed worker/model capability:

- raw worker correctness `P(X)`;
- acceptance coverage `P(A)`;
- accepted correctness `P(X|A)`;
- Accepted Error Rate (AER) / accepted-system success;
- false acceptance/rejection and verifier `UNKNOWN`;
- cost, latency, throughput and orchestration overhead.

Start with:

- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md) — current implementation/qualification state;
- [`docs/research.md`](docs/research.md) — research claim, prior art and evidence boundaries;
- [`docs/papers/reliability-from-unreliable-computation.md`](docs/papers/reliability-from-unreliable-computation.md) — IEEE-style working manuscript;
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md) — controlled study design;
- [`docs/cic-integration.md`](docs/cic-integration.md) — opt-in CIC constraint grouping, bounded feasibility, and comparison fixtures;
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation/reproduction guidance.

## Documentation map

**Start / operate**
- [`START-HERE.md`](START-HERE.md)
- [`docs/quickstart.md`](docs/quickstart.md)
- [`docs/faq.md`](docs/faq.md)

**Current state**
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)
- [`docs/roadmap/README.md`](docs/roadmap/README.md)

**Understand the system**
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/station/ARCHITECTURE.md`](docs/station/ARCHITECTURE.md)
- [`docs/station/RUN-CONTROL.md`](docs/station/RUN-CONTROL.md)
- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/factory/M2-EXECUTION.md`](docs/factory/M2-EXECUTION.md)
- [`docs/factory/M3-EVIDENCE-BUS.md`](docs/factory/M3-EVIDENCE-BUS.md)

**Build / extend**
- [`docs/extending.md`](docs/extending.md)
- [`docs/module-tutorial.md`](docs/module-tutorial.md)
- [`docs/station/SPECIFICATION.md`](docs/station/SPECIFICATION.md)
- [`docs/studio/STUDIO_SPECS.md`](docs/studio/STUDIO_SPECS.md)

**Research / validate**
- [`docs/research.md`](docs/research.md)
- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/station/VALIDATION.md`](docs/station/VALIDATION.md)

## Verification

```bash
python3 -m unittest discover -s tests -v
node --check residual/station/static/app.js

# optional browser QA
npm install
npx playwright install chromium
npm run test:ui
```

Exact Factory/research claims should additionally retain commit/tree identity and the machine-readable evidence produced by the corresponding qualification run.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier proves only what its contract and evidence allow it to check. Receipts are evidence of checked acceptance under stated conditions, not certificates of arbitrary truth. Plugins and host integrations remain trusted code unless explicitly isolated by another boundary.

The project does not currently claim a universal verifier, universally optimal scheduler, new foundation model, guaranteed token savings, guaranteed quality preservation, blanket production readiness, live proof of the central reliability hypothesis, or first-in-literature status.

---

**RESIDUAL’s thesis is architectural:** stochastic workers do not have to become trustworthy before they can be useful. Make their authority small, their behavior observable, their outputs checkable, and their accepted effects controlled and reproducible.
