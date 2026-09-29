# RESIDUAL Fleet / Multi-Station Research Program R0

Status: **DESIGN-FROZEN / EXECUTION-DEFERRED**

This specification extends the Research Workbench with a preregistered experimental program for hierarchical multi-Station coordination, cross-platform portability, and coordination-plane fault tolerance. It does not activate experiments, authorize deployment, or compete with v1 convergence.

## 1. Research thesis

RESIDUAL should be able to coordinate a heterogeneous fleet through independent Station authority domains, host-local coordinators, explicitly enrolled claws/runners, portable evidence/checkpoints, and bounded authority transfer while preserving unambiguous authority under provider, agent, coordinator, Station, host, transport, and communications failures.

No single Station process, Station host, coordinator agent, inference provider, or Shared Comms transport should be the sole holder of mission truth required for safe continuation.

Lossless automatic cross-Station continuation is not claimed unless the durable state required for continuation has been independently proven replicated or transferable.

## 2. Reference laboratory

The initial experimental topology is:

- **DELL** — native Linux; first Linux reference/test Station; initial single-Station dogfood domain.
- **LEGION** — Windows 11 with WSL2; Windows/cross-platform reference Station; GPU-capable host.
- **DBOX** — native Linux; second Linux reproducibility and heterogeneous-onboarding specimen.

Hostnames are observations, not authority identities. Station authority binds an exact Station identity, data-root identity, epoch, and admitted evidence.

## 3. Hierarchy

The intended hierarchy is:

```
Cluster
  -> Station
      -> Local Coordinator
          -> Runner / Claw
              -> Provider
```

Authority may only narrow downward. Evidence/results flow upward. Shared Comms is projection/transport/observability and never mission authority.

A local coordinator may decompose only within its parent assignment. It may not broaden mission scope, create top-level authority, bypass independent verification, resurrect stale generations, or infer authority from chat/session presence.

## 4. Program work packages

### FLEET-01 — Discovery and enrollment

Research read-only discovery of existing OpenClaw/claw processes and configuration without reading secret values. Discovery creates candidates only.

Lifecycle:

`DISCOVERED -> MAPPED -> ENROLLED -> QUALIFIED -> ACTIVE`

Additional states: `IGNORED`, `DEGRADED`, `STALE`.

Presence never grants authority.

### FLEET-02 — Runner/claw mapping

Study explicit user mapping between a discovered claw, a RESIDUAL seat, and an enrolled runner. Display-name equality is insufficient identity evidence. Stable fingerprints must use non-secret host/config-root/agent/runtime identity inputs.

### FLEET-03 — Local coordinator

Study host-local decomposition and aggregation:

`Station assignment -> coordinator -> bounded subtasks -> mapped claws -> evidence/results -> coordinator -> Station`.

Coordinator replacement must not require conversational memory.

### FLEET-04 — Station registry

Define a cluster-visible registry containing Station identity, epoch, capabilities, capacity, provider capabilities, health, active mission summary, event head, and last heartbeat.

Registry visibility grants no mission authority.

### FLEET-05 — Station affinity and agent rebinding

A claw may have a preferred Station and admitted alternates. Affinity identifies eligible destinations only.

Runtime failover requires failure classification, old-authority fencing, checkpoint/evidence reconciliation, alternate-Station admission, and a fresh generation.

### FLEET-06 — Cross-Station delegation

Cluster authority may delegate a bounded mission to one Station authority domain. A Station may not widen that delegation.

### FLEET-07 — Portable checkpoints

Define the minimum checkpoint/evidence package required to continue work on another Station without conversational memory. Portability must bind exact mission, assignment, source/event heads, artifacts, acceptance state, provider state where relevant, and authority lineage.

### FLEET-08 — General authority transfer

Research a reusable authority-transfer primitive:

```
subject
scope
old_authority
old_epoch_or_generation
new_authority
new_epoch_or_generation
checkpoint_identity
last_accepted_event
evidence_head
reason
transfer_receipt
old_authority_fenced
new_authority_activated
```

Agent rebinding, coordinator replacement, Station restart, and cross-Station mission migration should be tested as scoped instances of the same primitive where possible.

### FLEET-09 — Station failure detection

Distinguish Station-process loss from Station-domain/host loss. Temporary process loss should use a bounded reconnect window before cross-Station rebinding becomes eligible.

### FLEET-10 — Cross-Station failover

Test safe continuation after the current Station becomes unavailable. An alternate Station must validate durable handoff evidence and issue fresh authority. A returning old Station must not resume fenced work.

### FLEET-11 — State/evidence replication

Determine which durable state must be replicated, exported, or otherwise transferable before automatic failover can claim lossless continuation. Replication is not equivalent to authority.

### FLEET-12 — Cluster scheduler

Study placement at Station granularity. Cluster scheduling chooses the Station; Station scheduling chooses local execution resources. Initial placement should remain deterministic and evidence-bound.

### FLEET-13 — Cross-platform qualification

Qualify Windows/WSL <-> Linux and Linux <-> Linux paths independently so host-specific, OS-specific, and architectural defects can be separated.

### FLEET-14 — Fleet operations and onboarding

Study the user workflow:

`ADD RUNNER -> DISCOVER CLAWS -> REVIEW -> MAP/IGNORE -> VALIDATE -> QUALIFY -> ACTIVATE`.

CLI/API contracts should precede cosmetic UI work. No silent mapping or secret transport through chat.

## 5. Failure-domain taxonomy

