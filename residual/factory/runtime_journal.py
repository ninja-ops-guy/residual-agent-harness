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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from observation_layer import Observation, ObservationKind, SCHEMA_VERSION, verify_chain
from residual.core import canonical, strict_json
from .worker_contract import WorkerContract, WorkerContractError


class JournalError(WorkerContractError):
    pass


@dataclass(frozen=True)
class LeaseRead:
    """Atomic lease-read outcome: state plus its own diagnostic.

    ``diag`` is bound to THIS read at construction, so a concurrent attempt's
    failed read can never overwrite another attempt's provenance. It carries
    only (exception type name, sqlite_errorcode) — never exception text.
    """
    state: str  # 'current' | 'revoked' | 'unknown'
    diag: tuple[str, int] | None = None


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
        with self._connect(write=True) as db:
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

    # Readers get a longer bounded budget than writers: an expected
    # observation/status read must not fail merely because a writer holds a
    # transaction briefly (CI contention). Writers fail fast as before.
    READ_CONNECT_TIMEOUT_S = 5.0
    WRITE_CONNECT_TIMEOUT_S = 0.2

    @contextmanager
    def _connect(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        # Lock-sensitive write pragmas (synchronous) run ONLY on writer
        # connections. A reader connection must be able to initialize and
        # serve a consistent WAL snapshot without taking or waiting on the
        # write lock beyond the bounded busy-timeout.
        timeout = self.WRITE_CONNECT_TIMEOUT_S if write else self.READ_CONNECT_TIMEOUT_S
        db = sqlite3.connect(self.path, timeout=timeout, isolation_level=None)
        try:
            if write:
                db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            yield db
        finally:
            db.close()

    def _read(self, query: str, params: tuple = (), *,
              row_factory: Any = None) -> list:
        """One bounded read: retries transient lock contention up to
        READ_CONNECT_TIMEOUT_S, then raises the last sqlite3.Error.

        The connection's own busy-timeout covers waitable locks; this retry
        covers contention classes the busy handler does not wait out (for
        example SQLITE_BUSY_SNAPSHOT during WAL checkpointing), so a held
        writer can never turn an expected read into an unbounded block or an
        immediate failure.
        """
        deadline = time.monotonic() + self.READ_CONNECT_TIMEOUT_S
        delay = 0.02
        while True:
            try:
                with self._connect() as db:
                    if row_factory is not None:
                        db.row_factory = row_factory
                    return db.execute(query, params).fetchall()
            except sqlite3.OperationalError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                time.sleep(min(delay, remaining))
                delay = min(delay * 2, 0.2)

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._connect(write=True) as db:
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

    LEASE_READ_TIMEOUT_S = 2.0

    def lease_read(self, contract: WorkerContract, *, deadline: float | None = None,
                   clock: Callable[[], float] = time.monotonic) -> LeaseRead:
        """Atomic tri-state lease read returning state AND its own diagnostic.

        The returned LeaseRead binds (state, diag) for THIS read, so a
        concurrent attempt's failed read can never overwrite this attempt's
        provenance. 'unknown' is returned ONLY when the durable store itself
        cannot be read (sqlite3.Error, including a bounded busy-timeout) or
        when the caller-supplied absolute ``deadline`` is already exhausted.
        A missing, revoked, terminal, or mismatched row is 'revoked' — never
        'unknown'. Callers must never retype an 'unknown' outcome as a
        revocation.

        When ``deadline`` (on ``clock``) is given, this read's busy budget is
        capped at the remaining time so the caller's total lease-denial bound
        is honored end to end.
        """
        budget = self.LEASE_READ_TIMEOUT_S
        if deadline is not None:
            remaining = deadline - clock()
            if remaining <= 0:
                return LeaseRead('unknown', ('read_budget_exhausted', 0))
            budget = min(budget, remaining)
        try:
            db = sqlite3.connect(self.path, timeout=budget, isolation_level=None)
            try:
                db.execute(f"PRAGMA busy_timeout={int(budget * 1000)}")
                row = db.execute(
                    "SELECT lease_id,generation,revoked,state,contract_hash FROM attempts "
                    "WHERE attempt_id=?", (contract.attempt_id,)).fetchone()
            finally:
                db.close()
        except sqlite3.Error as exc:
            code = getattr(exc, 'sqlite_errorcode', None)
            diag = (type(exc).__name__, code) if type(code) is int else (type(exc).__name__, -1)
            return LeaseRead('unknown', diag)
        current = bool(row and row[0] == contract.lease_id and row[1] == contract.lease_generation
                       and not row[2] and row[3] in ('RESERVED', 'RUNNING')
                       and row[4] == contract.contract_hash)
        return LeaseRead('current' if current else 'revoked')

    def lease_state(self, contract: WorkerContract) -> str:
        """Tri-state convenience wrapper over lease_read(); see its contract."""
        return self.lease_read(contract).state

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
        rows = self._read("SELECT * FROM attempts ORDER BY created_ns,attempt_id",
                          row_factory=sqlite3.Row)
        return [dict(row) for row in rows]

    def observations(self) -> list[Observation]:
        rows = self._read("SELECT record FROM events ORDER BY sequence")
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
