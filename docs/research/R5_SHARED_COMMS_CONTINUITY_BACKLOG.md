# Residual R5 Shared Comms continuity backlog

Status: planning only  
Prepared: 2026-09-23  
R4.1 disposition supplied by the coordination handoff: `READY_FOR_CANARY`

> This source backlog is preserved for provenance. Its requirements are
> normalized into the acyclic machine-readable DAG and qualification program in
> `docs/r5/R5_DAG.json`, `R5_QUALIFICATION_MATRIX.md`, `R5_PHASE_PLAN.md`,
> `R5_GATE_SPECIFICATIONS.md`, and `R5_TEST_CORPUS_SPECIFICATIONS.md`.

## Scope and evidence boundary

This document extracts valuable work that is explicitly **not required for the
R4.1 canary**. It does not revise the R4.1 candidate, its gates, its evidence,
or the canary authorization boundary. None of the items below may be used to
retroactively broaden R4.1 or delay its already-issued `READY_FOR_CANARY`
disposition unless the canary independently discovers a new safety defect.

The referenced candidate is HEAD
`8701367db6d3202f24b3eb9f4696b0cadf657985`, tree
`79bfe6ed1743907065ed44aeb9c460c47527e0c6`. The reviewed qualification
architecture is the external R4.1 harness pinned to that identity. Its relevant
coverage is:

- R4-G10: normal durable outbox delivery and local ACK;
- R4-G13: receiver commit, lost ACK, restart, receipt lookup before repost, one
  receiver event, and reconciled local ACK;
- R4-G14: SIGKILL after enqueue and durable pending-row recovery;
- R4-G16/G17: rollback comparison and exact R3.4 regression replay;
- fail-closed final disposition: every R4-G01..G17 gate must be `PASS`, the
  baseline digest must match, and missing evidence cannot become `PASS`.

The local planning handoff did not contain the authoritative runtime
`QUALIFICATION_R4.json`; therefore this review accepts `READY_FOR_CANARY` as a
supplied fact and does not claim independent rerun or requalification. The
source artifacts show a single SQLite outbox with `PENDING`/`ACKED` states,
payload digests, receipt lookup by `(project_id, operation_id)`, and a stale-age
send cutoff. That is sufficient to identify residual design questions, not to
invalidate the qualified boundary.

## Prioritized backlog

Priorities mean: **P0** establishes the R5 safety foundation, **P1** is required
before broader or multi-process production use, and **P2** is lifecycle and
scale hardening. Dependencies refer to requirement IDs in this document.

### R5-SC-001 — Exclusive recovery ownership and fencing (P0)

- **Problem statement:** Multiple workers can open the same SQLite outbox and
  recover the same `PENDING` operation. R4 proves one restarting owner, not
  concurrent recovery ownership.
- **Invariant:** At most one live recovery authority may advance an operation;
  every send and ACK transition is conditional on a current monotonically
  fenced lease. A superseded owner cannot mutate state.
- **Threat/failure model:** Concurrent startup, overlapping supervisors,
  process pause beyond lease expiry, PID reuse, clock skew, split-brain file
  access, and a stale process resuming after takeover.
- **Proposed qualification gate:** `R5-G01` starts at least two independent
  processes against one outbox, injects pauses and lease takeover, and proves
  only the highest fencing token can send or transition each operation.
- **Required evidence:** Process timelines, lease/fence rows, network-action
  trace, transition journal, receiver event count, and final database image.
- **Dependencies:** None; foundation for R5-SC-005 and R5-SC-009.
- **Derivation:** Direct from the single-owner scope of R4-G13/G14; concurrent
  ownership risk is a new hypothesis.

### R5-SC-002 — Authenticated, request-bound receipts (P0)

- **Problem statement:** The current local ACK accepts receipt JSON returned by
  the authenticated Station channel but does not itself verify a signed or
  MAC-bound receipt before persisting `ACKED`.
- **Invariant:** `ACKED` is reachable only with a receipt whose issuer,
  protocol version, project, operation ID, canonical request digest, event
  identity/sequence, and outcome are cryptographically bound and verified
  against an authorized key and trust epoch.
- **Threat/failure model:** Forged response, compromised intermediary, receipt
  substitution across projects or operations, replay from another Station,
  tampered local receipt, key rotation, and confused-deputy lookup.
- **Proposed qualification gate:** `R5-G02` runs a signed-receipt positive case
  plus mutations of every bound field, foreign-key/epoch cases, replay cases,
  and missing-signature cases; every mutation must fail closed without ACK.
