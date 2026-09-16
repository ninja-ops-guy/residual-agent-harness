"""RUN-R7: abort/cancel propagation to active async operations within a budget.

``CancellationController.abort`` cancels every tracked task and terminates every
tracked worker process group within the configured budget. Outcomes are
fail-closed: any surviving task or live process-group member makes the report
``cancelled=False``.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import signal
from typing import Any


@dataclass(frozen=True)
class CancellationBudget:
    budget_s: float

    def __post_init__(self):
        if not math.isfinite(self.budget_s) or self.budget_s <= 0:
            raise ValueError("cancellation budget must be positive")


@dataclass(frozen=True)
class CancellationReport:
    cancelled: bool
    propagated: int
    survived: tuple[str, ...] = ()
    reason: str = ""
    outcomes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    descendants_clean: bool = True
    process_outcomes: tuple[tuple[str, str], ...] = field(default_factory=tuple)


class CancellationController:
    """Tracks active asyncio tasks and explicitly-owned worker process groups."""

    def __init__(self, budget: CancellationBudget):
        self._budget = budget
        self._tasks: dict[str, asyncio.Task] = {}
        self._processes: dict[str, tuple[Any, int | None]] = {}

    def track(self, task: asyncio.Task, *, name: str | None = None) -> asyncio.Task:
        key = name or task.get_name()
        existing = self._tasks.get(key)
        if existing is not None and existing is not task and not existing.done():
            raise ValueError(f"task name already tracked: {key}")
        self._tasks[key] = task

        def forget(completed):
            if self._tasks.get(key) is completed:
                self._tasks.pop(key, None)

        task.add_done_callback(forget)
        return task

    def track_process(self, process: Any, *, name: str,
                      process_group_id: int | None = None) -> Any:
        """Track one worker process and, when supplied, its owned POSIX group.

        The caller must create the process group/session; this controller never
        guesses group ownership from a PID. A group id is therefore explicit
        authority to signal that group during abort.
        """
        if not name:
            raise ValueError("process name is required")
        if name in self._processes and self._processes[name] != (process, process_group_id):
            raise ValueError(f"process name already tracked: {name}")
        if process_group_id is not None and (not isinstance(process_group_id, int) or process_group_id <= 0):
            raise ValueError("process_group_id must be a positive integer")
        self._processes[name] = (process, process_group_id)
        return process

    @property
    def active(self) -> tuple[str, ...]:
        return tuple(sorted(self._tasks))

    @property
    def active_processes(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, (process, pgid) in self._processes.items()
                            if self._process_active(process, pgid)))

    def _process_active(self, process: Any, pgid: int | None) -> bool:
        # Leader exit does not discharge ownership of its surviving children.
        return (getattr(process, "returncode", None) is None or
                (pgid is not None and os.name == "posix" and
                 self._group_has_live_members(pgid)))

    @staticmethod
    def _group_has_live_members(pgid: int) -> bool:
        """Return True only for non-zombie members when /proc is available."""
        proc = Path("/proc")
        if proc.is_dir():
            try:
                # Some containers mount a /proc view from a different PID
                # namespace. Its group numbers cannot qualify our process API.
                own_stat = (proc / "self" / "stat").read_text()
                own_fields = own_stat.rsplit(")", 1)[1].split()
                if (int(own_stat.split(" ", 1)[0]) != os.getpid() or
                        int(own_fields[2]) != os.getpgrp()):
                    raise ValueError("proc namespace differs from process API")
                incomplete = False
                for entry in proc.iterdir():
                    if not entry.name.isdigit():
                        continue
                    try:
                        remainder = (entry / "stat").read_text().rsplit(")", 1)[1].split()
                        state, group = remainder[0], int(remainder[2])
                    except FileNotFoundError:
                        # A process disappearing during the scan is harmless.
                        continue
                    except (OSError, ValueError, IndexError):
                        incomplete = True
                        continue
                    if group == pgid and state != "Z":
                        return True
                if not incomplete:
                    return False
            except (OSError, ValueError, IndexError):
                pass
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def _signal_group(pgid: int, sig: signal.Signals) -> bool:
        try:
            os.killpg(pgid, sig)
            return True
        except ProcessLookupError:
            return False

    async def abort(self) -> CancellationReport:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._budget.budget_s
        tasks = [(name, task) for name, task in sorted(self._tasks.items()) if not task.done()]
        processes = [(name, process, pgid) for name, (process, pgid) in sorted(self._processes.items())
                     if self._process_active(process, pgid)]

        for _name, task in tasks:
            task.cancel()

        process_modes: dict[str, str] = {}
        for name, process, pgid in processes:
            if pgid is not None and os.name == "posix":
                self._signal_group(pgid, signal.SIGTERM)
                process_modes[name] = "terminated_group"
            else:
                try:
                    process.terminate()
                    process_modes[name] = "terminated_process"
                except ProcessLookupError:
                    process_modes[name] = "already_exited"

        if processes:
            await asyncio.sleep(min(0.05, max(0.0, deadline - loop.time())))

        for name, process, pgid in processes:
            if pgid is not None and os.name == "posix":
                if self._group_has_live_members(pgid):
                    if self._signal_group(pgid, signal.SIGKILL):
                        process_modes[name] = "killed_group"
            elif getattr(process, "returncode", None) is None:
                try:
                    process.kill()
                    process_modes[name] = "killed_process"
                except ProcessLookupError:
                    pass

        task_wait = [task for _name, task in tasks]
        process_waiters = {
            name: asyncio.create_task(process.wait(), name=f"cancel-wait:{name}")
            for name, process, _pgid in processes
        }
        all_waiters = task_wait + list(process_waiters.values())
        pending: set[asyncio.Future] = set()
        if all_waiters:
            remaining = max(0.0, deadline - loop.time())
            _done, pending = await asyncio.wait(all_waiters, timeout=remaining)

        outcomes: list[tuple[str, str]] = []
        survived: list[str] = []
        for name, task in tasks:
            if task in pending or not task.done():
                survived.append(name)
                outcomes.append((name, "budget_exceeded"))
            elif task.cancelled():
                outcomes.append((name, "cancelled"))
            elif task.exception() is not None:
                outcomes.append((name, f"error:{type(task.exception()).__name__}"))
            else:
                outcomes.append((name, "completed"))

        process_outcomes: list[tuple[str, str]] = []
        for name, process, pgid in processes:
            waiter = process_waiters[name]
            group_clean = True
            if pgid is not None and os.name == "posix":
                while loop.time() < deadline and self._group_has_live_members(pgid):
                    await asyncio.sleep(min(0.02, max(0.0, deadline - loop.time())))
                group_clean = not self._group_has_live_members(pgid)
            if waiter in pending or getattr(process, "returncode", None) is None or not group_clean:
                survived.append(name)
                process_outcomes.append((name, "budget_exceeded"))
            else:
                process_outcomes.append((name, process_modes.get(name, "completed")))
            if not waiter.done():
                waiter.cancel()

        descendants_clean = not any(outcome == "budget_exceeded" for _name, outcome in process_outcomes)
        propagated = len(tasks) + len(processes)
        if survived:
            return CancellationReport(
                cancelled=False,
                propagated=propagated,
                survived=tuple(sorted(set(survived))),
                reason="cancellation_budget_exceeded",
                outcomes=tuple(outcomes),
                descendants_clean=descendants_clean,
                process_outcomes=tuple(process_outcomes),
            )
        if propagated == 0:
            return CancellationReport(cancelled=True, propagated=0, reason="no_active_operations")
        return CancellationReport(
            cancelled=True,
            propagated=propagated,
            reason="propagated_within_budget",
            outcomes=tuple(outcomes),
            descendants_clean=descendants_clean,
            process_outcomes=tuple(process_outcomes),
        )
