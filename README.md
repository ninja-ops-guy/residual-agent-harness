# RESIDUAL

**Reliable AI systems without assuming reliable AI workers.**

RESIDUAL is a verification-first control plane for AI-assisted engineering. Models and agents are treated as **untrusted compute**: they can propose work, but they do not get to define success, approve themselves, or directly own accepted state.

The system around them does that.

> **Core hypothesis:** reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

RESIDUAL is the engineering platform and research harness I am using to test that idea.

## The problem

Most agent frameworks put more capability inside the agent: more context, more tools, more retries, more autonomy. That can improve what a model is able to do, but it does not automatically improve what the system can safely trust.

RESIDUAL takes the opposite approach. The worker is replaceable. Authority stays outside it.

```text
intent
  ↓
frozen requirements + execution plan
  ↓
route / schedule bounded workers
  ↓
observe execution + collect evidence
  ↓
independent verification
  ↓
PASS ──→ deterministic acceptance / integration ──→ signed/auditable receipt
  │
  └─ FAIL / UNKNOWN ──→ counterexample / retry / residual escalation
```

A worker can be wrong without automatically making the accepted system state wrong.

## What RESIDUAL is now

The repository has grown into four connected layers.

### 1. Verification kernel

The original harness provides obligation DAGs, immutable evidence snapshots, verifier-owned acceptance, counterexample-directed repair, scoped evidence negotiation, residual delegation, disclosure controls, budgets, receipt-bound caching, and tamper-evident traces.

`FAIL`, `UNKNOWN`, malformed results, verifier exceptions, provider errors, and abstention never silently become success.

### 2. Command Station

Command Station is the self-hosted operator surface. It adds mission/spec workflows, run control, local/cloud provider routing, observations, HITL, security inspection, model management, lifecycle hooks, distributed adapters, evidence export, and source-release packaging.

Supported provider paths include OpenAI, OpenAI-compatible endpoints, Anthropic, Gemini, Azure, Bedrock, and Ollama. Provider/framework output remains advisory until RESIDUAL accepts it.

### 3. Factory runtime

Factory is the headless execution layer for turning approved plans into bounded worker attempts.

Current `main` includes:

- deterministic requirement compilation and graph hashing;
- exact plan approval binding;
- immutable worker contracts;
- Linux fail-closed worker isolation with libseccomp enforcement;
- per-attempt worktrees and private candidate object stores;
- bounded file brokering and resource controls;
- durable attempt journals, leases, cancellation, watchdogs, and restart-visible state;
- Station-issued Ed25519 worker receipts;
- content-addressed accepted artifacts;
- receipt-only dependency admission;
- append-oriented evidence storage and provenance queries.

The important boundary is simple: **worker exit success still does not mean accepted work.** Candidate output remains quarantined until trusted Station-side verification and receipt issuance succeed.

See [`docs/factory/M2-EXECUTION.md`](docs/factory/M2-EXECUTION.md) and [`docs/factory/M3-EVIDENCE-BUS.md`](docs/factory/M3-EVIDENCE-BUS.md).

### 4. Studio / swarm platform

The newest platform work expands Factory into a broader multi-worker control plane. Current `main` now includes implementation paths for:

- sandbox hardening and red-team testing;
- cluster and orchestration primitives;
- evaluation and soak infrastructure;
- gateway and lifecycle glue;
- cryptographic abstraction work;
- connector conformance;
- Studio frontend development surfaces;
- onboarding examples;
- source-of-truth implementation-status tooling;
- swarm-specific acceptance verification.

A repository-level v3 swarm acceptance check now validates required deliverable paths, protects the Factory-owned runtime/evidence/integration boundaries from accidental overlap, runs the full test suite, and re-checks the earlier spec verifier. The latest retained merged-tree evidence reports **1,033 pytest tests + 166 subtests passing** with the v2 verifier still green.

This is not the same thing as claiming every Studio spec is production-complete. It does mean the project has moved well past a paper architecture or UI mockup.

## Adaptive assurance

RESIDUAL also measures the reliability of the control plane itself instead of assuming all verification and orchestration decisions are equally good.

Implemented primitives include:

- **Verifier quality profiles** — precision, recall, false-accept behavior, calibration, coverage, posterior confidence, and assurance-class gating.
- **Orchestration tax learning** — observed success, cost, and latency by execution strategy so swarms have to justify their overhead.
- **Verified compute selection** — engine choice based on capability, privacy, cost, latency, observed quality, and uncertainty.
- **Quorum-aware authority boundaries** — authoritative writes can fail closed when the required consistency boundary is unavailable.
- **Assurance receipts** — execution strategy, engine choice, verifier state, quality snapshot, and outcome are all inspectable.

