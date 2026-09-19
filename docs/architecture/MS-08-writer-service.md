# MS-08 Writer Service — Authoritative Single-Writer Control Plane Design

> **DESIGN / CONTRACT-TEST SKELETONS ONLY (Swarm G).** No production implementation.
> Base: residual-agent-harness main @ `3cff6bcd52e352a6ba048c958949a7bbb2a039eb`.
> Consumes Swarm F (MS-00 ledger) prior art: `wave-a/a1/writer-service-protocol.md`,
> `wave-a/a1/startup-reconciliation.md`, `wave-a/a2/scheduler-fencing-tests.md` (SF-01..10).
> Verified seams on current main: `residual/dsm/lease.py`, `store.py`, `journal.py`,
> `delivery.py`, `faults.py`, `recovery.py`, `ownership.py` all present at base SHA.

## 1. Target architecture

```
 clients (Factory runtime / Station / DSM adapters)
        │  proposals (never direct DB connections)
        ▼
 ┌─────────────────────┐      ┌──────────────────────────┐
 │  MS-08 Writer        │─────▶│ shared authoritative      │
 │  (single lease       │ CAS  │ control store (SQLite     │
 │   holder, fenced)    │      │ ledger, MS-00 schema)     │
 └─────────────────────┘      └──────────────────────────┘
        │ ack {seq, hash, disposition, fencing_token}
        ▼
 per-lane observation shards   +   local emergency journals
 (read-only replicas fed from    (append-only local buffers used
  the committed journal stream)  when the writer is unreachable;
                                  drained to the writer on reconnect,
                                  never authoritative)
```

- **Shared authoritative control store**: one ledger file; storage-level CAS is the
  backstop even if the Writer role is violated (prior art §2).
- **Dedicated MS-08 writer**: the only process holding the write lease; only it
  executes `BEGIN IMMEDIATE` transactions.
- **Per-lane observation shards**: materialized from the committed journal in seq
  order; they never mutate control state. Stale shard reads are labeled with the
  shard's cursor `(seq, hash)` so callers can detect lag.
- **Local emergency journals**: when the writer/scheduler is unavailable, a lane
  appends locally with the same envelope (`event_id`, payload, hash link). On
  reconnect the journal is drained into the writer as ordinary proposals; the
  writer's idempotency dedupe makes re-drain safe. Emergency journals carry no
  write authority.

**Scope: single host.** Multi-host writer failover across machines requires a
consensus-backed lease quorum and is **unsupported pending a consensus decision**
(carries forward prior art §7 non-goal and the SF-07 finding: volatile lease tables
reset fencing tokens on restart; only ledger-durable tokens on a single host close
that gap).

## 2. IPC / API contract

Transport-agnostic request/response; in-process call, Unix socket, or localhost
HTTP are all admissible bindings. The contract below is normative for any binding.

### 2.1 Requests

| Request | Fields | Semantics |
|---|---|---|
| `propose` | `event_id` (idempotency key), `domain`, `kind`, `payload`, `expected` (CAS precondition or `null`), `writer_token` (client-observed token, advisory) | Submit one mutation. Server assigns seq. |
| `read` | `domain`, `key`, `min_seq` (optional) | Bounded snapshot read; if `min_seq` is beyond the head, return `BEHIND` rather than blocking indefinitely. |
| `acquire_lease` | `writer_id`, `ttl_ms` | Writer-candidate claim CAS; returns new durable `fencing_token`. |
| `renew_lease` | `writer_id`, `fencing_token`, `ttl_ms` | Bumps token (SF-04: renewal invalidates pre-renew in-flight writes). |
| `drain` | `events[]` (from an emergency journal) | Batch of `propose`; each resolved independently. |

Every `propose` ack:

```json
{"seq": 42, "hash": "sha256:…", "disposition": "accepted|duplicate|rejected",
 "fencing_token": 7, "reason": null}
```

- `seq`, `hash` are the client's durable cursor (prior art §4.5).
- `disposition=duplicate` returns the *originally stored* `{seq, hash}` — the retry
  after a crash resolves here.
- `disposition=rejected` carries a typed `reason`:
  `schema`, `ownership`, `stale_fencing`, `cas_conflict`, `illegal_transition`,
  `lease_lost`, `writer_unavailable`. UNKNOWN/BLOCKED-class reasons are never
  coerced to `accepted`.

### 2.2 Ordering normative rule: commit-before-ack

For every `propose` with idempotency key `event_id` (prior art §4, verbatim intent):

1. **Validate** — schema, ownership, fencing, transition legality. Fail ⇒ reject,
   nothing written.
2. **Dedupe** — `event_id` already journaled ⇒ return stored `{seq, hash}` with
   `disposition: "duplicate"`.
3. **Write** — state CAS + event append in one `BEGIN IMMEDIATE` transaction,
   `synchronous=FULL`.
4. **Commit-before-ack** — ack returned only after `COMMIT` returns. Crash between
   write and ack ⇒ client retries the same `event_id` ⇒ resolves at step 2 as
   `duplicate`. **No ack before commit, no commit without event append, no event
   append outside the state-mutation transaction.**
