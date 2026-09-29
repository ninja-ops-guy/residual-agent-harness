# SC-CONTROL-001 — Shared Comms Control-Plane Integration

**Status:** V1 RELEASE REQUIREMENT — DESIGN / QUALIFICATION SPEC  
**Implementation target:** RESIDUAL v1  
**Documentation branch:** `v2/solpi-evidence-context-environment-bank`  
**Reason for branch placement:** the v2 branch is the current parked specification/harvest branch; this document defines a v1 requirement and MUST NOT be interpreted as deferring the requirement to v2.  
**Implementation authority:** no mutation of the frozen v1 release candidate is authorized by this document alone. Admission to the active v1 backlog, candidate construction, verification, merge/release, and protected owner gates remain separately controlled.  
**Relationship to v2:** successful SC-CONTROL-001 becomes substrate for HCOR-002/004/006. HCOR hierarchy, recursive delegation, and scale-out remain v2.

## 1. Problem

RESIDUAL currently owns durable mission state, receipts, Mission Board projection, assignment authority, provider state, checkpoints, and acceptance semantics, while Kimi/OpenClaw Shared Comms is the practical human/agent coordination surface.

If those two planes are only loosely coupled, the swarm can appear autonomous while the owner or coordinator still acts as hidden message-routing infrastructure:

```text
RESIDUAL says task A is terminal
        |
        | human/coordinator notices
        v
Shared Comms tells worker B what to do next
```

That is insufficient for the v1 claim that RESIDUAL can coordinate a real swarm.

SC-CONTROL-001 makes Shared Comms an observable and actionable coordination projection of RESIDUAL without making chat authoritative.

The required topology is:

```text
                    authoritative
                 +------------------+
                 |     RESIDUAL     |
                 | event log / DAG  |
                 | authority / MB   |
                 +--------+---------+
                          |
                          | durable event -> projection
                          v
                 +--------+---------+
                 |  Shared Comms    |
                 | human/agent UI   |
                 +--------+---------+
                          |
                          | ACK/result/reference
                          v
                 +--------+---------+
                 | validated ingress|
                 | authority + IDs  |
                 +--------+---------+
                          |
                          v
                 +------------------+
                 |     RESIDUAL     |
                 +------------------+
```

Shared Comms makes RESIDUAL visible and usable. It never replaces RESIDUAL authority.

## 2. North-star v1 claim

A real bounded mission can progress through:

`Station assignment -> Shared Comms dispatch -> worker ACK -> execution -> result artifact -> independent verification -> Station acceptance -> Mission Board closure -> DAG recompute -> successor dispatch`

with:

- zero owner routing messages;
- zero chat-only authoritative transitions;
- zero silent artifact reconstruction;
- zero stale-generation acceptance;
- visible queue/scheduling transitions in Shared Comms;
- durable evidence sufficient to reconstruct the sequence without trusting chat history.

Terminal qualification state:

`SHARED_COMMS_CONTROL_PLANE_QUALIFIED`

## 3. Scope

### 3.1 In scope

SC-CONTROL-001 specifies:

1. outbound projection of authoritative RESIDUAL events into Shared Comms;
2. inbound correlation of agent ACK/result/control messages back to durable assignments;
3. mission/thread or mission/conversation identity mapping when stable provider identifiers exist;
4. visible queue and scheduling deltas;
5. work-conserving successor dispatch;
6. verifier queue projection and dispatch;
7. authority/generation fencing at ingress;
8. artifact-reference and BL-016 transport boundaries;
9. restart/cold-start reconciliation;
10. provider-readiness projection;
11. owner-gate projection;
12. qualification, negative tests, and a real dogfood campaign.

### 3.2 Explicit non-goals

SC-CONTROL-001 does NOT define:

- hierarchical coordinators;
- recursive mission decomposition;
- multi-level authority attenuation beyond existing DF-AUTH-001 semantics;
- arbitrary agent-to-agent authority transfer;
- distributed consensus;
- ambient remote shell;
- automatic merge/release authority;
- v2 HCOR scale-out;
- chat as the artifact store;
- chat as the authoritative ledger.

