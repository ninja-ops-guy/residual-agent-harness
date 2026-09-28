# HCOR-006 — Coordinator Survivability & Recovery

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000  
**Depends on:** HCOR-001/002/004, BL-009 provider continuity, HLS, OBSH/CMPE, persistent workspace

## Objective

Ensure worker, provider, coordinator, Station, and host failures do not destroy mission truth or cause duplicate accepted work.

## Failure hierarchy

Required recovery classes:
1. worker/seat loss;
2. provider/model path loss;
3. mission coordinator loss;
4. root coordinator loss;
5. Station/service restart;
6. host loss/rejoin;
7. cold-start reconstruction.

Each class has explicit authority/fencing/reconciliation semantics.

## Durable coordinator checkpoint

Checkpoint includes event-head digest, mission/DAG digest, active child leases, pending dispatches, verification queue, provider/runner readiness references, owner gates, budget consumption, context handles, and unresolved first failures.

Checkpoint accelerates recovery; durable events/artifacts remain authority.

## Exactly-once authority, at-least-once evidence

Execution may produce duplicate observations during failures, but only one generation/fencing token may advance authoritative mission state. Late/duplicate outputs remain evidence and are explicitly rejected from authority.

## Provider continuity

Provider failover preserves mission/assignment/checkpoint identity while advancing provider-attempt epoch. Late primary responses are stale after fallback epoch advancement.

## Coordinator failover

Replacement coordinator must:
- prove old lease expired/rescinded;
- acquire new generation/fencing;
- rebuild from durable event head;
- reconcile outstanding children;
- detect dispatches persisted-but-not-delivered and delivered-but-not-acked;
- avoid duplicate accepted execution.

## Lifecycle integration

HLS governs supported process/service restarts. A coordinator hosted inside the restart blast radius cannot be sole lifecycle authority. Post-restart health requires authoritative-state reconciliation, not merely process liveness.

## Cold start

Reconstruct in order:
`Station -> workspace -> Mission DAG -> seats/runners -> leases/fencing -> providers/readiness -> context/checkpoints -> pending verification -> owner gates`.

Missing state is surfaced, never invented.

## Negative qualification

Crash coordinator at every boundary: before/after event persist, before/after dispatch, before/after ACK, before/after epoch advance, result-before-acceptance, verifier-result-before-adjudication. Also provider loss, host partition/rejoin, stale coordinator wake-up, Station restart, lifecycle failure, and corrupted checkpoint.

## Qualification target

Active multi-host mission survives sequential loss of worker, provider, mission coordinator, root coordinator, and one host. Owner performs no coordination. No duplicate acceptance, stale authority, or lost evidence.

**Terminal:** `COORDINATOR_SURVIVABILITY_QUALIFIED`.
