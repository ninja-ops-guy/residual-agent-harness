# Swarm migration control plane — state synchronization foundation

**Status:** implementation slice for SPEC #358  
**Baseline:** `main@2f9dda3882f39c28a1c766859b1bf9579eea7911`  
**Scope:** SM-01 / SM-02 / SM-03 contract foundation only

This slice establishes the durable contracts needed to move from manually coordinated
agents to a synchronized RESIDUAL development swarm. It intentionally does **not**
add worker HTTP endpoints or change the current worker credential model. Those
integration points must converge with AUD-1 F2 runner-identity remediation rather
than creating a second identity system.

## Authority hierarchy

Project-state conflicts are resolved by source authority, not by model confidence:

1. repository / Git identity, Station receipts, qualification artifacts and verifier evidence;
2. explicit operator/HITL decisions;
3. deterministic derived state from those sources;
4. model-generated synthesis and annotations;
5. worker/agent assertions.

Lower layers cannot overwrite higher layers. In this slice, authoritative project
state and non-authoritative annotations are separate fields. Annotation keys are
rejected if they shadow an authoritative field.

## Project state

`residual.station.swarm_state.SwarmStateStore` stores immutable, generation-numbered
project-state snapshots. Each store is explicitly bound to a project/workspace `scope_id`;
that scope is included in the state envelope and hash so a state or delta cannot be
replayed across projects. Every snapshot is domain-separated and SHA-256 bound.

The authoritative payload currently requires:

- `main_sha`
- `release_sha`
- `release_phase`
- `active_missions`
- `blockers`
- `readiness_gates`
- `accepted_changes`
- `retained_failures`
- `experiments`
- `res_up_candidates`
- `claim_boundaries`
- `topology_generation`
- `operator_decisions`
- `evidence`

Publishing an identical state is idempotent and does not create generation churn.

## StateDelta

A stale runner can be brought forward with a bounded top-level `StateDelta`.
The delta binds:

- source generation/hash;
- target generation/hash;
- authoritative set/remove operations;
- annotation set/remove operations.

Applying a delta recomputes the target state and fails closed unless the recomputed
hash exactly matches the declared target hash.

This is deliberately deterministic logic. No model call is required to apply or
validate synchronization state.

## Durable runner identity and capabilities

The capability registry separates a durable enrolled identity from display/presence
metadata.

A runner profile contains:

- stable `runner_id`;
- SHA-256 `identity_digest` supplied by the enrollment/authentication layer;
- host identity;
- display name;
- local/remote placement;
- provider/model;
- adapter version;
- capabilities;
- constraints;
- derived `capability_revision`.

Capability states are:

`advertised → observed → qualified`

Changing provider/model/adapter/capabilities/constraints/host/identity changes the
capability revision. A display-name change does not grant authority.

The same `runner_id` cannot be rebound to a different identity digest.

## Synchronization acknowledgement

A runner becomes synchronization-eligible only after acknowledging:

- its durable runner identity;
- its exact project/workspace `scope_id`;
- the exact current `state_generation`;
- the exact current `state_hash`;
- its exact current `capability_revision`.

A new ProjectState generation invalidates the previous acknowledgement.

A capability revision change also invalidates the previous acknowledgement.

Acknowledgements are durable across Station restart.

## Claim gating

This slice provides the contract-level gate:

`SwarmStateStore.require_current(runner_id)`

It fails closed until the enrolled runner has acknowledged the exact current state
and current capability revision.

**It is not yet wired into `/api/worker/claim`.**

That is intentional. The current Station uses a shared worker token and self-reported
runner name. AUD-1 F2 requires a real identity binding. Wiring synchronization
eligibility to self-reported names would make the migration feature appear safer
than the authentication boundary actually is.

The integration order is therefore:

```text
AUD-1 F2 runner identity
        ↓
identity digest / runner credential binding
        ↓
SwarmStateStore enrollment
        ↓
sync acknowledgement
        ↓
require_current()
        ↓
worker claim eligibility
```

## Presence is not enrollment

Shared Comms runner presence remains an ephemeral operational signal.

Presence disappearing must not erase:

- enrollment identity;
- capabilities;
- synchronization history;
- evidence.

Conversely, appearing in a presence roster does not grant task authority.

## Current qualification coverage

`tests/station/test_swarm_state.py` covers:

- generation-numbered and hash-bound ProjectState;
- idempotent state publication;
- annotation/authority separation;
- exact StateDelta reconstruction;
- tampered and cross-scope delta rejection;
- project-scoped state/synchronization isolation;
- stale runner ineligibility after a new state generation;
- exact acknowledgement requirement;
- capability revision invalidating synchronization;
- advertised vs qualified capability distinction;
- runner identity rebinding rejection;
- durable enrollment and sync across restart.

## Deferred follow-on slices

After AUD-1 identity convergence:

1. bind enrolled runner credentials to `runner_id` + `identity_digest`;
2. expose authenticated state/sync endpoints;
3. make `/api/worker/claim` require current synchronization;
4. bind state generation/hash and capability revision into work packets/receipts;
5. promote the #349 connected-runner UI from presence-only to enrolled capability
   + sync state;
6. add intelligence routing (SM-04);
7. add experiment controller and operator-effort ledger (SM-05/06).

## Claim boundary

This foundation does **not** establish that the current distributed worker protocol
has per-runner cryptographic identity, cross-project isolation, or claim-time state
synchronization. Those properties remain unclaimed until their network/authentication
integration and adversarial qualification land.

It does establish the deterministic state, delta, capability-revision and durable
acknowledgement primitives required to implement those properties without using an
LLM as project truth.
