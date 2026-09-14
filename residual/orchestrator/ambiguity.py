"""Ambiguity detector for compiled requirements.

ORCH-I-R9: A requirement MUST be flagged when it lacks acceptance
           criteria, lacks an owner, or lacks a measurable condition.
ORCH-I-R10: The ambiguity report MUST be deterministic for a fixed graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .requirements import RequirementGraph

MISSING_OWNER = "missing-owner"
MISSING_ACCEPTANCE = "missing-acceptance-criteria"
MISSING_MEASURABLE = "missing-measurable-condition"


@dataclass(frozen=True)
class AmbiguityFlag:
    requirement_id: str
    kind: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"requirement_id": self.requirement_id, "kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class AmbiguityReport:
    flags: tuple[AmbiguityFlag, ...]

    @property
    def has_ambiguity(self) -> bool:
        return bool(self.flags)

    def flags_for(self, requirement_id: str) -> tuple[AmbiguityFlag, ...]:
        return tuple(f for f in self.flags if f.requirement_id == requirement_id)

    def to_dict(self) -> dict[str, Any]:
        return {"flags": [f.to_dict() for f in self.flags],
                "has_ambiguity": self.has_ambiguity}


class AmbiguityDetector:
    """Flags requirements that are not independently verifiable."""

    def analyze(self, graph: RequirementGraph) -> AmbiguityReport:
        flags: list[AmbiguityFlag] = []
        for req in graph.requirements:  # sorted by id -> deterministic
            if req.owner is None:
                flags.append(AmbiguityFlag(req.requirement_id, MISSING_OWNER,
                                           "no owner assigned"))
            if not req.acceptance_criteria:
                flags.append(AmbiguityFlag(req.requirement_id, MISSING_ACCEPTANCE,
                                           "no acceptance criteria defined"))
            if req.measurable_condition is None:
                flags.append(AmbiguityFlag(req.requirement_id, MISSING_MEASURABLE,
                                           "no measurable success condition"))
        return AmbiguityReport(tuple(flags))
