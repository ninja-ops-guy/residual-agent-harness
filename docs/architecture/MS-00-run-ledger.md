# MS-00 Run Ledger — Design (Schema, Transition API, CAS Rules, Crash Matrix)

> **Status: DESIGN (G0/G1 design lane). No production implementation in this PR.**
> Base: `main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb` (seams re-verified against this HEAD;
> prior-art audit base was `699e2869` — seam file blob SHAs verified unchanged, see §10).
> Normative owner requirement implemented by this design: **storage-enforced
> exactly-one-terminal semantics via CAS + storage uniqueness — never a watchdog** — plus
> **projection reconstruction** from the event chain. Target architecture: a shared
> authoritative control store with a dedicated MS-08 writer, per-lane observation shards,
> and local emergency journals.
>
> Interface freezing (API signatures in §5, table names/columns in §4) is **gated on
> Swarm E's checked-in seam DAG**. This document is designed against the wave-a DRAFT seam
> DAG (`wave-a/a1/seam-dag.md`); no divergence discovered at authoring time — see §9.

## 1. Purpose and scope

MS-00 is the durable ledger core: tables, CAS primitives, and the hash-chained event log.
It owns **no policy** (ownership rules, transition tables, and provider/receipt policy live
in MS-08/MS-01/MS-02). It subsumes three current stores, verified present and unchanged at
base HEAD:

| Current store | Anchor (verified at `3cff6bcd`) | Disposition |
|---|---|---|
| `RuntimeJournal` (per-run SQLite, WAL) | `residual/factory/runtime_journal.py` (blob `c707da37`) | Subsumed into `attempts`, `lease_generations`, `events`. Filesystem hardening (0o700 dir / 0o600 file / no symlinks / single hard link) retained as ledger *instance* properties. |
| Station `Store` (per-station SQLite, JSON blobs) | `residual/station/store.py` (blob `052137f1`) | Subsumed; `tasks` JSON blob becomes typed columns for every field in a transition guard; event hash chain retained; `jobs`, `cursors`, `settings`, `artifacts`, `submissions`, `projects` carried forward. |
| DSM `Journal` (JSONL file) | `residual/dsm/journal.py`, `residual/dsm/store.py` (blob `9620d4eb`) | Subsumed into `events` with the same hash-chain + monotonic `seq` invariants, plus durable `event_id` dedupe. |

**Out of scope (unchanged authorities):** Factory/M4 protected implementation, verifier
authority, receipt serialization/bytes (ledger stores `receipt_hash` references only),
ownership pins/baselines, Evidence Fabric schemas, frozen research definitions, #108
candidate files, multi-host consensus (deferred per `dsm/store.py` docstring →
`docs/swarm/dsm-004.md`).

## 2. Normative invariants

1. **I-1 Exactly-one-terminal (storage-enforced).** An `attempts` row reaches at most one
   terminal state, ever. Enforced by a single-column `terminal_state` plus a CAS predicate
   `terminal_state IS NULL` in the same `BEGIN IMMEDIATE` transaction as the terminal event
   append. A watchdog is evidence collection only; it is never a correctness mechanism
   (precedent: `runtime.py:_watch` detects and kills; durable correctness today rests on
   `_lock` + `BEGIN IMMEDIATE` serialization, which is single-process only).
2. **I-2 Atomic state+event.** Every state mutation and its event row commit in one
   transaction. No ack before commit, no commit without event append, no event append
   outside the state-mutation transaction.
3. **I-3 Projection reconstruction.** Every read projection (`attempts` current state,
   `tasks` current state, per-entity current values) is recomputable from `events` alone
   under the deterministic total order argmax(`fencing_token`, `writer`, `event_id`)
   (precedent: `dsm/store.py:current_value`). Reconciliation cross-checks projection vs
   tables at startup; disagreement ⇒ abort (fail closed).
4. **I-4 Idempotent admission.** Every mutation carries an idempotency key `event_id`.
   Retry after an ambiguous commit resolves as `duplicate` with the original `(seq, hash)`
   (precedent: `dsm/store.py:submit` R4).
