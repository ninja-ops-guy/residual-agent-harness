"""Durable local M2 attempts and observations, using the existing event schema.

A FULL-synchronous SQLite transaction commits each event before acknowledgement.
This is an integrity ledger, not a signature or an external trust anchor.
"""
from __future__ import annotations

import json
import os
import sqlite3
import stat
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from observation_layer import Observation, ObservationKind, SCHEMA_VERSION, verify_chain
from residual.core import canonical, strict_json
from .worker_contract import WorkerContract, WorkerContractError


class JournalError(WorkerContractError):
    pass


def private_directory(path: Path) -> Path:
    path = Path(path).absolute()
    if path.resolve(strict=False) != path:
        raise JournalError("runtime directory must not traverse symlinks")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.resolve() != path:
        raise JournalError("runtime directory must not traverse symlinks")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise JournalError("runtime directory must be owned by the operator and not writable by others")
    return path


class RuntimeJournal:
    """One host-owned journal per run; worker/attempt IDs may never be reused."""
    def __init__(self, path: str | Path, *, trace_id: str):
        if not isinstance(trace_id, str) or not 0 < len(trace_id) <= 96:
            raise JournalError("invalid runtime trace_id")
        self.path = Path(path).absolute()
        private_directory(self.path.parent)
        self.trace_id = trace_id
        self._lock = threading.RLock()
        flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open(self.path, flags, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise JournalError("journal must be a private regular file")
        finally:
            os.close(descriptor)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript('''
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest TEXT UNIQUE NOT NULL, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY, task_id TEXT NOT NULL,
                    worker_id TEXT UNIQUE NOT NULL, swarm_id TEXT NOT NULL,
                    plan_hash TEXT NOT NULL, contract_hash TEXT NOT NULL, contract_json TEXT NOT NULL,
                    lease_id TEXT UNIQUE NOT NULL, generation INTEGER NOT NULL,
                    workspace TEXT UNIQUE NOT NULL, state TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0, pid INTEGER,
                    created_ns INTEGER NOT NULL, updated_ns INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS generations (
                    plan_hash TEXT NOT NULL, task_id TEXT NOT NULL,
                    generation INTEGER NOT NULL, PRIMARY KEY(plan_hash,task_id));
                CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT, 'append-only events'); END;
            ''')
            db.execute("BEGIN IMMEDIATE")
            saved = db.execute("SELECT value FROM metadata WHERE key='trace_id'").fetchone()
            if saved is not None and saved[0] != trace_id:
                raise JournalError("journal belongs to another run")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('trace_id',?)", (trace_id,))
            db.execute("COMMIT")
        self.observations()  # refuse a corrupt persisted chain on restart

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # A live worker can briefly hold the WAL write lock while another thread
        # opens a read connection for status polling. Configuring synchronous mode
        # is itself a database operation, so give SQLite a real busy window rather
        # than surfacing a transient lock as an audit failure.
        db = sqlite3.connect(self.path, timeout=2.0, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=2000")
            deadline = time.monotonic() + 2.0
            while True:
                try:
                    db.execute("PRAGMA synchronous=FULL")
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower() or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.01)
            db.execute("PRAGMA foreign_keys=ON")
            yield db
        finally:
            db.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def _append(self, db: sqlite3.Connection, payload: dict[str, Any]) -> None:
        # Round trip to detach mutable input and reject non-finite/duplicate JSON.
        payload = strict_json(canonical(payload))
        tail = db.execute("SELECT digest FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        observation = Observation(str(uuid.uuid4()), self.trace_id, ObservationKind.CUSTOM,
                                  time.time_ns(), SCHEMA_VERSION, tail[0] if tail else 'GENESIS',
                                  payload, {"component": "factory-runtime"}, "residual.factory.runtime")
        db.execute("INSERT INTO events(digest,record) VALUES (?,?)",
                   (observation.digest, canonical(observation.to_dict())))

    def observe(self, payload: dict[str, Any]) -> None:
        with self._transaction() as db:
            self._append(db, payload)

    def claim(self, contract: WorkerContract, *, source_hash: str, approval: dict) -> None:
        with self._transaction() as db:
            old = db.execute("SELECT generation FROM generations WHERE plan_hash=? AND task_id=?",
                             (contract.execution_plan_hash, contract.task_id)).fetchone()
            if old and contract.lease_generation <= old[0]:
                raise JournalError("lease generation must increase across attempts")
            active = db.execute("SELECT attempt_id FROM attempts WHERE plan_hash=? AND task_id=? "
                                "AND state NOT IN ('FAILED','VIOLATED','CANCELLED','CANDIDATE','AUDIT_FAILED')",
                                (contract.execution_plan_hash, contract.task_id)).fetchone()
            if active:
                raise JournalError("task already has an active attempt")
            now = time.time_ns()
            db.execute("INSERT INTO generations VALUES (?,?,?) ON CONFLICT(plan_hash,task_id) "
                       "DO UPDATE SET generation=excluded.generation",
                       (contract.execution_plan_hash, contract.task_id, contract.lease_generation))
            db.execute("INSERT INTO attempts(attempt_id,task_id,worker_id,swarm_id,plan_hash,contract_hash,contract_json,"
                       "lease_id,generation,workspace,state,created_ns,updated_ns) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (contract.attempt_id, contract.task_id, contract.worker_id, contract.swarm_id,
                        contract.execution_plan_hash, contract.contract_hash, canonical(contract.to_dict()),
                        contract.lease_id, contract.lease_generation, contract.workspace_root, 'CLAIMED', now, now))
            self._append(db, {"event": "RuntimeAttemptClaimed", "attempt_id": contract.attempt_id,
                              "task_id": contract.task_id, "worker_id": contract.worker_id,
                              "swarm_id": contract.swarm_id, "execution_plan_hash": contract.execution_plan_hash,
                              "contract_hash": contract.contract_hash, "source_hash": source_hash,
                              "approval": approval})

    def started(self, contract: WorkerContract, pid: int) -> None:
        with self._transaction() as db:
            row = db.execute("SELECT state,revoked FROM attempts WHERE attempt_id=?", (contract.attempt_id,)).fetchone()
            if row != ('CLAIMED', 0):
                raise JournalError("attempt is not launchable")
            db.execute("UPDATE attempts SET state='RUNNING',pid=?,updated_ns=? WHERE attempt_id=?",
                       (pid, time.time_ns(), contract.attempt_id))
            self._append(db, {"event": "RuntimeProcessSpawned", "attempt_id": contract.attempt_id,
                              "pid": pid, "contract_hash": contract.contract_hash})

    def revoke(self, attempt_id: str) -> None:
        with self._transaction() as db:
            row = db.execute("SELECT state FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if row is None or row[0] in {'FAILED','VIOLATED','CANCELLED','CANDIDATE','AUDIT_FAILED'}:
                raise JournalError("attempt is already terminal or missing")
            db.execute("UPDATE attempts SET revoked=1,updated_ns=? WHERE attempt_id=?", (time.time_ns(), attempt_id))
            self._append(db, {"event": "RuntimeAttemptRevoked", "attempt_id": attempt_id})

    def lease_is_current(self, contract: WorkerContract) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT generation,lease_id,revoked,state FROM attempts WHERE attempt_id=?",
                             (contract.attempt_id,)).fetchone()
        return bool(row and row[0] == contract.lease_generation and row[1] == contract.lease_id
                    and row[2] == 0 and row[3] in {'CLAIMED','RUNNING'})

    def finish(self, contract: WorkerContract, state: str, *, reason: str = "",
               process_reaped: bool = False, returncode: int | None = None,
               usage: dict[str, int] | None = None, candidate: dict | None = None) -> None:
        if state not in {'FAILED','VIOLATED','CANCELLED','CANDIDATE','AUDIT_FAILED'}:
            raise JournalError("invalid terminal state")
        with self._transaction() as db:
            row = db.execute("SELECT state,revoked FROM attempts WHERE attempt_id=?", (contract.attempt_id,)).fetchone()
            if row is None:
                raise JournalError("attempt missing")
            if row[0] in {'FAILED','VIOLATED','CANCELLED','CANDIDATE','AUDIT_FAILED'}:
                raise JournalError("attempt already terminal")
            if state == 'CANDIDATE' and row[1]:
                raise JournalError("revoked attempt cannot publish candidate")
            db.execute("UPDATE attempts SET state=?,updated_ns=? WHERE attempt_id=?",
                       (state, time.time_ns(), contract.attempt_id))
            self._append(db, {"event": "RuntimeAttemptFinished", "attempt_id": contract.attempt_id,
                              "state": state, "reason": reason, "process_reaped": process_reaped,
                              "returncode": returncode, "usage": usage or {}, "candidate": candidate})

    def attempts(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            columns = [row[1] for row in db.execute("PRAGMA table_info(attempts)").fetchall()]
            rows = db.execute("SELECT * FROM attempts ORDER BY created_ns").fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def observations(self) -> list[Observation]:
        with self._connect() as db:
            rows = db.execute("SELECT record FROM events ORDER BY sequence").fetchall()
        observations = [Observation.from_dict(strict_json(row[0])) for row in rows]
        if not verify_chain(observations, expected_count=len(observations)):
            raise JournalError("persisted observation chain failed verification")
        return observations

    def export_jsonl(self, path: str | Path) -> None:
        output = Path(path)
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w') as stream:
                for observation in self.observations():
                    stream.write(canonical(observation.to_dict()) + "\n")
                stream.flush(); os.fsync(stream.fileno())
        except BaseException:
            output.unlink(missing_ok=True)
            raise
