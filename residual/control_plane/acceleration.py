"""Deterministic portfolio orchestration for reducing human coordination latency.

This module is intentionally outside the Factory task scheduler. Factory/M4 remains
authoritative for task-level execution and receipt-backed integration. The acceleration
control plane operates one level above it: release scope, research-lane dependencies,
safe speculative preparation, and human authorization queues.

It never grants execution authority. It only derives what is eligible to execute,
prepare, or present to a human based on a closed manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from residual.core import ContractError, digest


SCHEMA_VERSION = "residual-acceleration-control-plane-v1"
RISK_CLASSES = frozenset({"A", "B", "C", "D"})


class Scope(str, Enum):
    REQUIRED = "required"
    POST_V1 = "post_v1"
    RESEARCH = "research"


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    HUMAN_GATE = "human_gate"
    DEFERRED = "deferred"


class DerivedStatus(str, Enum):
    COMPLETE = "complete"
    RUNNING = "running"
    FAILED = "failed"
    DEFERRED = "deferred"
    READY = "ready"
    PREP_READY = "prep_ready"
    BLOCKED = "blocked"
    OWNER_READY = "owner_ready"
    OWNER_BLOCKED = "owner_blocked"
    FROZEN = "frozen"


def _closed_keys(value: Mapping[str, object], allowed: set[str], *, where: str) -> None:
    extras = set(value) - allowed
    if extras:
        raise ContractError(f"{where} has unknown fields: {sorted(extras)}")


def _nonempty(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a nonempty string")
    return value.strip()


def _bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{field} must be boolean")
    return value


def _string_list(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ContractError(f"{field} must be an array of nonempty strings")
    if len(set(value)) != len(value):
        raise ContractError(f"{field} must not contain duplicates")
    return tuple(value)


@dataclass(frozen=True)
class Lane:
    id: str
    title: str
    benefit: str

    @classmethod
    def from_dict(cls, value: object) -> "Lane":
        if not isinstance(value, Mapping):
            raise ContractError("lane must be an object")
        _closed_keys(value, {"id", "title", "benefit"}, where="lane")
        return cls(
            id=_nonempty(value.get("id"), field="lane.id"),
            title=_nonempty(value.get("title"), field="lane.title"),
            benefit=_nonempty(value.get("benefit"), field="lane.benefit"),
        )

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "title": self.title, "benefit": self.benefit}


@dataclass(frozen=True)
class OwnerAction:
    summary: str
    approval_text: str
    evidence_digest: str
    risk_class: str
    checks_passed: bool
    independent_review_passed: bool
    unresolved_findings: int

    @classmethod
    def from_dict(cls, value: object) -> "OwnerAction":
        if not isinstance(value, Mapping):
            raise ContractError("owner_action must be an object")
        allowed = {
            "summary", "approval_text", "evidence_digest", "risk_class",
            "checks_passed", "independent_review_passed", "unresolved_findings",
        }
        _closed_keys(value, allowed, where="owner_action")
        unresolved = value.get("unresolved_findings")
        if not isinstance(unresolved, int) or isinstance(unresolved, bool) or unresolved < 0:
            raise ContractError("owner_action.unresolved_findings must be a nonnegative integer")
        evidence_digest = _nonempty(value.get("evidence_digest"), field="owner_action.evidence_digest")
        if len(evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in evidence_digest):
            raise ContractError("owner_action.evidence_digest must be a lowercase sha256 hex digest")
        risk_class = _nonempty(value.get("risk_class"), field="owner_action.risk_class")
        if risk_class not in RISK_CLASSES:
            raise ContractError("owner_action.risk_class must be one of A, B, C, D")
        return cls(
            summary=_nonempty(value.get("summary"), field="owner_action.summary"),
            approval_text=_nonempty(value.get("approval_text"), field="owner_action.approval_text"),
            evidence_digest=evidence_digest,
            risk_class=risk_class,
            checks_passed=_bool(value.get("checks_passed"), field="owner_action.checks_passed"),
            independent_review_passed=_bool(
                value.get("independent_review_passed"),
                field="owner_action.independent_review_passed",
            ),
            unresolved_findings=unresolved,
        )

    @property
    def ready(self) -> bool:
        return (
            self.checks_passed
            and self.independent_review_passed
            and self.unresolved_findings == 0
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "approval_text": self.approval_text,
            "evidence_digest": self.evidence_digest,
            "risk_class": self.risk_class,
            "checks_passed": self.checks_passed,
            "independent_review_passed": self.independent_review_passed,
            "unresolved_findings": self.unresolved_findings,
        }


@dataclass(frozen=True)
class PortfolioTask:
    id: str
    lane: str
    scope: Scope
    state: TaskState
    depends_on: tuple[str, ...]
    preparable: bool
    summary: str
    owner_action: OwnerAction | None = None

    @classmethod
    def from_dict(cls, value: object) -> "PortfolioTask":
        if not isinstance(value, Mapping):
            raise ContractError("task must be an object")
        allowed = {
            "id", "lane", "scope", "state", "depends_on", "preparable", "summary",
            "owner_action",
        }
        _closed_keys(value, allowed, where="task")
        try:
            scope = Scope(value.get("scope"))
        except (TypeError, ValueError):
            raise ContractError("task.scope is invalid") from None
        try:
            state = TaskState(value.get("state"))
        except (TypeError, ValueError):
            raise ContractError("task.state is invalid") from None
        owner_raw = value.get("owner_action")
        owner = None if owner_raw is None else OwnerAction.from_dict(owner_raw)
        if state is TaskState.HUMAN_GATE and owner is None:
            raise ContractError("human_gate task requires owner_action")
        if state is not TaskState.HUMAN_GATE and owner is not None:
            raise ContractError("owner_action is only valid for human_gate tasks")
        return cls(
            id=_nonempty(value.get("id"), field="task.id"),
            lane=_nonempty(value.get("lane"), field="task.lane"),
            scope=scope,
            state=state,
            depends_on=_string_list(value.get("depends_on", []), field="task.depends_on"),
            preparable=_bool(value.get("preparable"), field="task.preparable"),
            summary=_nonempty(value.get("summary"), field="task.summary"),
            owner_action=owner,
        )

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.id,
            "lane": self.lane,
            "scope": self.scope.value,
            "state": self.state.value,
            "depends_on": list(self.depends_on),
            "preparable": self.preparable,
            "summary": self.summary,
        }
        if self.owner_action is not None:
            result["owner_action"] = self.owner_action.to_dict()
        return result


@dataclass(frozen=True)
class PortfolioManifest:
    release_freeze: bool
    lanes: tuple[Lane, ...]
    tasks: tuple[PortfolioTask, ...]

    @classmethod
    def from_dict(cls, value: object) -> "PortfolioManifest":
        if not isinstance(value, Mapping):
            raise ContractError("manifest must be an object")
        _closed_keys(value, {"schema_version", "release_freeze", "lanes", "tasks"}, where="manifest")
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ContractError(f"manifest.schema_version must be {SCHEMA_VERSION!r}")
        release_freeze = _bool(value.get("release_freeze"), field="manifest.release_freeze")
        lanes_raw = value.get("lanes")
        tasks_raw = value.get("tasks")
        if not isinstance(lanes_raw, list) or not lanes_raw:
            raise ContractError("manifest.lanes must be a nonempty array")
        if not isinstance(tasks_raw, list) or not tasks_raw:
            raise ContractError("manifest.tasks must be a nonempty array")
        lanes = tuple(Lane.from_dict(item) for item in lanes_raw)
        tasks = tuple(PortfolioTask.from_dict(item) for item in tasks_raw)
        manifest = cls(release_freeze=release_freeze, lanes=lanes, tasks=tasks)
        manifest._validate()
        return manifest

    def _validate(self) -> None:
        lane_ids = [lane.id for lane in self.lanes]
        if len(set(lane_ids)) != len(lane_ids):
            raise ContractError("lane ids must be unique")
        task_ids = [task.id for task in self.tasks]
        if len(set(task_ids)) != len(task_ids):
            raise ContractError("task ids must be unique")
        known_lanes = set(lane_ids)
        known_tasks = set(task_ids)
        by_id = {task.id: task for task in self.tasks}
        for task in self.tasks:
            if task.lane not in known_lanes:
                raise ContractError(f"task {task.id} references unknown lane {task.lane}")
            if task.id in task.depends_on:
                raise ContractError(f"task {task.id} cannot depend on itself")
            missing = set(task.depends_on) - known_tasks
            if missing:
                raise ContractError(f"task {task.id} references unknown dependencies: {sorted(missing)}")
            if task.state is TaskState.RUNNING:
                incomplete = [dep for dep in task.depends_on if by_id[dep].state is not TaskState.COMPLETE]
                if incomplete:
                    raise ContractError(f"running task {task.id} has incomplete dependencies: {incomplete}")
                if self.release_freeze and task.scope is not Scope.REQUIRED:
                    raise ContractError(f"running task {task.id} violates release freeze")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ContractError(f"task dependency cycle includes {task_id}")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dep in by_id[task_id].depends_on:
                visit(dep)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in task_ids:
            visit(task_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "release_freeze": self.release_freeze,
            "lanes": [lane.to_dict() for lane in self.lanes],
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @property
    def manifest_hash(self) -> str:
        return digest(self.to_dict())


class AccelerationConductor:
    """Derive portfolio readiness without crossing execution or human authority gates."""

    def __init__(self, manifest: PortfolioManifest):
        if not isinstance(manifest, PortfolioManifest):
            raise ContractError("AccelerationConductor requires a PortfolioManifest")
        self.manifest = manifest
        self._tasks = {task.id: task for task in manifest.tasks}
        self._lanes = {lane.id: lane for lane in manifest.lanes}

    def _deps_complete(self, task: PortfolioTask) -> bool:
        return all(self._tasks[dep].state is TaskState.COMPLETE for dep in task.depends_on)

    def _deps_failed(self, task: PortfolioTask) -> bool:
        return any(self._tasks[dep].state is TaskState.FAILED for dep in task.depends_on)

    def _execution_allowed(self, task: PortfolioTask) -> bool:
        return not self.manifest.release_freeze or task.scope is Scope.REQUIRED

    def status_for(self, task_id: str) -> DerivedStatus:
        try:
            task = self._tasks[task_id]
        except KeyError:
            raise ContractError(f"unknown task {task_id}") from None

        if task.state is TaskState.COMPLETE:
            return DerivedStatus.COMPLETE
        if task.state is TaskState.RUNNING:
            return DerivedStatus.RUNNING
        if task.state is TaskState.FAILED:
            return DerivedStatus.FAILED
        if task.state is TaskState.DEFERRED:
            return DerivedStatus.DEFERRED

        if self._deps_failed(task):
            return DerivedStatus.BLOCKED

        deps_complete = self._deps_complete(task)

        if task.state is TaskState.HUMAN_GATE:
            if not deps_complete:
                return DerivedStatus.BLOCKED
            if not self._execution_allowed(task):
                return DerivedStatus.FROZEN
            if task.owner_action is None:
                raise ContractError(f"human gate {task.id} is missing owner_action")
            return DerivedStatus.OWNER_READY if task.owner_action.ready else DerivedStatus.OWNER_BLOCKED

        if deps_complete and self._execution_allowed(task):
            return DerivedStatus.READY
        if task.preparable:
            return DerivedStatus.PREP_READY
        if deps_complete and not self._execution_allowed(task):
            return DerivedStatus.FROZEN
        return DerivedStatus.BLOCKED

    def owner_queue(self) -> list[dict[str, object]]:
        queue: list[dict[str, object]] = []
        for task in sorted(self.manifest.tasks, key=lambda item: item.id):
            if self.status_for(task.id) is not DerivedStatus.OWNER_READY:
                continue
            if task.owner_action is None:
                raise ContractError(f"human gate {task.id} is missing owner_action")
            queue.append({
                "task_id": task.id,
                "lane": task.lane,
                "summary": task.summary,
                "risk_class": task.owner_action.risk_class,
                "evidence_digest": task.owner_action.evidence_digest,
                "approval_text": task.owner_action.approval_text,
                "checks_passed": task.owner_action.checks_passed,
                "independent_review_passed": task.owner_action.independent_review_passed,
                "unresolved_findings": task.owner_action.unresolved_findings,
            })
        return queue

    def ready_work(self) -> dict[str, list[dict[str, object]]]:
        execute: list[dict[str, object]] = []
        prepare: list[dict[str, object]] = []
        for task in sorted(self.manifest.tasks, key=lambda item: item.id):
            status = self.status_for(task.id)
            item = {
                "task_id": task.id,
                "lane": task.lane,
                "scope": task.scope.value,
                "summary": task.summary,
                "depends_on": list(task.depends_on),
            }
            if status is DerivedStatus.READY:
                execute.append(item)
            elif status is DerivedStatus.PREP_READY:
                prepare.append(item)
        return {"execute": execute, "prepare": prepare}

    def lane_summary(self, lane_id: str) -> dict[str, object]:
        try:
            lane = self._lanes[lane_id]
        except KeyError:
            raise ContractError(f"unknown lane {lane_id}") from None
        tasks = [task for task in self.manifest.tasks if task.lane == lane_id]
        counts: dict[str, int] = {status.value: 0 for status in DerivedStatus}
        for task in tasks:
            counts[self.status_for(task.id).value] += 1

        if tasks and counts[DerivedStatus.COMPLETE.value] == len(tasks):
            state = "complete"
        elif counts[DerivedStatus.FAILED.value]:
            state = "attention"
        elif counts[DerivedStatus.OWNER_READY.value] or counts[DerivedStatus.OWNER_BLOCKED.value]:
            state = "human_gate"
        elif counts[DerivedStatus.RUNNING.value]:
            state = "running"
        elif counts[DerivedStatus.READY.value]:
            state = "ready"
        elif counts[DerivedStatus.PREP_READY.value]:
            state = "preparing"
        elif counts[DerivedStatus.FROZEN.value] or counts[DerivedStatus.DEFERRED.value]:
            state = "deferred"
        else:
            state = "blocked"

        return {
            "lane": lane.id,
            "title": lane.title,
            "benefit": lane.benefit,
            "state": state,
            "counts": counts,
        }

    def snapshot(self) -> dict[str, object]:
        lane_summaries = [
            self.lane_summary(lane.id)
            for lane in sorted(self.manifest.lanes, key=lambda item: item.id)
        ]
        task_status = {
            task.id: self.status_for(task.id).value
            for task in sorted(self.manifest.tasks, key=lambda item: item.id)
        }
        ready = self.ready_work()
        owner = self.owner_queue()
        snapshot = {
            "schema_version": "residual-acceleration-snapshot-v1",
            "manifest_hash": self.manifest.manifest_hash,
            "release_freeze": self.manifest.release_freeze,
            "lanes": lane_summaries,
            "task_status": task_status,
            "ready_work": ready,
            "owner_queue": owner,
        }
        snapshot["snapshot_hash"] = digest(snapshot)
        return snapshot
