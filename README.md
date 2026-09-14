# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first orchestration and verification harness for AI-assisted engineering. It treats model output as an untrusted proposal rather than an answer: workers operate inside explicit contracts, actions are observed, outputs are independently checked, and only accepted artifacts cross a deterministic integration boundary.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

RESIDUAL is the applied engineering system used to make that hypothesis testable.

## Current status

The package is currently **v0.5.0** and requires Python 3.11+. The repository now spans five connected areas rather than only the original harness/Station prototype:

| Area | Current implementation role |
| --- | --- |
| Verification harness | Obligation DAGs, evidence negotiation, independent verification, residual delegation, receipts, budgets and traces |
| Command Station | Self-hosted operator surface, provider routing, observations, local/cloud execution, HITL hooks and evidence packaging |
| Factory / Studio | Frozen execution plans, bounded multi-worker execution, isolated worktrees, evidence flow and deterministic integration |
| Assurance / evaluation | Controlled studies, verifier-quality work, fault-oriented evaluation and provider-backed external evidence |
| Enterprise layer | IAM, compliance/audit, multi-tenancy, HA/DR, supply-chain security, integration hub, governance and commercial/licensing controls |

The enterprise layer implements **SPEC-ENT-001 through SPEC-ENT-008 (62 requirements)** with requirement-to-implementation/test traceability under [`docs/enterprise/`](docs/enterprise/). Implementation is not the same as independent certification or production validation of every deployment topology.

A governed OpenClaw `ExecutionEngine` integration is currently under review in **PR #10**. It is intentionally described as pending until merged; its authority rule is: **OpenClaw executes; Residual decides whether the execution counts.**

## Why this exists

Most agent systems concentrate capability inside the worker: give a model more context, tools, retries, or autonomy and hope the resulting trajectory is correct. RESIDUAL moves authority out of the worker and into the surrounding system.

A worker may be local or cloud-hosted, weak or strong, deterministic or stochastic. It may fail. What matters is that the harness can bound what it is allowed to do, preserve evidence about what happened, reject unsupported work, escalate only the unresolved residual, and integrate accepted results reproducibly.

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

The model is replaceable compute. The harness owns authority.

## Implemented architecture

### Verification kernel

The original harness provides obligation DAGs, immutable evidence snapshots, verifier-defined acceptance, counterexample-directed repair, residual delegation, evidence negotiation, receipt-bound caching, disclosure controls, budgets, and tamper-evident traces. `FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider errors, and abstention do not silently become success.

### Command Station

Command Station exposes the system as a self-hosted operations console with mission/spec import, run control, local/cloud execution, provider routing, observation traces, model management, HITL hooks, security inspection, downloadable evidence, and source-release packaging.

The Station provider layer supports OpenAI, OpenAI-compatible endpoints, Anthropic, Gemini, Azure, Bedrock, and Ollama routes through bounded adapters. Local-first execution and residual cloud escalation are explicit policy decisions.

### Factory / Studio

Factory extends the kernel toward Residual Studio. Requirements are compiled into frozen plans; workers operate under contracts and isolated worktree boundaries; observations and evidence cross explicit interfaces; scheduling and integration are separated from worker discretion.

Current work includes deterministic requirement compilation, worker contracts, bounded swarm execution, evidence/receipt plumbing, deterministic scheduling and integration, verifier-quality profiles, orchestration-tax estimation, heterogeneous engine routing, distributed-state boundaries, async I/O, observability, metrics, and exact-source CI evidence.

### Assurance and external evidence

The evaluation surface now includes controlled scripted studies and provider-backed external assurance runs. [`docs/EXTERNAL_ASSURANCE_EVIDENCE.md`](docs/EXTERNAL_ASSURANCE_EVIDENCE.md) documents the external evidence path. External execution is useful evidence, but results remain scoped to the recorded workload, provider, configuration, verifier, and commit.

### Enterprise controls

The enterprise implementation maps eight normative specification families into concrete packages:

- IAM → `residual/iam/`
- compliance/audit → `residual/compliance/`
- multi-tenancy → `residual/tenancy/`
- HA/DR → `residual/hadr/`
- supply-chain security → `residual/supplychain/`
- enterprise integrations → `residual/integrations/`
- governance/commercial controls → `residual/licensing/` plus enterprise governance/commercial documentation

See [`docs/enterprise/README.md`](docs/enterprise/README.md) and [`docs/enterprise/TRACEABILITY.md`](docs/enterprise/TRACEABILITY.md).

## Design principles

1. **Workers propose; verifiers decide.** Generation and acceptance are separate authorities.
2. **Unknown is not pass.** Uncertainty remains visible.
3. **Contracts precede execution.** Scope, tools, resources, dependencies, evidence and checks should be explicit before work begins.
4. **Evidence survives handoffs.** Receipts bind accepted results to inputs, verifier revisions, dependencies and artifacts.
5. **Escalate the residual, not the whole problem.** Preserve accepted independent work and transfer only unresolved obligations and permitted evidence.
6. **Integration is deterministic.** Stochastic workers do not get unilateral authority over accepted state.
7. **Parallelism must earn its cost.** Swarms are evaluated against coordination overhead, latency, rework, rejection and integration risk.
8. **Verifier reliability is measured.** Assurance depends on check quality and coverage, not merely check existence.
9. **Compute is policy-governed.** Local, cloud and heterogeneous runtimes are resources selected under capability, cost, privacy, latency and quality constraints.
10. **Claims require evidence.** Implemented, demonstrated, externally exercised, hypothesized and established are different statuses.

## Quick start

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher builds the Station environment and serves the UI at `http://localhost:8765`.

