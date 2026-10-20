# Ledger Schema — Control-Plane Durable Ledger

> DRAFT — derived from owner directive 2026-09-18 and current-system audit; not from a ratified MS specification.
> Audit base: residual-agent-harness @ `699e2869` (main). Additive specification only; no current file is modified by this document.

## 1. Purpose and relationship to current code

The ledger is the single durable control-plane store for run/attempt/task state. It subsumes two current stores:

| Current store | File | Ledger disposition |
|---|---|---|
| `RuntimeJournal` (per-run SQLite, WAL) | `residual/factory/runtime_journal.py:54-413` | Subsumed into `attempts`, `lease_generations`, and `events` tables below. The per-run single-file isolation and 0o600/0o700 filesystem hardening (`runtime_journal.py:41-70`) are retained as ledger *instance* properties, one ledger per control plane rather than one per run (see gap-notes §1). |
| Station `Store` (per-station SQLite, JSON blobs) | `residual/station/store.py:25-317` | Subsumed: `tasks` JSON blob becomes typed columns; `events` hash chain is retained; `jobs`, `cursors`, `settings` carried forward unchanged in shape. |
| DSM `Journal` (JSONL file) | `residual/dsm/journal.py:1-76` | Subsumed into `events` (same hash-chain + monotonic `seq` invariants, implemented in SQLite instead of line-delimited file). |

## 2. Storage engine invariants (normative, inherited from current code)

1. SQLite, `PRAGMA journal_mode=WAL` (current: `runtime_journal.py:72`, `store.py:37`).
2. Writer connections use `PRAGMA synchronous=FULL` and `PRAGMA foreign_keys=ON`; reader connections never set lock-sensitive pragmas (`runtime_journal.py:122-148`).
3. All mutations inside `BEGIN IMMEDIATE` transactions (`runtime_journal.py:204`, `store.py:60`).
4. Bounded busy budgets: writer admission ≤ 1.0 s, reader ≤ 5.0 s, lease-read ≤ 2.0 s (`runtime_journal.py:106-108`, `:312`). Only transaction *admission* is retryable; admitted body/commit work is never replayed (`runtime_journal.py:184-247`).
5. Ledger file and directory are operator-private: 0o700 dir, 0o600 file, no symlink traversal, single hard link (`runtime_journal.py:41-70`).
6. A persisted hash chain is verified at open; a corrupt chain is fail-closed (`runtime_journal.py:100`, `:398-403`; `dsm/journal.py:_load`).

## 3. Tables

### 3.1 `metadata`
```
key TEXT PRIMARY KEY, value TEXT NOT NULL
```
Carries `control_plane_id` (subsumes `trace_id` binding, `runtime_journal.py:94-99`), `schema_version`, `created_ns`. A ledger opened with a mismatched `control_plane_id` is refused.

### 3.2 `events` (append-only hash chain)
```
seq        INTEGER PRIMARY KEY AUTOINCREMENT,
digest     TEXT UNIQUE NOT NULL,          -- sha256 of canonical record
prev_hash  TEXT NOT NULL,                 -- '0'*64 genesis (station store.py:93; dsm GENESIS)
record     TEXT NOT NULL                  -- canonical JSON Observation
```
- UPDATE and DELETE are forbidden by trigger (current: `runtime_journal.py:89-92`).
- Every state mutation in §3.3–§3.6 appends its event row in the **same transaction** as the state change (current precedent: `runtime_journal.py:_append` called inside `_transaction`; `station/store.py:_event`).
- Genesis digest is the literal `'GENESIS'` in `RuntimeJournal` (`runtime_journal.py:254`) vs `'0'*64` in Station/DSM (`store.py:93`, `dsm/journal.py:GENESIS`). **Ledger normalizes on `'0'*64`; this is a recorded divergence (gap-notes §2).**

### 3.3 `attempts`
```
attempt_id     TEXT PRIMARY KEY,                -- _identifier grammar (worker_contract.py:33-36)
task_id        TEXT NOT NULL,
worker_id      TEXT UNIQUE NOT NULL,            -- never reused (runtime_journal.py:55,80)
swarm_id       TEXT NOT NULL,
plan_hash      TEXT NOT NULL,                   -- [0-9a-f]{64}
contract_hash  TEXT NOT NULL,
contract_json  TEXT NOT NULL,
lease_id       TEXT UNIQUE NOT NULL,
generation     INTEGER NOT NULL,                -- >= 1, monotonic per (plan_hash,task_id)
fencing_token  INTEGER NOT NULL,                -- NEW: ledger-issued, monotonic per task_id (§3.4)
workspace      TEXT UNIQUE NOT NULL,
state          TEXT NOT NULL,                   -- enum per state-transitions.md §2
revoked        INTEGER NOT NULL DEFAULT 0,
terminal_state TEXT,                            -- NEW, NULL until terminal; see §4 uniqueness
pid            INTEGER,
created_ns     INTEGER NOT NULL,
updated_ns     INTEGER NOT NULL,
CHECK (state IN ('RESERVED','RUNNING','CANDIDATE','VIOLATED','FAILED',
                 'CANCELLED','AUDIT_FAILED','PURGED')),
CHECK (terminal_state IS NULL OR state = terminal_state)
```
All constraints carried from `runtime_journal.py:78-85`; `fencing_token`/`terminal_state` are additive.

