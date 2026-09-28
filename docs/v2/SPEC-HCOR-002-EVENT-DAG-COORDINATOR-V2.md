# HCOR-002 — Event-Driven DAG Coordinator

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000  
**Depends on:** HCOR-001

## Objective

Replace manual coordinator polling and room-driven progression with deterministic event-driven DAG evaluation.

## Durable event inputs

Mission/assignment registration; artifact byte verification; checkpoints; worker ACK/results; verifier verdicts; dependency changes; lease expiry/rescission; provider readiness/failure; runner health; owner-gate satisfaction; lifecycle reconciliation; first failure; mission freeze/supersession.

Chat is not an event source unless converted into an admissible artifact through a defined ingress contract.

## Deterministic DAG evaluation

Given `previous DAG state + ordered event prefix + policy version`, produce the same mission states, runnable/blocked sets, owner gates, scheduling requests, and convergence candidates. Projection must rebuild from event zero.

## Runnable semantics

Runnable requires all hard dependencies satisfied, valid authority, no blocking actionable gate, admissible resources/verification, nonterminal state, and no conflicting lease. Unrelated failures cannot freeze independent subgraphs.

## Reactions

Artifact arrival unlocks verification; verifier PASS unlocks dependents; verifier FAIL preserves first failure; lease expiry fences and reschedules; provider failure invokes continuity policy; owner gate parks the lane and releases capacity; coordinator loss lets replacement consume the same event log/checkpoint.

## Idempotency/order

Events carry sequence, canonical digest, logical identity, and predecessor/authority context. Duplicate byte/semantic events follow evidence/projection identity rules. Reordered/missing events are detected.

## Coordinator checkpoint

Binds consumed event head, DAG digest, runnable/blocked sets, outstanding leases, pending verification, owner gates, and policy/config digests. Checkpoint accelerates recovery; event log remains authority.

## Backpressure

Expose runnable depth, verifier depth, host/provider pressure, blocked-on-owner count, stale leases. Do not generate unbounded child work when verification/resources saturate.

## Negative qualification

Inject duplicate/reordered/missing events, verifier PASS before candidate, premature owner-gate satisfaction, lease-expiry/result races, provider-failure/result races, crash between event persist and dispatch, stale checkpoint replay, and unrelated blocked subgraphs. No duplicate authoritative dispatch/acceptance.

## Qualification target

Run multi-mission DAG for hours without polling. Kill coordinator mid-run; replacement reproduces runnable/blocked state and continues without duplicate accepted work.

**Terminal:** `EVENT_DAG_COORDINATOR_QUALIFIED`.