- **Required evidence:** Canonical signed payloads, public key/epoch manifest,
  verification decisions and reason codes, mutation matrix, outbox states, and
  receiver event counts.
- **Dependencies:** Protocol schema work in R5-SC-011 may be developed jointly.
- **Derivation:** Direct from R4-G10/G13 accepting receipt data and from the
  current `(project_id, operation_id)` lookup; authenticity is a new threat
  hypothesis.

### R5-SC-003 — Explicit durable reconciliation state machine (P0)

- **Problem statement:** `PENDING` and `ACKED` collapse unsent, send-in-flight,
  lookup-in-flight, retryable failure, stale, and ambiguous commit outcomes.
- **Invariant:** Every operation has one crash-durable, validated transition
  path such as `QUEUED -> SENDING -> INDETERMINATE -> RECONCILING -> ACKED`,
  with terminal `FAILED`/`QUARANTINED`; no ambiguity is represented as success
  or silently retransmitted.
- **Threat/failure model:** Crash at every persistence/network boundary,
  timeout after partial response, process restart, invalid transition,
  duplicate invocation, and repeated lookup outage.
- **Proposed qualification gate:** `R5-G03` uses deterministic crash points
  before/after every state write and network action, restarts after each, and
  model-checks observed transitions against the allowed graph.
- **Required evidence:** Versioned state graph, transition table, fault-point
  matrix, before/after database snapshots, network traces, and invariant-check
  report.
- **Dependencies:** R5-SC-001 and R5-SC-004.
- **Derivation:** Direct from R4-G13's commit-with-lost-ACK ambiguity and the
  two-state implementation.

### R5-SC-004 — Malformed/cross-bound receipt fail-closed behavior (P0)

- **Problem statement:** Receipt parsing and semantic validation are not
  independently qualified for malformed types, missing fields, oversized
  values, wrong project/operation/digest, or locally corrupted stored JSON.
- **Invariant:** A receipt is atomic and valid in full or it causes no ACK and
  no destructive state change. Project, operation, request digest, and event
  identity must all match the pending record.
- **Threat/failure model:** Truncated JSON, valid JSON with wrong types,
  duplicate keys, canonicalization traps, oversized receipt, cross-project or
  cross-operation substitution, and corrupted receipt-at-rest.
- **Proposed qualification gate:** `R5-G04` executes a bounded adversarial
  corpus at both HTTP and database boundaries and requires deterministic
  reason-coded rejection into `INDETERMINATE` or `QUARANTINED`.
- **Required evidence:** Corpus and hashes, parser limits, per-vector result,
  state delta, logs showing no unbounded/raw hostile data, and zero false ACKs.
- **Dependencies:** R5-SC-002 and R5-SC-003.
- **Derivation:** New hypothesis exposed by the receipt parsing/ACK seam used in
  R4-G10/G13.

### R5-SC-005 — Crash-safe local ACK persistence (P0)

- **Problem statement:** R4 qualifies crash before ACK and recovery afterward,
  but not power loss or write failure during the local ACK transaction itself.
- **Invariant:** After any crash during ACK persistence, restart yields either
  the prior reconcilable state or one fully durable verified ACK; never a torn,
  falsely ACKed, or unrecoverable row.
- **Threat/failure model:** Kill/power loss at SQLite commit/WAL/fsync points,
  I/O error, short write, filesystem reorder, and stale fenced owner ACK.
- **Proposed qualification gate:** `R5-G05` injects failures at each ACK
  persistence boundary, including fenced-owner races, and validates recovery
  with SQLite integrity checks and receipt re-verification.
- **Required evidence:** Fault injection map, SQLite journal/synchronous mode,
  integrity-check output, recovered row/receipt, fence token, and network trace.
- **Dependencies:** R5-SC-001 through R5-SC-004.
- **Derivation:** Direct extension of R4-G13; the in-transaction crash cases are
  a new hypothesis.

### R5-SC-006 — Corruption quarantine and recoverability (P1)

- **Problem statement:** Corrupted database pages, schema, payload JSON,
  digests, or receipt data can currently surface as generic exceptions and may
  prevent recovery of unrelated operations.
- **Invariant:** Corruption never causes send, ACK, deletion, or silent repair.
  The process fails closed, quarantines the smallest safe unit, preserves
  forensic bytes, and continues only when unaffected data is provably sound.
- **Threat/failure model:** Bit flips, truncation, invalid schema/version,
  digest mismatch, malicious local edit, damaged WAL, and partial backup.
