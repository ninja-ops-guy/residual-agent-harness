# Residual Studio — Platform Vision

**Status:** Proposed platform direction  
**Date:** 2026-09-13  
**Target:** Residual v1.0+

## Thesis

Residual Studio is a self-hosted, evidence-driven multi-swarm engineering platform.

The objective is not to make language models intrinsically deterministic. The objective is to **deterministically constrain, verify, schedule, and integrate nondeterministic workers** so that large software changes can be decomposed, executed in parallel, and accepted through explicit evidence.

A concise product position is:

> **Cursor for multi-swarm engineering — self-hosted, parallel, evidence-driven, and designed to finish large projects as coordinated systems rather than one-agent-at-a-time coding sessions.**

The IDE is the human interface. The core product is the distributed runtime beneath it.

## Platform model

```text
Layer 5  Residual Cluster       heterogeneous local/cloud compute
Layer 4  Swarm Runtime          coordinators, workers, critics, verifiers, integrators
Layer 3  Residual Orchestrator  requirement DAG, partitioning, routing, scheduling, replanning
Layer 2  Residual Station       existing verification/safety kernel
Layer 1  Residual Studio        browser IDE, swarm control plane, evidence explorer
```

The current Station remains authoritative for safety and verification. Studio extends it; it does not replace it.

## Operating model

Residual Studio supports three per-task modes:

- **Pair:** one human and one agent for small interactive work.
- **Team:** a bounded 3–5 worker swarm for medium parallel work.
- **Factory:** multiple concurrent swarms for project-scale execution.

A session may mix modes. A developer can remain in Pair Mode for editing and escalate a single feature or specification to Factory Mode.

## Deterministic boundary

LLM generation is treated as untrusted and potentially nondeterministic. Determinism is enforced around generation:

```text
nondeterministic generation
        ↓
frozen worker contract
        ↓
filesystem / tool boundary
        ↓
explicit verifier
        ↓
receipt
        ↓
deterministic integration policy
```

An agent output is never integration-eligible merely because an agent claims success. It becomes eligible only when a verifier issues the required evidence and the resulting receipt is accepted.

## Parallelism model

Parallelism is planned from a dependency graph, not from agent count. Work is partitioned so workers receive disjoint or explicitly ordered write scopes. Swarms can resize dynamically as the ready frontier changes.

The system measures useful parallelism using effective speedup, coordination overhead, rework rate, verifier rejection rate, blocked work, and worker utilization. These metrics are research outputs as well as operator telemetry.

## Self-hosted compute

Residual Cluster treats intelligence as a schedulable heterogeneous resource. A deployment may combine local GPUs, workstations, homelab nodes, and permitted cloud providers. Nodes advertise capabilities; the router selects the cheapest capable placement while preferring local execution when capability is equivalent.

This makes the runtime closer to a compute scheduler for engineering work than a conventional chat-based coding assistant.

## Product surfaces

Residual is intentionally separated into surfaces:

- **Residual Runtime:** execution, verification, receipts, policy, and lifecycle.
- **Residual Studio:** the browser IDE and operational control plane.
- **Residual Protocol:** typed contracts, evidence, provenance, and integration rules.
- **Residual Bench:** parallelism, reliability, cost, and quality evaluation.

## Primary research questions

1. How much wall-clock speedup can verified multi-swarm execution achieve over serial agent execution?
2. At what worker count does coordination overhead dominate useful parallelism?
3. Which task partitioning policies minimize rework and merge conflicts?
4. How effectively can heterogeneous local models absorb low-risk work before cloud escalation is required?
5. Can receipt-mediated integration reduce cross-agent trust and hidden shared-state failures?
6. What classes of software changes remain poorly parallelizable even with dependency-aware decomposition?

## Implementation order

The critical path is:

```text
Requirement Compiler
        ↓
Swarm Runtime + Evidence Bus
        ↓
Deterministic Integration
        ↓
Parallel Metrics
        ↓
Studio IDE
        ↓
Residual Cluster expansion
```

Cluster work can proceed in parallel once engine abstraction and capability routing are stable.

The normative requirements are defined in [`STUDIO_SPECS.md`](STUDIO_SPECS.md).
