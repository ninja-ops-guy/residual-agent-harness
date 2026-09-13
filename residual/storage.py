"""Revalidated content-addressed cache and hash-linked run events."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .core import ContractError, canonical, digest, strict_json


class Cache:
    def __init__(self, path=":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS results (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def get(self, key):
        row = self.db.execute("SELECT value FROM results WHERE key=?", (key,)).fetchone()
        if row is None:
            return False, None
        try:
            return True, strict_json(row[0])
        except (ValueError, TypeError, RecursionError):
            return False, None

    def put(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO results VALUES (?, ?)", (key, canonical(value)))
        self.db.commit()

    def close(self):
        self.db.close()


class Ledger:
    def __init__(self):
        self.events = []
        self.head = "0" * 64

    def add(self, kind, **data):
        payload = {"seq": len(self.events), "kind": kind, "time_ns": time.time_ns(),
                   "previous": self.head, "data": data}
        self.head = digest(payload)
        self.events.append({**payload, "sha256": self.head})

    def write(self, path):
        Path(path).write_text("".join(canonical(e) + "\n" for e in self.events), encoding="utf-8")


def verify_ledger(path, expected_root=None):
    previous = "0" * 64
    events = []
    for index, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        event = strict_json(line)
        expected = event.pop("sha256")
        if event["seq"] != index or event["previous"] != previous or digest(event) != expected:
            raise ContractError(f"trace integrity mismatch at event {index}")
        previous = expected
        events.append(event)
    if not events or events[0]["kind"] != "run_started" or events[-1]["kind"] != "run_finished":
        raise ContractError("trace is empty or incomplete")
    if expected_root is not None and previous != expected_root:
        raise ContractError("trace differs from supplied root")
    return {"events": len(events), "root": previous, "externally_anchored": expected_root is not None}
