"""Minimal local frozen-workload fixture for SPEC-SWARM-OTX-003 (OTX-R6).

NOTE (integration point): Swarm A (SPEC-SWARM-EVAL-001) owns the full
versioned ``FrozenWorkload`` schema with immutable workload hash. This
module defines the *minimal* local fixture OTX needs — a deterministic,
hash-bound list of tasks spanning multiple task granularities — so the
controller can be evaluated before that schema lands. When EVAL-001's
schema is available, ``FrozenWorkloadFixture.from_eval_workload`` is the
adapter point: map its task records into :class:`Task` tuples and keep
the upstream workload hash in ``upstream_hash``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .models import Task

GRANULARITIES: Tuple[str, ...] = ("atomic", "composite", "project")


@dataclass(frozen=True)
class FrozenWorkloadFixture:
    """Deterministic, hash-bound workload over multiple granularities (OTX-R6)."""

    name: str
    version: str
    tasks: Tuple[Task, ...]
    seed: int = 0
    upstream_hash: Optional[str] = None  # set when derived from EVAL-001 schema

    @property
    def workload_hash(self) -> str:
        payload = {
            "name": self.name,
            "version": self.version,
            "seed": self.seed,
            "upstream_hash": self.upstream_hash,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "task_class": t.task_class,
                    "granularity": t.granularity,
                    "value": t.value,
                    "size": t.size,
                }
                for t in self.tasks
            ],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def granularities(self) -> Tuple[str, ...]:
        return tuple(sorted({t.granularity for t in self.tasks}))

    def task_classes(self) -> Tuple[str, ...]:
        return tuple(sorted({t.task_class for t in self.tasks}))

    def slice(self, granularity: str) -> Tuple[Task, ...]:
        return tuple(t for t in self.tasks if t.granularity == granularity)

    @classmethod
    def from_eval_workload(cls, upstream) -> "FrozenWorkloadFixture":
        """Adapter for the EVAL-001 FrozenWorkload schema (Swarm A).

        Expects an object with ``name``, ``version``, ``workload_hash`` and
        an iterable of task records exposing id/class/granularity/value/size.
        """
        tasks = tuple(
            Task(
                task_id=str(rec.task_id),
                task_class=str(rec.task_class),
                granularity=str(getattr(rec, "granularity", "atomic")),
                value=float(getattr(rec, "value", 1.0)),
                size=float(getattr(rec, "size", 1.0)),
            )
            for rec in upstream.tasks
        )
        return cls(
            name=str(upstream.name),
            version=str(upstream.version),
            tasks=tasks,
            upstream_hash=str(upstream.workload_hash),
        )


def default_fixture() -> FrozenWorkloadFixture:
    """The canonical local development fixture (frozen; do not mutate).

    Two task classes x three granularities x four replicas = 24 tasks.
    """
    tasks: List[Task] = []
    specs = [
        # (task_class, granularity, value, size)
        ("lookup", "atomic", 1.0, 0.5),
        ("lookup", "composite", 1.0, 1.0),
        ("lookup", "project", 1.0, 2.0),
        ("synthesis", "atomic", 4.0, 1.5),
        ("synthesis", "composite", 4.0, 3.0),
        ("synthesis", "project", 4.0, 6.0),
    ]
    for rep in range(4):
        for cls, gran, value, size in specs:
            tasks.append(
                Task(
                    task_id=f"{cls}-{gran}-{rep}",
                    task_class=cls,
                    granularity=gran,
                    value=value,
                    size=size,
                )
            )
    return FrozenWorkloadFixture(name="otx-dev-fixture", version="1.0.0", tasks=tuple(tasks), seed=20240513)