5. **I-5 Tri-state integrity.** A lease read yields `current | revoked | unknown`;
   `unknown` is produced only by a failed/unreadable store or an exhausted deadline and is
   never retyped as revoked and never authorizes a terminal transition (precedent:
   `runtime_journal.py:lease_read`; policy: `docs/governance/SOLO_MAINTAINER_POLICY.md`).
6. **I-6 Fail-closed integrity.** Hash-chain verification at open; corruption aborts
   startup; nothing is silently repaired into a PASS-equivalent state.

## 3. Storage engine discipline (carried verbatim from current code)

- SQLite, `PRAGMA journal_mode=WAL`; writer connections `synchronous=FULL`,
  `foreign_keys=ON`; readers never set lock-sensitive pragmas.
- All mutations in `BEGIN IMMEDIATE`; only transaction *admission* is retryable for genuine
  `SQLITE_BUSY`/`SQLITE_LOCKED` within a bounded budget (writer ≤ 1.0 s); admitted
  body/commit work is never replayed.
- Bounded busy budgets: writer admission ≤ 1.0 s, readers ≤ 5.0 s, lease reads ≤ 2.0 s.
- Ledger file/dir operator-private (0o700/0o600, `O_NOFOLLOW`, single hard link).
- Genesis digest normalized to `'0'*64` (recorded divergence: `RuntimeJournal` uses the
  literal `'GENESIS'` today; Station/DSM use `'0'*64`).

## 4. Schema (final, design-level)

### 4.1 `metadata`
```sql
key TEXT PRIMARY KEY, value TEXT NOT NULL
-- carries control_plane_id, schema_version, created_ns
```

### 4.2 `events` (append-only hash chain)
```sql
seq       INTEGER PRIMARY KEY AUTOINCREMENT,
event_id  TEXT UNIQUE NOT NULL,        -- idempotency key (MS-08 dedupe)
digest    TEXT UNIQUE NOT NULL,        -- sha256 of canonical record
prev_hash TEXT NOT NULL,               -- '0'*64 genesis
record    TEXT NOT NULL                -- canonical JSON
-- UPDATE/DELETE forbidden by trigger (current precedent).
```

### 4.3 `attempts`
```sql
attempt_id     TEXT PRIMARY KEY,
task_id        TEXT NOT NULL,
worker_id      TEXT UNIQUE NOT NULL,   -- never reused
swarm_id       TEXT NOT NULL,
plan_hash      TEXT NOT NULL,          -- [0-9a-f]{64}
contract_hash  TEXT NOT NULL,
contract_json  TEXT NOT NULL,
lease_id       TEXT UNIQUE NOT NULL,
generation     INTEGER NOT NULL,       -- >= 1, monotonic per (plan_hash, task_id)
fencing_token  INTEGER NOT NULL,       -- ledger-issued, monotonic per control plane
workspace      TEXT UNIQUE NOT NULL,
state          TEXT NOT NULL,
revoked        INTEGER NOT NULL DEFAULT 0,
terminal_state TEXT,                   -- NULL until terminal; set exactly once
pid            INTEGER,
created_ns     INTEGER NOT NULL,
updated_ns     INTEGER NOT NULL,
CHECK (state IN ('RESERVED','RUNNING','CANDIDATE','VIOLATED','FAILED',
                 'CANCELLED','AUDIT_FAILED','PURGED')),
CHECK (terminal_state IS NULL OR state = terminal_state)
```

### 4.4 `lease_generations`
```sql
plan_hash     TEXT NOT NULL,
task_id       TEXT NOT NULL,
generation    INTEGER NOT NULL,
fencing_token INTEGER NOT NULL,        -- issued at claim/write-lease acquisition
PRIMARY KEY (plan_hash, task_id)
-- well-known row ('__control__','writer') carries the MS-08 writer fencing token
```

