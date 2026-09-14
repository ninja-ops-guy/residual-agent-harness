# Residual Studio / Factory

Residual Studio is the platform layer growing around RESIDUAL's verification kernel. **Factory** is the current headless execution path; Studio adds the multi-worker, operator, cluster, evaluation, and orchestration surfaces around it.

The goal is not to maximize agent count. The goal is to make heterogeneous compute useful **without turning extra autonomy into extra trust**.

## Control model

```text
requirements
    ↓
frozen execution plan
    ↓
bounded worker contracts
    ↓
execution + observations
    ↓
Station-side verification
    ↓
trusted evidence / receipts
    ↓
deterministic integration
    ↓
auditable accepted state
```

A worker can fail. A verifier can be uncertain. A network can partition. A scheduler can choose badly. Studio is designed so those failures remain explicit inputs to the control plane instead of being hidden behind an agent success message.

## Current implementation

The platform is no longer only a vision/specification layer.

### Factory plan boundary

`residual/factory/compiler.py` and `models.py` provide structured requirements, task DAGs, canonical graph hashing, ambiguity rejection, and approval bound to the exact frozen plan.

See [`../factory/PLAN-CONTRACT.md`](../factory/PLAN-CONTRACT.md).

### M2 worker execution

Current `main` contains concrete bounded worker execution under `residual/factory/`:

- immutable worker contracts;
- Linux/libseccomp fail-closed sandbox bootstrap;
- resource, deadline, memory, and cancellation controls;
- safe brokered file access;
- isolated per-attempt worktrees;
- private candidate Git object stores;
- durable runtime journals and leases;
- parallel independent attempts;
- quarantined candidate output rather than implicit acceptance.

See [`../factory/M2-EXECUTION.md`](../factory/M2-EXECUTION.md) and [`../factory/M2-IMPLEMENTATION-STATUS.md`](../factory/M2-IMPLEMENTATION-STATUS.md).

### M3 trusted evidence handoff

Current `main` also includes the trusted evidence boundary:

- Station Ed25519 identity;
- signed worker receipts;
- exact contract/plan/input/output binding;
- content-addressed accepted artifacts;
- append-oriented evidence storage;
- receipt verification and dependency admission;
- stale-receipt failure behavior;
- provenance/query indexes.

A candidate becomes trusted evidence only after Station-side verification and receipt issuance.

See [`../factory/M3-EVIDENCE-BUS.md`](../factory/M3-EVIDENCE-BUS.md).

### Swarm/platform buildout

The newest merged buildout adds or establishes implementation paths for:

- `residual/sandbox` and red-team testing;
- `residual/cluster`;
- `residual/orchestrator`;
- `residual/eval` and `residual/soak`;
- `residual/gateway` and lifecycle glue;
- `residual/crypto`;
- connector conformance;
- `residual/studio_frontend`;
- onboarding examples;
- generated implementation-status tooling;
- a dedicated swarm acceptance verifier.

The Studio frontend currently includes a **development stub API**, not a production claim. It serves local fixture-backed plan, worker-contract, swarm-status, receipt, timeline, and approval views. Mutating approval state is in-memory and resets on restart.

Launch it with:

```bash
python3 -m residual.studio_frontend.stub_server --port 8787
```

## Swarm acceptance evidence

`verifier/v3/check_swarm.py` provides a repository-level acceptance gate for the merged swarm buildout. It checks that required deliverable paths exist, guards owned M2–M4 boundaries against accidental overlap, runs the full pytest suite, and requires the earlier spec verifier to remain green.

The latest retained merged-tree evidence reports:

- **1,033 pytest tests passed**;
- **166 subtests passed**;
- protected Factory-owned paths unchanged by the unrelated swarm tracks;
- verifier v2 green.

That is implementation/CI evidence, not a blanket production-safety claim.

## Adaptive assurance

The platform also includes a control layer that can evaluate its own decisions:

- `VerifierQualityProfile` tracks verifier outcomes and uncertainty rather than assuming checker infallibility.
- `OrchestrationTaxController` learns observed utility by execution strategy so swarms have to earn their overhead.
- `VerifiedComputeMarket` considers capability, privacy, latency, cost, quality, and uncertainty when selecting engines.
- quorum-aware interfaces define where authoritative state should fail closed.
- assurance receipts bind the chosen strategy, engine, verifier state, and outcome.

This is important because the research question is not simply whether multiple agents can work in parallel. It is whether a system can decide **when parallelism helps, when it hurts, and how much evidence is required before accepting the result**.

## Reliability research program

The repository now includes a dedicated swarm reliability program covering evaluation, verifier quality, orchestration tax, distributed state, runtime/async integration, observability, production hardening, and reproducibility.

Some of those work packages may exist as active PRs rather than merged `main`. Do not treat an open research PR as shipped platform behavior until it lands.

For claim boundaries and experimental design, read:

- [`../research.md`](../research.md)
- [`../papers/reliability-from-unreliable-computation.md`](../papers/reliability-from-unreliable-computation.md)
- [`../controlled-evaluation.md`](../controlled-evaluation.md)

## Relationship to Command Station

Command Station remains the operator-facing verification/safety kernel. Studio/Factory extends it without changing the core authority model:

- workers do not self-approve;
- provider-native safety or HITL behavior is advisory to RESIDUAL's own policy boundary;
- `UNKNOWN` remains non-accepting;
- evidence and verifier revisions remain part of provenance;
- remote disclosure remains policy-controlled;
- accepted state is a harness decision.

## Normative documents

- [`PLATFORM_VISION.md`](PLATFORM_VISION.md) — product thesis and long-term architecture.
- [`STUDIO_SPECS.md`](STUDIO_SPECS.md) — normative Studio requirements.
- [`../factory/PLAN-CONTRACT.md`](../factory/PLAN-CONTRACT.md) — frozen plan boundary.
- [`../factory/M2-EXECUTION.md`](../factory/M2-EXECUTION.md) — worker execution implementation.
- [`../factory/M3-EVIDENCE-BUS.md`](../factory/M3-EVIDENCE-BUS.md) — trusted evidence implementation.

A normative spec can lead the code. For exact current behavior, source + tests + component implementation docs are authoritative.

## What success means

Studio succeeds if additional compute increases **verified useful work** without proportionally increasing coordination cost, false acceptance, integration risk, disclosure, or operator burden.

The metrics that matter are therefore things like verified task success, false acceptance, verifier coverage, orchestration tax, useful speedup, rework, conflicts, retries, latency, resource usage, and reproducibility—not raw agent count.