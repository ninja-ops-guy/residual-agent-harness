"""Deterministic M4 scheduler intelligence over the approved task DAG."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .worker_contract import WorkerContractError


@dataclass(frozen=True, slots=True)
class SchedulerTask:
    task_id: str
    dependencies: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    failures: int = 0


@dataclass(frozen=True, slots=True)
class EngineOption:
    name: str
    capabilities: tuple[str, ...]
    cost_per_unit: float
    locality: str
    available_capacity: int

    @property
    def is_local(self) -> bool:
        return self.locality == "local"


@dataclass(frozen=True, slots=True)
class SchedulerMetrics:
    active_workers: int
    total_workers: int
    blocked_tasks: int
    total_tasks: int
    verification_queue_depth: int
    integration_conflicts: int

    @property
    def worker_utilization(self) -> float:
        return self.active_workers / self.total_workers if self.total_workers else 0.0

    @property
    def blocked_ratio(self) -> float:
        return self.blocked_tasks / self.total_tasks if self.total_tasks else 0.0


class Scheduler:
    def __init__(self, *, observe: Callable[[dict[str, Any]], None] | None = None,
                 verification_threshold: int = 4, conflict_threshold: int = 2):
        self.observe = observe or (lambda event: None)
        self.verification_threshold = verification_threshold
        self.conflict_threshold = conflict_threshold

    def _emit(self, event: str, **data: Any) -> None:
        self.observe({"event": event, "component": "factory-scheduler", **data})

    @staticmethod
    def ready_tasks(tasks: tuple[SchedulerTask, ...], completed: set[str]) -> tuple[SchedulerTask, ...]:
        ids = {task.task_id for task in tasks}
        if len(ids) != len(tasks):
            raise WorkerContractError("duplicate scheduler task")
        if any(dep not in ids and dep not in completed for task in tasks for dep in task.dependencies):
            raise WorkerContractError("scheduler dependency missing")
        return tuple(sorted((task for task in tasks
                            if task.task_id not in completed and set(task.dependencies) <= completed),
                           key=lambda task: task.task_id))

    def independence_fraction(self, tasks: tuple[SchedulerTask, ...], completed: set[str]) -> float:
        remaining = tuple(task for task in tasks if task.task_id not in completed)
        if not remaining:
            return 1.0
        return len(self.ready_tasks(tasks, completed)) / len(remaining)

    def select_engine(self, task: SchedulerTask, engines: tuple[EngineOption, ...]) -> EngineOption:
        needed = set(task.required_capabilities)
        candidates = [engine for engine in engines
                      if needed <= set(engine.capabilities) and engine.available_capacity > 0]
        if not candidates:
            raise WorkerContractError("no engine satisfies task capability/capacity")
        # Capability equality: local wins. Otherwise prefer fewer excess capabilities, then cost, then name.
        selected = sorted(candidates, key=lambda engine: (
            len(set(engine.capabilities) - needed),
            0 if engine.is_local else 1,
            engine.cost_per_unit,
            engine.name,
        ))[0]
        self._emit("SchedulerEngineSelected", task_id=task.task_id, engine=selected.name,
                   locality=selected.locality, cost=selected.cost_per_unit,
                   reasoning="capability_then_locality_then_cost")
        return selected

    def decide_resize(self, *, independent_tasks: int, metrics: SchedulerMetrics,
                      current_workers: int, current_verifiers: int) -> dict[str, Any]:
        if min(independent_tasks, current_workers, current_verifiers) < 0:
            raise WorkerContractError("scheduler counts must be non-negative")
        workers, verifiers = current_workers, current_verifiers
        paused = False
        reasons = []
        if metrics.integration_conflicts > self.conflict_threshold:
            paused = True; reasons.append("integration_conflict_threshold")
        elif independent_tasks > metrics.blocked_tasks * 2 and independent_tasks > current_workers:
            workers = min(independent_tasks, current_workers + max(1, independent_tasks // 4))
            reasons.append("independence_capacity_gap")
        elif metrics.blocked_tasks > independent_tasks * 2 and current_workers > 1:
            workers = max(1, current_workers - max(1, current_workers // 4))
            reasons.append("dependency_blocking")
        if metrics.verification_queue_depth > self.verification_threshold:
            verifiers += max(1, metrics.verification_queue_depth // self.verification_threshold)
            reasons.append("verification_queue")
        decision = {"workers": workers, "verifiers": verifiers, "paused": paused,
                    "reasoning": tuple(reasons) or ("steady_state",)}
        self._emit("SchedulerResized", previous_workers=current_workers, previous_verifiers=current_verifiers,
                   **decision)
        return decision

    def structural_replan_candidates(self, tasks: tuple[SchedulerTask, ...], completed: set[str]) -> tuple[str, ...]:
        downstream: dict[str, int] = {task.task_id: 0 for task in tasks}
        children: dict[str, list[str]] = {task.task_id: [] for task in tasks}
        by_id = {task.task_id: task for task in tasks}
        for task in tasks:
            for dep in task.dependencies:
                if dep in children:
                    children[dep].append(task.task_id)
        for root in children:
            seen, stack = set(), list(children[root])
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                stack.extend(children.get(current, ()))
            downstream[root] = len(seen)
        candidates = tuple(sorted(task.task_id for task in tasks
                                  if task.task_id not in completed and task.failures >= 3
                                  and downstream[task.task_id] >= 10))
        for task_id in candidates:
            self._emit("SchedulerReplanRequested", task_id=task_id,
                       downstream_tasks=downstream[task_id], failures=by_id[task_id].failures,
                       reasoning="structural_bottleneck")
        return candidates
