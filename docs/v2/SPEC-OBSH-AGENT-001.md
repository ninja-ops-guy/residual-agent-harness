# SPEC-OBSH-AGENT-001 — Swarm Runtime Observability & Stall Intelligence

**Status:** SPEC_PROPOSED / PARKED / POST-v1  
**Track:** RESIDUAL v2 → OBSH / Shared Comms / Autonomous Operations  
**Implementation authority:** none before the v2 kickoff gate.

## 1. Purpose

Make every seat, assignment, execution, dependency wait, and recovery transition observable and evidence-backed so RESIDUAL can distinguish **alive, working, waiting, blocked, stalled, and dead**, then recover autonomously when existing authority permits.

Motivating case `OBS-STALL-001`: a seat may remain visibly ONLINE while useful-work progression is externally indeterminate. Presence therefore MUST NOT imply health, progress, task execution, or admissibility.

## 2. Orthogonal runtime state

Transport: `UNREACHABLE | REACHABLE | DEGRADED`  
Process: `ABSENT | STARTING | RUNNING | EXITED | FAILED | UNKNOWN`  
Lease: `NONE | OFFERED | ACKNOWLEDGED | ACTIVE | EXPIRING | EXPIRED | FENCED | ORPHANED`  
Work: `IDLE | RUNNING | WAITING | BLOCKED | BACKOFF | VERIFYING | COMPLETING | FAILED | COMPLETE | UNKNOWN`  
Progress: `ADVANCING | QUIESCENT_EXPECTED | NO_PROGRESS | STALLED | UNKNOWN`

No state implies another. A reachable/running seat with an active lease may still be stalled.

## 3. Typed waits and blocks

Waiting reasons include model, tool, transport, remote seat, dependency, verifier, authority, rate limit, resource, retry window, external system, and UNKNOWN.

Blocked reasons include capability, admission, authority, transport, identity, evidence, resource, first failure, and UNKNOWN.

RESIDUAL MUST NOT infer a causal explanation from inactivity alone.

## 4. WorkProgressReceipt

Each active assignment MUST periodically emit or permit derivation of a receipt binding:
- seat/host/generation;
- work/task/lease identity;
- current phase;
- transport/process/lease/work/progress states;
- bounded progress counters where meaningful;
- last transition/evidence/heartbeat timestamps;
- typed wait/block reason;
- authority class;
- source HEAD/TREE where applicable;
- evidence head and previous-receipt digest.

A heartbeat is not a progress receipt. A progress receipt is not proof of correctness.

## 5. Progress signals

Progress may be established from lifecycle transitions, receipt emission, Evidence Bus advancement, relevant artifact change, Factory transitions, tool/model completion, test/check completion, scheduler transition, checkpoint creation, verifier transition, or Station transition.

CPU, memory, I/O, process existence, and socket activity are supplementary only.

## 6. StallAssessment

Required classifications:
`HEALTHY_PROGRESS | HEALTHY_WAIT | SUSPECTED_STALL | VERIFIED_STALL | TARGET_FAILURE | OBSERVER_STALLED | UNKNOWN`.

`OBSERVER_STALLED` and `TARGET_FAILURE` MUST remain distinct. Observer inability to see progress cannot be upgraded to target failure.

## 7. Predicate-specific stall policy

There is no universal timeout. Each work class declares a stall policy with heartbeat deadline, progress deadline, expected quiescent states, invalidating events, and execution-time revalidation requirements.

## 8. StallDiagnosisReceipt

A diagnosis binds observations, last transition, lease, process/Factory identity, outstanding model/tool operation, dependencies, admission/authority state, transport, evidence cursor, resource observations, supported and unsupported causes, provenance/confidence, recommended recovery, and recovery authority.

Derived causes MUST be traceable to observations. Unsupported causes remain UNKNOWN.

## 9. Recovery authority

Diagnosis feeds existing Factory/scheduler authority. Permitted autonomous recovery may include checkpoint, authorized retry, transport failover, stale-lease fencing, assignment expiry, reassignment, accepted-checkpoint resume, or failed-worker replacement.

Protected recovery produces `OWNER_GATE_REQUIRED` with exact evidence and requested authority. The stall detector itself receives no mutation authority.

## 10. First-failure and generation discipline

Recovery preserves the original lease/generation, evidence head, progress receipt, diagnosis, failure classification, checkpoint, recovery decision, and replacement generation.

A fenced generation cannot later become accepted work. Late results are `STALE_GENERATION`.

## 11. Command Station surfaces

Add a Swarm Operations view showing host/seat topology and, per seat:
- work/phase/lease/generation;
- state and state age;
- last heartbeat/progress/evidence;
- typed wait/block reason;
- process and transport state;
- StallAssessment;
- authority class;
- causal event timeline.

UI state MUST be derived from evidence/telemetry, not decorative inference.

## 12. Correlation identity

Trace WorkID, MissionID, LeaseID, Generation, SeatID, HostID, FactoryExecutionID, ProviderRequestID, ToolCallID, EvidenceID, ReceiptID, and CandidateID across one causal chain.

## 13. Metrics

Initial metrics include seat liveness/health, active leases, work state/age, last-progress age, evidence cursor, model/tool/transport wait, suspected/verified stalls, fenced leases, reassignments, recovery success, owner interventions, `owner_coordination_messages_total`, and `owner_authority_actions_total`.

Owner coordination and owner authority MUST remain separate metrics.

## 14. Security/privacy

Telemetry MUST NOT expose credentials, API keys, secrets, protected configuration, or private prompts absent explicit evidence authority. Prefer digests, identities, state, duration, errno/error class, and bounded metadata.

## 15. Required adversarial qualification

At minimum test:
1. seat online / worker dead;
2. process alive / lease expired;
3. active lease / no progress;
4. healthy long model wait;
5. tool timeout;
6. Shared Comms partition;
7. observer failure masquerading as target failure;
8. late result from fenced generation;
9. artifacts emitted without progress receipt;
10. heartbeats while execution deadlocked;
11. dependency satisfied while parked;
12. legitimate owner-gate wait;
13. worker recovery before reassignment;
14. reassignment racing original result;
15. recovery with missing first-failure evidence;
16. fake progress spam;
17. irrelevant evidence-cursor advancement;
18. CPU consumption without lifecycle progress.

## 16. Multi-host acceptance campaign

Qualify across at least two hosts and multiple seats. Inject model delay, worker kill, transport partition, tool hang, lease expiry, provider throttle, dependency wait, observer outage, late result, and process deadlock.

Separate terminal claims:
- `SWARM_RUNTIME_OBSERVABILITY_QUALIFIED`
- `STALL_CLASSIFICATION_QUALIFIED`
- `AUTONOMOUS_STALL_RECOVERY_QUALIFIED`

No later claim is implied by an earlier one.

## 17. Success criterion

The end-to-end target is:

`worker stops progressing → RESIDUAL observes → evidence-backed diagnosis → recovery authority evaluated → authorized recovery → successor continues exact work → independent continuity evidence → owner did not diagnose or route recovery`.

This spec is a prerequisite input to SELFHOST-R0 unattended-operation claims: RESIDUAL must not operate on itself unattended unless it can distinguish progressing, blocked, stalled, observer-stalled, and dead workers with evidence-backed recovery.
