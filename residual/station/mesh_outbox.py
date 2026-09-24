"""Crash-durable worker-side outbox/inbox for SPEC-SC-MESH-001."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from residual.core import ContractError, canonical


class MeshOutbox:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS outbox(
                operation_id TEXT PRIMARY KEY,
                digest TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt REAL NOT NULL DEFAULT 0,
                receipt TEXT,
                terminal_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS inbox(
                project TEXT NOT NULL,
                seq INTEGER NOT NULL,
                digest TEXT NOT NULL,
                applied_at REAL NOT NULL,
                PRIMARY KEY(project,seq)
            );
            CREATE TABLE IF NOT EXISTS cursors(
                project TEXT PRIMARY KEY,
                seq INTEGER NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            columns = {r["name"] for r in c.execute("PRAGMA table_info(outbox)").fetchall()}
            if "terminal_reason" not in columns:
                c.execute("ALTER TABLE outbox ADD COLUMN terminal_reason TEXT")

    def connect(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _digest(value):
        return hashlib.sha256(canonical(value).encode()).hexdigest()

    def enqueue(self, operation_id, value):
        digest = self._digest(value)
        now = time.time()
        with self.connect() as c:
            row = c.execute("SELECT digest FROM outbox WHERE operation_id=?", (operation_id,)).fetchone()
            if row:
                if row["digest"] != digest:
                    raise ContractError("Outbox operation ID conflicts with different bytes")
                return
            c.execute("INSERT INTO outbox(operation_id,digest,value,created_at,next_attempt) VALUES(?,?,?,?,?)",
                      (operation_id, digest, canonical(value), now, now))

    def due(self, *, now=None, limit=50):
        current = time.time() if now is None else now
        with self.connect() as c:
            rows = c.execute(
                "SELECT * FROM outbox WHERE receipt IS NULL AND terminal_reason IS NULL AND next_attempt<=? "
                "ORDER BY created_at LIMIT ?", (current, limit)
            ).fetchall()
        return [{"operation_id": r["operation_id"], "attempts": r["attempts"],
                 "value": json.loads(r["value"]), "created_at": r["created_at"]} for r in rows]

    def fail(self, operation_id, *, base_delay=1.0, cap=60.0):
        with self.connect() as c:
            row = c.execute("SELECT attempts FROM outbox WHERE operation_id=?", (operation_id,)).fetchone()
            if not row:
                raise ContractError("Outbox operation was not found")
            attempts = row["attempts"] + 1
            # deterministic bounded jitter from operation id: [0.875, 1.125)
            h = int(hashlib.sha256(operation_id.encode()).hexdigest()[:8], 16)
            jitter = 0.875 + (h / 0xFFFFFFFF) * 0.25
            delay = min(cap, base_delay * (2 ** min(attempts - 1, 10))) * jitter
            c.execute("UPDATE outbox SET attempts=?,next_attempt=? WHERE operation_id=?",
                      (attempts, time.time() + delay, operation_id))
            return {"attempts": attempts, "delay_s": delay}

    def exhaust(self, operation_id, reason="retry_exhausted"):
        with self.connect() as c:
            row = c.execute("SELECT receipt,terminal_reason FROM outbox WHERE operation_id=?", (operation_id,)).fetchone()
            if not row:
                raise ContractError("Outbox operation was not found")
            if row["receipt"] is not None:
                raise ContractError("Acknowledged outbox operation cannot be exhausted")
            if row["terminal_reason"] is None:
                c.execute("UPDATE outbox SET terminal_reason=? WHERE operation_id=?", (str(reason)[:200], operation_id))
        return {"operation_id": operation_id, "terminal_reason": reason}

    def ack(self, operation_id, receipt):
        with self.connect() as c:
            row = c.execute("SELECT receipt FROM outbox WHERE operation_id=?", (operation_id,)).fetchone()
            if not row:
                raise ContractError("Outbox operation was not found")
            if row["receipt"] is not None:
                old = json.loads(row["receipt"])
                if canonical(old) != canonical(receipt):
                    raise ContractError("Outbox receipt changed for an acknowledged operation")
                return old
            c.execute("UPDATE outbox SET receipt=? WHERE operation_id=?",
                      (canonical(receipt), operation_id))
        return receipt

    def pending(self):
        with self.connect() as c:
            return c.execute("SELECT count(*) n FROM outbox WHERE receipt IS NULL AND terminal_reason IS NULL").fetchone()["n"]

    def oldest_age_s(self):
        with self.connect() as c:
            row = c.execute("SELECT min(created_at) t FROM outbox WHERE receipt IS NULL AND terminal_reason IS NULL").fetchone()
        return max(0.0, time.time() - row["t"]) if row["t"] is not None else 0.0

    def apply_inbox(self, project, seq, envelope, apply):
        """Atomically record dedup state/cursor around an idempotent local apply callback.

        The callback must write only to the same SQLite connection if it mutates
        durable local state. A pure callback is also valid. External effects must
        use their own effect ledger and are intentionally not abstracted here.
        """
        digest = self._digest(envelope)
        with self.connect() as c:
            row = c.execute("SELECT digest FROM inbox WHERE project=? AND seq=?", (project, seq)).fetchone()
            if row:
                if row["digest"] != digest:
                    raise ContractError("Inbox sequence conflicts with different bytes")
                return False
            apply(c)
            now = time.time()
            c.execute("INSERT INTO inbox(project,seq,digest,applied_at) VALUES(?,?,?,?)",
                      (project, seq, digest, now))
            c.execute(
                "INSERT INTO cursors(project,seq,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(project) DO UPDATE SET seq=max(seq,excluded.seq),updated_at=excluded.updated_at",
                (project, seq, now),
            )
            return True

    def cursor(self, project):
        with self.connect() as c:
            row = c.execute("SELECT seq FROM cursors WHERE project=?", (project,)).fetchone()
        return row["seq"] if row else 0
