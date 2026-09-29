# Health Coordination Failure Register R0

Status: observed-failure corpus; detector implementation is separate.

| ID | Classification | Stage | Required diagnostic distinction |
|---|---|---|---|
| HC-001 | WATCHDOG_NOT_ACTUALLY_SCHEDULED | WAKEUP | Policy text is not a real deadline/wake source. |
| HC-002 | WAKEUP_FIRED_NO_ACTION | WAKEUP | Timer/event fire is distinct from durable consumer action. |
| HC-003 | CONTROL_PLANE_AUTHORITY_GAP | AUTHORITY | Coordinator/chat queue is not authoritative Station state. |
| HC-004 | FREE_SEAT_UNDISPOSED | SCHEDULING | Free seat needs successor or explicit IDLE/PARKED disposition. |
| HC-005 | STALE_DISPATCH | SCHEDULING | Dispatch past ACK/progress deadline must be classified. |
| HC-006 | TRANSPORT_STALL | TRANSPORT | Sender claim is insufficient without recipient byte verification. |
| HC-007 | PROJECTION_LAG | PROJECTION | Authoritative event and Shared Comms projection freshness are separate. |
| HC-008 | SEMANTIC_DUPLICATE_REBIND_RISK | EVIDENCE | Byte identity and semantic identity must not be conflated. |
| HC-009 | ASSIGNMENT_BOUNDARY_VIOLATION | AUTHORITY | Wrong-seat execution must reject and retain evidence. |
| HC-010 | PROVIDER_AUTH_MISSING | PROVIDER | Provider/profile credential presence/resolution missing. |
| HC-011 | MEMORY_PROVIDER_DEGRADED | PROVIDER | Embedding/memory health is separate from chat inference. |
| HC-012 | DUPLICATE_OR_STALE_GATEWAY | DISCOVERY | Extra gateway/profile/listener can consume work incorrectly. |
| HC-013 | DEAD_STATION_POLLING | EXECUTION | Worker alive while polling unavailable Station. |
| HC-014 | RUNNER_UNENROLLED | ENROLLMENT | OpenClaw seat presence != RESIDUAL enrollment. |
| HC-015 | RUNNER_EXEC_CONTRACT_MISMATCH | EXECUTION | Enrolled runner runtime lacks exact bridge execution contract. |
| HC-016 | RUNNER_RUNTIME_VERSION_SKEW | EXECUTION | Runtime version/capabilities do not satisfy adapter contract. |
| HC-017 | RESTART_AUTHORITY_DRIFT | RECONCILIATION | Stale pre-restart generation/session may retain authority. |
| HC-018 | BASELINE_HEAD_FALSE_MISMATCH | RECONCILIATION | Healthy H->H+n growth must use continuity, not equality. |
| HC-019 | PROVIDER_RESULT_REPLAY_HAZARD | PROVIDER | Durable result exists but resume would invoke provider again. |
| HC-020 | INDETERMINATE_PROVIDER_OUTCOME | PROVIDER | Invocation may have escaped with no durable result; replay unsafe. |
| HC-021 | CONTEXT_EXHAUSTION | EXECUTION | Agent/coordinator cannot consume work because context overflowed. |
| HC-022 | STALE_STATION_PROJECTION | PROJECTION | Board projection is stale/non-authoritative. |
| HC-023 | MULTIPLE_STATION_ROOTS_AMBIGUOUS | AUTHORITY | Multiple roots require explicit authority classification. |
| HC-024 | BRIDGE_FENCING_NOT_IMPLEMENTED | AUTHORITY | Bridge topology exists but epoch/generation enforcement absent. |
| HC-025 | CREDENTIAL_OR_CONFIG_HYGIENE_ANOMALY | PROVIDER | Missing/unexpected auth, permissions or credential proliferation. |
| HC-026 | FACE_DIGEST_MISMATCH | EVIDENCE | Human-facing digest differs from sealed bytes. |
| HC-027 | DEDUP_IDENTITY_DEGRADED | PROJECTION | Weak dedup mode must be explicit. |
| HC-028 | PROJECTION_ATTEMPT_IDENTITY_CONFLICT | PROJECTION | Retry identity mutates cursor-referenced projection identity. |
| HC-029 | FOREIGN_KEY_ENFORCEMENT_DISABLED | EVIDENCE | Schema depends on FK but connection does not enforce it. |
| HC-030 | RUNNER_REGISTRATION_INCOMPLETE | ENROLLMENT | Enrollment exists but execution/heartbeat/binding/native qualification incomplete. |
| HC-031 | KERNEL_TIMER_STALL_UNDETECTED | WAKEUP | Kernel process may remain alive while its deadline-consumer/timer thread stops making progress; require internal heartbeat plus process-level health complement. |
| HC-032 | DELIVERY_VISIBILITY_GAP | TRANSPORT | Sender-side delivery record may exist while the intended room/coordinator/recipient never observes the message or attachment; direction and missing hop must be explicit. |
| HC-033 | ARTIFACT_ARRIVAL_NO_CONSUMER_WAKE | WAKEUP | Artifact bytes may land in shared/download storage without waking the assigned seat; artifact arrival is not equivalent to consumer activation. |
| HC-034 | SCHEDULED_JOB_CONSUMER_TIMEOUT | EXECUTION | Scheduled job may start successfully but fail inside the consumer/model phase; distinguish scheduler/wake success from execution timeout. |

## Recent evidence refinements

- **HC-031** is derived from the SC-E review amendment: SC-E-I01/I02 pass structurally, but timer-thread liveness is itself unobserved unless a supervisor heartbeat and external process-health complement exist.
- **HC-032** covers both observed transport directions: seat→room delivery not surfacing to the coordinator, and room→host attachment visibility lag. It is not the same as byte corruption; the failure is visibility/delivery at a hop.
- **HC-033** captures the BL-009/Piston stall pattern: the 7/7 bundle was already present in shared downloads, but a sleeping seat was not activated by passive file arrival. The later stall check, not the artifact landing, caused consumption.
- **HC-034** captures cron/scheduled jobs that do wake and begin execution but then fail or time out during the consumer/model-call phase. It remains distinct from HC-001 (no scheduler), HC-002 (fired but no consumer action), and HC-021 (context overflow specifically).

Lifecycle: `OBSERVED -> CORRELATED -> REPRODUCED -> DETECTOR_DESIGNED -> DETECTOR_IMPLEMENTED -> INDEPENDENTLY_QUALIFIED -> PRODUCTION_DIAGNOSTIC`.

Rules: IDs append-only; missing evidence never PASS; preserve earliest causal divergence; no secret values in fixtures; generic detectors must state host-independent predicates; each implemented detector requires positive and adversarial controls.
