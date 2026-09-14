# Factory Execution Plan Contract

This document defines the integration boundary between the Requirement Compiler and downstream Factory components (Worker Contract / Swarm Runtime, Evidence Bus, Scheduler, Deterministic Integrator, and Evaluation).

## Authoritative identity

`ExecutionPlan.graph_hash` is the immutable plan identity.

It is the SHA-256 digest of the canonical payload containing:

- `schema_version`
- normalized `intent`
- requirements sorted by requirement ID
- tasks sorted by task ID
- each requirement's acceptance criteria and dependencies
- each task's requirement bindings, task dependencies, and optional swarm assignment

Downstream components MUST consume this hash; they MUST NOT silently reconstruct or mutate the approved requirement/task DAG.

## Approval binding

`FrozenPlan` binds operator approval to exactly one `ExecutionPlan.graph_hash`.

A downstream Factory run MUST reject execution when the supplied approval does not match the supplied plan.

Changes to intent, requirements, acceptance criteria, dependencies, task decomposition, task bindings, or swarm assignment produce a different graph hash and therefore require a new approval.

## Downstream requirements

Every run-scoped trust-bearing object SHOULD carry `execution_plan_hash`, including:

- `WorkerContract`
- worker attempt records
- scheduler decisions
- Station-issued `WorkerReceipt`
- Evidence Bus records
- integration attempts
- `IntegrationReceipt`
- evaluation run metadata

Objects that authorize execution or integration MUST validate that their `execution_plan_hash` matches the active approved plan before they are consumed.

## Determinism boundary

The Requirement Compiler does not claim model generation is deterministic. Model-assisted drafting may occur before the compiler boundary.

The deterministic boundary begins once structured input is validated and canonicalized. The approved graph hash anchors all subsequent scheduling, execution, verification, evidence, and integration provenance.

## Compatibility rule

Current plan schema: `factory-plan-v1`.

Downstream components MUST fail closed on unsupported future plan schema versions rather than interpreting them heuristically.
