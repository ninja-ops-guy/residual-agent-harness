# CANARY_ATTACK_CORPUS_V1

Status: **review-only; canary execution is not authorized**.

This matrix is generated from `CANARY_ATTACK_CORPUS_V1.json`. Cases use disposable/synthetic fixtures only. `R4.1 coverage` does not classify an untested case as an R4.1 defect. `PRE_CANARY_BLOCKER` is conditional: it applies only if the deterministic oracle is violated by pre-canary validation.

Corpus cases: **36**. Candidate: `8701367db6d3202f24b3eb9f4696b0cadf657985` / `79bfe6ed1743907065ed44aeb9c460c47527e0c6`.

## Human-readable matrix

| ID | Scenario | Category | Status | Severity | Expected network actions | Expected durable result | R4.1 coverage | Future gate |
|---|---|---|---|---|---|---|---|---|
| CAA-001 | commit succeeds + ACK lost | lost_ack | PROVEN | CRITICAL | POST comms -> indeterminate transport result → PROCESS_RESTART → GET comms/receipt -> matching receipt → LOCAL_ACK | ACKED; receipt=matching authoritative receipt; receiver=1 | DIRECT: R4-G13, R4-G14 | R5-LOST-ACK |
| CAA-002 | receipt lookup unavailable | reconciliation | OBSERVED | CRITICAL | GET comms/receipt -> unavailable | PENDING; receipt=UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13 | R5-RECONCILIATION |
| CAA-003 | receipt lookup timeout | reconciliation | R5_CANDIDATE | HIGH | GET comms/receipt -> timeout | PENDING; receipt=UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13 | R5-RECONCILIATION |
| CAA-004 | receipt endpoint 4xx | http_semantics | R5_CANDIDATE | HIGH | GET comms/receipt -> 4xx → ABORT | PENDING; receipt=REJECTED_OR_UNKNOWN; receiver=[0, 1] | NONE: R4-G13 | R5-HTTP-SEMANTICS |
| CAA-005 | receipt endpoint 5xx | http_semantics | R5_CANDIDATE | HIGH | GET comms/receipt -> 5xx → ABORT | PENDING; receipt=UNKNOWN; receiver=[0, 1] | NONE: R4-G13 | R5-HTTP-SEMANTICS |
| CAA-006 | malformed receipt | receipt_integrity | R5_CANDIDATE | CRITICAL | GET comms/receipt -> malformed → ABORT | PENDING; receipt=INVALID; receiver=[0, 1] | PARTIAL: R4-G11, R4-G13 | R5-RECEIPT-INTEGRITY |
| CAA-007 | wrong operation_id receipt | receipt_integrity | R5_CANDIDATE | CRITICAL | GET comms/receipt -> mismatched operation_id → ABORT | PENDING; receipt=MISMATCHED; receiver=[0, 1] | NONE: R4-G13 | R5-RECEIPT-INTEGRITY |
| CAA-008 | wrong project receipt | receipt_integrity | R5_CANDIDATE | CRITICAL | GET comms/receipt -> mismatched project → ABORT | PENDING; receipt=MISMATCHED; receiver=[0, 1] | NONE: R4-G13 | R5-RECEIPT-INTEGRITY |
| CAA-009 | stale receipt | receipt_integrity | OPEN_HYPOTHESIS | CRITICAL | GET comms/receipt -> stale receipt → ABORT | PENDING; receipt=STALE; receiver=[0, 1] | NONE: R4-G13 | R5-RECEIPT-INTEGRITY |
| CAA-010 | duplicate operation_id / same payload | idempotency | OBSERVED | HIGH | POST comms → POST comms same key/payload | ACKED; receipt=same receipt returned twice; receiver=1 | PARTIAL: R4-G10, R4-G17 | R5-IDEMPOTENCY |
| CAA-011 | duplicate operation_id / different payload | idempotency | OBSERVED | CRITICAL | POST comms payload A → POST comms payload B -> reject | ACKED_FOR_A_AND_REJECT_B; receipt=receipt binds payload A only; receiver=1 | PARTIAL: R4-G10, R4-G17 | R5-IDEMPOTENCY |
| CAA-012 | sender crash before POST | crash_boundary | R5_CANDIDATE | HIGH | PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt -> absent → POST comms → LOCAL_ACK | ACKED; receipt=matching new receipt; receiver=1 | PARTIAL: R4-G10, R4-G14 | R5-CRASH-BOUNDARY |
| CAA-013 | sender crash during POST | crash_boundary | R5_CANDIDATE | CRITICAL | POST comms -> indeterminate → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt -> receipt_or_absent → POST only if absent → LOCAL_ACK | ACKED_OR_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-CRASH-BOUNDARY |
| CAA-014 | sender crash after remote commit | crash_boundary | PROVEN | CRITICAL | POST comms -> remote commit → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt -> matching receipt → LOCAL_ACK | ACKED; receipt=matching authoritative receipt; receiver=1 | DIRECT: R4-G13, R4-G14 | R5-CRASH-BOUNDARY |
| CAA-015 | sender crash before local ACK | crash_boundary | R5_CANDIDATE | HIGH | GET comms/receipt -> matching receipt → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt -> matching receipt → LOCAL_ACK | ACKED; receipt=matching authoritative receipt; receiver=1 | PARTIAL: R4-G13, R4-G14 | R5-CRASH-BOUNDARY |
| CAA-016 | sender crash during local ACK persistence | crash_boundary | OPEN_HYPOTHESIS | CRITICAL | GET comms/receipt -> matching receipt → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt -> matching receipt → LOCAL_ACK | ACKED_AFTER_ATOMIC_RECOVERY; receipt=matching authoritative receipt; receiver=1 | PARTIAL: R4-G10, R4-G14 | R5-CRASH-BOUNDARY |
| CAA-017 | repeated restart | restart | OBSERVED | HIGH | RESTART → RESTART → RESTART | ACKED; receipt=matching receipt retained; receiver=1 | DIRECT: R4-G13, R4-G14 | R5-RESTART |
| CAA-018 | two simultaneous recovery processes | concurrency | OPEN_HYPOTHESIS | CRITICAL | GET receipt by A → GET receipt by B → at most one POST if absent | ACKED_ONCE_OR_PENDING_FAIL_CLOSED; receipt=single matching receipt or unknown; receiver=[0, 1] | NONE: R4-G10, R4-G13 | R5-CONCURRENCY |
| CAA-019 | SQLite lock/contention | storage | R5_CANDIDATE | HIGH | GET receipt only if durable row can be read safely → NO_POST_ON_STORAGE_UNCERTAINTY | PENDING_OR_EXPLICIT_STORAGE_ERROR; receipt=UNCHANGED_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G10 | R5-STORAGE |
| CAA-020 | corrupted outbox | storage | R5_CANDIDATE | CRITICAL | none | QUARANTINED_OR_EXPLICIT_ERROR; receipt=UNQUERIED; receiver=[0, 1] | NONE: R4-G10 | R5-STORAGE |
| CAA-021 | truncated outbox | storage | R5_CANDIDATE | CRITICAL | none | QUARANTINED_OR_EXPLICIT_ERROR; receipt=UNQUERIED; receiver=[0, 1] | NONE: R4-G10 | R5-STORAGE |
| CAA-022 | stale pending operation | retention | OBSERVED | HIGH | none | PENDING_STALE_NOT_AUTO_SENT; receipt=UNQUERIED; receiver=[0, 1] | PARTIAL: R4-G10, R4-G17 | R5-RETENTION |
| CAA-023 | server restart during reconciliation | server_lifecycle | R5_CANDIDATE | CRITICAL | GET receipt -> disconnect_or_timeout → ABORT_WITHOUT_POST | PENDING; receipt=UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G15 | R5-SERVER-LIFECYCLE |
| CAA-024 | evidence collector failure | evidence | R5_CANDIDATE | CRITICAL | protocol actions may complete → NO_SUCCESS_DECLARATION | ACKED_OR_PENDING_AS_OBSERVED; receipt=as observed but not sufficient for PASS; receiver=[0, 1] | PARTIAL: R4-G16 | R5-EVIDENCE |
| CAA-025 | rollback invocation failure | rollback | R5_CANDIDATE | HIGH | none | PRESERVED; receipt=UNCHANGED; receiver=[0, 1] | PARTIAL: R4-G16 | R5-ROLLBACK |
| CAA-026 | network partition | network | R5_CANDIDATE | CRITICAL | GET receipt -> unavailable → ABORT_WITHOUT_POST | PENDING; receipt=UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G02, R4-G13 | R5-NETWORK |
| CAA-027 | authentication expiration | authorization | R5_CANDIDATE | CRITICAL | GET receipt -> auth failure → ABORT_WITHOUT_POST | PENDING; receipt=UNKNOWN; receiver=[0, 1] | NONE: R4-G13 | R5-AUTHORIZATION |
| CAA-028 | authorization rejection | authorization | R5_CANDIDATE | CRITICAL | none | UNCHANGED; receipt=UNQUERIED; receiver=0 | PARTIAL: R4-G11, R4-G12 | R5-AUTHORIZATION |
| CAA-029 | disk-write failure | storage | R5_CANDIDATE | CRITICAL | NO_POST_IF_DURABLE_ENQUEUE_OR_SCOPE_EVIDENCE_FAILED | PENDING_IF_PREEXISTING_OTHERWISE_ABSENT; receipt=UNQUERIED_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G10, R4-G16 | R5-STORAGE |
| CAA-030A | SIGKILL before receipt lookup | sigkill_matrix | R5_CANDIDATE | CRITICAL | PROCESS_RESTART → GET comms/receipt | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |
| CAA-030B | SIGKILL during receipt lookup | sigkill_matrix | R5_CANDIDATE | CRITICAL | GET comms/receipt -> indeterminate → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |
| CAA-030C | SIGKILL after receipt hit before ACK | sigkill_matrix | R5_CANDIDATE | CRITICAL | GET comms/receipt -> matching receipt → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt -> matching receipt → LOCAL_ACK | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |
| CAA-030D | SIGKILL during ACK transaction | sigkill_matrix | R5_CANDIDATE | CRITICAL | GET comms/receipt -> matching receipt → LOCAL_ACK -> interrupted → PROCESS_RESTART → GET comms/receipt -> matching receipt → LOCAL_ACK | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |
| CAA-030E | SIGKILL after ACK commit before exit | sigkill_matrix | R5_CANDIDATE | CRITICAL | PROCESS_EXIT → PROCESS_RESTART | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |
| CAA-030F | SIGKILL after absent receipt before POST | sigkill_matrix | R5_CANDIDATE | CRITICAL | GET comms/receipt -> absent → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt → POST only if still absent | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |
| CAA-030G | SIGKILL during conditional POST | sigkill_matrix | R5_CANDIDATE | CRITICAL | GET comms/receipt -> absent → POST comms -> indeterminate → PROCESS_EXIT → PROCESS_RESTART → GET comms/receipt | ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED; receipt=MATCHING_OR_UNKNOWN; receiver=[0, 1] | PARTIAL: R4-G13, R4-G14 | R5-SIGKILL-MATRIX |

