"""RUN-R7: abort/cancel propagation to active async operations within a budget.

``CancellationController.abort`` cancels every tracked task and waits up to
the configured budget. Outcomes are deterministic:

- all tasks cancelled within budget -> ``cancelled=True``
- any task still running at budget expiry -> report records the survivor and
  ``cancelled=False`` (fail-closed: callers must not treat the abort as
  complete)
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CancellationBudget:
    budget_s: float

    def __post_init__(self):
        if self.budget_s <= 0:
            raise ValueError("cancellation budget must be positive")


@dataclass(frozen=True)
class CancellationReport:
    cancelled: bool
    propagated: int
    survived: tuple[str, ...] = ()
    reason: str = ""
    outcomes: tuple[tuple[str, str], ...] = field(default_factory=tuple)


class CancellationController:
    """Tracks active asyncio tasks and propagates abort within a budget."""

    def __init__(self, budget: CancellationBudget):
        self._budget = budget
        self._tasks: dict[str, asyncio.Task] = {}

    def track(self, task: asyncio.Task, *, name: str | None = None) -> asyncio.Task:
        key = name or task.get_name()
        self._tasks[key] = task
        task.add_done_callback(lambda _t, k=key: self._tasks.pop(k, None))
        return task

    @property
    def active(self) -> tuple[str, ...]:
        return tuple(sorted(self._tasks))

    async def abort(self) -> CancellationReport:
        tasks = [(name, t) for name, t in sorted(self._tasks.items()) if not t.done()]
        for _name, t in tasks:
            t.cancel()
        if not tasks:
            return CancellationReport(cancelled=True, propagated=0, reason="no_active_operations")
        done, pending = await asyncio.wait(
            [t for _n, t in tasks], timeout=self._budget.budget_s)
        outcomes = []
        survived = []
        for name, t in tasks:
            if t in pending or not t.done():
                survived.append(name)
                outcomes.append((name, "budget_exceeded"))
            elif t.cancelled():
                outcomes.append((name, "cancelled"))
            elif t.exception() is not None:
                outcomes.append((name, f"error:{type(t.exception()).__name__}"))
            else:
                outcomes.append((name, "completed"))
        if survived:
            return CancellationReport(
                cancelled=False, propagated=len(tasks), survived=tuple(sorted(survived)),
                reason="cancellation_budget_exceeded", outcomes=tuple(outcomes))
        return CancellationReport(cancelled=True, propagated=len(tasks),
                                  reason="propagated_within_budget",
                                  outcomes=tuple(outcomes))