### 4.5 `tasks` (typed guard fields; remaining payload stays JSON)
```sql
project TEXT NOT NULL, id TEXT NOT NULL,
state TEXT NOT NULL,
attempt INTEGER NOT NULL DEFAULT 0,
owner TEXT, lease_id TEXT, fencing_token INTEGER, lease_until REAL,
base_commit TEXT, head_commit TEXT, checks_hash TEXT,
value TEXT NOT NULL,
PRIMARY KEY (project, id),
UNIQUE (project, id, lease_id) -- partial: WHERE lease_id IS NOT NULL
```

### 4.6 `jobs`, `cursors`, `settings`, `artifacts`, `submissions`, `projects`
Carried unchanged; `jobs` gains NULLable `lease_id`/`fencing_token`.

### 4.7 Uniqueness that carries I-1

1. `attempts.attempt_id` PK — one durable row per attempt ever.
2. `attempts.terminal_state` — one column, one write; CAS predicate makes a second terminal
   write impossible even if the writer service misbehaves.
3. Partial unique index for the winning terminal kind (additive hardening over the current
   application-level check in `claim()`):
   ```sql
   CREATE UNIQUE INDEX one_candidate_per_task
     ON attempts(plan_hash, task_id) WHERE terminal_state = 'CANDIDATE';
   ```
4. `events.event_id UNIQUE` + `events.digest UNIQUE` + append-only triggers.

## 5. Transition API (signatures — FREEZE GATED on Swarm E seam DAG)

```python
class RunLedger:
    def __init__(self, path: str | Path, *, control_plane_id: str) -> None: ...
        # private-file checks; schema; verify hash chain or raise JournalError (I-6).

    # --- attempt lifecycle (Factory/M2 vocabulary preserved) ---
    def claim(self, contract: WorkerContract, *, source_hash: str,
              approval: dict, event_id: str) -> Ack: ...
        # generation CAS + active-attempt uniqueness + identity uniqueness + event append.
    def started(self, attempt_id: str, pid: int, *, event_id: str) -> Ack: ...
        # CAS: state='RESERVED' AND revoked=0.
    def finish(self, attempt_id: str, state: TerminalState, *,
               fencing_token: int, event_id: str, **details) -> Ack: ...
        # CAS per §6; raises JournalError on rowcount != 1 or stale fencing.
    def revoke(self, attempt_id: str, *, event_id: str) -> Ack: ...
    def mark_purged(self, attempt_id: str, *, event_id: str) -> Ack: ...
    def lease_read(self, attempt_id: str, *,
                   deadline: float | None = None) -> LeaseRead: ...  # I-5

    # --- MS-08 admission surface (single writer backstopped by CAS) ---
    def acquire_writer_lease(self, writer_id: str) -> int: ...  # -> fencing_token
    def submit(self, event: dict) -> Ack: ...
        # validate → dedupe (event_id) → fencing → CAS write → commit → ack.

    # --- projection / reconciliation (MS-01) ---
    def reconcile(self, *, writer_id: str, fencing_token: int) -> ReconcileReport: ...
        # §8 algorithm; idempotent; appends one control.reconciled event.
    def verify_chain(self) -> None: ...
```

`Ack = {"seq": int, "hash": str, "disposition": "accepted" | "duplicate",
        "fencing_token": int}` (commit-before-ack; precedent `dsm/store.py:submit`).
`TerminalState = Literal['CANDIDATE','VIOLATED','FAILED','CANCELLED','AUDIT_FAILED']`.

## 6. CAS SQL (normative)

Terminal transition (I-1 carrier), with fencing backstop:
```sql
UPDATE attempts
SET state = :to, terminal_state = :to, updated_ns = :now
WHERE attempt_id = :aid
  AND state IN ('RESERVED','RUNNING','CANDIDATE')   -- legal pre-terminal set
  AND terminal_state IS NULL                        -- exactly-one-terminal
  AND (:to != 'CANDIDATE' OR revoked = 0)           -- preserved revoked guard
  AND :token >= (SELECT fencing_token FROM attempts WHERE attempt_id = :aid);
-- Driver contract: cursor.rowcount MUST equal 1, else ROLLBACK and raise JournalError.
-- Event append happens in the SAME transaction (I-2). Commit-before-ack (I-4).
```

