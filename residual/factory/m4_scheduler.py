"""Observed M4 scheduler intelligence over the receipt-backed Ready DAG.

The scheduler is host-owned and deterministic.  It selects capable execution
locations, measures bottlenecks, proposes bounded capacity changes, and emits a
new frozen-plan candidate when a structural bottleneck requires decomposition.
It never mutates an approved ExecutionPlan in place.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from residual.assurance.market import MarketProfile, VerifiedComputeMarket
from residual.core import digest, identifier

from .m4_evidence import ReadyDagSnapshot
from .models import ExecutionPlan, FactoryTask


class M4SchedulerError(RuntimeError):
    pass


ObservationSink = Callable[[dict[str, object]], None]


@dataclass(frozen=True, slots=True)
class SchedulerNode:
    node_id: str
    engine_id: str
    locality: str
    capabilities: frozenset[str]
    capacity: int
    active_slots: int = 0
    healthy: bool = True

    def __post_init__(self) -> None:
        identifier(self.node_id)
        if not isinstance(self.engine_id, str) or not self.engine_id.strip():
            raise M4SchedulerError("scheduler node engine_id required")
        if self.locality not in {"local", "cloud"}:
            raise M4SchedulerError("scheduler node locality must be local or cloud")
        if not self.capabilities or any(not isinstance(x, str) or not x.strip() for x in self.capabilities):
            raise M4SchedulerError("scheduler node capabilities required")
        if type(self.capacity) is not int or self.capacity < 1:
            raise M4SchedulerError("scheduler node capacity must be positive")
        if type(self.active_slots) is not int or not 0 <= self.active_slots <= self.capacity:
            raise M4SchedulerError("scheduler node active_slots outside capacity")
        if type(self.healthy) is not bool:
            raise M4SchedulerError("scheduler node healthy must be boolean")

    @property
    def available_slots(self) -> int:
        return self.capacity - self.active_slots if self.healthy else 0


@dataclass(frozen=True, slots=True)
class EnginePlacement:
    task_id: str
    capability: str
    engine_id: str
    node_id: str
    locality: str
    cost_per_task: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "capability": self.capability,
            "engine_id": self.engine_id,
            "node_id": self.node_id,
            "locality": self.locality,
            "cost_per_task": self.cost_per_task,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SchedulerMeasurements:
    ready_dag_hash: str
    worker_utilization: float
    blocked_task_ratio: float
    verification_queue_depth: int
    integration_conflict_rate: float
    independent_tasks: int
    blocked_tasks: int
    active_workers: int
    total_workers: int
    integration_conflicts: int
    integration_attempts: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "factory-m4-scheduler-measurements-v1",
            "ready_dag_hash": self.ready_dag_hash,
            "worker_utilization": self.worker_utilization,
            "blocked_task_ratio": self.blocked_task_ratio,
            "verification_queue_depth": self.verification_queue_depth,
            "integration_conflict_rate": self.integration_conflict_rate,
            "independent_tasks": self.independent_tasks,
            "blocked_tasks": self.blocked_tasks,
            "active_workers": self.active_workers,
            "total_workers": self.total_workers,
            "integration_conflicts": self.integration_conflicts,
            "integration_attempts": self.integration_attempts,
        }

    @property
    def measurement_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SchedulerCapacity:
    workers: int
    verifiers: int
    min_workers: int = 1
    max_workers: int = 32
    min_verifiers: int = 1
    max_verifiers: int = 16

    def __post_init__(self) -> None:
        values = (self.workers, self.verifiers, self.min_workers, self.max_workers,
                  self.min_verifiers, self.max_verifiers)
        if any(type(value) is not int or value < 1 for value in values):
            raise M4SchedulerError("scheduler capacity values must be positive integers")
        if not self.min_workers <= self.workers <= self.max_workers:
            raise M4SchedulerError("worker capacity outside configured bounds")
        if not self.min_verifiers <= self.verifiers <= self.max_verifiers:
            raise M4SchedulerError("verifier capacity outside configured bounds")


@dataclass(frozen=True, slots=True)
class SchedulerAction:
    action: str
    resource: str
    before: int
    after: int
    reason: str
    measurement_hash: str

    def __post_init__(self) -> None:
        if self.action not in {"resize", "pause"}:
            raise M4SchedulerError("invalid scheduler action")
        if self.resource not in {"workers", "verifiers", "integration"}:
            raise M4SchedulerError("invalid scheduler resource")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise M4SchedulerError("scheduler action reason required")

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "resource": self.resource,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "measurement_hash": self.measurement_hash,
        }


@dataclass(frozen=True, slots=True)
class StructuralReplanProposal:
    blocking_task_id: str
    downstream_tasks: tuple[str, ...]
    failure_count: int
    replacement_task_ids: tuple[str, ...]
    source_plan_hash: str
    replacement_plan: ExecutionPlan
    reason: str

    @property
    def replacement_plan_hash(self) -> str:
        return self.replacement_plan.graph_hash

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "factory-m4-structural-replan-v1",
            "blocking_task_id": self.blocking_task_id,
            "downstream_tasks": list(self.downstream_tasks),
            "failure_count": self.failure_count,
            "replacement_task_ids": list(self.replacement_task_ids),
            "source_plan_hash": self.source_plan_hash,
            "replacement_plan_hash": self.replacement_plan_hash,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SchedulerPolicy:
    imbalance_ratio: float = 2.0
    verification_queue_threshold: int = 4
    integration_conflict_threshold: int = 2
    worker_step: int = 1
    verifier_step: int = 1
    structural_downstream_threshold: int = 10
    structural_failure_threshold: int = 3
    structural_parts: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.imbalance_ratio, (int, float)) or self.imbalance_ratio <= 1:
            raise M4SchedulerError("imbalance_ratio must be greater than one")
        integers = (
            self.verification_queue_threshold,
            self.integration_conflict_threshold,
            self.worker_step,
            self.verifier_step,
            self.structural_downstream_threshold,
            self.structural_failure_threshold,
            self.structural_parts,
        )
        if any(type(value) is not int or value < 1 for value in integers):
            raise M4SchedulerError("scheduler policy thresholds must be positive integers")
        if self.structural_parts < 2:
            raise M4SchedulerError("structural replan must create at least two subtasks")


class M4AdaptiveScheduler:
    def __init__(self, plan: ExecutionPlan, market: VerifiedComputeMarket,
                 nodes: Sequence[SchedulerNode], *, policy: SchedulerPolicy | None = None,
                 observe: ObservationSink | None = None) -> None:
        if not isinstance(plan, ExecutionPlan):
            raise M4SchedulerError("scheduler requires ExecutionPlan")
        if not isinstance(market, VerifiedComputeMarket):
            raise M4SchedulerError("scheduler requires VerifiedComputeMarket")
        if not nodes:
            raise M4SchedulerError("scheduler requires at least one node")
        if len({node.node_id for node in nodes}) != len(nodes):
            raise M4SchedulerError("duplicate scheduler node")
        self.plan = plan
        self.market = market
        self.nodes = tuple(nodes)
        self.policy = policy or SchedulerPolicy()
        self.observe = observe
        self._tasks = {task.id: task for task in plan.tasks}

    def _emit(self, event: str, **payload: object) -> None:
        if self.observe is not None:
            self.observe({"event": event, "component": "factory-m4-scheduler", **payload})

    def _market_profile(self, engine_id: str) -> MarketProfile:
        profile = self.market.profiles.get(engine_id)
        if profile is None or profile.retired or profile.availability <= 0:
            raise M4SchedulerError("scheduler node references unavailable market engine")
        return profile

    def select_engine(self, task_id: str, capability: str, *,
                      max_privacy_class: int = 99,
                      max_latency_ms: float | None = None) -> EnginePlacement:
        if task_id not in self._tasks:
            raise M4SchedulerError("unknown scheduler task")
        if not isinstance(capability, str) or not capability.strip():
            raise M4SchedulerError("task capability required")
        candidates: list[tuple[tuple[object, ...], SchedulerNode, MarketProfile]] = []
        local_capable = False
        local_available = False
        for node in self.nodes:
            if not node.healthy or capability not in node.capabilities:
                continue
            profile = self._market_profile(node.engine_id)
            if capability not in profile.capabilities:
                continue
            if profile.privacy_class > max_privacy_class:
                continue
            if max_latency_ms is not None and profile.latency_ms > max_latency_ms:
                continue
            if node.locality == "local":
                local_capable = True
            if node.available_slots <= 0:
                continue
            if node.locality == "local":
                local_available = True
            # Capability is already equal. Locality is therefore authoritative
            # before cost; cost and latency break ties within the same locality.
            key = (
                0 if node.locality == "local" else 1,
                profile.cost_per_task,
                profile.latency_ms,
                node.active_slots / node.capacity,
                node.engine_id,
                node.node_id,
            )
            candidates.append((key, node, profile))
        if not candidates:
            raise LookupError(f"no available node supports {capability}")
        _, node, profile = min(candidates, key=lambda item: item[0])
        if node.locality == "local":
            reason = "local_capability_equal_preferred"
        elif local_capable and not local_available:
            reason = "cloud_selected_local_capacity_exhausted"
        else:
            reason = "cloud_selected_for_capability_gap"
        placement = EnginePlacement(
            task_id=task_id,
            capability=capability,
            engine_id=node.engine_id,
            node_id=node.node_id,
            locality=node.locality,
            cost_per_task=profile.cost_per_task,
            reason=reason,
        )
        self._emit("M4EngineSelected", **placement.to_dict())
        return placement

    def measure(self, snapshot: ReadyDagSnapshot, *, total_workers: int,
                active_workers: int, verification_queue_depth: int,
                integration_conflicts: int, integration_attempts: int) -> SchedulerMeasurements:
        if snapshot.plan_hash != self.plan.graph_hash:
            raise M4SchedulerError("Ready DAG belongs to another ExecutionPlan")
        integers = (total_workers, active_workers, verification_queue_depth,
                    integration_conflicts, integration_attempts)
        if any(type(value) is not int or value < 0 for value in integers):
            raise M4SchedulerError("scheduler measurements must be nonnegative integers")
        if total_workers < 1 or active_workers > total_workers:
            raise M4SchedulerError("invalid worker utilization measurement")
        if integration_conflicts > integration_attempts:
            raise M4SchedulerError("integration conflicts exceed attempts")
        remaining = len(snapshot.ready_tasks) + len(snapshot.blocked_tasks)
        blocked_ratio = len(snapshot.blocked_tasks) / remaining if remaining else 0.0
        conflict_rate = integration_conflicts / integration_attempts if integration_attempts else 0.0
        result = SchedulerMeasurements(
            ready_dag_hash=snapshot.snapshot_hash,
            worker_utilization=active_workers / total_workers,
            blocked_task_ratio=blocked_ratio,
            verification_queue_depth=verification_queue_depth,
            integration_conflict_rate=conflict_rate,
            independent_tasks=len(snapshot.ready_tasks),
            blocked_tasks=len(snapshot.blocked_tasks),
            active_workers=active_workers,
            total_workers=total_workers,
            integration_conflicts=integration_conflicts,
            integration_attempts=integration_attempts,
        )
        self._emit("M4SchedulerMeasurements", measurement_hash=result.measurement_hash,
                   **result.to_dict())
        return result

    def resize(self, measurements: SchedulerMeasurements,
               capacity: SchedulerCapacity) -> tuple[SchedulerCapacity, tuple[SchedulerAction, ...]]:
        if not isinstance(measurements, SchedulerMeasurements) or not isinstance(capacity, SchedulerCapacity):
            raise M4SchedulerError("typed scheduler measurements and capacity required")
        actions: list[SchedulerAction] = []
        workers, verifiers = capacity.workers, capacity.verifiers

        if measurements.integration_conflicts > self.policy.integration_conflict_threshold:
            action = SchedulerAction(
                "pause", "integration", 0, 0,
                "integration_conflicts_above_threshold_human_required",
                measurements.measurement_hash,
            )
            actions.append(action)
            self._emit("M4SchedulerPaused", **action.to_dict())
            # Conflict pressure is a hard stop; do not expand execution while the
            # integration boundary is explicitly waiting for a human.
            return capacity, tuple(actions)

        if measurements.verification_queue_depth > self.policy.verification_queue_threshold:
            new_value = min(capacity.max_verifiers, verifiers + self.policy.verifier_step)
            if new_value != verifiers:
                action = SchedulerAction(
                    "resize", "verifiers", verifiers, new_value,
                    "verification_queue_above_threshold",
                    measurements.measurement_hash,
                )
                actions.append(action)
                verifiers = new_value
                self._emit("M4SchedulerResize", **action.to_dict())

        independent = measurements.independent_tasks
        blocked = measurements.blocked_tasks
        if independent > max(1, blocked) * self.policy.imbalance_ratio:
            target = min(capacity.max_workers, workers + self.policy.worker_step, max(workers, independent))
            if target != workers:
                action = SchedulerAction(
                    "resize", "workers", workers, target,
                    "independent_tasks_dominate_blocked_tasks",
                    measurements.measurement_hash,
                )
                actions.append(action)
                workers = target
                self._emit("M4SchedulerResize", **action.to_dict())
        elif blocked > max(1, independent) * self.policy.imbalance_ratio:
            target = max(capacity.min_workers, workers - self.policy.worker_step)
            if target != workers:
                action = SchedulerAction(
                    "resize", "workers", workers, target,
                    "blocked_tasks_dominate_independent_tasks",
                    measurements.measurement_hash,
                )
                actions.append(action)
                workers = target
                self._emit("M4SchedulerResize", **action.to_dict())

        return SchedulerCapacity(
            workers=workers,
            verifiers=verifiers,
            min_workers=capacity.min_workers,
            max_workers=capacity.max_workers,
            min_verifiers=capacity.min_verifiers,
            max_verifiers=capacity.max_verifiers,
        ), tuple(actions)

    def _downstream(self, task_id: str) -> tuple[str, ...]:
        direct: dict[str, set[str]] = {task.id: set() for task in self.plan.tasks}
        for task in self.plan.tasks:
            for dependency in task.depends_on:
                direct[dependency].add(task.id)
        found: set[str] = set()
        pending = list(direct[task_id])
        while pending:
            current = pending.pop()
            if current in found:
                continue
            found.add(current)
            pending.extend(direct[current] - found)
        return tuple(sorted(found))

    def structural_replan(self, failure_counts: Mapping[str, int]) -> tuple[StructuralReplanProposal, ...]:
        for task_id, count in failure_counts.items():
            if task_id not in self._tasks or type(count) is not int or count < 0:
                raise M4SchedulerError("invalid scheduler failure count")
        proposals: list[StructuralReplanProposal] = []
        for task in sorted(self.plan.tasks, key=lambda item: item.id):
            downstream = self._downstream(task.id)
            failures = failure_counts.get(task.id, 0)
            if (len(downstream) < self.policy.structural_downstream_threshold
                    or failures < self.policy.structural_failure_threshold):
                continue
            replacement_ids = tuple(
                f"{task.id}.part{index:02d}"
                for index in range(1, self.policy.structural_parts + 1)
            )
            replacement_tasks: list[FactoryTask] = []
            for original in self.plan.tasks:
                if original.id == task.id:
                    for index, replacement_id in enumerate(replacement_ids, 1):
                        replacement_tasks.append(FactoryTask(
                            id=replacement_id,
                            description=(
                                f"Part {index}/{len(replacement_ids)} of decomposed task: "
                                f"{task.description}"
                            ),
                            requirement_ids=task.requirement_ids,
                            depends_on=task.depends_on,
                            swarm=task.swarm,
                        ))
                    continue
                dependencies: list[str] = []
                for dependency in original.depends_on:
                    if dependency == task.id:
                        dependencies.extend(replacement_ids)
                    else:
                        dependencies.append(dependency)
                replacement_tasks.append(FactoryTask(
                    id=original.id,
                    description=original.description,
                    requirement_ids=original.requirement_ids,
                    depends_on=tuple(dependencies),
                    swarm=original.swarm,
                ))
            replacement_plan = ExecutionPlan(
                intent=self.plan.intent,
                requirements=self.plan.requirements,
                tasks=tuple(replacement_tasks),
            )
            reason = (
                f"task blocks {len(downstream)} downstream tasks and has failed "
                f"{failures} times; decompose into {len(replacement_ids)} subtasks"
            )
            proposal = StructuralReplanProposal(
                blocking_task_id=task.id,
                downstream_tasks=downstream,
                failure_count=failures,
                replacement_task_ids=replacement_ids,
                source_plan_hash=self.plan.graph_hash,
                replacement_plan=replacement_plan,
                reason=reason,
            )
            proposals.append(proposal)
            self._emit("M4StructuralReplan", **proposal.to_dict())
        return tuple(proposals)