- **FD-0 Provider failure** -> only policy-eligible provider fallback.
- **FD-1 Claw failure** -> bounded local reassignment.
- **FD-2 Coordinator failure** -> replacement from durable Station state.
- **FD-3 Station process failure** -> reconnect/reconcile, then admitted alternate-Station rebinding if required.
- **FD-4 Station host/domain failure** -> cross-Station mission migration from transferable state.
- **FD-5 Shared Comms failure** -> mission execution continues; projection outbox catches up.
- **FD-6 Inter-Station partition** -> leases/epochs/fencing prevent dual authority.
- **FD-7 Artifact transport failure** -> byte-admission boundary fails closed.
- **FD-8 Checkpoint corruption** -> previous admissible checkpoint or stop; never fabricate.
- **FD-9 Stale authority return** -> old epoch/generation rejected.
- **FD-10 Compound failure** -> preserve first divergence and test composed recovery without relaxing individual invariants.

## 6. Research invariants

- **FR-I01** OpenClaw/claw presence != RESIDUAL enrollment.
- **FR-I02** Runner registration != claw mapping.
- **FR-I03** Mapping != qualification.
- **FR-I04** Station affinity != authority.
- **FR-I05** Shared Comms projection != mission truth.
- **FR-I06** Provider fallback may preserve availability but cannot repair authority/correctness failures.
- **FR-I07** A stale Station/agent generation can never regain authority by returning late.
- **FR-I08** Execution location and coordination location are independent where the admitted transport permits.
- **FR-I09** Cross-Station continuation requires portable/replicated durable evidence sufficient to reconstruct the bounded state.
- **FR-I10** No conversational memory is authoritative recovery state.
- **FR-I11** A coordinator is a replaceable capability, not the sole holder of queue/mission truth.
- **FR-I12** Every automatic failover must be causally attributable to durable failure/lease evidence and produce a durable transfer receipt.

## 7. Preregistered experiment sequence

### FR-EXP-01 — DELL single-Station dogfood

Onboard all intended DELL claws to one test Station. Demonstrate discovery, explicit mapping, enrollment, qualification, local decomposition, result admission, provider continuity, Shared Comms projection, restart reconstruction, and zero unexplained authority transitions.

### FR-EXP-02 — Linux reproducibility

Run the same onboarding path on DBOX without first normalizing the host. Record every manual intervention in an onboarding-friction ledger. Special DBOX-only code paths are a negative result unless explicitly justified.

### FR-EXP-03 — Cross-platform remote coordination

Prove a Windows/WSL Station can coordinate surviving Linux claws and a Linux Station can coordinate surviving LEGION claws without moving the claw processes.

### FR-EXP-04 — Station-process loss

Kill only the active Station process while host and claws survive. Expected: bounded reconnect; if recovery does not occur, admitted alternate Station rebinds surviving claws using fresh authority.

### FR-EXP-05 — Station-domain loss

Remove the Station host/domain. Expected: old delegation fenced; portable mission state admitted on alternate Station; no stale result can regain authority.

### FR-EXP-06 — Shared Comms outage

Disconnect Shared Comms while a mission runs. Expected: mission authority/execution continues, projections queue, reconnect catches up by authoritative identity with no duplicate authority.

### FR-EXP-07 — Provider degradation

Cause an eligible provider-availability failure. Expected: only a READY + admitted fallback route is selected; correctness/authority failures do not trigger availability fallback.

### FR-EXP-08 — Inter-Station partition

Partition Station-to-Station connectivity. Expected: lease/fencing rules prevent simultaneous authoritative ownership. Any split-brain acceptance is terminal failure.

### FR-EXP-09 — Coordinator loss

Terminate the local coordinator while Station and claws remain. Expected: Station truth survives; replacement coordinator generation reconstructs from durable state.

### FR-EXP-10 — Compound north-star run

During one bounded mission: eligible provider failure -> claw failure -> Shared Comms outage -> Station process/domain failure -> alternate-Station continuation -> old Station return -> projection reconciliation.

Target terminal predicates:

```
mission_completed = PASS
duplicate_authoritative_acceptance = 0
lost_accepted_events = 0
stale_authority_accepted = 0
unexplained_provider_reinvocations = 0
projection_loss = 0
owner_interventions = 0
```

A failed predicate is retained as experimental evidence; no retry-until-green.

## 8. Onboarding friction ledger

DBOX and future hosts maintain append-only findings such as:

```
finding_id
host
stage
manual_action_required
failure_class
evidence_digest
generic_product_fix
host_specific_exception
disposition
```

Examples include manual config-root discovery, duplicate listeners, ambiguous identities, firewall/discovery failures, stale enrollment, credential-store mismatch, fingerprint drift, and user-facing internal terminology.

The research target is not merely host qualification. It is convergence toward zero undocumented manual interventions, zero implicit mappings, zero secret copying through chat, zero stale authority acceptance, and zero unexplained discovery failures.

## 9. v1/v2 boundary

v1 should establish composable primitives: explicit runner enrollment, claw discovery/mapping, one authoritative Station, local coordination, durable assignments/generations, provider continuity, Shared Comms projection, checkpointing, restart reconciliation, fencing, and portable artifact/evidence identities.

v2 research composes those primitives into multi-Station registry, cross-Station delegation, Station affinity, coordinator replacement, mission transfer, state/evidence replication, automatic Station failover, cluster scheduling, capacity-aware placement, rolling upgrades, and fleet operations.

No item in this document changes the v1 release boundary merely by being specified here.

## 10. Activation gate

This program remains execution-deferred until the relevant v1 primitives have independently qualified. Each experiment requires its own preregistration, exact topology identities, failure injection boundary, negative controls, acceptance predicates, and evidence bundle before execution.

The Workbench must represent a staged definition as staged, never as executed evidence.
