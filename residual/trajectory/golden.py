"""Explicit golden promotion with compare-and-swap; no auto-learning of baselines."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3

from ..core import ContractError, identifier
from ..receipts import hash_id
from .recorder import TrajectoryRecorder, TrajectoryRegressionEngine


class GoldenTrajectoryStore:
    def __init__(self, path: str | Path, recorder: TrajectoryRecorder):
        self.path, self.recorder = Path(path), recorder
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS golden(name TEXT PRIMARY KEY, hash TEXT NOT NULL)")

    def promote(self, name: str, trajectory_hash: str, *, expected: str | None = None) -> None:
        identifier(name)
        hash_id(trajectory_hash)
        trace = self.recorder.load(trajectory_hash)
        if trace is None or trace.get("outcome") != "success":
            raise ContractError("golden promotion requires an intact successful trajectory")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT hash FROM golden WHERE name=?", (name,)).fetchone()
            if (previous[0] if previous else None) != expected:
                raise ContractError("golden changed; explicit expected hash is required")
            db.execute("INSERT OR REPLACE INTO golden VALUES (?,?)", (name, trajectory_hash))

    def entries(self) -> dict[str, str]:
        with closing(sqlite3.connect(self.path)) as db:
            return dict(db.execute("SELECT name,hash FROM golden ORDER BY name"))

    def compare(self, name: str, trajectory) -> tuple[bool, str]:
        identifier(name)
        target = self.entries().get(name)
        if target is None:
            return False, "golden_not_configured"
        return TrajectoryRegressionEngine(self.recorder).evaluate_regression(trajectory, target)
