"""Intent schema for the orchestration track (Swarm 4 / track I).

ORCH-I-R1: An Intent MUST carry a non-empty goal string.
ORCH-I-R2: Constraints and context references MUST be unique, non-empty
           strings, stored in canonical (sorted) order so that equal
           intents compare equal regardless of input ordering.
ORCH-I-R3: An Intent MUST be immutable and content-addressed; the
           identity hash MUST be derivable from the intent alone (no
           clocks, no randomness).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import ContractError, canonical, digest


def _unique_sorted(values, name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ContractError(f"{name} must be a sequence of strings")
    cleaned = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ContractError(f"{name} entries must be non-empty strings")
        value = value.strip()
        if value not in seen:
            seen.add(value)
            cleaned.append(value)
    return tuple(sorted(cleaned))


@dataclass(frozen=True)
class Intent:
    """Validated, immutable orchestration intent."""

    goal: str
    constraints: tuple[str, ...] = ()
    context_refs: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ContractError("intent goal must be a non-empty string")
        object.__setattr__(self, "goal", self.goal.strip())
        object.__setattr__(self, "constraints", _unique_sorted(self.constraints, "constraints"))
        object.__setattr__(self, "context_refs", _unique_sorted(self.context_refs, "context_refs"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.orchestrator.intent.v1",
            "goal": self.goal,
            "constraints": list(self.constraints),
            "context_refs": list(self.context_refs),
        }

    @property
    def content_hash(self) -> str:
        """SHA-256 over the canonical JSON form. Deterministic by construction."""
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Intent":
        if not isinstance(data, dict) or "goal" not in data:
            raise ContractError("intent payload requires a goal")
        return cls(
            goal=data["goal"],
            constraints=tuple(data.get("constraints", ())),
            context_refs=tuple(data.get("context_refs", ())),
        )

    def canonical_json(self) -> str:
        return canonical(self.to_dict())
