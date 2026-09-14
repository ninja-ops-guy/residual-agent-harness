"""Fault injection hooks for evaluation runs.

Faults are injected per-task with seeded RNG so runs are reproducible
(T10-R4). A FaultInjector wraps a task execution: backends call
``inject`` before running a task; a returned Fault MUST be surfaced in
the TaskResult's ``fault`` field so the stats pipeline can separate
fault-affected runs from clean runs.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

FAULT_KINDS = ("bad_config", "missing_dependency", "timeout", "adversarial_input")


@dataclass(frozen=True)
class Fault:
    kind: str
    detail: str

    def __post_init__(self) -> None:
        if self.kind not in FAULT_KINDS:
            raise ValueError(f"unknown fault kind: {self.kind}")


@dataclass(frozen=True)
class FaultSpec:
    kind: str
    probability: float  # 0..1, probability per task
    detail: str = ""


class FaultInjector:
    """Seeded, reproducible per-task fault injection."""

    def __init__(self, specs: Sequence[FaultSpec] = (), seed: int = 0):
        self._specs: Tuple[FaultSpec, ...] = tuple(specs)
        for spec in self._specs:
            if spec.kind not in FAULT_KINDS:
                raise ValueError(f"unknown fault kind: {spec.kind}")
            if not 0.0 <= spec.probability <= 1.0:
                raise ValueError("fault probability must be in [0, 1]")
        self._seed = seed

    @property
    def specs(self) -> Tuple[FaultSpec, ...]:
        return self._specs

    def rng_for(self, task_id: str, repeat: int) -> random.Random:
        # Derive a deterministic per-(task, repeat) stream from the seed so
        # injection does not depend on iteration order.
        return random.Random(f"{self._seed}:{task_id}:{repeat}")

    def inject(self, task_id: str, repeat: int) -> Optional[Fault]:
        """Return the fault to apply to this task run, or None."""
        rng = self.rng_for(task_id, repeat)
        for spec in self._specs:
            if rng.random() < spec.probability:
                return Fault(kind=spec.kind, detail=spec.detail or f"injected {spec.kind}")
        return None


def standard_faults(probability: float = 0.05) -> List[FaultSpec]:
    """Default injection mix used by the evaluation harness."""
    return [
        FaultSpec(kind="bad_config", probability=probability, detail="syntactically invalid harness config"),
        FaultSpec(kind="missing_dependency", probability=probability, detail="required tool not installed"),
        FaultSpec(kind="timeout", probability=probability / 2, detail="provider timeout"),
        FaultSpec(kind="adversarial_input", probability=probability / 2, detail="prompt-injection attempt in log data"),
    ]