### 3.4 `lease_generations`
```
plan_hash  TEXT NOT NULL,
task_id    TEXT NOT NULL,
generation INTEGER NOT NULL,
fencing_token INTEGER NOT NULL,                 -- NEW: monotonic, issued at claim
PRIMARY KEY (plan_hash, task_id)
```
Subsumes `generations` (`runtime_journal.py:86-88`). Invariant: `generation` strictly increases across claims (enforced today by `claim()` read-check, `runtime_journal.py:265-268`; ledger makes it a monotonic-update CAS, see state-transitions.md §4).

### 3.5 `tasks` (Station lifecycle projection, typed)
Replaces the JSON blob (`station/store.py:39`, `:109-112`) with typed columns for every field that participates in a transition guard:
```
project TEXT NOT NULL, id TEXT NOT NULL,
state TEXT NOT NULL,                            -- enum per state-transitions.md §3
attempt INTEGER NOT NULL DEFAULT 0,
owner TEXT, lease_id TEXT, fencing_token INTEGER, lease_until REAL,
base_commit TEXT, head_commit TEXT, checks_hash TEXT,
value TEXT NOT NULL,                            -- remaining JSON payload (findings, artifacts, …)
PRIMARY KEY (project, id),
UNIQUE (project, id, lease_id) WHERE lease_id IS NOT NULL
```
`state`, `owner`, `lease_id`, `lease_until`, `attempt` remain writable **only** through the transition path (current enforcement is application-level: `store.py:163-166`; ledger moves this to CAS SQL).

### 3.6 `jobs`, `cursors`, `settings`, `artifacts`, `submissions`, `projects`
Carried unchanged from `station/store.py:38-48`. `jobs` gains `lease_id`/`fencing_token` columns (NULLable) so interrupted-job fencing participates in the same mechanism as task leases.

## 4. Uniqueness constraints that carry the exactly-one-terminal invariant

1. `attempts.attempt_id` PRIMARY KEY — one durable row per attempt ever.
2. `attempts.terminal_state` — set exactly once by a single CAS UPDATE whose predicate requires `state IN ('RESERVED','RUNNING','CANDIDATE') AND terminal_state IS NULL` (state-transitions.md §4). Because a row has one `terminal_state` column and the CAS predicate fails after it is set, storage uniqueness makes a second terminal write impossible even if the writer service misbehaves.
3. Partial unique index for the *winning* terminal kind per task, if the qualification plan requires at-most-one candidate publisher per task:
```
CREATE UNIQUE INDEX one_candidate_per_task
  ON attempts(plan_hash, task_id) WHERE terminal_state = 'CANDIDATE';
```
This is additive hardening over the current `claim()` application check (`runtime_journal.py:269-273`).
4. `events.digest UNIQUE` + append-only triggers — no event rewrite, so the audit trail of the terminal transition is itself immutable.

## 5. What is deliberately NOT in the ledger

- Receipt bytes and receipt verification (frozen; `docs/roadmap/FOUNDATION-CONTRACT.md` §1). The ledger stores `receipt_hash` references only.
- Evidence Fabric schemas, verifier authority, ownership baselines — out of scope per exclusion boundary.
- OS/process liveness. The ledger records `pid` and `revoked` as *evidence*, never as a liveness claim (precedent: `worker_contract.py:302-308`, `runtime.py:81-120`).


## Appendix A — Normative summary (dogfood mission anchor)

- The ledger enforces the **exactly-one-terminal** invariant: every attempt reaches at most
  one terminal state, enforced by a **CAS** state transition (`terminal_state IS NULL` predicate
  with `rowcount == 1` verification) plus storage-level uniqueness — never by a watchdog.
- The single writer-service follows **commit-before-ack**: an acknowledgement is returned only
  after `COMMIT` returns; a client crash between write and ack retries with the same `event_id`
  and resolves as a duplicate.
