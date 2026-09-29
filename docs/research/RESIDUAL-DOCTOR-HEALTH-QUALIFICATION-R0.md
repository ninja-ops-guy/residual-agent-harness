# RESIDUAL Doctor — Health Coordination Qualification R0

Status: **PREREGISTERED / NON-RUNNABLE**

This defines the minimum qualification program for Health Coordination Doctor R1. It does not authorize failure injection on production hosts.

## Objective

Prove Doctor detects known coordination failures, distinguishes DEGRADED from BLOCKED, preserves UNKNOWN, identifies first divergence, remains read-only, emits stable machine evidence, and never grants scheduling/provider/mission authority.

## Fixture families

### Q-HC-01 Wakeup chain

Cases:
- deadline absent -> HC-001;
- deadline registered but not due -> healthy waiting state;
- deadline fired + event emitted + no consumer -> HC-002;
- deadline fired + durable consumer transition -> PASS;
- consumer action exists only in chat prose -> never PASS.

### Q-HC-02 Scheduling liveness

Cases:
- terminal -> free -> recompute -> successor dispatch -> ACK;
- terminal -> free -> recompute -> IDLE_NO_ADMISSIBLE_WORK;
- terminal -> free -> nothing -> HC-004;
- dispatch beyond deadline without ACK/classification -> HC-005.

Strict successor-dogfood and work-conservation accounting remain separate.

### Q-HC-03 Station authority

Fixtures:
- one authoritative Station;
- stale projection only;
- multiple roots with one explicitly authoritative;
- multiple roots with ambiguous authority;
- coordinator/chat queue with no Station authority.

Expected HC-003/HC-022/HC-023 must not be conflated.

### Q-HC-04 Runner lifecycle

Exercise independently:

```
seat discovered
runner enrolled
execution contract present
runner process alive
heartbeat current
Station sees runner
seat binding valid
native assignment ACK
terminal result accepted
```

Removing each predicate yields the corresponding DEGRADED/FAIL/NOT_QUALIFIED state. Presence of later-looking config cannot satisfy an earlier missing gate. Include HC-014/015/016/030.

### Q-HC-05 Provider health

Cases:
- configured but no readiness receipt;
- READY with current receipt;
- selected provider auth missing;
- memory provider unavailable while chat remains healthy;
- durable provider result followed by restart;
- stranded INVOCATION_STARTED without result.

Expected HC-010/011/019/020 and CONFIGURED != READY.

### Q-HC-06 Projection/transport

Cases:
- sender/recipient byte exact;
- sender-only claim;
- digest mismatch;
- authoritative event ahead of projection cursor;
- semantic duplicate with different bytes;
- retry under stable projection_id with separate attempt;
- face digest mismatch.

Expected HC-006/007/008/026/027/028.

### Q-HC-07 Restart/fencing

Cases:
- baseline H == current head;
- baseline H verified ancestor of H+n with admissible intervening events;
- chain break;
- stale generation returns;
- bridge lacks epoch/generation enforcement.

Expected HC-017/018/024. Healthy ledger growth after baseline MUST NOT fail merely because H != H+n.

### Q-HC-08 Context failure

Simulate coordinator/worker context exhaustion without deleting durable Station state.

PASS requires Doctor to identify session consumption failure while preserving Station/queue authority separately. It must not infer mission loss solely from session loss.

### Q-HC-09 SQLite integrity

Run with FK enforcement on and off against a schema requiring FKs. Doctor must identify HC-029 when enforcement is absent; it must not mutate PRAGMA state in read-only diagnosis.

### Q-HC-10 Multi-root host

Construct operational, stale, specimen and disposable roots. Doctor must classify all roots and avoid selecting authority from recency/name alone.

## Causal oracle

Every negative fixture declares one intended first divergence. Qualification fails if Doctor reports a downstream symptom as the root while the declared upstream evidence is available.

Example:

`deadline registered -> fired -> event emitted -> consumer absent`

Correct primary: HC-002. Incorrect primary: generic scheduler stalled.

## Read-only oracle

Run Doctor against a filesystem/DB/process snapshot and compare before/after:

- file digests;
- DB/WAL identities where stable;
- service/process set;
- listeners;
- provider config;
- runner config;
- credential stores.

No Doctor-induced mutation is allowed.

## JSON determinism

Given the same normalized evidence snapshot and frozen clock, semantic JSON output must canonicalize identically. Volatile presentation fields are separated from identity-bearing findings.

## Qualification levels

- **D0 Detector unit:** one detector + synthetic controls.
- **D1 Component:** complete stage (e.g. runner/provider/wakeup).
- **D2 Host:** read-only real-host qualification against DELL/LEGION/DBOX evidence.
- **D3 Fleet:** cross-Station report with explicit UNKNOWN where evidence is unavailable.
- **D4 Onboarding:** discovery -> mapping -> Doctor -> qualification, proving Doctor does not auto-promote lifecycle state.

## Research Workbench conversion

Observed HC classes should become staged Workbench definitions before destructive fault injection. Each experiment preregisters topology, injected failure, first-divergence oracle, safe-continuation expectation, and cleanup boundary.

No production detector is marked QUALIFIED solely because it recognizes the original historical specimen.
