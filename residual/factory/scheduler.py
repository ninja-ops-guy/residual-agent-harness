"""M4 dependency-aware scheduler decisions; execution remains delegated to the runtime."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

from .models import ExecutionPlan


@dataclass(frozen=True, slots=True)
class EngineCapability:
    name: str
    node: str
    locality: str
    capabilities: frozenset[str]
    cost_rank: float
    available_slots: int = 1


@dataclass(frozen=True, slots=True)
class SchedulerSnapshot:
    total_tasks: int
    independent_tasks: int
    blocked_tasks: int
    active_workers: int
    total_workers: int
    verification_queue: int
    integration_conflicts: int

    @property
    def utilization(self):
        return self.active_workers / self.total_workers if self.total_workers else 0.0

    @property
    def blocked_ratio(self):
        return self.blocked_tasks / self.total_tasks if self.total_tasks else 0.0


@dataclass(frozen=True, slots=True)
class SchedulerDecision:
    action: str
    value: Any
    reasoning: str


class FactoryScheduler:
    def __init__(self, *, observe: Callable[[dict], None] | None = None,
                 conflict_threshold=2, verify_threshold=4, max_workers=32):
        self.observe = observe or (lambda e: None)
        self.conflict_threshold = conflict_threshold
        self.verify_threshold = verify_threshold
        self.max_workers = max_workers

    def _emit(self, kind, **data):
        self.observe({"event": "SchedulerDecision", "decision": kind, **data})

    @staticmethod
    def ready(plan: ExecutionPlan, completed: set[str]) -> tuple[str, ...]:
        return tuple(sorted(t.id for t in plan.tasks
                            if t.id not in completed and set(t.depends_on) <= completed))

    @staticmethod
    def independence_fraction(plan: ExecutionPlan, completed: set[str]) -> float:
        remaining = [t for t in plan.tasks if t.id not in completed]
        if not remaining:
            return 0.0
        return len([t for t in remaining if set(t.depends_on) <= completed]) / len(remaining)

    def select_engine(self, required: set[str], engines: tuple[EngineCapability, ...]) -> EngineCapability:
        viable = [e for e in engines if e.available_slots > 0 and required <= set(e.capabilities)]
        if not viable:
            raise RuntimeError("no capable engine/node")
        viable.sort(key=lambda e: (0 if e.locality == "local" else 1,
                                   e.cost_rank, e.name, e.node))
        chosen = viable[0]
        self._emit("engine_select", engine=chosen.name, node=chosen.node,
                   reasoning="capability satisfied; local preferred, then cost/name/node")
        return chosen

    def resize(self, snapshot: SchedulerSnapshot) -> SchedulerDecision:
        if snapshot.integration_conflicts > self.conflict_threshold:
            decision = SchedulerDecision("pause_for_conflicts", snapshot.integration_conflicts,
                                         "conflicts exceeded threshold")
        elif snapshot.verification_queue > self.verify_threshold:
            decision = SchedulerDecision("add_verifier", 1,
                                         "verification queue exceeded threshold")
        elif snapshot.independent_tasks > max(1, snapshot.blocked_tasks * 2) \
                and snapshot.total_workers < self.max_workers:
            decision = SchedulerDecision("add_worker", 1,
                                         "independent work dominates blocked work")
        elif snapshot.blocked_tasks > max(1, snapshot.independent_tasks * 2) \
                and snapshot.total_workers > 1:
            decision = SchedulerDecision("release_worker", 1,
                                         "blocked work dominates independent work")
        else:
            decision = SchedulerDecision("hold", 0, "no resize threshold crossed")
        self._emit(decision.action, value=decision.value, reasoning=decision.reasoning)
        return decision

    def structural_replan(self, plan: ExecutionPlan, task_id: str,
                          failures: int) -> SchedulerDecision | None:
        downstream = {task_id}
        changed = True
        while changed:
            changed = False
            for task in plan.tasks:
                if task.id not in downstream and set(task.depends_on) & downstream:
                    downstream.add(task.id)
                    changed = True
        blocked = len(downstream) - 1
        if failures >= 3 and blocked >= 10:
            decision = SchedulerDecision(
                "replan_required", {"task_id": task_id, "downstream": blocked},
                "task failed at least 3 times and blocks at least 10 downstream tasks; compile a new approved plan")
            self._emit(decision.action, value=decision.value, reasoning=decision.reasoning)
            return decision
        return None
