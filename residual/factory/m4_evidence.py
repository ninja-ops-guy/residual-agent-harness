"""Receipt-backed M4 scheduler readiness and deterministic integration planning.

This module deliberately stops before mutating the project checkout. It consumes only
locally verified M3 WorkerReceipts, derives scheduler readiness from the approved task
DAG, validates dependency receipt bindings, and produces a deterministic integration
plan with conservative overlap detection. Project mutation, accumulated verification,
and final IntegrationReceipt issuance remain a separate trusted stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from residual.core import digest

from .evidence_bus import EvidenceBus
from .evidence_receipts import WorkerReceipt
from .models import ExecutionPlan


class M4EvidenceError(RuntimeError):
    pass


ObservationSink = Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class ReadyDagSnapshot:
    plan_hash: str
    completed_tasks: tuple[str, ...]
    ready_tasks: tuple[str, ...]
    blocked_tasks: tuple[str, ...]
    independence_fraction: float
    receipt_hashes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "factory-m4-ready-dag-v1",
            "plan_hash": self.plan_hash,
            "completed_tasks": list(self.completed_tasks),
            "ready_tasks": list(self.ready_tasks),
            "blocked_tasks": list(self.blocked_tasks),
            "independence_fraction": self.independence_fraction,
            "receipt_hashes": list(self.receipt_hashes),
        }

    @property
    def snapshot_hash(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True)
class IntegrationConflict:
    path: str
    receipt_hashes: tuple[str, ...]
    artifact_hashes: tuple[str | None, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "receipt_hashes": list(self.receipt_hashes),
            "artifact_hashes": list(self.artifact_hashes),
        }


@dataclass(frozen=True)
class PlannedArtifact:
    path: str
    sha256: str | None
    deleted: bool
    source_receipt_hashes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "deleted": self.deleted,
            "source_receipt_hashes": list(self.source_receipt_hashes),
        }


@dataclass(frozen=True)
class EvidenceIntegrationPlan:
    execution_plan_hash: str
    ordered_receipt_hashes: tuple[str, ...]
    ordered_task_ids: tuple[str, ...]
    artifacts: tuple[PlannedArtifact, ...]
    conflicts: tuple[IntegrationConflict, ...]

    @property
    def integration_eligible(self) -> bool:
        return not self.conflicts

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "factory-m4-evidence-integration-plan-v1",
            "execution_plan_hash": self.execution_plan_hash,
            "ordered_receipt_hashes": list(self.ordered_receipt_hashes),
            "ordered_task_ids": list(self.ordered_task_ids),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "integration_eligible": self.integration_eligible,
        }

    @property
    def plan_hash(self) -> str:
        return digest(self.to_dict())


class ReceiptBackedM4:
    """Consume signed M3 evidence for scheduler and integration decisions.

    The caller supplies the Station public key used by the EvidenceBus. Every receipt
    is re-verified locally through `EvidenceBus.consumable`; stale receipts therefore
    fail closed unless they already carry explicit human stale approval in M3.
    """

    def __init__(
        self,
        plan: ExecutionPlan,
        bus: EvidenceBus,
        *,
        station_public_key: bytes,
        observe: ObservationSink | None = None,
    ) -> None:
        if not isinstance(plan, ExecutionPlan):
            raise M4EvidenceError("M4 requires an ExecutionPlan")
        if not isinstance(bus, EvidenceBus):
            raise M4EvidenceError("M4 requires an EvidenceBus")
        self.plan = plan
        self.bus = bus
        self.station_public_key = station_public_key
        self.observe = observe
        self._tasks = {task.id: task for task in plan.tasks}

    def _emit(self, event: str, **payload: object) -> None:
        if self.observe is not None:
            self.observe({"event": event, "component": "factory-m4-evidence", **payload})

    def _receipts(self, receipt_hashes: Sequence[str]) -> tuple[WorkerReceipt, ...]:
        if len(set(receipt_hashes)) != len(receipt_hashes):
            raise M4EvidenceError("duplicate M3 receipt hash")
        receipts = tuple(
            self.bus.consumable(value, station_public_key=self.station_public_key)
            for value in receipt_hashes
        )
        for receipt in receipts:
            if receipt.execution_plan_hash != self.plan.graph_hash:
                raise M4EvidenceError("receipt belongs to another ExecutionPlan")
            if receipt.task_id not in self._tasks:
                raise M4EvidenceError("receipt task is absent from ExecutionPlan")
        by_task: dict[str, WorkerReceipt] = {}
        for receipt in receipts:
            if receipt.task_id in by_task:
                raise M4EvidenceError("multiple consumable receipts supplied for one task")
            by_task[receipt.task_id] = receipt
        return receipts

    def ready_dag(self, receipt_hashes: Sequence[str]) -> ReadyDagSnapshot:
        receipts = self._receipts(receipt_hashes)
        completed = {receipt.task_id for receipt in receipts}
        remaining = [task for task in self.plan.tasks if task.id not in completed]
        ready = sorted(task.id for task in remaining if set(task.depends_on) <= completed)
        blocked = sorted(task.id for task in remaining if task.id not in set(ready))
        independence = (len(ready) / len(remaining)) if remaining else 1.0
        snapshot = ReadyDagSnapshot(
            plan_hash=self.plan.graph_hash,
            completed_tasks=tuple(sorted(completed)),
            ready_tasks=tuple(ready),
            blocked_tasks=tuple(blocked),
            independence_fraction=independence,
            receipt_hashes=tuple(sorted(receipt.receipt_hash for receipt in receipts)),
        )
        self._emit(
            "M4SchedulerSnapshot",
            snapshot_hash=snapshot.snapshot_hash,
            ready_tasks=list(snapshot.ready_tasks),
            blocked_tasks=list(snapshot.blocked_tasks),
            independence_fraction=snapshot.independence_fraction,
        )
        return snapshot

    def integration_plan(self, receipt_hashes: Sequence[str]) -> EvidenceIntegrationPlan:
        receipts = self._receipts(receipt_hashes)
        by_task = {receipt.task_id: receipt for receipt in receipts}
        supplied_tasks = set(by_task)

        # A supplied receipt is integration-eligible only when every task dependency
        # is represented by a supplied, locally consumable receipt and every receipt's
        # parent hashes bind exactly those dependency receipts.
        for task_id, receipt in by_task.items():
            task = self._tasks[task_id]
            missing = set(task.depends_on) - supplied_tasks
            if missing:
                raise M4EvidenceError(f"receipt set omits task dependencies for {task_id}")
            expected_parents = {by_task[dep].receipt_hash for dep in task.depends_on}
            if set(receipt.parent_receipts) != expected_parents:
                raise M4EvidenceError(f"receipt parent bindings do not match task dependencies for {task_id}")

        unresolved = set(supplied_tasks)
        ordered_tasks: list[str] = []
        while unresolved:
            ready = sorted(
                task_id for task_id in unresolved
                if set(self._tasks[task_id].depends_on) <= set(ordered_tasks)
            )
            if not ready:
                raise M4EvidenceError("receipt dependency order cannot be resolved")
            ordered_tasks.extend(ready)
            unresolved.difference_update(ready)

        ordered_receipts = [by_task[task_id] for task_id in ordered_tasks]
        paths: dict[str, list[tuple[str, str | None, bool]]] = {}
        for receipt in ordered_receipts:
            for artifact in receipt.artifacts:
                paths.setdefault(artifact.path, []).append(
                    (receipt.receipt_hash, artifact.sha256, artifact.deleted)
                )

        artifacts: list[PlannedArtifact] = []
        conflicts: list[IntegrationConflict] = []
        for path in sorted(paths):
            values = paths[path]
            states = {(sha, deleted) for _, sha, deleted in values}
            receipt_ids = tuple(receipt for receipt, _, _ in values)
            if len(states) > 1:
                conflicts.append(IntegrationConflict(
                    path=path,
                    receipt_hashes=receipt_ids,
                    artifact_hashes=tuple(sha for _, sha, _ in values),
                ))
                continue
            sha, deleted = next(iter(states))
            artifacts.append(PlannedArtifact(
                path=path,
                sha256=sha,
                deleted=deleted,
                source_receipt_hashes=receipt_ids,
            ))

        result = EvidenceIntegrationPlan(
            execution_plan_hash=self.plan.graph_hash,
            ordered_receipt_hashes=tuple(receipt.receipt_hash for receipt in ordered_receipts),
            ordered_task_ids=tuple(ordered_tasks),
            artifacts=tuple(artifacts),
            conflicts=tuple(conflicts),
        )
        self._emit(
            "M4IntegrationPlan",
            integration_plan_hash=result.plan_hash,
            receipt_count=len(result.ordered_receipt_hashes),
            conflict_count=len(result.conflicts),
            integration_eligible=result.integration_eligible,
        )
        if result.conflicts:
            self._emit(
                "M4IntegrationConflict",
                integration_plan_hash=result.plan_hash,
                paths=[conflict.path for conflict in result.conflicts],
                action="hitl_required",
            )
        return result
