from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from residual.core import ContractError, identifier

from .models import ExecutionPlan, FactoryTask, Requirement


@dataclass(frozen=True)
class CompileResult:
    plan: ExecutionPlan | None
    questions: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.plan is not None and not self.questions


class RequirementCompiler:
    """Compile a structured intent document into a canonical execution plan.

    Model-assisted drafting can happen before this boundary. This compiler is the
    deterministic validator/canonicalizer: ambiguity is surfaced, never guessed.
    """

    def compile(self, document: dict[str, Any]) -> CompileResult:
        if not isinstance(document, dict):
            raise ContractError("factory input must be an object")
        allowed = {"intent", "requirements", "tasks"}
        if set(document) - allowed:
            raise ContractError("unknown factory input keys")

        questions: list[str] = []
        intent = document.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            questions.append("What is the project intent or desired outcome?")

        raw_requirements = document.get("requirements")
        if not isinstance(raw_requirements, list) or not raw_requirements:
            questions.append("What requirements must the project satisfy?")
            return CompileResult(None, tuple(questions))

        requirements: list[Requirement] = []
        seen_req: set[str] = set()
        for index, item in enumerate(raw_requirements, start=1):
            if not isinstance(item, dict):
                raise ContractError("requirement entries must be objects")
            req_id = item.get("id")
            if not isinstance(req_id, str):
                questions.append(f"Requirement {index} needs a stable id.")
                continue
            identifier(req_id)
            if req_id in seen_req:
                raise ContractError("duplicate requirement id")
            seen_req.add(req_id)
            statement = item.get("statement")
            acceptance = item.get("acceptance")
            if not isinstance(statement, str) or not statement.strip():
                questions.append(f"What exactly must {req_id} require?")
                continue
            if not isinstance(acceptance, list) or not acceptance or any(not isinstance(x, str) or not x.strip() for x in acceptance):
                questions.append(f"What observable acceptance criteria prove {req_id} is complete?")
                continue
            depends_on = item.get("depends_on", [])
            if not isinstance(depends_on, list) or any(not isinstance(x, str) for x in depends_on):
                raise ContractError("requirement depends_on must be an array of ids")
            requirements.append(Requirement(req_id, statement.strip(), tuple(x.strip() for x in acceptance), tuple(depends_on)))

        if questions:
            return CompileResult(None, tuple(questions))

        req_ids = {r.id for r in requirements}
        for req in requirements:
            missing = set(req.depends_on) - req_ids
            if missing:
                raise ContractError(f"unknown requirement dependency: {sorted(missing)[0]}")

        raw_tasks = document.get("tasks")
        if raw_tasks is None:
            tasks = self._derive_tasks(requirements)
        else:
            if not isinstance(raw_tasks, list) or not raw_tasks:
                raise ContractError("tasks must be a nonempty array when supplied")
            tasks = self._parse_tasks(raw_tasks, req_ids)

        plan = ExecutionPlan(intent=intent.strip(), requirements=tuple(requirements), tasks=tuple(tasks))
        return CompileResult(plan)

    @staticmethod
    def _derive_tasks(requirements: list[Requirement]) -> list[FactoryTask]:
        req_to_task = {req.id: f"task.{req.id}" for req in requirements}
        return [
            FactoryTask(
                id=req_to_task[req.id],
                description=req.statement,
                requirement_ids=(req.id,),
                depends_on=tuple(req_to_task[parent] for parent in req.depends_on),
            )
            for req in sorted(requirements, key=lambda x: x.id)
        ]

    @staticmethod
    def _parse_tasks(raw_tasks: list[dict[str, Any]], req_ids: set[str]) -> list[FactoryTask]:
        tasks: list[FactoryTask] = []
        for item in raw_tasks:
            if not isinstance(item, dict):
                raise ContractError("task entries must be objects")
            allowed = {"id", "description", "requirement_ids", "depends_on", "swarm"}
            if set(item) - allowed:
                raise ContractError("unknown factory task keys")
            requirement_ids = item.get("requirement_ids")
            if not isinstance(requirement_ids, list) or not requirement_ids or any(not isinstance(x, str) for x in requirement_ids):
                raise ContractError("factory task requirement_ids must be a nonempty array")
            if set(requirement_ids) - req_ids:
                raise ContractError("factory task references unknown requirement")
            depends_on = item.get("depends_on", [])
            if not isinstance(depends_on, list) or any(not isinstance(x, str) for x in depends_on):
                raise ContractError("factory task depends_on must be an array")
            tasks.append(
                FactoryTask(
                    id=item["id"],
                    description=item["description"],
                    requirement_ids=tuple(requirement_ids),
                    depends_on=tuple(depends_on),
                    swarm=item.get("swarm"),
                )
            )
        return tasks
