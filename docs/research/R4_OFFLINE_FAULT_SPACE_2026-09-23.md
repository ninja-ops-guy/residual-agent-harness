# Frozen R4.1 offline fault-space exploration

Target: exact detached candidate
`8701367db6d3202f24b3eb9f4696b0cadf657985`, tree
`79bfe6ed1743907065ed44aeb9c460c47527e0c6`, cloned with no hardlinks into a
disposable directory. The original candidate was clean, had no remotes, and was
not modified. Tests used temporary SQLite databases and in-process synthetic
transports only; no live Station, provider, canary, or production service ran.

`CONTRADICTION=true` below means the observation contradicts the proposed R5
invariant, not necessarily a frozen R4 acceptance criterion. Potential canary
scope implications are conservatively marked `BLOCKING_CANDIDATE_FINDING` for
human disposition; no automatic repair was made.

## Results

| Scenario | OBSERVED | EXPECTED | CONTRADICTION | OPEN_HYPOTHESIS |
|---|---|---|---|---|
| malformed durable outbox row | invalid payload JSON raises unhandled `JSONDecodeError`; batch cannot continue | fail closed with reason-coded minimal quarantine | true | unrelated-row availability is unqualified |
| duplicate `operation_id`, different payload | rejected with `ContractError` | deterministic rejection | false | none |
| malformed receipt | string receipt persisted and row became `ACKED` | reject and retain reconcilable state | true; **BLOCKING_CANDIDATE_FINDING** | transport authentication is not client-side semantic binding |
| wrong-project receipt | foreign project receipt persisted and row became `ACKED` | exact project binding | true; **BLOCKING_CANDIDATE_FINDING** | same as above |
| wrong-operation receipt | foreign operation receipt persisted and row became `ACKED` | exact operation binding | true; **BLOCKING_CANDIDATE_FINDING** | same as above |
| receipt timeout | each restart performed one GET, zero POST, remained `PENDING` | fail closed while commit state is unknown | false | persistent ambiguity is not represented distinctly |
| receipt endpoint 4xx | one GET, zero POST, remained `PENDING` | no repost without authoritative lookup | false | 4xx is collapsed with transient transport outage |
| receipt endpoint 5xx | one GET, zero POST, remained `PENDING` | no repost without authoritative lookup | false | 5xx is collapsed with transient transport outage |
| repeated restart | three timeouts produced three GETs, zero POSTs, durable `PENDING` | no blind retransmit | false | retry schedule/observability remains unspecified |
| SQLite exclusive contention | ACK waited ~15.0s then raised `database is locked`; after release row was `PENDING` | bounded error, no false ACK | false | 15s may exceed service-level budget |
| corrupted outbox / digest mismatch | recovery ignored stored digest, POSTed tampered payload, then `ACKED` | quarantine and zero network actions | true; **BLOCKING_CANDIDATE_FINDING** | digest is checked on duplicate enqueue but not recovery |
| two simultaneous recoverers | synchronized lookup absence produced two POST actions; both ACK writes completed | one fenced recovery authority | true; **BLOCKING_CANDIDATE_FINDING** | receiver idempotency can hide sender split-brain |
| truncated database | constructor raised unhandled `DatabaseError` | fail closed with forensic preservation/quarantine | true | no bounded recovery interface observed |
| stale pending operation | zero network actions; row remained `PENDING`; report returned `stale=1` | age must not imply resend/success/delete | false | staleness is computed, not a durable policy/disposition |

## Crash-boundary exploration

| Boundary | OBSERVED / evidence | Status |
|---|---|---|
| sender crash before POST | enqueue durability is covered by R4-G14; restart performs lookup before a possible POST | OBSERVED safe for tested single owner |
| sender crash during POST | R4-G13/R1 fixtures cover receiver commit plus lost response: restart lookup precedes retransmit | OBSERVED safe for tested retained receipt |
| sender crash after receiver commit | R4-G13 found the original defect and R4.1 repaired it | OBSERVED PASS in authoritative gate |
| sender crash before local ACK | authoritative R4-G13 restart lookup reconciles and persists ACK | OBSERVED PASS |
| sender crash during local ACK persistence | SQLite transaction atomicity suggests old/new state, but no fsync/WAL kill-point corpus ran | OPEN_HYPOTHESIS; proposed R5-G05 |
| disk-write failure | safe OS-level disk exhaustion was not available; source uses ordinary SQLite transactions and exposes exceptions | OPEN_HYPOTHESIS; mock/loopback filesystem gate required |

## Safety interpretation

The four `BLOCKING_CANDIDATE_FINDING` groups are: receipt semantic binding,
outbox digest verification on recovery, and concurrent recovery fencing. They
are outside the exact single-owner/honest-loopback fixtures that passed R4.1,
but they could matter if the proposed canary assumes a compromised/misbehaving
authenticated channel, local state tampering/corruption, or overlapping sender
processes. Human scope review is required before changing the existing
`READY_FOR_CANARY` disposition.

Positive observations remain important: different-payload operation-ID reuse is
rejected; lookup outage, 4xx, and 5xx do not trigger restart repost; repeated
restart remains fail-closed; lock contention does not falsely ACK; stale age does
not trigger a network/destructive action.

## Proposed gates

- R5-G01: process-level fenced concurrent recovery with stale-owner resume.
- R5-G02/G04: exact signed receipt binding plus malformed/cross-bound corpus.
- R5-G03: durable `INDETERMINATE`/`QUARANTINED` states and transition oracle.
- R5-G05: real kill/I/O injection at ACK transaction/WAL/fsync boundaries.
- R5-G06: digest/page/WAL/schema/JSON corruption quarantine with zero network.
- R5-G07: bounded ENOSPC/IOERR/read-only injection and recovery.
- R5-G08: durable authorized stale-operation disposition.

Evidence source: frozen candidate source, authoritative R4/R4.1 G13/G14 records,
and disposable deterministic probes. Tests performed: synthetic transport,
temporary SQLite, lock contention, byte corruption, synchronized threads, and
static crash-boundary reconciliation. Blockers: real fsync/power-loss, ENOSPC,
and process-level fencing fixtures remain. Pre-production: all proposed R5 gates.
Research: distinguish sender authority, receiver idempotency, and downstream
external-effect uniqueness. Canary execution status: **NOT EXECUTED**.