## Coverage map against R4 gates

- **R4-G01:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G02:** CAA-026
- **R4-G03:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G04:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G05:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G06:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G07:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G08:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G09:** No direct attack-corpus mapping; existing gate scope remains unchanged.
- **R4-G10:** CAA-010, CAA-011, CAA-012, CAA-016, CAA-018, CAA-019, CAA-020, CAA-021, CAA-022, CAA-029
- **R4-G11:** CAA-006, CAA-028
- **R4-G12:** CAA-028
- **R4-G13:** CAA-001, CAA-002, CAA-003, CAA-004, CAA-005, CAA-006, CAA-007, CAA-008, CAA-009, CAA-013, CAA-014, CAA-015, CAA-017, CAA-018, CAA-023, CAA-026, CAA-027, CAA-030A, CAA-030B, CAA-030C, CAA-030D, CAA-030E, CAA-030F, CAA-030G
- **R4-G14:** CAA-001, CAA-012, CAA-013, CAA-014, CAA-015, CAA-016, CAA-017, CAA-030A, CAA-030B, CAA-030C, CAA-030D, CAA-030E, CAA-030F, CAA-030G
- **R4-G15:** CAA-023
- **R4-G16:** CAA-024, CAA-025, CAA-029
- **R4-G17:** CAA-010, CAA-011, CAA-022

