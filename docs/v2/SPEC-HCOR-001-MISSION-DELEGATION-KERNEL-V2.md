# HCOR-001 — Mission & Delegation Kernel

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000

## Objective

Generalize the current backlog/assignment/receipt workflow into durable mission objects recursively delegable without losing authority, acceptance criteria, evidence provenance, or owner intent.

## Core objects

`Mission`, `MissionSpec`, `SubMission`, `Assignment`, `DependencyEdge`, `AcceptanceContract`, `AuthorityEnvelope`, `ResourceBudget`, `VerificationRequirement`, `CheckpointPolicy`, `MissionCheckpoint`, `MissionEvent`, `MissionReceipt`.

All identity-bearing objects use canonical serialization and content digests.

## Mission state machine

`DRAFT -> REGISTERED -> READY -> LEASED -> RUNNING -> CANDIDATE -> VERIFYING -> ACCEPTED -> FROZEN`

Side/terminal states: `BLOCKED_DEPENDENCY | OWNER_GATE_READY | FIRST_FAILURE | REJECTED | EXPIRED | CANCELLED | SUPERSEDED`.

Transitions are atomic read-check-write operations and emit append-only events.

## Delegation rules

A coordinator may decompose only when decomposition is permitted, every child has bounded acceptance, child authority is a subset of parent authority, aggregate budgets fit the parent, evidence/verification requirements are not weakened, and original controlling artifacts remain directly referenced. Parent completion requires declared child convergence.

## Anti-telephone-game invariant

Every worker/verifier resolves the exact original mission spec, acceptance contract, authority envelope, source/environment identities, and evidence schema. Coordinator summaries are advisory only.

## Lease/fencing model

Assignments bind `seat_id, generation, lease_id, fencing_token, issued_at, expires_at, checkpoint_digest`. Lease expiry/rescission makes later results stale. Stale results are retained as evidence but cannot advance state.

## Owner gates

Owner gates explicitly carry defined/actionable-now state, prerequisites, requested capability, pre-spend evidence, and terminal receipt. `NEEDS YOU` projects actionable-now only.

## First-failure doctrine

`observe -> preserve -> classify -> stop affected lane -> coordinator disposition`. Repair creates a successor candidate/generation; failed bytes remain immutable.

## Negative qualification

Reject/detect child authority expansion, budget over-allocation, acceptance weakening, missing controlling artifacts, stale lease results, duplicate acceptance, concurrent conflicting transitions, parent freeze with unresolved required child, chat-inferred owner gates, rescinded mutation, and candidate overwrite instead of successor generation.

## Qualification target

Root mission decomposes into at least three children; one child decomposes again; one worker lease expires/reassigns; one child first-fails and produces a successor; final acceptance reconstructs entirely from durable mission/events/receipts.

**Terminal:** `MISSION_DELEGATION_KERNEL_QUALIFIED`.