Those remain existing v1 mechanisms or post-v1/v2 work.

## 4. Core invariants

### SC-I01 — RESIDUAL remains authoritative

Shared Comms messages are projections, transport messages, ACKs, observations, or requests. They do not directly define authoritative mission state.

Only the existing authoritative RESIDUAL state-transition path may advance mission truth.

### SC-I02 — Every projected control message is correlatable

Every RESIDUAL-generated Shared Comms control message MUST carry or resolve to:

- `event_id` or durable event digest;
- `mission_id`;
- `task_id` / `assignment_id` when applicable;
- `dispatch_id` when applicable;
- `authority_epoch` when applicable;
- `seat`;
- `generation`;
- relevant artifact/receipt digests;
- event type;
- authoritative state after the event.

Human-friendly prose MAY accompany these fields but MUST NOT replace them.

### SC-I03 — Inbound messages are never accepted by prose identity alone

An inbound ACK/result/control message MUST bind to an existing durable dispatch/assignment.

At minimum the ingress validator checks:

- mission/assignment identity;
- dispatch ID;
- seat identity;
- generation;
- authority state;
- candidate/artifact identity where relevant;
- message/event type admissibility for current mission state.

### SC-I04 — Stale authority remains visible but cannot mutate

Messages from stale, superseded, rescinded, expired, or consumed generations/dispatches MAY be preserved as evidence but MUST NOT advance authoritative state.

### SC-I05 — Chat is not byte authority

Shared Comms text is not sufficient to admit source, executable, security-sensitive, or qualification artifacts.

Artifact admission follows the controlling transport contract, including BL-016 where applicable.

A message may carry:

- artifact ID;
- artifact digest;
- transfer ID;
- retrieval handle/path/reference;
- transport state;
- verification receipt identity.

It MUST NOT cause an artifact to become accepted merely because source code or a digest appears in chat.

### SC-I06 — Terminal receipts are scheduling events

A terminal receipt, dependency change, lease expiration, verifier verdict, provider-readiness transition, or owner-gate transition MUST trigger DAG/queue recomputation.

No owner ping is required.

### SC-I07 — Mission blocked does not imply seat blocked

When a mission becomes dependency-blocked, verifier-blocked, owner-gated, or frozen awaiting another seat, its worker capacity SHOULD be released for unrelated admissible work after checkpointing, unless the mission contract explicitly requires seat retention.

### SC-I08 — Independent verification remains independent

Shared Comms routing MUST NOT collapse author/verifier independence. An implementation author cannot consume its own terminal verification assignment merely because it is the first available seat.

### SC-I09 — Projection is reconstructable

Shared Comms output is a projection of durable events. The same authoritative event stream MUST be sufficient to reconstruct the same control-plane projection modulo presentation-only fields.

### SC-I10 — Restart does not require conversational memory

After Kimi/OpenClaw/LEGION/Station restart, outstanding missions, queues, assignments, provider state, and pending handoffs are recovered from durable artifacts and then re-projected. No authoritative continuation may depend on pre-restart chat memory.

## 5. Shared Comms event vocabulary

At minimum v1 supports these projected classes:

- `DISPATCH`
- `ACK`
- `CHECKPOINT`
- `RESULT`
- `FIRST_FAILURE`
- `VERIFY_REQUEST`
- `VERIFY_RESULT`
- `ACCEPT`
- `REJECT`
- `QUEUE_SNAPSHOT`
- `QUEUE_DELTA`
- `OWNER_GATE`
- `PROVIDER_READINESS`
- `LEASE_FENCED`
- `MISSION_PARKED`
- `MISSION_RESUMED`
- `SWARM_QUIESCENT`
- `RECONCILIATION_BEGIN`
- `RECONCILIATION_COMPLETE`

Implementations MAY add presentation-only subtypes, but authoritative semantics MUST map to a stable event class.

Recommended human-visible prefix:

`[RESIDUAL][<EVENT_CLASS>]`

Example:

```text
[RESIDUAL][DISPATCH]
mission=BL-010
assignment=BL-010-NATIVE-001
dispatch=DSP-BL010-004
seat=Mason/LEGION
generation=4
event=sha256:...
acceptance_contract=sha256:...
```