## Proposed R5 gates

- **R5-AUTHORIZATION:** CAA-027, CAA-028
- **R5-CONCURRENCY:** CAA-018
- **R5-CRASH-BOUNDARY:** CAA-012, CAA-013, CAA-014, CAA-015, CAA-016
- **R5-EVIDENCE:** CAA-024
- **R5-HTTP-SEMANTICS:** CAA-004, CAA-005
- **R5-IDEMPOTENCY:** CAA-010, CAA-011
- **R5-LOST-ACK:** CAA-001
- **R5-NETWORK:** CAA-026
- **R5-RECEIPT-INTEGRITY:** CAA-006, CAA-007, CAA-008, CAA-009
- **R5-RECONCILIATION:** CAA-002, CAA-003
- **R5-RESTART:** CAA-017
- **R5-RETENTION:** CAA-022
- **R5-ROLLBACK:** CAA-025
- **R5-SERVER-LIFECYCLE:** CAA-023
- **R5-SIGKILL-MATRIX:** CAA-030A, CAA-030B, CAA-030C, CAA-030D, CAA-030E, CAA-030F, CAA-030G
- **R5-STORAGE:** CAA-019, CAA-020, CAA-021, CAA-029

Each proposed gate must use a frozen fixture, bounded clock/attempt budget, exact network trace, durable-state postconditions, receiver count, protected-service comparison, and hash-complete evidence. Missing evidence yields `EVIDENCE_INCOMPLETE`, not PASS.

