"""Requirement model and requirement DAG.

ORCH-I-R4: Requirement identifiers MUST be valid identifiers and unique
           within a graph.
ORCH-I-R5: Edges MUST reference declared requirements only; a graph with
           dangling dependencies is rejected.
ORCH-I-R6: Topological ordering MUST be deterministic (Kahn's algorithm
           with a sorted ready set); cycles MUST be reported with the
           cycle path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import ContractError, identifier


def _str_tuple(values, name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ContractError(f"{name} must be a sequence of strings")
    out = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ContractError(f"{name} entries must be non-empty strings")
        out.append(value.strip())
    return tuple(out)


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    description: str
    depends_on: tuple[str, ...] = ()
    owner: str | None = None
    acceptance_criteria: tuple[str, ...] = ()
    measurable_condition: str | None = None
    files: tuple[str, ...] = ()
    external_io: bool = False

    def __post_init__(self):
        identifier(self.requirement_id)
        if not isinstance(self.description, str) or not self.description.strip():
            raise ContractError("requirement description must be a non-empty string")
        deps = _str_tuple(self.depends_on, "depends_on")
        for dep in deps:
            identifier(dep)
        dupes = sorted({d for d in deps if deps.count(d) > 1})
        if dupes:
            raise ContractError(f"duplicate dependencies: {dupes}")
        if self.requirement_id in deps:
            raise ContractError("requirement cannot depend on itself")
        object.__setattr__(self, "depends_on", tuple(sorted(deps)))
        if self.owner is not None and (not isinstance(self.owner, str) or not self.owner.strip()):
            raise ContractError("owner must be a non-empty string or None")
        object.__setattr__(self, "acceptance_criteria",
                           _str_tuple(self.acceptance_criteria, "acceptance_criteria"))
        if self.measurable_condition is not None and (
                not isinstance(self.measurable_condition, str) or not self.measurable_condition.strip()):
            raise ContractError("measurable_condition must be a non-empty string or None")
        object.__setattr__(self, "files", _str_tuple(self.files, "files"))
        if type(self.external_io) is not bool:
            raise ContractError("external_io must be a bool")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "description": self.description.strip(),
            "depends_on": list(self.depends_on),
            "owner": self.owner,
            "acceptance_criteria": list(self.acceptance_criteria),
            "measurable_condition": self.measurable_condition,
            "files": list(self.files),
            "external_io": self.external_io,
        }


class RequirementGraph:
    """Immutable DAG over Requirement nodes. Cycles are rejected at build time."""

    def __init__(self, requirements):
        reqs = tuple(requirements)
        ids = [r.requirement_id for r in reqs]
        if len(set(ids)) != len(ids):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ContractError(f"duplicate requirement ids: {dupes}")
        known = set(ids)
        for req in reqs:
            missing = [d for d in req.depends_on if d not in known]
            if missing:
                raise ContractError(
                    f"requirement {req.requirement_id} depends on unknown ids: {sorted(missing)}")
        self._nodes = {r.requirement_id: r for r in reqs}
        self.topological_order()  # fail fast on cycles

    @property
    def requirements(self) -> tuple[Requirement, ...]:
        return tuple(self._nodes[k] for k in sorted(self._nodes))

    def get(self, requirement_id: str) -> Requirement:
        identifier(requirement_id)
        return self._nodes[requirement_id]

    def __len__(self) -> int:
        return len(self._nodes)

    def _dependencies(self) -> dict[str, set[str]]:
        return {rid: set(r.depends_on) for rid, r in self._nodes.items()}

    def _dependents(self) -> dict[str, set[str]]:
        dependents: dict[str, set[str]] = {rid: set() for rid in self._nodes}
        for rid, r in self._nodes.items():
            for dep in r.depends_on:
                dependents[dep].add(rid)
        return dependents

    def dependents(self, requirement_id: str) -> tuple[str, ...]:
        identifier(requirement_id)
        if requirement_id not in self._nodes:
            raise ContractError(f"unknown requirement id {requirement_id}")
        return tuple(sorted(self._dependents()[requirement_id]))

    def find_cycle(self) -> list[str] | None:
        """Return one cycle as a path [a, b, ..., a], or None."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {rid: WHITE for rid in self._nodes}
        stack: list[str] = []

        def visit(node: str) -> list[str] | None:
            color[node] = GRAY
            stack.append(node)
            for dep in sorted(self._nodes[node].depends_on):
                if color[dep] == GRAY:
                    return stack[stack.index(dep):] + [dep]
                if color[dep] == WHITE:
                    found = visit(dep)
                    if found is not None:
                        return found
            stack.pop()
            color[node] = BLACK
            return None

        for rid in sorted(self._nodes):
            if color[rid] == WHITE:
                found = visit(rid)
                if found is not None:
                    return found
        return None

    def _require_acyclic(self):
        cycle = self.find_cycle()
        if cycle is not None:
            raise ContractError(
                "requirement graph contains a cycle: " + " -> ".join(cycle))

    def topological_order(self) -> tuple[str, ...]:
        """Deterministic Kahn's algorithm. Raises ContractError on cycles."""
        deps = self._dependencies()
        dependents = self._dependents()
        ready = sorted(rid for rid, ds in deps.items() if not ds)
        order: list[str] = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for child in sorted(dependents[node]):
                deps[child].discard(node)
                if not deps[child] and child not in order and child not in ready:
                    ready.append(child)
            ready.sort()
        if len(order) != len(self._nodes):
            self._require_acyclic()
        return tuple(order)

    def levels(self) -> tuple[tuple[str, ...], ...]:
        """BFS levels: all requirements in one level are mutually independent."""
        deps = self._dependencies()
        dependents = self._dependents()
        levels: list[tuple[str, ...]] = []
        current = sorted(rid for rid, ds in deps.items() if not ds)
        done = 0
        while current:
            levels.append(tuple(current))
            done += len(current)
            nxt: set[str] = set()
            for node in current:
                for child in dependents[node]:
                    deps[child].discard(node)
                    if not deps[child]:
                        nxt.add(child)
            current = sorted(nxt)
        if done != len(self._nodes):
            self._require_acyclic()
        return tuple(levels)

    def to_dict(self) -> dict[str, Any]:
        return {"requirements": [r.to_dict() for r in self.requirements]}
