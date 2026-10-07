"""Soak-state persistence for deterministic resume.

State is persisted after every completed day as JSON: the next day
index, the accumulated metrics snapshot, the red team results so far,
and the generator seed. Resuming reloads the snapshot and continues at
``next_day``; because task/fault streams are pure functions of
(seed, day, index), a resumed run reproduces an uninterrupted run's
totals exactly.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .metrics import SoakMetrics

SCHEMA_VERSION = "residual.soak.state.v1"


@dataclass
class SoakState:
    seed: int
    tasks_per_day: int
    total_days: int
    next_day: int = 0
    metrics: SoakMetrics = field(default_factory=SoakMetrics)
    red_team_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def days_completed(self) -> int:
        return self.next_day

    @property
    def complete(self) -> bool:
        return self.next_day >= self.total_days

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "seed": self.seed,
            "tasks_per_day": self.tasks_per_day,
            "total_days": self.total_days,
            "next_day": self.next_day,
            "metrics": self.metrics.to_dict(),
            "red_team_results": self.red_team_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoakState":
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported soak state schema: {data.get('schema_version')}")
        return cls(
            seed=data["seed"],
            tasks_per_day=data["tasks_per_day"],
            total_days=data["total_days"],
            next_day=data["next_day"],
            metrics=SoakMetrics.from_dict(data["metrics"]),
            red_team_results=list(data.get("red_team_results", [])),
        )

    def save(self, path: str) -> None:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
        os.replace(tmp, path)  # atomic-ish: never leave a half-written state

    @classmethod
    def load(cls, path: str) -> "SoakState":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))