- **Proposed qualification gate:** `R5-G06` applies a reproducible corruption
  corpus to copies of valid outboxes and checks quarantine scope, no network
  actions, evidence preservation, and documented operator recovery.
- **Required evidence:** Corpus hashes, original/corrupt database hashes,
  integrity output, quarantine manifest, network trace, and recovery report.
- **Dependencies:** R5-SC-003 and R5-SC-004.
- **Derivation:** New hypothesis; R4-G14 covers process death, not corrupt data.

### R5-SC-007 — Disk exhaustion and persistence error semantics (P1)

- **Problem statement:** Enqueue, state transition, receipt persistence, and
  evidence/log writes need explicit behavior under `ENOSPC`, quota exhaustion,
  read-only remount, and permission loss.
- **Invariant:** No network send begins unless its durable pre-send state is
  committed; no ACK is reported unless the verified receipt is durable. Storage
  failure is visible, bounded, and never downgraded to success.
- **Threat/failure model:** Full filesystem, inode exhaustion, SQLite `FULL` or
  `IOERR`, directory permission change, read-only storage, and log amplification.
- **Proposed qualification gate:** `R5-G07` uses a bounded disposable filesystem
  and injected SQLite errors at enqueue/send/ACK transitions, proving no
  unjournaled effects and deterministic recovery after capacity restoration.
- **Required evidence:** Capacity/inode telemetry, injected error location,
  network trace, API/exit status, database snapshots, and post-restoration run.
- **Dependencies:** R5-SC-003 and R5-SC-005.
- **Derivation:** New hypothesis outside R4-G10/G13/G14.

### R5-SC-008 — Stale-operation policy and explicit operator disposition (P1)

- **Problem statement:** The current age threshold merely excludes older rows
  from automatic recovery; retained stale operations have no durable policy,
  expiry reason, or safe resume/cancel workflow.
- **Invariant:** Age alone never implies not-committed, resend, success, or
  deletion. Every stale/indeterminate operation remains queryable and requires
  a versioned policy decision or authenticated operator disposition.
- **Threat/failure model:** Long outage, clock rollback/jump, delayed receipt,
  abandoned project, operator error, and restart after policy change.
- **Proposed qualification gate:** `R5-G08` crosses age boundaries under
  monotonic/wall-clock anomalies and exercises inspect, reconcile, cancel, and
  resume actions with authorization and audit checks.
- **Required evidence:** Policy version, operation history, clock trace,
  authorization receipt, receiver lookup/event counts, and final disposition.
- **Dependencies:** R5-SC-003 and R5-SC-010.
- **Derivation:** Direct from the existing `max_age_s`/`stale_count` behavior.

### R5-SC-009 — Multi-process and multi-host recovery contract (P1)

- **Problem statement:** SQLite locking alone is not a distributed ownership
  protocol, and shared/network filesystems may not provide the assumed locking
  or durability semantics.
- **Invariant:** Supported deployment topologies are explicit. Multi-process or
  multi-host recovery either uses a qualified consensus/lease authority with
  fencing or fails closed before any send.
- **Threat/failure model:** Two hosts, network partition, shared filesystem
  lock loss, asymmetric connectivity, failover, stale replica, and node reboot.
- **Proposed qualification gate:** `R5-G09` runs the declared topology matrix,
  partitions lease and Station paths independently, and proves fenced single
  advancement or explicit unsupported-topology rejection.
- **Required evidence:** Topology manifest, lease history, partition schedule,
  per-node action traces, receiver event counts, and final converged state.
- **Dependencies:** R5-SC-001, R5-SC-003, and R5-SC-012.
- **Derivation:** New hypothesis extending the single-host R4 design.

### R5-SC-010 — Reconciliation observability and SLO metrics (P1)

- **Problem statement:** R4 evidence records gate-local traces, but continuous
  operation needs low-cardinality metrics and correlated, redacted events for
  pending age, indeterminate duration, retries, fencing, quarantine, and ACKs.
- **Invariant:** Every state transition emits one correlation-safe observation;
  aggregate metrics reconcile to durable state without leaking messages,
  tokens, credentials, or unbounded receipt bodies.
- **Threat/failure model:** Telemetry loss/duplication, metric cardinality
  attack, secret/message leakage, exporter outage, clock skew, and alert storm.
- **Proposed qualification gate:** `R5-G10` replays a mixed recovery workload,
  recomputes counters from the database/journal, checks bounded labels and
  redaction, and verifies alerts for stuck indeterminate and lease contention.
