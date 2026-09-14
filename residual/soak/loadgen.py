"""Load generator for the soak harness (N9-R9).

N9-R9 requires at least 1000 tasks/day; ``tasks_per_day`` is
configurable but the constructor enforces the >= 1000 floor for any
harness configured in production-soak mode (``enforce_minimum=True``).
Tests use smaller loads with the floor relaxed.
"""
from __future__ import annotations

from typing import Iterator

from .tasks import SyntheticTask, make_task

MIN_TASKS_PER_DAY = 1000


class LoadGenerator:
    def __init__(self, seed: int = 20260914, tasks_per_day: int = MIN_TASKS_PER_DAY,
                 enforce_minimum: bool = True):
        if enforce_minimum and tasks_per_day < MIN_TASKS_PER_DAY:
            raise ValueError(f"N9-R9 requires >= {MIN_TASKS_PER_DAY} tasks/day")
        if tasks_per_day < 1:
            raise ValueError("tasks_per_day must be positive")
        self.seed = seed
        self.tasks_per_day = tasks_per_day

    def tasks_for_day(self, day: int) -> Iterator[SyntheticTask]:
        """Yield the deterministic task stream for a given day."""
        if day < 0:
            raise ValueError("day must be >= 0")
        for index in range(self.tasks_per_day):
            yield make_task(self.seed, day, index)
