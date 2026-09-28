# HCOR-000 — Hierarchical Coordination & Delegation Plane

**Status:** PARKED / POST-v1 DESIGN  
**Program:** RESIDUAL v2 — Hierarchical Swarm Coordination  
**Implementation authority:** none until the v2 kickoff gates in `docs/v2/ROADMAP.md` are satisfied.

## North star

RESIDUAL owns durable truth; coordinators own decomposition. The owner supplies intent, priorities, protected authority, and risk decisions. RESIDUAL maintains missions, dependencies, authority, leases, checkpoints, evidence, provider/runner state, verification requirements, and convergence. Coordinators are replaceable leased control-plane workers; workers execute; independent verifiers adjudicate; Station controls authoritative state transitions.

Adding machines or agents should increase capacity without increasing owner coordination load.

North-star campaign:

```text
add 10 machines / 50 agents
kill a provider
kill a worker
kill a mission coordinator
take a host offline
owner does nothing

RESIDUAL preserves truth, reallocates leases, fences stale work,
continues runnable missions, verifies independently, preserves failures,
parks protected gates, and converges completed work.

owner returns -> NEEDS YOU contains only genuine protected decisions
```

## Doctrine

1. RESIDUAL owns truth; chat is never authoritative mission state.
2. Coordinators delegate intent but cannot manufacture authority.
3. Child authority is always a subset of parent authority.
4. Every delegation binds mission, authority, resource, evidence, acceptance, and expiry contracts.
5. Workers execute; verifiers independently recompute/challenge; Station adjudicates authoritative transitions.
6. Ownership is leased and generation/fencing-token protected.
7. First failures are preserved before repair.
8. Provider, worker, coordinator, and host failure must not destroy mission truth.
9. Runnable DAG work continues when unrelated dependencies fail.
10. Owner gates park affected work without making the owner coordination infrastructure.
11. Coordinators are event-driven; polling/nagging is not the control plane.
12. Convergence freezes satisfied missions; new ideas become new work rather than silently expanding completed scope.
13. Original controlling artifacts are referenced by digest at every hierarchy level; summaries cannot replace them.
14. Paths locate software/artifacts; digests identify them; qualification receipts authorize them.
15. Configured does not imply ready; self-reported PASS does not imply accepted.

## Planes

Authority Plane; Mission/DAG Plane; Coordinator Plane; Scheduling/Admission Plane; Execution Plane; Verification/Challenge Plane; Evidence Plane; Continuity/Recovery Plane; Mission Board Projection.

Models are replaceable compute, agents are replaceable workers, machines are schedulable resources, providers are replaceable inference backends, and coordinators are replaceable control-plane workers.

## Required child specs

- HCOR-001 — Mission & Delegation Kernel
- HCOR-002 — Event-Driven DAG Coordinator
- HCOR-003 — Resource / Capability Scheduler
- HCOR-004 — Hierarchical Coordinator Runtime
- HCOR-005 — Independent Verification & Challenge Plane
- HCOR-006 — Coordinator Survivability & Recovery
- HCOR-007 — Convergence, Scope & Backlog Admission
- HCOR-008 — Qualification Campaigns & Scale-Out Program

These specs are separable work packages for independent cloud swarm sessions after v2 kickoff.

## Canonical hierarchy

Hierarchy is mission-based, not host-based:

```text
Owner
  -> Root Coordinator
      -> Program / Mission Coordinator
          -> Sub-mission Coordinator (only when complexity warrants)
              -> Workers
          -> Independent Verification Queue
      -> Station Authority
```

Machines are placement targets chosen by the scheduler. Hierarchy depth is dynamic: small tasks use root->worker->verifier; larger programs may add mission/sub-mission coordinators.

## Universal delegation envelope

Every delegated mission/submission binds mission_id, parent_mission_id, assignment_id, dispatch_id, authority_epoch, coordinator lease/generation/fencing token, controlling artifact digests, acceptance-contract digest, authority-envelope digest, resource-budget digest, verification-requirement digest, checkpoint-policy digest, priority, issue/expiry times.

No descendant may replace a controlling artifact with a paraphrase.

## Authority attenuation

For every edge: `child_authority ⊆ parent_authority`. The runtime proves this mechanically before dispatch. Mutation-capable dispatches compose with DF-AUTH-001 semantics: dispatch ID, authority epoch, ACTIVE/RESCINDED/SUPERSEDED/EXPIRED/CONSUMED, immediate pre-mutation revalidation, and keyed rescission.

## Success metrics

Primary: `owner_interventions / completed_missions`.

Also measure throughput, runnable-to-dispatched latency, lease recovery, stale-result rejection, duplicate execution/acceptance, verification-independence coverage, first-failure preservation, evidence completeness, coordinator recovery, unrelated-work continuity, and convergence latency.

## Non-goals

Not a single omniscient super-agent, chat router, unrestricted remote shell, autonomous merge/release authority, authority-expansion mechanism, self-verification bypass, or uncontrolled recursive self-modification.

## Dependencies

SC-MESH, Mission Board, DF-AUTH-001, BL-006 model admission, BL-008 persistent workspace, BL-009 provider continuity, EVPR-001, OBSH-003, CMPE-004, ENVB-002, HarnessBench, Host Lifecycle Supervisor, enterprise HA/fencing.

## Program release gate

No hierarchical-autonomy claim until HCOR-001..007 qualify, HCOR-008 scale campaigns pass, coordinator replacement has no lost/duplicate accepted work, authority attenuation passes negative tests, verification remains independent through failures, durable artifacts reconstruct mission truth without chat, and owner intervention rate falls as capacity grows.

**Terminal design state:** `HCOR_V2_PROGRAM_SPECIFIED`.
