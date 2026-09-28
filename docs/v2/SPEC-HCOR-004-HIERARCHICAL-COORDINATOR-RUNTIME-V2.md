# HCOR-004 — Hierarchical Coordinator Runtime

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000  
**Depends on:** HCOR-001/002/003

## Objective

Make coordinators ordinary leased, fenced, replaceable roles that can recursively decompose missions while operating under attenuated authority and bounded resources.

## Coordinator lease

A coordinator instance binds:
- coordinator_id / seat_id / generation;
- mission_id and parent coordinator;
- lease_id / fencing_token / expiry;
- authority envelope;
- resource budget;
- event-head/checkpoint digest;
- allowed decomposition depth;
- policy version.

Coordinator authority never exceeds its mission envelope.

## Responsibilities

Coordinators: decompose, assign, track, reconcile, escalate, reschedule, converge. They SHOULD NOT become default implementers. A coordinator may execute worker work only if the mission contract explicitly allows role collapse and verification independence remains satisfied.

## Recursive decomposition

Same runtime operates at root/program/mission/sub-mission levels. Child coordinators receive a MissionEnvelope subset. Depth is justified by complexity; trivial work must not create supervisory bureaucracy.

## Original-artifact access

Every child coordinator/worker/verifier receives direct digest references to controlling artifacts. Parent summaries are never substitutes.

## Coordinator replacement

On lease loss:
1. fence old generation;
2. elect/schedule replacement;
3. replacement loads durable event head + checkpoint;
4. recompute DAG/runnable state;
5. reconcile child leases;
6. continue without duplicate dispatch.

Old coordinator messages/results are stale after fencing and cannot mutate authority.

## Coordinator budgets

Bound max children, workers, parallelism, tokens/cost, runtime, retries, providers/hosts, and owner-interrupt budget. Child coordinators cannot collectively reserve beyond parent limits.

## Escalation

Escalate only:
- protected owner capability required;
- acceptance contract ambiguous/contradictory;
- no admissible placement;
- unresolved authority conflict;
- first failure requiring policy disposition;
- verification cannot satisfy independence.

Routine status progression never requires owner polling.

## Negative qualification

Test coordinator attempts authority expansion, budget expansion, self-verification, stale-generation mutation, child creation after rescission, duplicate child dispatch after crash, recursive decomposition explosion, summary-only controlling input, and owner polling as a required progress mechanism.

## Qualification target

Two-level hierarchy: root -> two mission coordinators -> workers/verifiers. Kill one mission coordinator, replace it, continue. Then kill root coordinator, replace it from durable truth. No accepted work lost/duplicated and no authority expands.

**Terminal:** `HIERARCHICAL_COORDINATOR_RUNTIME_QUALIFIED`.