Claim (generation CAS, atomic — replaces current read-then-write):
```sql
UPDATE lease_generations
SET generation = :gen, fencing_token = :tok
WHERE plan_hash = :ph AND task_id = :tid AND generation < :gen;
-- rowcount 1 required; 0 rows ⇒ stale claim, fail closed.
```

Writer-lease acquisition (MS-08 fencing token issuance):
```sql
INSERT INTO lease_generations(plan_hash, task_id, generation, fencing_token)
VALUES ('__control__', 'writer', 1, 1)
ON CONFLICT(plan_hash, task_id) DO UPDATE
SET generation = generation + 1, fencing_token = fencing_token + 1
RETURNING fencing_token;
```

Why CAS, not a watchdog: the current single-process `_lock` + SELECT-then-UPDATE is correct
for one process but is **not** a storage-level guarantee; two writer processes could both
pass the SELECT. The CAS predicate holds for any number of writers against the same file;
the MS-08 writer-service then reduces writer count to one by construction, with storage CAS
as the permanent backstop.

## 7. Crash matrix (kill points × expected typed outcome × evidence destination)

Typed-outcome vocabulary (from wave-a/a2): `REJECT:JournalError`, `REJECT:ContractError`,
`REJECT:FencingError`, `CRASH:CrashError`, `DISPOSITION:duplicate`, `RESTART:refused`,
`UNKNOWN`, `BLOCKED`. **UNKNOWN/BLOCKED are never PASS.** KP identifiers map to wave-a/a2
LN-01..15 kill points.

| KP | Kill point (seam at base HEAD) | Stimulus | Expected typed outcome | Evidence destination |
|---|---|---|---|---|
| KP-01 | claim at generation CAS (`runtime_journal.py` claim path) | claim with `generation ≤ stored` | `REJECT:JournalError`("generation"); 0 rows, 0 events | `attempts`/`events` row-count delta; `lease_generations` dump |
| KP-02 | claim while attempt active | second claim for (P,T) | `REJECT:JournalError`("active or quarantined") | `attempts` snapshot; event tail unchanged |
| KP-03 | duplicate identity insert | reuse worker_id / lease_id / workspace | `REJECT:JournalError` from `sqlite3.IntegrityError`; no partial rows | captured sqlite error code; table dumps |
| KP-04 | `started` on revoked/non-RESERVED | revoke then started; started twice | `REJECT:JournalError`; no `RuntimeProcessSpawned` event | events chain; attempts row |
| KP-05 | commit-before-ack crash (journal write window) | `submit(crash_after="journal_write")` | `CRASH:CrashError`; reopen; re-submit ⇒ `DISPOSITION:duplicate` with same `(seq,hash)` | journal byte diff; `accepted_transitions()` |
| KP-06 | crash after COMMIT before caller ack (SQLite FULL-sync window) | SIGKILL subprocess between COMMIT and `finish` return | exactly one `RuntimeAttemptFinished`; reopen passes chain check; re-finish ⇒ `REJECT:JournalError` | post-restart `export_jsonl`; terminal count = 1 |
| KP-07 | double-finish race (≥100 interleavings) | threads: finish FAILED vs VIOLATED | exactly one winner; loser `REJECT:JournalError`; exactly one terminal event | per-thread outcome log; chain-verified events |
| KP-08 | finish(CANDIDATE) vs revoke race | raced and ordered variants | revoke-first ⇒ CANDIDATE rejected; finish-first ⇒ revoke rejected; no terminal→revoked-and-candidate row | event order; final state |
| KP-09 | stale/forged/expired lease transition (Station) | expired lease; forged same-length token; wrong owner | `REJECT:ContractError` (constant-time compare preserved); no candidate mutation | task row unchanged; `worker.expired` event after recover |
| KP-10 | duplicate delivery replay (incl. cross-restart) | deterministic duplicate fault schedule | first `accepted`; all later `DISPOSITION:duplicate`; one journal record | delivery trace; inbox journal |
| KP-11 | writer restart mid-stream | publish E1..E5, ack E1/E2, kill | pending = {E3,E4,E5} sorted; re-publish E1 no-op; re-ack False | ack-log journal; pending list |
| KP-12 | scheduler/worker plane absent at recovery | `recover(startup=True)` | running local task ⇒ `blocked`, lease cleared, `worker.expired` event; jobs ⇒ `interrupted`; **no manufactured terminal success** | task row + events; replay log |
| KP-13 | lease read under corruption pressure | row deleted / revoked OOB / DB corrupt / deadline exhausted | `revoked`, `revoked`, `UNKNOWN`, `UNKNOWN`; diag carries only (exc type, sqlite_errorcode); never retyped | `LeaseRead.diag` tuples |
| KP-14 | watchdog ablation | disable watchdog; rerun terminal-race suite | outcome diff = [] — terminal correctness unchanged (watchdog is evidence only) | suite outcome diff |
| KP-15 | `mark_purged` on active attempt | purge RESERVED attempt | `REJECT:JournalError`; purge-after-terminal once-only (design normative: second purge rejected — resolves wave-a predicted FAIL in favor of once-only) | state transitions in `attempts` |
| KP-16 | event append fails after state CAS | inject failure between CAS and append | whole transaction rolls back; no state, no event (I-2) | row-count deltas = 0 |
| KP-17 | hash-chain tamper | flip one event byte on disk | reopen `RESTART:refused` (`JournalError`), no state served | startup diagnostic |
| KP-18 | crash mid-reconciliation | SIGKILL between reconciliation steps | re-run from Step 0 is idempotent; every mutation is a CAS; events dedupe by `event_id` | `control.reconciled` event; pre/post head hashes |