5. Ambiguous `COMMIT` result ⇒ discard the connection, enter startup
   reconciliation before serving further writes ("no ambiguous state is reused").

## 3. CAS / outbox protocol

- **State CAS**: mutation commits only if `expected` matches the current row
  (generation / `terminal_state IS NULL` predicates per MS-00 state-transitions).
  Conflict ⇒ `rejected/cas_conflict`, nothing appended.
- **Outbox**: every accepted event is the outbox record. Observation shards and
  downstream consumers replay the journal by cursor; delivery is at-least-once and
  consumers dedupe by `event_id` (SF-06 inbox discipline). Lost delivery is
  recovered only via outbox retransmission from the retained journal — there is no
  consumer-side watchdog substitute.
- **External adapters**: per the SF-08 rule — an adapter incapable of fencing
  requires an idempotency proxy (durable key `(resource, fencing_token, effect_id)`,
  journaled admission, typed outcomes `PROXY_ADMIT` / `PROXY_DEDUP` /
  `PROXY_REJECT_STALE`) or the integration **loses the effectively-once
  classification** and receipts must say `at_least_once_external`.

## 4. Writer lease and fencing-token issuance

1. Exactly one writer candidate acquires the lease via claim CAS against the
   well-known control row (`plan_hash='__control__'`); success increments a
   **durable** `fencing_token` stored in the ledger (closes the DSM volatile-lease
   gap; SF-07 predicted FAIL is fixed by durability, single-host only).
2. Renewal also bumps the token; tokens are strictly monotonic per ledger forever
   (never reset, even across restart — they are reloaded from the ledger at Step 1
   of reconciliation).
3. Every proposal carries `(writer_id, fencing_token)`; the writer rejects any
   token below the highest it has durably issued (`stale_fencing`), and the storage
   CAS predicate independently rejects stale generations (defense in depth).

## 5. Takeover / failover rules (single host)

1. New candidate acquires only via the claim CAS. If the old writer is alive and
   mid-transaction, its `BEGIN IMMEDIATE` holds the SQLite write lock; the claim
   waits, then sees the bumped generation — concurrent same-ledger split commit is
   impossible (prior art §6).
2. Takeover ⇒ run startup reconciliation (Steps 0–6: verify hash chain, acquire
   lease, rebuild projections, classify interrupted attempts, stale leases,
   in-flight jobs → `interrupted`, append `control.reconciled` checkpoint) **before**
   accepting proposals.
3. The fenced-off old writer's next proposal fails fencing; if its process is
   still running a worker, the watchdog lease fence applies (`watchdog_lease_fence`,
   SF-10).
4. If the lease table is ever unreadable, the writer enters a fenced-off recovery
   epoch (`FENCING_UNAVAILABLE`) rather than guessing tokens — UNKNOWN is not PASS.
5. Multi-host failover: unsupported (see §1). A second host MUST NOT attempt claim;
   the design provides no quorum and makes no split-brain claim across hosts.

## 6. Failure model (normative)

| Failure | Required behavior |
|---|---|
| Writer crash after COMMIT, before ack | Client retries same `event_id` → `duplicate`. |
| Writer crash mid-transaction | SQLite rolls back; no partial state, no orphan event. |
| Duplicate client (retry, replay, drained emergency journal) | Idempotent: dedupe by `event_id`, stored `{seq, hash}` returned. |
| Stale writer (lease lost, still alive) | Fencing rejection + storage CAS backstop rejection. |
| Scheduler / writer unavailable | Lanes append to local emergency journals; writer returns `writer_unavailable`; drain on reconnect resolves duplicates. |
| Ambiguous COMMIT | Discard connection, reconcile before further writes. |
| Unparseable state on read-back | Fail closed `unknown`; never retyped. |
| Lease-table loss | `FENCING_UNAVAILABLE` recovery epoch; re-register at max(observed token)+1. |
| Two hosts attempt write | Unsupported; no correctness claim (pending consensus decision). |

## 7. Contract-test skeletons

`docs/architecture/ms08/` contains a **minimal in-process reference
implementation** (stdlib-only, in-memory ledger with hash-chained journal) plus
contract tests proving: commit-before-ack, idempotent retry (incl. crash between
write and ack), stale-fencing rejection, renew-token invalidation (SF-04),
takeover reconciliation gating, duplicate drain, outbox redelivery dedupe (SF-06),
and unavailable-writer emergency journaling. These are skeletons: they bind the
contract, not a production store.

## 8. Divergences from prior art (Swarm F)

1. Prior art §3.1 names the claim row `lease_generations(plan_hash='__control__')`;
   retained, but token issuance is specified as *durable and reload-verified at
   reconciliation* (SF-07 fix) rather than merely stored.
2. Adds explicit `read.min_seq`/`BEHIND` and `drain` requests to cover observation
   shards and emergency journals (not in prior art, which was mutation-centric).
3. SF-05 silent-release audit gap carried forward unchanged: failed release
   attempts remain silent no-ops in this design; flagged as an open audit question,
   not resolved here.
4. Everything else (commit-before-ack ordering, failure table, non-goals) is
   adopted verbatim in intent; no weakening.
