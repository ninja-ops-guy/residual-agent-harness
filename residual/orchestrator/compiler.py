"""Requirement compiler: Intent -> requirement DAG.

ORCH-I-R7: Compilation MUST be deterministic: the same intent MUST yield
           the same requirement graph (ids, edges, and field values).
ORCH-I-R8: The default decomposition MUST produce one context requirement
           per context reference, one goal requirement depending on all
           context requirements, and one constraint requirement per
           constraint depending on the goal requirement.

Hosts may supply a custom `decompose(intent) -> Iterable[Requirement]`
callable; the compiler only validates and assembles the resulting graph.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable

from ..core import ContractError
from .intent import Intent
from .requirements import Requirement, RequirementGraph

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _slug(text: str, limit: int = 60) -> str:
    slug = _SLUG_RE.sub("-", text.strip())[:limit].strip("-.")
    if not slug or not slug[0].isalpha():
        slug = "r-" + slug
    return slug


def default_decompose(intent: Intent) -> Iterable[Requirement]:
    """Deterministic baseline decomposition of an intent."""
    reqs: list[Requirement] = []
    context_ids = []
    for index, ref in enumerate(intent.context_refs):
        rid = f"context-{index}-{_slug(ref)}"
        context_ids.append(rid)
        reqs.append(Requirement(
            requirement_id=rid,
            description=f"Load and validate context reference: {ref}",
        ))
    reqs.append(Requirement(
        requirement_id="goal",
        description=f"Satisfy goal: {intent.goal}",
        depends_on=tuple(context_ids),
    ))
    for index, constraint in enumerate(intent.constraints):
        reqs.append(Requirement(
            requirement_id=f"constraint-{index}-{_slug(constraint)}",
            description=f"Enforce constraint: {constraint}",
            depends_on=("goal",),
        ))
    return reqs


class RequirementCompiler:
    """Intent -> validated, acyclic RequirementGraph."""

    def __init__(self, decompose: Callable[[Intent], Iterable[Requirement]] | None = None):
        if decompose is not None and not callable(decompose):
            raise ContractError("decompose must be callable")
        self._decompose = decompose or default_decompose

    def compile(self, intent: Intent) -> RequirementGraph:
        if not isinstance(intent, Intent):
            raise ContractError("compile requires an Intent")
        produced = list(self._decompose(intent))
        if not produced:
            raise ContractError("decomposition produced no requirements")
        for req in produced:
            if not isinstance(req, Requirement):
                raise ContractError("decomposition must yield Requirement objects")
        return RequirementGraph(produced)

    def compile_to_dict(self, intent: Intent) -> dict[str, Any]:
        graph = self.compile(intent)
        return {
            "schema_version": "residual.orchestrator.requirements.v1",
            "intent_hash": intent.content_hash,
            "topological_order": list(graph.topological_order()),
            **graph.to_dict(),
        }