## 8. Reconciliation (projection reconstruction, normative order)

Run inside the MS-08 writer before accepting proposals; every step fails closed.

0. **Open & verify.** Private-file checks; verify full event hash chain (I-6).
1. **Acquire write lease.** Writer-claim CAS (§6); new `fencing_token` fences stale writers.
2. **Rebuild projections** from `events` alone under argmax(`fencing_token`, `writer`,
   `event_id`); cross-check against `attempts`/`tasks`; disagreement ⇒ abort (I-3).
3. **Classify interrupted attempts.** Rows `state IN ('RESERVED','RUNNING')` owned by a
   different control-plane identity ⇒ CAS to terminal `FAILED` with reason
   `interrupted_at_startup` (truthful terminal, never retyped). Crash between reap and
   finish ⇒ terminal `AUDIT_FAILED` with preserved diagnostic (never a manufactured
   completion row).
4. **Stale leases.** `tasks` rows `state='running'` with expired lease or (startup ∧
   non-`remote:` owner) ⇒ `blocked`, finding "Interrupted work requires re-triage. Existing
   evidence is retained." (verbatim current semantics).
5. **In-flight jobs.** `queued`/`running` ⇒ `interrupted`, detail "The station restarted;
   start this operation again." (verbatim). Jobs never auto-resume.
6. **Checkpoint.** Append one `control.reconciled` event with per-class counts and
   pre/post head hashes — durable proof reconciliation ran.

Test-hook invariants: no duplicate accepted transition across restart/replay; projection
determinism (two reconciliations agree exactly); exactly-one-terminal preserved by
reconciliation CAS; provenance (writer, fencing token, hash link) survives; no retyping of
corrupt state into benign values.

## 9. Dependency on Swarm E seam DAG

- Design assumes the wave-a DRAFT seam DAG: MS-00 (this document) ← MS-08 (admission &
  fencing) ← MS-01 (lifecycle) ← MS-02 (resolution). API signatures in §5 and table/column
  names in §4 are **frozen only when Swarm E's checked-in DAG lands on main**; until then
  they are design-frozen within this PR and subject to a single re-binding PR.