The goal is not "always swarm." The goal is to learn when direct execution, stronger verification, a small swarm, a larger swarm, or escalation provides the best verified result for the cost and risk.

## What makes this different

RESIDUAL is not primarily an agent personality layer, prompt framework, or tool router.

Its core design choices are:

- **Workers propose. Verifiers decide.**
- **UNKNOWN is a real state, not a soft PASS.**
- **Contracts exist before execution.**
- **Evidence survives every handoff.**
- **Accepted state belongs to the harness, not the agent.**
- **Residual escalation preserves work that already passed.**
- **Parallelism is measured by useful speedup and verified output, not agent count.**
- **Verifier quality is part of the assurance model.**
- **Local and cloud models are compute resources, not trust anchors.**
- **Research claims stay narrower than implementation ambition.**

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

Or run natively with Python 3.11+ and Git:

```bash
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md).

### Factory

Start with the execution-plan contract, then the worker/evidence layers:

- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/factory/M2-EXECUTION.md`](docs/factory/M2-EXECUTION.md)
- [`docs/factory/M2-IMPLEMENTATION-STATUS.md`](docs/factory/M2-IMPLEMENTATION-STATUS.md)
- [`docs/factory/M3-EVIDENCE-BUS.md`](docs/factory/M3-EVIDENCE-BUS.md)

### Studio development surface

A development-only Studio frontend stub exists for plan, contract, swarm, receipt, worker-timeline, and approval views. It uses local fixtures and in-memory approval state; it is **not** presented as the authoritative production swarm API.

```bash
python3 -m residual.studio_frontend.stub_server --port 8787
```

## Architecture

| Layer | Owns | Does not trust |
| --- | --- | --- |
| Requirement compiler | structured intent, DAG, graph hash | free-form execution state |
| Scheduler / router | placement and execution strategy | model self-assessment |
| Worker runtime | bounded candidate generation | worker exit code as acceptance |
| Evidence layer | observations, artifacts, receipts, provenance | unsigned/unbound handoffs |
| Verifier layer | acceptance decision | candidate claims |
| Integrator | accepted state transition | stochastic merge authority |
| Assurance layer | quality, cost, uncertainty, escalation | verifier infallibility |
| Operator / HITL | explicit high-risk decisions | implicit approval |

For the original invariants, read [`docs/architecture.md`](docs/architecture.md). For the platform direction, read [`docs/studio/README.md`](docs/studio/README.md).

## Research program

RESIDUAL is also a research instrument for the hypothesis described above.

The working paper is:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](docs/papers/reliability-from-unreliable-computation.md)**

The evaluation program now spans scripted controller studies, controlled independent grading, adaptive-assurance fixtures, external/live evidence runners, preregistration support, benchmark infrastructure, and the newer swarm reliability research program.

Important distinction:

| Level | Meaning |
| --- | --- |
| **Implemented** | mechanism exists in source |
| **Demonstrated** | repository fixtures/CI exercise the mechanism |
| **Hypothesized** | expected system property still under test |
| **Established** | supported by appropriate external/controlled evidence |

Synthetic fixtures and CI can prove controller behavior. They do **not** by themselves prove real-model superiority, universal cost savings, or production safety.

Start with [`docs/research.md`](docs/research.md), [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md), and [`docs/README.md`](docs/README.md).

## Verification

Core checks:

```bash
python3 -m unittest discover -s tests -v
python3 verifier/v2/check_specs.py
python3 verifier/v3/check_swarm.py
node --check residual/station/static/app.js
```

Optional browser QA:

```bash
npm install
npx playwright install chromium
npm run test:ui
```

## Current status

RESIDUAL is an active research and platform-engineering project. The verification kernel and Command Station are established foundations; Factory M2/M3 execution and evidence paths are now concrete on `main`; broader Studio, cluster, orchestration, evaluation, and assurance work is advancing in parallel.

Some generated status documentation may temporarily lag the newest merge wave. For exact current behavior, prefer source, tests, Factory-specific implementation docs, and retained verifier evidence over older prose snapshots.

## Non-claims

RESIDUAL is not a universal proof system. A verifier can only establish what its contract and evidence let it check. Receipts prove checked acceptance under stated inputs; they do not certify arbitrary truth.

The project does not currently claim a universally optimal scheduler, universal verifier, guaranteed token savings, guaranteed model-quality preservation, full multi-tenant production certification, or first-in-literature status.

---

**RESIDUAL is built around one idea:** stochastic workers do not need unlimited trust to be useful. Keep their authority small, make their behavior observable, verify what matters, and make accepted effects deterministic.