Native mode requires Python 3.11+ and Git:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md) for setup and [`docs/README.md`](docs/README.md) for the current documentation map.

## Architecture at a glance

| Layer | Responsibility | Trust boundary |
| --- | --- | --- |
| Requirement / plan | Convert intent into explicit obligations and dependencies | Frozen before execution |
| Router / scheduler | Select direct, verified, swarm, ensemble, local or remote execution | Policy + observed performance |
| Worker runtime | Produce candidate artifacts under bounded contracts | Untrusted computation |
| Evidence bus | Preserve observations, artifacts, hashes, provenance and outcomes | Append-oriented evidence |
| Verifier layer | Evaluate acceptance and surface counterexamples/UNKNOWN | Independent authority |
| Integrator | Accept verified work and resolve ordered state transitions | Deterministic authority |
| Receipt / audit | Bind accepted state to its acceptance conditions | Reproducibility + audit |
| Enterprise controls | Identity, tenancy, compliance, continuity and integration policy | Deployment/control plane |

## Research program

RESIDUAL is both software and a research instrument. The working paper, **“Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems,”** develops the system-level reliability hypothesis and experiments intended to falsify it.

The repository does **not** claim the hypothesis is proven. Controlled and external evaluation improve the evidence base without converting bounded results into universal claims.

Start with [`docs/research.md`](docs/research.md), [`docs/papers/reliability-from-unreliable-computation.md`](docs/papers/reliability-from-unreliable-computation.md), [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md), [`docs/assurance-evaluation.md`](docs/assurance-evaluation.md), and [`docs/EXTERNAL_ASSURANCE_EVIDENCE.md`](docs/EXTERNAL_ASSURANCE_EVIDENCE.md).

## Documentation map

**Current index:** [`docs/README.md`](docs/README.md)

**Architecture / operation:** [`docs/architecture.md`](docs/architecture.md), [`docs/station/`](docs/station/), [`docs/factory/`](docs/factory/), [`docs/studio/`](docs/studio/)

**Enterprise:** [`docs/enterprise/README.md`](docs/enterprise/README.md), [`docs/enterprise/ENTERPRISE_SPECS.md`](docs/enterprise/ENTERPRISE_SPECS.md), [`docs/enterprise/TRACEABILITY.md`](docs/enterprise/TRACEABILITY.md)

**Research / evidence:** [`docs/research.md`](docs/research.md), [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md), [`docs/assurance-evaluation.md`](docs/assurance-evaluation.md), [`docs/EXTERNAL_ASSURANCE_EVIDENCE.md`](docs/EXTERNAL_ASSURANCE_EVIDENCE.md)

## Verification

```bash
python3 -m compileall -q residual
python3 -m unittest discover -s tests -v
node --check residual/station/static/app.js

# optional browser QA
npm install
npx playwright install chromium
npm run test:ui
```

Specialized Factory, enterprise, browser, and external-evidence checks may add prerequisites. Pin the exact commit for reproducible experiments.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only what its contract and evidence let it check. Receipts are evidence of checked acceptance under stated conditions, not certificates of arbitrary truth. Plugins, external identity systems, runtime adapters and host integrations introduce their own trust boundaries. Native project commands are opt-in and are not automatically an OS sandbox.

The repository does not claim a universal verifier, universally optimal scheduler, guaranteed token savings, guaranteed quality preservation, complete production readiness for every enterprise topology, or first-in-literature status. Those remain empirical, deployment-specific, or scholarly questions.

---

**RESIDUAL’s thesis is architectural:** do not require stochastic workers to become trustworthy before they can be useful. Make their authority small, their behavior observable, their outputs checkable, and their accepted effects deterministic.