- Divergence check performed at authoring: prior-art seam anchors re-fetched at base HEAD;
  `runtime_journal.py`, `station/store.py`, `dsm/store.py`, `dsm/journal.py`,
  `dsm/delivery.py` blob SHAs match the wave-a audit exactly (verified via API against
  `3cff6bcd`). No divergence discovered.
- `docs/architecture/` on base HEAD contains only `ci-cd.md`, `compliance-audit.md`,
  `incident-response.md` — E's DAG is not yet checked in, so the gate remains open.

## 10. Migration approach (RuntimeJournal / Station Store / DSM Journal → ledger)

Migration is import-once, verify-always, never rewrite history:

1. **M-a Export.** For each legacy store, enumerate records in durable order
   (`events.sequence` / `seq` / JSONL line order) into a canonical intermediate JSONL with
   per-record digests. Legacy genesis literals (`'GENESIS'` vs `'0'*64`) are mapped, and the
   mapping is recorded in the migration manifest (not silently normalized).
2. **M-b Re-key.** Assign ledger `event_id`s deterministically:
   `sha256(store_kind || store_identity || old_seq || old_digest)`. Store identity is
   `trace_id` (RuntimeJournal), project id (Station), or root path hash (DSM).
3. **M-c Import.** Replay intermediate records through the *same* admission path as live
   writes (§5 `submit`), so dedupe/fencing/chain invariants are exercised by migration
   itself. Import appends to a fresh ledger; existing ledgers are never merged
   cross-control-plane.
4. **M-d Verify.** Recompute the imported chain; recompute projections from imported events
   and compare field-by-field against a legacy store dump; emit a signed-off
   `control.migration` event with counts and head hashes of both sides. Any mismatch aborts
   and retains both stores untouched (fail closed; retained failure, not weakened).
5. **M-e Cutover.** MS-01 orchestration re-points at the ledger only after M-d passes for
   every store in the control plane. Legacy files are retained read-only as evidence.

Open owner decision (flagged, not silently resolved): whether per-run RuntimeJournal files
are consolidated into the single control-plane ledger at cutover, or archived per run with
only projections imported.

## 11. Implementation plan (ordered milestones)

| Gate | Milestone | Exit criteria |
|---|---|---|
| **G0** (this PR, design) | MS-00 design + reference SQLite implementation (`ms00/reference_ledger.py`) + contract-test skeletons green against the reference | This PR; contract suite (CAS, exactly-one-terminal, crash-recovery, reconciliation, fencing) passes locally against reference |
| **G0-impl** | Production MS-00 ledger crate/module implementing §4–§6, bound to the contract suite unchanged | Contract suite passes against production implementation with **zero test edits**; KP-01..08, KP-15..17 green |
| **G1** | MS-01 reconciliation (§8) against G0 ledgers, reproducing Station `recover` semantics | KP-11..13, KP-18 green; projection determinism proof; `control.reconciled` evidence |
| **G1-impl** | MS-08 writer service (single-writer lease, durable fencing tokens) fronting the ledger | Writer-lease CAS under multi-process contention; stale-fencing rejection; KP-14 watchdog ablation diff = [] |
| **M** | Migration tooling (§10) | M-a..M-e on fixture stores; migration verification events |

Hard rule carried into every gate: never weaken a test to obtain green; retain first-attempt
failures; UNKNOWN/BLOCKED never reported as PASS.

## 12. Reference implementation & contract tests (this PR)

- `docs/architecture/ms00/reference_ledger.py` — minimal, dependency-free SQLite reference
  implementing §4.1–§4.4, §6 CAS SQL, fencing tokens, `event_id` dedupe, hash chain, and
  §8 reconciliation classification (attempts subset). It exists **only** to make the
  contract skeletons executable; it is not the production MS-00.
- `docs/architecture/ms00/tests/test_ms00_contract.py` — pytest contract skeletons encoding
  I-1..I-6 and KP rows against a ledger object. Binding to the future production
  implementation is a one-fixture change (`ledger_factory` fixture).