- **Required evidence:** Metric schema, sample scrape, transition-to-metric
  reconciliation report, redaction corpus/results, alert timeline, and SLOs.
- **Dependencies:** R5-SC-003, R5-SC-006, R5-SC-007, and R5-SC-008.
- **Derivation:** New operational hypothesis; R4 traces are qualification
  evidence rather than a production observability contract.

### R5-SC-011 — Protocol versioning and compatibility negotiation (P1)

- **Problem statement:** Outbox rows and receipt endpoints have no explicit
  protocol/schema version negotiation, making safe rolling upgrades and
  canonicalization changes ambiguous.
- **Invariant:** Sender, Station, stored request, and receipt declare compatible
  versions and features before mutation; unknown major versions fail closed,
  and downgrade cannot remove required safety bindings.
- **Threat/failure model:** Old sender/new Station and reverse, rolling restart,
  unsupported fields, canonicalization drift, downgrade attack, and rollback
  with newer persisted rows.
- **Proposed qualification gate:** `R5-G11` runs a supported/unsupported version
  matrix across send, lookup, restart, upgrade, and rollback; incompatible
  pairs must perform no external effect.
- **Required evidence:** Version/feature registry, compatibility matrix,
  negotiated transcript, persisted row versions, network traces, and rollback
  results.
- **Dependencies:** R5-SC-002 and R5-SC-003.
- **Derivation:** New hypothesis based on unversioned current schemas.

### R5-SC-012 — Distributed receipt lookup availability and consistency (P2)

- **Problem statement:** Lookup currently assumes the contacted Station has
  immediate access to the authoritative submission record. Failover/replication
  can return false absence and tempt unsafe retransmission.
- **Invariant:** `not found` is distinguishable from `not authoritative` and
  `temporarily indeterminate`; only a quorum/authority-backed answer may drive
  state, and absence never directly authorizes a duplicate external effect.
- **Threat/failure model:** Replica lag, leader failover, partition, stale cache,
  disaster recovery, lost index with retained event, and regional outage.
- **Proposed qualification gate:** `R5-G12` exercises lag/partition/failover
  schedules and verifies authoritative positive/negative/indeterminate answers,
  convergence, and no unsafe repost.
- **Required evidence:** Authority/replication manifest, fault schedule, lookup
  transcripts with consistency metadata, event/submission records, and action
  traces.
- **Dependencies:** R5-SC-002, R5-SC-003, R5-SC-009, and R5-SC-011.
- **Derivation:** New distributed-systems hypothesis outside the single Station
  R4 qualification.

### R5-SC-013 — Receipt retention, tombstones, and garbage collection (P2)

- **Problem statement:** Indefinite retention is unbounded, while deleting a
  receipt/idempotency record can make an old operation appear new and permit a
  repeated external effect.
- **Invariant:** GC cannot erase the uniqueness proof while any operation can be
  retried. Expiry creates an authenticated tombstone or equivalent uniqueness
  record for at least the maximum replay horizon, with auditable policy.
- **Threat/failure model:** Late retry, restored old backup, delayed worker,
  concurrent GC/lookup, policy shrink, storage pressure, and legal deletion.
- **Proposed qualification gate:** `R5-G13` races lookup/recovery against GC,
  restores pre-GC outbox snapshots, crosses retention boundaries, and proves
  no second event plus bounded storage growth.
- **Required evidence:** Retention policy/version, GC journal, tombstone proof,
  restored-client trace, receiver event counts, and storage-growth report.
- **Dependencies:** R5-SC-002, R5-SC-003, R5-SC-008, and R5-SC-011.
- **Derivation:** New lifecycle hypothesis; current code has no receipt GC.

### R5-SC-014 — Formal at-most-once external-effect claim boundary (P2)

- **Problem statement:** One retained `comms.message` event is demonstrated, but
  “at most once” across arbitrary external consumers cannot follow from sender
  idempotency alone.
- **Invariant:** The claim is precisely scoped: either the Station append is the
  sole external effect, or every downstream effect consumes a globally stable
  effect ID transactionally/idempotently. Unverified downstream delivery is
  reported as indeterminate, never as exactly-once.
- **Threat/failure model:** Consumer crash after effect before offset/ACK,
  duplicate event delivery, reordering, replay after restore, non-idempotent
  connector, and partial multi-sink fanout.
