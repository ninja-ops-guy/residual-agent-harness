"""FrozenWorkload: a frozen, content-addressed evaluation task set.

T10-R3/T10-R4: the workload definition MUST be in the repo and MUST be
reproducible. A FrozenWorkload is immutable once created; its manifest
is hash-locked: every task carries a content hash and the manifest hash
covers the ordered list of task hashes plus workload metadata. Loading a
tampered workload artifact fails verification.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

SCHEMA_VERSION = "residual.eval.frozen_workload.v1"


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkloadTask:
    """A single immutable evaluation task."""

    task_id: str
    kind: str  # e.g. "netops", "secops", "incident"
    prompt: str
    expected: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def content(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "prompt": self.prompt,
            "expected": self.expected,
            "metadata": self.metadata,
        }

    def content_hash(self) -> str:
        return _sha256(_canonical(self.content()))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkloadTask":
        return cls(
            task_id=data["task_id"],
            kind=data["kind"],
            prompt=data["prompt"],
            expected=dict(data.get("expected", {})),
            metadata=dict(data.get("metadata", {})),
        )


class FrozenWorkload:
    """An immutable, hash-locked task set.

    Instances cannot be mutated: the task tuple and manifest are fixed at
    construction and there are no mutating methods. ``verify`` recomputes
    all hashes so any tampering with a serialized artifact is detected.
    """

    __slots__ = ("_name", "_tasks", "_seed", "_manifest_hash")

    def __init__(self, name: str, tasks: Tuple[WorkloadTask, ...], seed: int):
        if not tasks:
            raise ValueError("FrozenWorkload requires at least one task")
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_tasks", tuple(tasks))
        object.__setattr__(self, "_seed", seed)
        object.__setattr__(self, "_manifest_hash", self._compute_manifest_hash())

    def __setattr__(self, key: str, value: Any) -> None:
        raise AttributeError("FrozenWorkload is immutable")

    @property
    def name(self) -> str:
        return self._name

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def tasks(self) -> Tuple[WorkloadTask, ...]:
        return self._tasks

    @property
    def manifest_hash(self) -> str:
        return self._manifest_hash

    def manifest(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self._name,
            "seed": self._seed,
            "task_count": len(self._tasks),
            "task_hashes": [t.content_hash() for t in self._tasks],
            "manifest_hash": self._manifest_hash,
        }

    def verify(self) -> bool:
        """Recompute the manifest hash and compare against the locked value."""
        return self.manifest_hash == self._compute_manifest_hash()

    def _compute_manifest_hash(self) -> str:
        manifest_body = {
            "schema_version": SCHEMA_VERSION,
            "name": self._name,
            "seed": self._seed,
            "task_count": len(self._tasks),
            "task_hashes": [t.content_hash() for t in self._tasks],
        }
        return _sha256(_canonical(manifest_body))

    # -- serialization -------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest": self.manifest(),
            "tasks": [t.content() for t in self._tasks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrozenWorkload":
        manifest = data["manifest"]
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported workload schema: {manifest.get('schema_version')}")
        tasks = tuple(WorkloadTask.from_dict(t) for t in data["tasks"])
        wl = cls(name=manifest["name"], tasks=tasks, seed=manifest["seed"])
        # Hash-locked: a tampered artifact (edited task, reordered list,
        # edited manifest_hash) fails verification here.
        if wl.manifest_hash != manifest.get("manifest_hash"):
            raise ValueError("workload manifest hash mismatch: artifact tampered or corrupt")
        if len(tasks) != manifest.get("task_count"):
            raise ValueError("workload task count mismatch")
        return wl

    @classmethod
    def from_json(cls, text: str) -> "FrozenWorkload":
        return cls.from_dict(json.loads(text))

    # -- standard synthetic suite --------------------------------------
    @classmethod
    def standard(cls, cases: int = 16, seed: int = 20260914) -> "FrozenWorkload":
        """The canonical FrozenWorkload v1 suite (NetOps/SecOps incidents)."""
        import random

        rng = random.Random(seed)
        kinds = ["netops", "secops", "incident"]
        tasks = []
        for i in range(cases):
            kind = kinds[i % len(kinds)]
            noise = rng.randint(64, 512)
            tasks.append(
                WorkloadTask(
                    task_id=f"fw1-{i:03d}",
                    kind=kind,
                    prompt=f"[{kind}] investigate alert #{1000 + i} with {noise} log lines",
                    expected={"checks_passed": True, "max_steps": 12 + noise // 64},
                    metadata={"noise_lines": noise, "difficulty": rng.choice(["low", "medium", "high"])},
                )
            )
        return cls(name="FrozenWorkload-v1", tasks=tuple(tasks), seed=seed)
