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
                                "AND state IN ('RESERVED','RUNNING','CANDIDATE')",
                                (contract.execution_plan_hash, contract.task_id)).fetchone()
            if active:
                raise JournalError("task already has an active or quarantined attempt")
            now = time.time_ns()
            try:
                db.execute("INSERT INTO attempts(attempt_id,task_id,worker_id,swarm_id,plan_hash,"
                           "contract_hash,contract_json,lease_id,generation,workspace,state,created_ns,updated_ns) "
                           "VALUES (?,?,?,?,?,?,?,?,?,?,'RESERVED',?,?)",
                           (contract.attempt_id, contract.task_id, contract.worker_id, contract.swarm_id,
                            contract.execution_plan_hash, contract.contract_hash, canonical(contract.to_dict()), contract.lease_id,
                            contract.lease_generation, contract.workspace_root, now, now))
            except sqlite3.IntegrityError as exc:
                raise JournalError("attempt, worker, lease or workspace identity was already used") from exc
            db.execute("INSERT INTO generations VALUES (?,?,?) ON CONFLICT(plan_hash,task_id) "
                       "DO UPDATE SET generation=excluded.generation",
                       (contract.execution_plan_hash, contract.task_id, contract.lease_generation))
            self._append(db, {"event": "RuntimeAttemptClaimed", "contract": contract.to_dict(),
                              "contract_hash": contract.contract_hash,
                              "execution_plan_hash": contract.execution_plan_hash,
                              "attempt_id": contract.attempt_id, "source_sha256": source_hash,
                              "approval": approval, "approval_trust": "local_operator",
                              "profile": "linux-seccomp-broker-v1"})

    def started(self, contract: WorkerContract, pid: int) -> None:
        with self._transaction() as db:
            cursor = db.execute("UPDATE attempts SET state='RUNNING',pid=?,updated_ns=? "
                                "WHERE attempt_id=? AND state='RESERVED' AND revoked=0",
                                (pid, time.time_ns(), contract.attempt_id))
            if cursor.rowcount != 1:
                raise JournalError("attempt is not reserved or has been revoked")
            self._append(db, {"event": "RuntimeProcessSpawned", "attempt_id": contract.attempt_id,
                              "contract_hash": contract.contract_hash, "pid": pid})

    def lease_is_current(self, contract: WorkerContract) -> bool:
        # Separate bounded read connection: watchdog never waits for the writer's lock.
        with self._connect() as db:
            row = db.execute("SELECT lease_id,generation,revoked,state,contract_hash FROM attempts "
                             "WHERE attempt_id=?", (contract.attempt_id,)).fetchone()
        return bool(row and row[0] == contract.lease_id and row[1] == contract.lease_generation
                    and not row[2] and row[3] in ('RESERVED', 'RUNNING') and row[4] == contract.contract_hash)

    def revoke(self, attempt_id: str) -> None:
        with self._transaction() as db:
            row = db.execute("SELECT state FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if row is None or row[0] not in ('RESERVED', 'RUNNING'):
                raise JournalError("only an active attempt can be revoked")
            db.execute("UPDATE attempts SET revoked=1,updated_ns=? WHERE attempt_id=?",
                       (time.time_ns(), attempt_id))
            self._append(db, {"event": "RuntimeLeaseRevoked", "attempt_id": attempt_id})

    def finish(self, contract: WorkerContract, state: str, **details) -> None:
        if state not in {"CANDIDATE", "VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED"}:
            raise JournalError("invalid terminal runtime state")
        with self._transaction() as db:
            row = db.execute("SELECT state,revoked FROM attempts WHERE attempt_id=?",
                             (contract.attempt_id,)).fetchone()
            if row is None or row[0] not in ('RESERVED', 'RUNNING'):
                raise JournalError("attempt already terminal or unknown")
            if state == 'CANDIDATE' and row[1]:
                raise JournalError("revoked attempt cannot produce a candidate")
            db.execute("UPDATE attempts SET state=?,updated_ns=? WHERE attempt_id=?",
                       (state, time.time_ns(), contract.attempt_id))
            self._append(db, {"event": "RuntimeAttemptFinished", "attempt_id": contract.attempt_id,
                              "execution_plan_hash": contract.execution_plan_hash,
                              "contract_hash": contract.contract_hash, "state": state, **details})

    def mark_purged(self, attempt_id: str) -> None:
        with self._transaction() as db:
            row = db.execute("SELECT state FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if row is None or row[0] in ('RESERVED', 'RUNNING'):
                raise JournalError("active attempts cannot be purged")
            db.execute("UPDATE attempts SET state='PURGED',updated_ns=? WHERE attempt_id=?",
                       (time.time_ns(), attempt_id))
            self._append(db, {"event": "RuntimeCandidatePurged", "attempt_id": attempt_id})

    def attempts(self) -> list[dict]:
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM attempts ORDER BY created_ns,attempt_id")]

    def observations(self) -> list[Observation]:
        with self._connect() as db:
            rows = db.execute("SELECT record FROM events ORDER BY sequence").fetchall()
        values = [Observation(**strict_json(row[0])) for row in rows]
        if not verify_chain(values):
            raise JournalError("observation chain is invalid")
        return values

    def export_jsonl(self, path: str | Path) -> None:
        # Exclusive create avoids overwriting or following an operator-selected symlink.
        values = self.observations()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            for value in values:
                stream.write(canonical(value.to_dict()) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
