# RESIDUAL Health Coordination Failure Register R0

Status: **OBSERVED-FAILURE CORPUS / DESIGN INPUT**

These classes are derived from fleet dogfooding. An entry records an observed class; it does not claim a Doctor detector is implemented.

| ID | Classification | Stage | Doctor predicate |
|---|---|---|---|
| HC-001 | WATCHDOG_NOT_ACTUALLY_SCHEDULED | WAKEUP | Required watchdog has durable deadline and actual wake source. |
| HC-002 | WAKEUP_FIRED_NO_ACTION | WAKEUP | Wake fired AND durable consumer action occurred; identify missing edge. |
| HC-003 | CONTROL_PLANE_AUTHORITY_GAP | AUTHORITY | Exactly one admitted authoritative Station/event source owns claimed queue truth. |
| HC-004 | FREE_SEAT_UNDISPOSED | SCHEDULING | Freed seat reaches successor assignment or explicit durable IDLE/PARKED disposition. |
| HC-005 | STALE_DISPATCH | SCHEDULING | Dispatch deadline/lease state is current and classified. |
| HC-006 | TRANSPORT_STALL | TRANSPORT | Sender commitment and recipient byte count/digest converge. |
| HC-007 | PROJECTION_LAG | PROJECTION | Projection cursor/outbox lag is bounded or explicitly DEGRADED. |
| HC-008 | SEMANTIC_DUPLICATE_REBIND_RISK | EVIDENCE | Byte identity and semantic identity are separate; semantic duplicate cannot rebind authority. |
| HC-009 | ASSIGNMENT_BOUNDARY_VIOLATION | AUTHORITY | ACK/acquire seat matches dispatch binding; wrong-seat attempt rejected and retained. |
| HC-010 | PROVIDER_AUTH_MISSING | PROVIDER | Required credential presence/resolution exists without exposing value. |
| HC-011 | MEMORY_PROVIDER_DEGRADED | PROVIDER | Memory/embedding health is independent from chat inference health. |
| HC-012 | DUPLICATE_OR_STALE_GATEWAY | DISCOVERY | Gateway/profile/listener inventory has explicit ownership and health. |
| HC-013 | DEAD_STATION_POLLING | EXECUTION | Worker target is reachable/current or worker explicitly degraded/stopped. |
| HC-014 | RUNNER_UNENROLLED | ENROLLMENT | Seat presence and runner enrollment are checked separately. |
| HC-015 | RUNNER_EXEC_CONTRACT_MISMATCH | EXECUTION | Exact bridge adapter contract exists on executable runner will invoke. |
| HC-016 | RUNNER_RUNTIME_VERSION_SKEW | EXECUTION | Runtime identity satisfies exact adapter capability/version contract. |
| HC-017 | RESTART_AUTHORITY_DRIFT | RECONCILIATION | Restart fences stale generations; fresh work uses current epoch/generation. |
| HC-018 | BASELINE_HEAD_FALSE_MISMATCH | RECONCILIATION | Baseline head is verified ancestor; intervening events admissible; epoch/fencing continuity holds. |
| HC-019 | PROVIDER_RESULT_REPLAY_HAZARD | PROVIDER | Durable result is reused; provider call count cannot increase after RESULT_RECORDED. |
| HC-020 | INDETERMINATE_PROVIDER_OUTCOME | PROVIDER | Stranded INVOCATION_STARTED stops unless provider idempotency proves replay safe. |
| HC-021 | CONTEXT_EXHAUSTION | EXECUTION | Session consumption capacity observable; coordination truth survives context failure. |
| HC-022 | STALE_STATION_PROJECTION | PROJECTION | Projection freshness and authoritative event head identified separately. |
| HC-023 | MULTIPLE_STATION_ROOTS_AMBIGUOUS | AUTHORITY | Every root classified; exactly one authoritative per authority domain/epoch. |
| HC-024 | BRIDGE_FENCING_NOT_IMPLEMENTED | AUTHORITY | Bridge enforces station/epoch/dispatch/assignment/seat/generation before execution. |
| HC-025 | CREDENTIAL_OR_CONFIG_HYGIENE_ANOMALY | PROVIDER | Presence, ownership, permissions and intended credential scope checked without disclosure. |
| HC-026 | FACE_DIGEST_MISMATCH | EVIDENCE | Human-facing digest is derived from live artifact bytes and independently recomputable. |
| HC-027 | DEDUP_IDENTITY_DEGRADED | PROJECTION | Dedup mode explicit; weak content-addressed mode never represented as strong message identity. |
| HC-028 | PROJECTION_ATTEMPT_IDENTITY_CONFLICT | PROJECTION | Stable projection_id plus append-only projection_attempt identities. |
| HC-029 | FOREIGN_KEY_ENFORCEMENT_DISABLED | EVIDENCE | Store connection proves foreign_keys=ON when schema depends on FKs. |
| HC-030 | RUNNER_REGISTRATION_INCOMPLETE | ENROLLMENT | Registration, exec contract, heartbeat, binding, native assignment and result are separate predicates. |

## Evidence origins represented

The corpus includes observed specimens from: policy-only watchdogs; a real cron fire without agent consumption; DELL Station enumeration showing no authoritative scheduler; silent free-seat/dispatch stalls; byte transport stalls; semantic duplicate rebinding; wrong-seat execution; DBOX provider/memory auth gaps and duplicate listener; DELL worker polling dead :8765; DELL OpenClaw seats existing without native runner enrollment; OpenClaw 2026.5.28 lacking the required runner execution surface; restart fencing/baseline continuity findings; BL-009 provider replay/indeterminate-call boundaries; Mason context overflow; stale qboard projection; multiple DELL Station roots; LEGION bridge fencing remaining spec-only; face-digest mistakes; SC-D projection identity/FK findings; and incomplete runner registration before native qualification.

## Register rules

1. IDs are append-only. Reclassification creates a successor/alias note; history is not rewritten.
2. Lifecycle: `OBSERVED -> DETECTOR_DESIGNED -> DETECTOR_IMPLEMENTED -> QUALIFIED`, or `RETIRED_WITH_REPLACEMENT`.
3. PASS requires positive evidence. Missing evidence is UNKNOWN/NOT_QUALIFIED.
4. Each implemented detector needs at least one positive and one negative/adversarial control.
5. Classification preserves earliest evidenced causal divergence.
6. Secrets/credential values are never fixtures; use synthetic/presence-only evidence.
7. Host-specific observations become generic detectors only after stating a hostname-independent predicate.
