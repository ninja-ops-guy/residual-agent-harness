"""MS-00 run ledger — minimal SQLite reference implementation.

This module exists ONLY to make the contract-test skeletons
(``tests/test_ms00_contract.py``) executable. It is a design artifact, not the
production MS-00 ledger. It implements, minimally and dependency-free:

- schema §4.1-§4.4 (metadata, events with hash chain + event_id dedupe,
  attempts with terminal_state + fencing_token, lease_generations),
- CAS SQL §6 (terminal CAS, generation CAS, writer-lease CAS),
- invariants I-1 (exactly-one-terminal, storage-enforced), I-2 (state+event
  atomicity), I-4 (idempotent admission), I-6 (fail-closed chain verification),
- reconciliation classification §8 steps 1-3 (writer fencing + orphaned-attempt
  terminal CAS) with a ``control.reconciled`` checkpoint event.

Binding the contract suite to the future production implementation requires
only replacing the ``ledger_factory`` fixture in the test module.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

TERMINAL_STATES = ("CANDIDATE", "VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED")
ACTIVE_STATES = ("RESERVED", "RUNNING", "CANDIDATE")
GENESIS = "0" * 64


class JournalError(Exception):
    """Fail-closed rejection; no mutation committed."""


class FencingError(Exception):
    """Stale fencing token rejected."""


class AmbiguousCommitError(JournalError):
    """COMMIT outcome unknown; connection discarded; consult the ledger."""


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Ack:
    seq: int
    hash: str
    disposition: str  # "accepted" | "duplicate"
    fencing_token: int


class ReferenceLedger:
    """One control-plane ledger. Exactly-one-terminal is storage-enforced."""

    def __init__(self, path: str | Path, *, control_plane_id: str):
        self.path = Path(path)
        self.control_plane_id = control_plane_id
        self._lock = threading.RLock()
        db = self._connect()
        try:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    digest TEXT UNIQUE NOT NULL,
                    prev_hash TEXT NOT NULL,
                    record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    worker_id TEXT UNIQUE NOT NULL,
                    swarm_id TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    contract_hash TEXT NOT NULL,
                    contract_json TEXT NOT NULL,
                    lease_id TEXT UNIQUE NOT NULL,
                    generation INTEGER NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    workspace TEXT UNIQUE NOT NULL,
                    state TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    terminal_state TEXT,
                    pid INTEGER,
                    created_ns INTEGER NOT NULL,
                    updated_ns INTEGER NOT NULL,
                    CHECK (state IN ('RESERVED','RUNNING','CANDIDATE','VIOLATED','FAILED',
                                     'CANCELLED','AUDIT_FAILED','PURGED')),
                    CHECK (terminal_state IS NULL OR state = terminal_state));
                CREATE TABLE IF NOT EXISTS lease_generations (
                    plan_hash TEXT NOT NULL, task_id TEXT NOT NULL,
                    generation INTEGER NOT NULL, fencing_token INTEGER NOT NULL,
                    PRIMARY KEY (plan_hash, task_id));
                CREATE UNIQUE INDEX IF NOT EXISTS one_candidate_per_task
                    ON attempts(plan_hash, task_id) WHERE terminal_state = 'CANDIDATE';
                CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                """
            )
            saved = db.execute(
                "SELECT value FROM metadata WHERE key='control_plane_id'").fetchone()
            if saved is not None and saved[0] != control_plane_id:
                db.close()
                raise JournalError("ledger belongs to another control plane")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('control_plane_id',?)",
                       (control_plane_id,))
            db.commit()
        finally:
            db.close()
        self.verify_chain()  # I-6: refuse a corrupt persisted chain on open

    # -- connections / transactions ---------------------------------------
    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=1.0, isolation_level=None)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _tx(self):
        db = self._connect()
        db.execute("BEGIN IMMEDIATE")
        return db

    def _commit(self, db):
        try:
            db.execute("COMMIT")
        except sqlite3.Error as exc:
            db.close()
            raise AmbiguousCommitError(str(exc)) from exc
        db.close()

    def _rollback(self, db):
        try:
            db.execute("ROLLBACK")
        except sqlite3.Error:
            pass  # preserve the original failure; connection is discarded
        finally:
            db.close()

    # -- event chain --------------------------------------------------------
    def _append(self, db, event_id: str, writer: str, fencing_token: int,
                payload: dict) -> tuple[int, str, str]:
        tail = db.execute(
            "SELECT digest FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = tail[0] if tail else GENESIS
        record = {"event_id": event_id, "writer": writer,
                  "fencing_token": fencing_token, "prev_hash": prev,
                  "payload": payload}
        digest = hashlib.sha256(_canonical(record).encode()).hexdigest()
        cur = db.execute(
            "INSERT INTO events(event_id, digest, prev_hash, record) VALUES (?,?,?,?)",
            (event_id, digest, prev, _canonical(record)))
        return cur.lastrowid, digest, prev

    def _find(self, db, event_id: str):
        return db.execute(
            "SELECT seq, digest FROM events WHERE event_id=?", (event_id,)).fetchone()

    def events(self) -> list[dict]:
        db = self._connect()
        try:
            return [json.loads(r[0]) for r in db.execute(
                "SELECT record FROM events ORDER BY seq")]
        finally:
            db.close()

    def verify_chain(self) -> None:
        prev = GENESIS
        for rec in self.events():
            if rec["prev_hash"] != prev:
                raise JournalError("event chain is invalid")
            digest = hashlib.sha256(_canonical(rec).encode()).hexdigest()
            row = self._read_one(
                "SELECT digest FROM events WHERE event_id=?", (rec["event_id"],))
            if row is None or row[0] != digest:
                raise JournalError("event chain is invalid")
            prev = digest

    def _read_one(self, query, params):
        db = self._connect()
        try:
            return db.execute(query, params).fetchone()
        finally:
            db.close()

    # -- MS-08 writer lease / fencing ---------------------------------------
    def acquire_writer_lease(self, writer_id: str) -> int:
        """Writer-claim CAS; returns the new durable fencing token."""
        with self._lock:
            db = self._tx()
            try:
                row = db.execute(
                    "INSERT INTO lease_generations(plan_hash, task_id, generation, fencing_token)"
                    " VALUES ('__control__','writer',1,1)"
                    " ON CONFLICT(plan_hash, task_id) DO UPDATE"
                    " SET generation = generation + 1, fencing_token = fencing_token + 1"
                    " RETURNING fencing_token").fetchone()
                token = row[0]
                db.execute("INSERT OR REPLACE INTO metadata VALUES ('writer_id',?)",
                           (writer_id,))
                self._commit(db)
                return token
            except BaseException:
                self._rollback(db)
                raise

    def _check_fence(self, db, fencing_token: int) -> None:
        row = db.execute(
            "SELECT fencing_token FROM lease_generations"
            " WHERE plan_hash='__control__' AND task_id='writer'").fetchone()
        if row is not None and fencing_token < row[0]:
            raise FencingError("stale fencing token")

    # -- attempt lifecycle ----------------------------------------------------
    def claim(self, *, attempt_id: str, task_id: str, worker_id: str, swarm_id: str,
              plan_hash: str, contract_hash: str, contract_json: str, lease_id: str,
              generation: int, workspace: str, fencing_token: int,
              event_id: str, writer: str) -> Ack:
        with self._lock:
            db = self._tx()
            try:
                dup = self._find(db, event_id)
                if dup:
                    self._rollback(db)
                    return Ack(dup[0], dup[1], "duplicate", fencing_token)
                self._check_fence(db, fencing_token)
                cur = db.execute(
                    "UPDATE lease_generations SET generation=?, fencing_token=?"
                    " WHERE plan_hash=? AND task_id=? AND generation < ?",
                    (generation, fencing_token, plan_hash, task_id, generation))
                if cur.rowcount == 0:
                    exists = db.execute(
                        "SELECT 1 FROM lease_generations WHERE plan_hash=? AND task_id=?",
                        (plan_hash, task_id)).fetchone()
                    if exists:
                        raise JournalError("lease generation must increase across attempts")
                    db.execute(
                        "INSERT INTO lease_generations VALUES (?,?,?,?)",
                        (plan_hash, task_id, generation, fencing_token))
                active = db.execute(
                    "SELECT attempt_id FROM attempts WHERE plan_hash=? AND task_id=?"
                    " AND state IN ('RESERVED','RUNNING','CANDIDATE')",
                    (plan_hash, task_id)).fetchone()
                if active:
                    raise JournalError("task already has an active or quarantined attempt")
                now = time.time_ns()
                try:
                    db.execute(
                        "INSERT INTO attempts(attempt_id,task_id,worker_id,swarm_id,plan_hash,"
                        "contract_hash,contract_json,lease_id,generation,fencing_token,"
                        "workspace,state,created_ns,updated_ns)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,'RESERVED',?,?)",
                        (attempt_id, task_id, worker_id, swarm_id, plan_hash, contract_hash,
                         contract_json, lease_id, generation, fencing_token, workspace,
                         now, now))
                except sqlite3.IntegrityError as exc:
                    raise JournalError(
                        "attempt, worker, lease or workspace identity was already used") from exc
                seq, digest, _ = self._append(
                    db, event_id, writer, fencing_token,
                    {"event": "RuntimeAttemptClaimed", "attempt_id": attempt_id,
                     "task_id": task_id, "plan_hash": plan_hash})
                self._commit(db)
                return Ack(seq, digest, "accepted", fencing_token)
            except BaseException:
                self._rollback(db)
                raise

    def started(self, attempt_id: str, pid: int, *, fencing_token: int,
                event_id: str, writer: str) -> Ack:
        with self._lock:
            db = self._tx()
            try:
                dup = self._find(db, event_id)
                if dup:
                    self._rollback(db)
                    return Ack(dup[0], dup[1], "duplicate", fencing_token)
                self._check_fence(db, fencing_token)
                cur = db.execute(
                    "UPDATE attempts SET state='RUNNING', pid=?, updated_ns=?"
                    " WHERE attempt_id=? AND state='RESERVED' AND revoked=0",
                    (pid, time.time_ns(), attempt_id))
                if cur.rowcount != 1:
                    raise JournalError("attempt is not reserved or has been revoked")
                seq, digest, _ = self._append(
                    db, event_id, writer, fencing_token,
                    {"event": "RuntimeProcessSpawned", "attempt_id": attempt_id,
                     "pid": pid})
                self._commit(db)
                return Ack(seq, digest, "accepted", fencing_token)
            except BaseException:
                self._rollback(db)
                raise

    def finish(self, attempt_id: str, state: str, *, fencing_token: int,
               event_id: str, writer: str, **details) -> Ack:
        """Terminal CAS (I-1). Storage predicate makes a second terminal impossible."""
        if state not in TERMINAL_STATES:
            raise JournalError("invalid terminal runtime state")
        with self._lock:
            db = self._tx()
            try:
                dup = self._find(db, event_id)
                if dup:
                    self._rollback(db)
                    return Ack(dup[0], dup[1], "duplicate", fencing_token)
                self._check_fence(db, fencing_token)
                cur = db.execute(
                    "UPDATE attempts SET state=?, terminal_state=?, updated_ns=?"
                    " WHERE attempt_id=?"
                    " AND state IN ('RESERVED','RUNNING','CANDIDATE')"
                    " AND terminal_state IS NULL"
                    " AND (? != 'CANDIDATE' OR revoked = 0)"
                    " AND ? >= (SELECT fencing_token FROM attempts WHERE attempt_id=?)",
                    (state, state, time.time_ns(), attempt_id,
                     state, fencing_token, attempt_id))
                if cur.rowcount != 1:
                    raise JournalError(
                        "attempt already terminal, unknown, revoked-candidate, or stale-fenced")
                seq, digest, _ = self._append(
                    db, event_id, writer, fencing_token,
                    {"event": "RuntimeAttemptFinished", "attempt_id": attempt_id,
                     "state": state, **details})
                self._commit(db)
                return Ack(seq, digest, "accepted", fencing_token)
            except BaseException:
                self._rollback(db)
                raise

    def revoke(self, attempt_id: str, *, fencing_token: int,
               event_id: str, writer: str) -> Ack:
        with self._lock:
            db = self._tx()
            try:
                dup = self._find(db, event_id)
                if dup:
                    self._rollback(db)
                    return Ack(dup[0], dup[1], "duplicate", fencing_token)
                self._check_fence(db, fencing_token)
                row = db.execute("SELECT state FROM attempts WHERE attempt_id=?",
                                 (attempt_id,)).fetchone()
                if row is None or row[0] not in ("RESERVED", "RUNNING"):
                    raise JournalError("only an active attempt can be revoked")
                db.execute("UPDATE attempts SET revoked=1, updated_ns=? WHERE attempt_id=?",
                           (time.time_ns(), attempt_id))
                seq, digest, _ = self._append(
                    db, event_id, writer, fencing_token,
                    {"event": "RuntimeLeaseRevoked", "attempt_id": attempt_id})
                self._commit(db)
                return Ack(seq, digest, "accepted", fencing_token)
            except BaseException:
                self._rollback(db)
                raise

    # -- reconciliation (§8, attempts subset) --------------------------------
    def reconcile(self, *, writer_id: str, fencing_token: int,
                  event_id: str | None = None) -> dict:
        """Classify orphaned attempts as terminal FAILED via the same CAS (I-1).

        Idempotent: re-running after a crash re-executes the same CAS, which
        no-ops on already-terminal rows, and dedupes the checkpoint event.
        """
        event_id = event_id or f"reconcile-{uuid.uuid4().hex}"
        with self._lock:
            db = self._tx()
            try:
                self._check_fence(db, fencing_token)
                orphaned = 0
                for row in db.execute(
                        "SELECT attempt_id FROM attempts"
                        " WHERE state IN ('RESERVED','RUNNING')").fetchall():
                    aid = row[0]
                    cur = db.execute(
                        "UPDATE attempts SET state='FAILED', terminal_state='FAILED',"
                        " updated_ns=? WHERE attempt_id=?"
                        " AND state IN ('RESERVED','RUNNING','CANDIDATE')"
                        " AND terminal_state IS NULL",
                        (time.time_ns(), aid))
                    if cur.rowcount == 1:
                        orphaned += 1
                        self._append(db, f"{event_id}:orphan:{aid}", writer_id,
                                     fencing_token,
                                     {"event": "RuntimeAttemptFinished",
                                      "attempt_id": aid, "state": "FAILED",
                                      "reason": "interrupted_at_startup"})
                dup = self._find(db, event_id)
                if dup is None:
                    seq, digest, _ = self._append(
                        db, event_id, writer_id, fencing_token,
                        {"event": "control.reconciled",
                         "orphaned_attempts": orphaned})
                else:
                    seq, digest = dup[0], dup[1]
                self._commit(db)
                return {"orphaned_attempts": orphaned, "seq": seq, "hash": digest}
            except BaseException:
                self._rollback(db)
                raise

    # -- projection reconstruction (I-3) --------------------------------------
    def project_attempt_states(self) -> dict[str, str]:
        """Rebuild per-attempt state from events alone (deterministic order)."""
        states: dict[str, str] = {}
        for rec in self.events():
            payload = rec["payload"]
            if payload.get("event") == "RuntimeAttemptClaimed":
                states[payload["attempt_id"]] = "RESERVED"
            elif payload.get("event") == "RuntimeProcessSpawned":
                states[payload["attempt_id"]] = "RUNNING"
            elif payload.get("event") == "RuntimeAttemptFinished":
                states[payload["attempt_id"]] = payload["state"]
        return states

    def attempt_state(self, attempt_id: str):
        return self._read_one(
            "SELECT state, terminal_state, revoked FROM attempts WHERE attempt_id=?",
            (attempt_id,))

    def attempts(self) -> list[dict]:
        db = self._connect()
        db.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in db.execute(
                "SELECT * FROM attempts ORDER BY created_ns, attempt_id")]
        finally:
            db.close()


def new_attempt_params(prefix: str, plan_hash: str, task_id: str, generation: int,
                       fencing_token: int, writer: str = "writer-0") -> dict:
    """Deterministic, always-unique attempt parameters for tests/migrations."""
    uid = f"{prefix}-{uuid.uuid4().hex[:12]}"
    return dict(attempt_id=f"a-{uid}", task_id=task_id, worker_id=f"w-{uid}",
                swarm_id=f"s-{uid}", plan_hash=plan_hash,
                contract_hash=hashlib.sha256(uid.encode()).hexdigest(),
                contract_json=_canonical({"id": uid}), lease_id=f"l-{uid}",
                generation=generation, workspace=f"/tmp/ws-{uid}",
                fencing_token=fencing_token, event_id=f"e-claim-{uid}",
                writer=writer)
