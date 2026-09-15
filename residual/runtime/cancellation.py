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
import os
import signal
from dataclasses import dataclass, field
from typing import Any


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
    process_outcomes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    descendants_clean: bool = True


class CancellationController:
    """Tracks active asyncio tasks and propagates abort within a budget."""

    def __init__(self, budget: CancellationBudget):
        self._budget = budget
        self._tasks: dict[str, asyncio.Task] = {}
        self._processes: dict[str, tuple[Any, int | None]] = {}

    def track(self, task: asyncio.Task, *, name: str | None = None) -> asyncio.Task:
        key = name or task.get_name()
        self._tasks[key] = task
        task.add_done_callback(lambda _t, k=key: self._tasks.pop(k, None))
        return task

    def track_process(self, process: Any, *, name: str | None = None,
                      process_group_id: int | None = None) -> Any:
        """Track a bounded subprocess and, optionally, its dedicated process group.

        ``process_group_id`` must name a group created specifically for the worker
        (for example by ``start_new_session=True``).  Explicit registration avoids
        ever signalling the coordinator's own process group by accident.
        """
        pid = int(getattr(process, "pid", 0) or 0)
        if pid <= 0 or not callable(getattr(process, "wait", None)):
            raise TypeError("process must expose pid and async wait()")
        if process_group_id is not None:
            process_group_id = int(process_group_id)
            if process_group_id <= 0 or process_group_id == os.getpgrp():
                raise ValueError("process group must be a dedicated positive group")
        key = name or f"pid-{pid}"
        self._processes[key] = (process, process_group_id)
        return process

    @property
    def active(self) -> tuple[str, ...]:
        tasks = [name for name, task in self._tasks.items() if not task.done()]
        processes = [name for name, (process, _pgid) in self._processes.items()
                     if getattr(process, "returncode", None) is None]
        return tuple(sorted(tasks + processes))

    @staticmethod
    def _signal_process(process: Any, process_group_id: int | None,
                        sig: signal.Signals) -> None:
        if process_group_id is not None:
            os.killpg(process_group_id, sig)
        elif sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()

    @staticmethod
    def _group_has_live_members(process_group_id: int) -> bool:
        """Return whether a POSIX group still has a non-zombie member."""
        proc_root = "/proc"
        if os.path.isdir(proc_root):
            for entry in os.scandir(proc_root):
                if not entry.name.isdigit():
                    continue
                try:
                    stat = open(f"{proc_root}/{entry.name}/stat", encoding="utf-8").read()
                    tail = stat.rsplit(")", 1)[1].split()
                    state, pgrp = tail[0], int(tail[2])
                    if pgrp == process_group_id and state != "Z":
                        return True
                except (FileNotFoundError, PermissionError, OSError, ValueError, IndexError):
                    continue
            return False
        try:
            os.killpg(process_group_id, 0)
            return True
        except ProcessLookupError:
            return False

    async def _wait_group_clean(self, process_group_id: int, deadline: float) -> bool:
        loop = asyncio.get_running_loop()
        while self._group_has_live_members(process_group_id):
            if loop.time() >= deadline:
                return False
            await asyncio.sleep(min(0.01, max(0.0, deadline - loop.time())))
        return True

    async def _stop_process(self, process: Any, process_group_id: int | None,
                            deadline: float) -> str:
        if getattr(process, "returncode", None) is not None:
            return "already_exited"
        loop = asyncio.get_running_loop()
        try:
            self._signal_process(process, process_group_id, signal.SIGTERM)
        except ProcessLookupError:
            return "already_exited"

        grace = max(0.0, min((deadline - loop.time()) / 2.0, 1.0))
        try:
            await asyncio.wait_for(asyncio.shield(process.wait()), timeout=grace)
            if process_group_id is None:
                return "terminated"
            if await self._wait_group_clean(process_group_id, deadline):
                return "terminated_group"
        except asyncio.TimeoutError:
            pass

        try:
            self._signal_process(process, process_group_id, signal.SIGKILL)
        except ProcessLookupError:
            return "terminated_group" if process_group_id is not None else "terminated"
        remaining = max(0.0, deadline - loop.time())
        try:
            await asyncio.wait_for(asyncio.shield(process.wait()), timeout=remaining)
            if process_group_id is None:
                return "killed"
            if await self._wait_group_clean(process_group_id, deadline):
                return "killed_group"
            return "budget_exceeded"
        except asyncio.TimeoutError:
            return "budget_exceeded"

    async def abort(self) -> CancellationReport:
        tasks = [(name, t) for name, t in sorted(self._tasks.items()) if not t.done()]
        processes = [(name, process, pgid)
                     for name, (process, pgid) in sorted(self._processes.items())
                     if getattr(process, "returncode", None) is None]
        for _name, t in tasks:
            t.cancel()
        if not tasks and not processes:
            return CancellationReport(cancelled=True, propagated=0, reason="no_active_operations")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._budget.budget_s
        process_results = await asyncio.gather(*(
            self._stop_process(process, pgid, deadline)
            for _name, process, pgid in processes
        )) if processes else []
        remaining = max(0.0, deadline - loop.time())
        _done, pending = await asyncio.wait(
            [t for _n, t in tasks], timeout=remaining) if tasks else (set(), set())
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
        process_outcomes = []
        for (name, _process, _pgid), result in zip(processes, process_results):
            process_outcomes.append((name, result))
            if result == "budget_exceeded":
                survived.append(name)
        descendants_clean = all(result != "budget_exceeded" for result in process_results)
        if survived:
            return CancellationReport(
                cancelled=False, propagated=len(tasks) + len(processes),
                survived=tuple(sorted(survived)), reason="cancellation_budget_exceeded",
                outcomes=tuple(outcomes), process_outcomes=tuple(process_outcomes),
                descendants_clean=descendants_clean)
        return CancellationReport(cancelled=True, propagated=len(tasks) + len(processes),
                                  reason="propagated_within_budget",
                                  outcomes=tuple(outcomes),
                                  process_outcomes=tuple(process_outcomes),
                                  descendants_clean=descendants_clean)