## 6. Mission / conversation binding

Where Shared Comms exposes stable thread, conversation, room, or message identifiers, RESIDUAL records:

- `shared_comms_room_id`;
- optional `shared_comms_thread_id`;
- projection cursor / last projected event;
- last inbound correlated message identifier.

The binding is metadata, not authority.

If stable thread identifiers are unavailable, mission identity MUST remain explicit in every control message.

Thread naming SHOULD be mission-centric, e.g.:

- `BL-009 Provider Continuity`;
- `BL-010 Native Execution Proof`;
- `Program D Knowledge Delta`;
- `BL-016 Artifact Transport`.

## 7. Outbound projection contract

### 7.1 Projector input

The projector consumes only durable RESIDUAL events/receipts that are eligible for operator/agent visibility.

### 7.2 Projector output

Each projection records:

- source event identity;
- projection timestamp;
- target room/thread identity;
- projection message identity if returned by provider;
- projection status;
- retry/reconciliation state.

### 7.3 Delivery semantics

Projection delivery MAY be at-least-once.

Therefore:

- projected messages carry stable source event identity;
- duplicate projection MUST be harmless;
- duplicate projection MUST NOT create duplicate assignments;
- the receiver/ingress layer deduplicates by authoritative identity rather than message text.

### 7.4 Projection failure

A Shared Comms projection failure MUST NOT mutate mission truth.

The system records the projection failure and chooses one of:

- bounded retry under transport policy;
- alternate approved projection path;
- mission remains authoritative but marked `COMMS_PROJECTION_DEGRADED`;
- owner gate only if agent execution genuinely cannot continue without the projection.

No silent loss.

## 8. Inbound ingress contract

Inbound agent messages are parsed into candidate control events.

The ingress path MUST:

1. identify the sending seat/session;
2. resolve mission/assignment/dispatch;
3. verify generation and authority state;
4. validate event type against current mission state;
5. validate referenced receipts/artifacts;
6. require BL-016-compatible byte verification where artifact bytes cross the boundary;
7. deduplicate repeated inbound messages;
8. preserve rejected ingress attempts as evidence;
9. emit a durable RESIDUAL event only after validation.

Unknown/unbound prose remains conversation only.

## 9. Assignment ACK contract

A valid ACK binds:

- mission ID;
- assignment ID;
- dispatch ID;
- seat;
- generation;
- authority epoch;
- worker runtime/session identity where observable;
- controlling artifact verification state;
- ACK timestamp;
- ACK receipt digest.

If a seat cannot observe a runtime fact outside its trust/visibility boundary, it MUST report `UNOBSERVABLE_FROM_SEAT` rather than fabricate proof. That does not invalidate the ACK when the controlling assignment contract does not require that seat to observe the fact directly.

## 10. Queue / scheduling model

v1 maintains durable scheduling sets:

### Q0_CRITICAL

Current convergence / qualification critical path.

### Q1_READY

Dependency-satisfied, authority-admissible work runnable immediately.

### Q2_PREPARATION

Bounded preparation useful for future DAG nodes but incapable of claiming downstream terminal success.

### VERIFICATION_QUEUE

Frozen candidates awaiting independent verification, ordered by critical-path impact and verifier constraints.

### PARKED

Dependency-blocked, owner-gated, frozen, missing-authority, missing-evidence, or otherwise inadmissible work.

Every nonterminal backlog item MUST belong to exactly one scheduling state.

## 11. Work-conserving scheduler contract

Whenever a seat becomes free because its assignment:

- passes;
- fails and parks;
- becomes dependency-blocked;
- reaches an owner gate;
- freezes awaiting verification;
- transfers to another seat;
- is fenced/revoked;

the scheduler recomputes runnable work.

Dispatch preference:

1. Q0 work the seat may validly perform;
2. Q1 work that removes future critical-path dependency;
3. Q1 independent verification;
4. Q2 qualification/harness/transport preparation;
5. Q2 specification/evidence preparation.

A healthy seat MAY remain idle only when no admissible work exists or when preserving independence/resource/authority constraints requires parking it.

