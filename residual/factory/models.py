from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from residual.core import ContractError, digest, identifier, strict_json, canonical


@dataclass(frozen=True)
class Requirement:
    id: str
    statement: str
    acceptance: tuple[str, ...]
    depends_on: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.id)
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ContractError("requirement statement must be nonempty")
        if not self.acceptance or any(not isinstance(x, str) or not x.strip() for x in self.acceptance):
            raise ContractError("requirement acceptance must contain nonempty criteria")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ContractError("duplicate requirement dependency")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "acceptance": list(self.acceptance),
            "depends_on": list(self.depends_on),
        }


@dataclass(frozen=True)
class FactoryTask:
    id: str
    description: str
    requirement_ids: tuple[str, ...]
    depends_on: tuple[str, ...] = ()
    swarm: str | None = None

    def __post_init__(self):
        identifier(self.id)
        if not isinstance(self.description, str) or not self.description.strip():
            raise ContractError("factory task description must be nonempty")
        if not self.requirement_ids:
            raise ContractError("factory task must bind at least one requirement")
        if self.swarm is not None:
            identifier(self.swarm)
        if len(set(self.requirement_ids)) != len(self.requirement_ids) or len(set(self.depends_on)) != len(self.depends_on):
            raise ContractError("duplicate factory task binding or dependency")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "requirement_ids": list(self.requirement_ids),
            "depends_on": list(self.depends_on),
            "swarm": self.swarm,
        }


@dataclass(frozen=True)
class ExecutionPlan:
    intent: str
    requirements: tuple[Requirement, ...]
    tasks: tuple[FactoryTask, ...]
    schema_version: str = "factory-plan-v1"

    def __post_init__(self):
        if not isinstance(self.intent, str) or not self.intent.strip():
            raise ContractError("execution plan intent must be nonempty")
        if not self.requirements or not self.tasks:
            raise ContractError("execution plan requires requirements and tasks")
        req_ids = [r.id for r in self.requirements]
        task_ids = [t.id for t in self.tasks]
        if len(req_ids) != len(set(req_ids)) or len(task_ids) != len(set(task_ids)):
            raise ContractError("duplicate requirement or task id")
        req_set, task_set = set(req_ids), set(task_ids)
        for req in self.requirements:
            if set(req.depends_on) - req_set:
                raise ContractError("unknown requirement dependency")
        for task in self.tasks:
            if set(task.requirement_ids) - req_set or set(task.depends_on) - task_set:
                raise ContractError("unknown task requirement or dependency")
        self._assert_acyclic([(r.id, r.depends_on) for r in self.requirements], "requirement")
        self._assert_acyclic([(t.id, t.depends_on) for t in self.tasks], "task")

    @staticmethod
    def _assert_acyclic(nodes: list[tuple[str, tuple[str, ...]]], kind: str) -> None:
        remaining = {node_id: set(deps) for node_id, deps in nodes}
        resolved: set[str] = set()
        while remaining:
            ready = sorted(node_id for node_id, deps in remaining.items() if deps <= resolved)
            if not ready:
                raise ContractError(f"{kind} dependency cycle")
            for node_id in ready:
                resolved.add(node_id)
                remaining.pop(node_id)

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "intent": self.intent.strip(),
            "requirements": [r.to_dict() for r in sorted(self.requirements, key=lambda x: x.id)],
            "tasks": [t.to_dict() for t in sorted(self.tasks, key=lambda x: x.id)],
        }

    @property
    def graph_hash(self) -> str:
        return digest(self.canonical_payload())

    def to_dict(self) -> dict[str, Any]:
        value = self.canonical_payload()
        value["graph_hash"] = self.graph_hash
        return value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionPlan":
        if not isinstance(data, dict):
            raise ContractError("execution plan must be an object")
        allowed = {"schema_version", "intent", "requirements", "tasks", "graph_hash"}
        if set(data) - allowed:
            raise ContractError("unknown execution plan keys")
        reqs = tuple(
            Requirement(
                id=item["id"],
                statement=item["statement"],
                acceptance=tuple(item["acceptance"]),
                depends_on=tuple(item.get("depends_on", [])),
            )
            for item in data["requirements"]
        )
        tasks = tuple(
            FactoryTask(
                id=item["id"],
                description=item["description"],
                requirement_ids=tuple(item["requirement_ids"]),
                depends_on=tuple(item.get("depends_on", [])),
                swarm=item.get("swarm"),
            )
            for item in data["tasks"]
        )
        plan = cls(intent=data["intent"], requirements=reqs, tasks=tasks, schema_version=data.get("schema_version", "factory-plan-v1"))
        supplied = data.get("graph_hash")
        if supplied is not None and supplied != plan.graph_hash:
            raise ContractError("execution plan hash mismatch")
        return plan


@dataclass(frozen=True)
class FrozenPlan:
    graph_hash: str
    approved_by: str
    approved_at: str
    schema_version: str = "factory-approval-v1"

    @classmethod
    def approve(cls, plan: ExecutionPlan, approved_by: str) -> "FrozenPlan":
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ContractError("approved_by must be nonempty")
        return cls(
            graph_hash=plan.graph_hash,
            approved_by=approved_by.strip(),
            approved_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "graph_hash": self.graph_hash,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
        }

    def assert_matches(self, plan: ExecutionPlan) -> None:
        if self.graph_hash != plan.graph_hash:
            raise ContractError("approval does not match execution plan")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FrozenPlan":
        return cls(
            graph_hash=data["graph_hash"],
            approved_by=data["approved_by"],
            approved_at=data["approved_at"],
            schema_version=data.get("schema_version", "factory-approval-v1"),
        )


def load_plan_text(text: str) -> ExecutionPlan:
    return ExecutionPlan.from_dict(strict_json(text))


def dump_plan(plan: ExecutionPlan) -> str:
    return canonical(plan.to_dict())