## Unresolved hypotheses

- **CAA-003 — receipt lookup timeout (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-004 — receipt endpoint 4xx (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-005 — receipt endpoint 5xx (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-006 — malformed receipt (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-007 — wrong operation_id receipt (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-008 — wrong project receipt (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-009 — stale receipt (OPEN_HYPOTHESIS):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-012 — sender crash before POST (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-013 — sender crash during POST (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-015 — sender crash before local ACK (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-016 — sender crash during local ACK persistence (OPEN_HYPOTHESIS):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-018 — two simultaneous recovery processes (OPEN_HYPOTHESIS):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-019 — SQLite lock/contention (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-020 — corrupted outbox (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-021 — truncated outbox (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-023 — server restart during reconciliation (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-024 — evidence collector failure (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-025 — rollback invocation failure (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-026 — network partition (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-027 — authentication expiration (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-028 — authorization rejection (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-029 — disk-write failure (R5_CANDIDATE):** Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030A — SIGKILL before receipt lookup (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030B — SIGKILL during receipt lookup (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030C — SIGKILL after receipt hit before ACK (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030D — SIGKILL during ACK transaction (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030E — SIGKILL after ACK commit before exit (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030F — SIGKILL after absent receipt before POST (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.
- **CAA-030G — SIGKILL during conditional POST (R5_CANDIDATE):** Systematically locates crash-consistency boundaries in receipt-first recovery. If its oracle is violated, disposition is `PRE_CANARY_BLOCKER`; this document does not assert that violation exists.

## Integrity

The JSON is canonicalized with sorted keys and a trailing newline. Validate by rerunning the generator and requiring a clean diff. Current JSON SHA-256 is inserted below after generation.
- `CANARY_ATTACK_CORPUS_V1.json`: `f350963a80e315f0ece1865bda3bb82f2acfc718e13fd8b6f59ea0ddd506884b`