When no work is admissible, project:

`SWARM_QUIESCENT`

with exact blocking reasons.

## 12. Queue projection

Shared Comms MUST expose sufficient queue state for an operator to observe scheduling behavior.

A snapshot includes:

- Q0;
- Q1;
- Q2;
- VERIFICATION_QUEUE;
- PARKED;
- active seats/assignments;
- actionable owner gates.

A delta includes:

- triggering event identity;
- task state transitions;
- newly runnable tasks;
- newly parked tasks;
- seat freed;
- seat assigned;
- fresh dispatch identity.

Example:

```text
[RESIDUAL][QUEUE_DELTA]
source_event=sha256:...
BL-009 VERIFYING -> ACCEPTED
BL-010 BLOCKED -> READY
Mason FREE -> ASSIGNED(BL-010)
dispatch=DSP-BL010-004
```

## 13. Provider-readiness projection

Shared Comms displays provider state derived from readiness receipts, not configuration presence.

Minimum state vocabulary:

- `NOT_CONFIGURED`
- `CONFIGURED_NOT_VERIFIED`
- `NOT_READY`
- `READY_PENDING_INDEPENDENT_VERIFICATION`
- `READY`
- `DEGRADED`

Provider projection binds exact readiness receipt identity, model identity where applicable, and freshness.

`CONFIGURED != READY`.

## 14. Owner-gate projection

Owner gates are projected separately from general queue state.

A gate becomes `NEEDS_YOU` only when:

- owner-exclusive authority is required; AND
- all preceding machine-executable dependencies are satisfied; AND
- the action is currently executable.

Non-actionable future gates remain visible as parked dependencies but MUST NOT page the owner.

## 15. Restart and cold-start behavior

Before planned restart, persist:

- authoritative ledger/event head;
- queue sets;
- active assignments;
- dispatches/authority epochs/generations;
- lease/fencing state;
- checkpoints;
- pending transports;
- verifier ownership;
- provider readiness receipts;
- projection cursor(s);
- pending unprojected events.

After restart:

1. reconstruct RESIDUAL authoritative state;
2. fence stale generations;
3. re-establish Shared Comms connection;
4. reconcile outbound projection cursor;
5. deduplicate already-projected events;
6. project reconciliation state;
7. revalidate provider readiness;
8. compute runnable queue;
9. issue fresh dispatches;
10. receive fresh ACKs.

Required observable terminal:

`SHARED_COMMS_RECONCILIATION_COMPLETE`

No agent may be reactivated solely because its old chat session exists.

## 16. Relationship to BL-016

SC-CONTROL-001 depends on the relevant BL-016 transport invariant at every artifact admission boundary.

Shared Comms may carry emergency transport envelopes during v1 qualification, but the control plane MUST distinguish:

`MESSAGE_DELIVERED`

from:

`BYTE_EXACT_VERIFIED`

from:

`ELIGIBLE_FOR_VALIDATION`

from:

`ACCEPTED`.

SC-CONTROL qualification MUST include at least one artifact-bearing assignment path that exercises the byte-verification boundary.

## 17. Relationship to BL-007 Mission Board

Mission Board and Shared Comms are sibling projections of the same authoritative state.

Required consistency relation:

```text
authoritative event state
        |
        +--> Mission Board projection
        |
        +--> Shared Comms projection
```

Neither projection may silently invent state not present in the authoritative event set.

For the qualification campaign, a deterministic reconciliation check MUST establish semantic agreement for the tested missions.

## 18. Relationship to BL-009 provider continuity

SC-CONTROL must visibly project:

- primary provider failure classification;
- breaker transition;
- fallback readiness/admission state;
- parking when no route is admissible;
- provider epoch/fencing;
- resumed mission checkpoint;
- terminal fallback receipt.

Provider continuity MAY advance without the owner acting as message bus.

## 19. Relationship to BL-010 proof program

SC-CONTROL-001 is a prerequisite for the strongest BL-010 native-execution claim.

The BL-010 native mission must visibly traverse Shared Comms while all authoritative transitions remain RESIDUAL-controlled.