- **Proposed qualification gate:** `R5-G14` supplies a small executable state
  model plus adversarial end-to-end consumer tests over all crash boundaries;
  model and traces must satisfy the published safety property and claim scope.
- **Required evidence:** Formal model/property and checker output, refinement
  map to implementation states, crash schedule, effect ledger, consumer ACKs,
  and counterexample retention on failure.
- **Dependencies:** R5-SC-001 through R5-SC-005, R5-SC-011, and R5-SC-012;
  R5-SC-013 is required for claims spanning the retention horizon.
- **Derivation:** Directly motivated by R4-G13's one-event result; extension to
  downstream effects is a new hypothesis.

## Proposed R5 qualification matrix

| Gate | Requirements | Minimum scenario set | Pass condition | Priority |
|---|---|---|---|---|
| R5-G01 | SC-001 | concurrent processes, pause/takeover, stale resume, skew | one fenced recovery authority; stale mutations rejected | P0 |
| R5-G02 | SC-002 | valid receipt plus issuer/project/op/digest/event/version/key mutations | only fully bound authorized receipts verify | P0 |
| R5-G03 | SC-003 | crash before/after every transition and network boundary | all restarts follow the versioned state graph; ambiguity is explicit | P0 |
| R5-G04 | SC-004 | malformed, oversized, corrupted, and cross-bound receipts | zero false ACKs; deterministic quarantine/indeterminate result | P0 |
| R5-G05 | SC-005 | kill/I/O failure during ACK commit and fenced-owner race | prior safe state or fully durable verified ACK; integrity PASS | P0 |
| R5-G06 | SC-006 | page/WAL/schema/payload/digest/receipt corruption corpus | no sends/ACK/deletion; bounded quarantine and preserved evidence | P1 |
| R5-G07 | SC-007 | ENOSPC/inodes/read-only/permission/SQLite errors at each phase | no unjournaled effect or false success; recovery after restoration | P1 |
| R5-G08 | SC-008 | age boundary, clock anomalies, inspect/reconcile/cancel/resume | no age-derived resend/success/delete; authorized durable disposition | P1 |
| R5-G09 | SC-009 | multi-process/host, partition, reboot, stale replica | fenced single advancement or fail-closed unsupported topology | P1 |
| R5-G10 | SC-010 | mixed states, exporter outage, hostile labels/content | metrics reconcile to state; bounded/redacted; stuck-state alerts fire | P1 |
| R5-G11 | SC-011 | old/new sender/Station, downgrade, upgrade/rollback | supported pairs interoperate; incompatible pairs create no effect | P1 |
| R5-G12 | SC-012 | replica lag, leader loss, partition, DR | authority-aware lookup converges without unsafe repost | P2 |
| R5-G13 | SC-013 | GC race, late retry, old backup restore, pressure | uniqueness survives replay horizon; storage remains bounded | P2 |
| R5-G14 | SC-014 | formal exploration plus downstream consumer crash matrix | published safety property holds within explicit claim boundary | P2 |

## Qualification architecture rules

Every R5 gate should inherit the R4 fail-closed evidence discipline:

1. Pin candidate HEAD/tree, harness revision/tree, schema versions, fault corpus,
   environment, and dependency identities before execution.
2. Run the harness externally; do not let qualification mutate the candidate.
3. Record all expected gate IDs. Missing, skipped, malformed, or unverifiable
   evidence is not `PASS`.
4. Preserve raw traces plus a machine-readable summary and SHA-256 manifest.
5. Separate safety from liveness: an unavailable system may remain safe, and a
   responsive system may still violate receipt/ownership invariants.
6. Use deterministic fault points first, then process/host/storage integration
   tests. Never substitute mocks for the final boundary a claim names.
7. Redact secrets and message bodies while retaining stable correlation IDs,
   reason codes, fence tokens, and digest bindings.
8. Retain counterexamples on failure and prohibit retry-to-green from replacing
   the original failed evidence.

## Recommended sequencing and disposition

Start R5 with SC-001 through SC-005 as one coherent safety tranche. Proceed to
SC-006 through SC-011 for operational hardening and rolling-deployment support,
then SC-012 through SC-014 for distributed lookup, lifecycle, and formal
end-to-end claims.

There are **no BLOCKING findings for the already-qualified R4.1 canary** in this
planning review and **no SHOULD_FIX_BEFORE_CANARY findings**. All items are
`POST_CANARY/R5`. Recommended disposition: preserve R4.1 exactly as qualified,
run its canary only under separate authorization, and schedule this backlog
without expanding that canary's scope.
