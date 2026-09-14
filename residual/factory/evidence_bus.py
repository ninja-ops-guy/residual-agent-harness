"""Durable append-only M3 Evidence Bus."""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from residual.core import canonical, strict_json
from .worker_contract import WorkerContract
from .evidence_receipts import (
    ArtifactBinding, EvidenceError, StationIdentity, VerificationDecision, WorkerReceipt, _hash, _require_hash, _sha256
)

class EvidenceBus:
    def __init__(self, path: str | Path, *, observe: Callable[[dict[str, Any]], None] | None = None):
        self.path = str(path)
        if self.path == ":memory:":
            raise EvidenceError("Evidence Bus requires durable file-backed SQLite storage")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._observe = observe or (lambda event: None)
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS receipts(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_hash TEXT UNIQUE NOT NULL,
                    receipt_json TEXT UNIQUE NOT NULL,
                    task_id TEXT NOT NULL, swarm_id TEXT NOT NULL,
                    engine_name TEXT NOT NULL, verdict TEXT NOT NULL,
                    issued_at_ns INTEGER NOT NULL, supersedes TEXT,
                    queue_previous TEXT NOT NULL, queue_hash TEXT UNIQUE NOT NULL,
                    FOREIGN KEY(supersedes) REFERENCES receipts(receipt_hash));
                CREATE TABLE IF NOT EXISTS receipt_requirements(
                    receipt_hash TEXT NOT NULL, requirement_id TEXT NOT NULL,
                    PRIMARY KEY(receipt_hash, requirement_id),
                    FOREIGN KEY(receipt_hash) REFERENCES receipts(receipt_hash));
                CREATE TABLE IF NOT EXISTS receipt_artifacts(
                    receipt_hash TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT, deleted INTEGER NOT NULL,
                    PRIMARY KEY(receipt_hash,path), FOREIGN KEY(receipt_hash) REFERENCES receipts(receipt_hash));
                CREATE TABLE IF NOT EXISTS artifacts(
                    sha256 TEXT PRIMARY KEY, bytes BLOB NOT NULL, size_bytes INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS stale_approvals(
                    receipt_hash TEXT PRIMARY KEY, approved_by TEXT NOT NULL, reason TEXT NOT NULL,
                    approved_at_ns INTEGER NOT NULL,
                    FOREIGN KEY(receipt_hash) REFERENCES receipts(receipt_hash));
                CREATE TABLE IF NOT EXISTS evidence_events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_json TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS stale_approvals_no_update BEFORE UPDATE ON stale_approvals
                    BEGIN SELECT RAISE(ABORT,'immutable stale approval'); END;
                CREATE TRIGGER IF NOT EXISTS stale_approvals_no_delete BEFORE DELETE ON stale_approvals
                    BEGIN SELECT RAISE(ABORT,'immutable stale approval'); END;
                CREATE TRIGGER IF NOT EXISTS receipts_no_update BEFORE UPDATE ON receipts
                    BEGIN SELECT RAISE(ABORT,'append-only receipt'); END;
                CREATE TRIGGER IF NOT EXISTS receipts_no_delete BEFORE DELETE ON receipts
                    BEGIN SELECT RAISE(ABORT,'append-only receipt'); END;
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, isolation_level=None, timeout=1)
        try:
            db.execute("PRAGMA foreign_keys=ON"); db.execute("PRAGMA synchronous=FULL")
            yield db
        finally:
            db.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK"); raise

    @staticmethod
    def _event_value(event: str, **data: Any) -> dict[str, Any]:
        return {"event": event, "component": "factory-evidence-bus", "time_ns": time.time_ns(), **data}

    def _append_event(self, db: sqlite3.Connection, value: dict[str, Any]) -> None:
        db.execute("INSERT INTO evidence_events(event_json) VALUES (?)", (canonical(value),))

    def _emit(self, event: str, **data: Any) -> None:
        value = self._event_value(event, **data)
        with self._tx() as db:
            self._append_event(db, value)
        self._observe(value)

    def observations(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT event_json FROM evidence_events ORDER BY sequence").fetchall()
        return [strict_json(row[0]) for row in rows]

    def append(self, receipt: WorkerReceipt, artifact_bytes: dict[str, bytes]) -> None:
        if receipt.overall_verdict != "pass":
            raise EvidenceError("non-passing receipt cannot enter Evidence Bus")
        expected = {a.path: a for a in receipt.artifacts if not a.deleted}
        if set(artifact_bytes) != set(expected):
            raise EvidenceError("artifact byte set differs from receipt")
        for path, data in artifact_bytes.items():
            if not isinstance(data, bytes) or _sha256(data) != expected[path].sha256 or len(data) != expected[path].size_bytes:
                raise EvidenceError("artifact bytes do not match receipt")
        with self._tx() as db:
            if receipt.supersedes is not None:
                old = db.execute("SELECT task_id FROM receipts WHERE receipt_hash=?", (receipt.supersedes,)).fetchone()
                if old is None or old[0] != receipt.task_id:
                    raise EvidenceError("superseded receipt missing or belongs to another task")
            for parent in receipt.parent_receipts:
                if db.execute("SELECT 1 FROM receipts WHERE receipt_hash=?", (parent,)).fetchone() is None:
                    raise EvidenceError("parent receipt missing")
            for path, data in artifact_bytes.items():
                sha = expected[path].sha256
                row = db.execute("SELECT bytes,size_bytes FROM artifacts WHERE sha256=?", (sha,)).fetchone()
                if row is None:
                    db.execute("INSERT INTO artifacts VALUES (?,?,?)", (sha, data, len(data)))
                elif row[0] != data or row[1] != len(data):
                    raise EvidenceError("content-address collision or corrupt artifact store")
            text = canonical(receipt.to_dict())
            tail = db.execute("SELECT queue_hash FROM receipts ORDER BY sequence DESC LIMIT 1").fetchone()
            previous = tail[0] if tail else "0" * 64
            queue_hash = _hash({"schema": "factory-evidence-queue-v1", "previous": previous,
                                "receipt_hash": receipt.receipt_hash})
            db.execute("INSERT INTO receipts(receipt_hash,receipt_json,task_id,swarm_id,engine_name,verdict,issued_at_ns,supersedes,queue_previous,queue_hash) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (receipt.receipt_hash, text, receipt.task_id, receipt.swarm_id, receipt.engine_name,
                        receipt.overall_verdict, receipt.issued_at_ns, receipt.supersedes, previous, queue_hash))
            for req, met in receipt.requirements_met:
                if met:
                    db.execute("INSERT INTO receipt_requirements VALUES (?,?)", (receipt.receipt_hash, req))
            for artifact in receipt.artifacts:
                db.execute("INSERT INTO receipt_artifacts VALUES (?,?,?,?)",
                           (receipt.receipt_hash, artifact.path, artifact.sha256, int(artifact.deleted)))
            emitted = [self._event_value("WorkerReceiptIssued", receipt_hash=receipt.receipt_hash,
                       task_id=receipt.task_id, swarm_id=receipt.swarm_id)]
            emitted += [self._event_value("ArtifactStored", receipt_hash=receipt.receipt_hash,
                        artifact_hash=a.sha256, path=a.path) for a in receipt.artifacts if not a.deleted]
            for value in emitted:
                self._append_event(db, value)
        for value in emitted:
            self._observe(value)

    def verify_queue(self) -> dict[str, Any]:
        previous = "0" * 64
        count = 0
        with self._connect() as db:
            rows = db.execute("SELECT receipt_hash,queue_previous,queue_hash FROM receipts ORDER BY sequence").fetchall()
        for receipt_hash, recorded_previous, recorded_hash in rows:
            expected = _hash({"schema": "factory-evidence-queue-v1", "previous": previous,
                              "receipt_hash": receipt_hash})
            if recorded_previous != previous or recorded_hash != expected:
                raise EvidenceError("Evidence Bus receipt queue integrity failure")
            previous = recorded_hash; count += 1
        return {"receipts": count, "queue_root": previous}

    def get(self, receipt_hash: str) -> WorkerReceipt:
        _require_hash(receipt_hash, "receipt hash")
        with self._connect() as db:
            row = db.execute("SELECT receipt_json FROM receipts WHERE receipt_hash=?", (receipt_hash,)).fetchone()
        if row is None:
            raise EvidenceError("receipt not found")
        return WorkerReceipt.from_dict(strict_json(row[0]))

    def is_stale(self, receipt_hash: str) -> bool:
        _require_hash(receipt_hash, "receipt hash")
        with self._connect() as db:
            rows = db.execute("SELECT receipt_json FROM receipts").fetchall()
        receipts = [WorkerReceipt.from_dict(strict_json(x[0])) for x in rows]
        superseded = {r.supersedes for r in receipts if r.supersedes}
        by_hash = {r.receipt_hash: r for r in receipts}
        seen, stack = set(), [receipt_hash]
        while stack:
            current = stack.pop()
            if current in seen: continue
            seen.add(current)
            if current in superseded: return True
            value = by_hash.get(current)
            if value is None: raise EvidenceError("receipt graph references missing receipt")
            stack.extend(value.parent_receipts)
        return False

    def approve_stale(self, receipt_hash: str, *, approved_by: str, reason: str) -> None:
        if not all(isinstance(x, str) and x.strip() for x in (approved_by, reason)):
            raise EvidenceError("stale approval identity and reason required")
        if not self.is_stale(receipt_hash):
            raise EvidenceError("receipt is not stale")
        with self._tx() as db:
            try:
                db.execute("INSERT INTO stale_approvals VALUES (?,?,?,?)",
                           (receipt_hash, approved_by.strip(), reason.strip(), time.time_ns()))
            except sqlite3.IntegrityError as exc:
                raise EvidenceError("stale receipt approval already exists") from exc
        self._emit("StaleReceiptApproved", receipt_hash=receipt_hash, approved_by=approved_by.strip())

    def consumable(self, receipt_hash: str, *, station_public_key: bytes) -> WorkerReceipt:
        receipt = self.get(receipt_hash)
        if not StationIdentity.verify(receipt, station_public_key):
            raise EvidenceError("Station signature invalid")
        with self._connect() as db:
            for artifact in receipt.artifacts:
                if artifact.deleted: continue
                row = db.execute("SELECT bytes,size_bytes FROM artifacts WHERE sha256=?", (artifact.sha256,)).fetchone()
                if row is None or len(row[0]) != artifact.size_bytes or _sha256(row[0]) != artifact.sha256:
                    raise EvidenceError("artifact store integrity failure")
            approved = db.execute("SELECT 1 FROM stale_approvals WHERE receipt_hash=?", (receipt_hash,)).fetchone()
        if self.is_stale(receipt_hash) and approved is None:
            raise EvidenceError("stale receipt requires explicit human approval")
        return receipt

    def admit_dependencies(self, contract: WorkerContract, receipt_hashes: tuple[str, ...], *,
                           station_public_key: bytes) -> tuple[WorkerReceipt, ...]:
        """Return only locally verified receipts matching the worker's declared dependencies."""
        if len(set(receipt_hashes)) != len(receipt_hashes):
            raise EvidenceError("duplicate dependency receipt")
        receipts = tuple(self.consumable(h, station_public_key=station_public_key) for h in receipt_hashes)
        if {r.task_id for r in receipts} != set(contract.dependencies):
            raise EvidenceError("dependency receipts do not match WorkerContract dependencies")
        if any(r.execution_plan_hash != contract.execution_plan_hash for r in receipts):
            raise EvidenceError("dependency receipt belongs to another ExecutionPlan")
        self._emit("EvidenceQueryExecuted", query="dependency-admission", task_id=contract.task_id,
                   result_count=len(receipts))
        return tuple(sorted(receipts, key=lambda r: r.task_id))

    def artifact(self, receipt_hash: str, path: str, *, station_public_key: bytes) -> bytes:
        receipt = self.consumable(receipt_hash, station_public_key=station_public_key)
        matches = [a for a in receipt.artifacts if a.path == path]
        if len(matches) != 1 or matches[0].deleted:
            raise EvidenceError("artifact path not available in receipt")
        with self._connect() as db:
            data = db.execute("SELECT bytes FROM artifacts WHERE sha256=?", (matches[0].sha256,)).fetchone()[0]
        self._emit("EvidenceQueryExecuted", receipt_hash=receipt_hash, artifact_hash=matches[0].sha256,
                   query="artifact")
        return data

    def query(self, *, task_id: str | None = None, requirement_id: str | None = None,
              artifact_hash: str | None = None, engine_name: str | None = None,
              verification_status: str | None = None, swarm_id: str | None = None,
              start_ns: int | None = None, end_ns: int | None = None) -> list[WorkerReceipt]:
        clauses, args = [], []
        if task_id is not None: clauses.append("r.task_id=?"); args.append(task_id)
        if engine_name is not None: clauses.append("r.engine_name=?"); args.append(engine_name)
        if verification_status is not None: clauses.append("r.verdict=?"); args.append(verification_status)
        if swarm_id is not None: clauses.append("r.swarm_id=?"); args.append(swarm_id)
        if start_ns is not None: clauses.append("r.issued_at_ns>=?"); args.append(start_ns)
        if end_ns is not None: clauses.append("r.issued_at_ns<=?"); args.append(end_ns)
        joins = ""
        if requirement_id is not None:
            joins += " JOIN receipt_requirements q ON q.receipt_hash=r.receipt_hash"
            clauses.append("q.requirement_id=?"); args.append(requirement_id)
        if artifact_hash is not None:
            _require_hash(artifact_hash, "artifact hash")
            joins += " JOIN receipt_artifacts a ON a.receipt_hash=r.receipt_hash"
            clauses.append("a.sha256=?"); args.append(artifact_hash)
        sql = "SELECT DISTINCT r.receipt_json FROM receipts r" + joins
        if clauses: sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY r.sequence"
        with self._connect() as db:
            rows = db.execute(sql, args).fetchall()
        self._emit("EvidenceQueryExecuted", query="receipt-index", result_count=len(rows))
        return [WorkerReceipt.from_dict(strict_json(x[0])) for x in rows]


from .station_issuer import FactoryStationIssuer

__all__ = ["ArtifactBinding", "EvidenceBus", "EvidenceError", "FactoryStationIssuer", "StationIdentity", "VerificationDecision", "WorkerReceipt"]