If BL-010 can only succeed because the owner manually tells agents what to do next, the native-execution claim is not closed.

## 20. Negative qualification matrix

### SC-N01 — stale generation ACK

Send a syntactically valid ACK from an older generation.

Expected: retained as evidence; authoritative assignment unchanged; stale ingress rejection projected.

### SC-N02 — rescinded dispatch result

Submit a result for a dispatch whose authority state is RESCINDED/SUPERSEDED.

Expected: result preserved but cannot advance mission.

### SC-N03 — duplicate projected DISPATCH

Deliver/project the same source dispatch event twice.

Expected: one authoritative assignment; duplicate projection harmless.

### SC-N04 — duplicate inbound RESULT

Submit the same correlated result twice.

Expected: one authoritative result transition; duplicate retained/deduplicated.

### SC-N05 — wrong-seat result

Valid mission/dispatch identifiers but unexpected seat/generation.

Expected: rejection/fencing.

### SC-N06 — chat-only artifact

Paste artifact contents or a claimed digest without admissible transport verification.

Expected: no artifact admission.

### SC-N07 — corrupted artifact transfer

Artifact referenced by Shared Comms arrives with byte mismatch.

Expected: blocked before validation/consumer use; transport failure visible.

### SC-N08 — blocked dependency

Worker completes predecessor while successor has another unsatisfied dependency.

Expected: DAG recompute occurs; successor remains PARKED; no fabricated readiness.

### SC-N09 — verifier independence conflict

Only the author seat is free when terminal verification is pending.

Expected: verification remains queued/parked rather than self-verified.

### SC-N10 — projection outage

Shared Comms projection fails while RESIDUAL remains healthy.

Expected: authoritative state remains correct; degraded projection recorded; no duplicate state mutation on recovery.

### SC-N11 — restart with pending assignment

Restart coordinator/host after durable checkpoint with active mission.

Expected: stale generation fenced; mission reconstructed; fresh dispatch/ACK; no duplicate accepted work.

### SC-N12 — late pre-restart result

Old seat sends result after ownership/generation advanced post-restart.

Expected: late evidence retained, authoritative transition rejected.

### SC-N13 — owner gate not actionable

Future owner-exclusive gate exists but prerequisite is incomplete.

Expected: gate visible but absent from actionable `NEEDS_YOU`.

### SC-N14 — no admissible work

All remaining missions parked or owner-gated.

Expected: `SWARM_QUIESCENT` with exact blockers, not silent idle and not fabricated work.

## 21. Qualification campaign

Qualification MUST use real Shared Comms and real RESIDUAL state. Unit tests alone are insufficient.

### SC-Q1 — Projection fidelity

For a frozen mission corpus, compare authoritative event stream, Mission Board projection, and Shared Comms projection.

Pass:

- all required control events represented;
- no invented authoritative state;
- source-event correlation complete;
- deterministic semantic reconciliation succeeds.

### SC-Q2 — Three-transition work-conserving dogfood

The owner sends no routing messages for at least three consecutive terminal scheduling transitions.

Required sequence:

1. Task A reaches terminal receipt.
2. RESIDUAL recomputes DAG.
3. Shared Comms shows queue delta.
4. successor Task B is automatically dispatched.
5. B worker ACK is correlated.
6. B reaches terminal/frozen state.
7. verifier or next successor is automatically dispatched.
8. verifier ACK/result is correlated.
9. Station acceptance updates authoritative state.
10. Task C becomes runnable/assigned or the swarm proves quiescence.

Pass:

- at least three automatic scheduling transitions;
- zero owner routing messages;
- every transition correlated to durable event/receipt identity;
- no unauthorized or duplicate authoritative transition.

### SC-Q3 — Artifact-bearing mission

At least one dispatched mission transports an artifact through the controlling byte-verification gate.

Pass:

- Shared Comms dispatch/reference visible;
- recipient byte verification visible;
- no chat-only admission;
- downstream verification consumes exact verified bytes.

### SC-Q4 — Provider continuity visibility

Exercise an admissible provider failure/fallback or controlled synthetic equivalent.

Pass:

- failure classification visible;
- provider readiness/admission visible;
- mission checkpoint/resume visible;
- authoritative receipt chain intact;
- owner not used as message bus.

### SC-Q5 — Cold-start reconciliation

Perform a planned Kimi/LEGION or equivalent coordinator-host restart after a durable pre-restart baseline.

Pass:

- stale generations fenced;
- queue reconstructed;
- projection cursor reconciled;
- no duplicate assignment/acceptance;
- provider readiness re-established honestly;
- outstanding missions resume from durable checkpoints;
- Shared Comms visibly reports reconciliation and new dispatches;
- owner does not re-explain mission state.

### SC-Q6 — Negative matrix

Execute SC-N01..N14 or documented equivalent injections.

Pass: every negative reaches the expected fail-closed state with retained evidence.

## 22. Release gate

SC-CONTROL-001 reaches `SHARED_COMMS_CONTROL_PLANE_QUALIFIED` only when all are true:

- SC-Q1..Q6 PASS;
- at least three consecutive automatic scheduling transitions demonstrated;
- zero owner routing messages during SC-Q2;
- zero unauthorized authoritative transitions;
- zero chat-only artifact admissions;
- stale/rescinded/wrong-seat messages rejected;
- restart/cold-start reconciliation PASS;
- Mission Board and Shared Comms semantically agree with authoritative state for qualification missions;
- verifier independence preserved;
- queue state reconstructable from durable artifacts;
- first failures preserved;
- exact qualification bundle and receipts sealed.

## 23. v1 release positioning

The intended v1 sequence is:

```text
SC-MESH / seat identity
    + Station acceptance
    + BL-006 model admission
    + BL-007 Mission Board
    + BL-009 provider continuity
    + BL-016 transport boundary
        |
        v
SC-CONTROL-001
        |
        v
BL-010 native execution / provider-continuity dogfood
        |
        v
v1 release qualification
```

SC-CONTROL-001 may be designed/prepared in parallel, but terminal qualification depends on the exact v1 surfaces it exercises.

## 24. v2 handoff

v2 HCOR consumes SC-CONTROL-001 as proven substrate.

SC-CONTROL proves:

- one authoritative RESIDUAL control plane can coordinate a real Shared Comms swarm;
- event-driven queue progression works;
- assignments/ACKs/results are correlated and fenced;
- Shared Comms can expose control-plane state without becoming authority;
- restart recovery can reconstruct coordination.

HCOR extends this to:

- hierarchical coordinators;
- recursive delegation;
- mission-based hierarchy;
- multi-host resource scheduling;
- coordinator replacement;
- larger scale and failure campaigns.

SC-CONTROL-001 is therefore a v1 prerequisite and a v2 foundation, not deferred v2 scope.

## 25. Required evidence bundle

Final qualification bundle SHOULD contain at minimum:

- frozen SC-CONTROL spec identity;
- implementation source/tree identity;
- event/projector/ingress interface identities;
- queue snapshot before campaign;
- raw Shared Comms transcript/message identities for qualification window;
- authoritative event-log slice;
- Mission Board projection slice;
- dispatch/ACK/result/verification/acceptance receipts;
- BL-016 transport receipts for artifact-bearing mission;
- provider-readiness receipts;
- pre/post restart baseline and reconciliation receipts;
- negative-test evidence;
- owner-message audit demonstrating zero routing messages in SC-Q2;
- final independent verification receipt.

## 26. Success metrics

Primary v1 metric:

`owner_routing_messages_per_completed_transition = 0`

Additional:

- terminal-receipt -> successor-dispatch latency;
- queue-recompute latency;
- projection lag;
- duplicate projection rate;
- rejected stale ingress count;
- owner intervention count;
- verifier independence coverage;
- restart recovery time;
- duplicate accepted-work count;
- projection/authoritative-state divergence count.

Required final values for qualification:

- unauthorized accepted transitions = 0;
- duplicate accepted work = 0;
- projection/state divergence = 0 for qualification corpus;
- chat-only artifact admissions = 0;
- owner routing messages during SC-Q2 = 0.

---

**Terminal design state:** `SC_CONTROL_001_V1_SPECIFIED`
