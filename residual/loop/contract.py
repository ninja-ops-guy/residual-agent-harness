from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from residual.core import ContractError, digest, identifier


@dataclass(frozen=True)
class AbortCondition:
    budget_threshold: Decimal | None = None
    time_threshold_s: int | None = None
    require_no_progress: bool = True

    def __post_init__(self) -> None:
        if self.budget_threshold is not None and self.budget_threshold < 0:
            raise ContractError("abort budget threshold must be nonnegative")
        if self.time_threshold_s is not None and self.time_threshold_s <= 0:
            raise ContractError("abort time threshold must be positive")
        if self.budget_threshold is None and self.time_threshold_s is None:
            raise ContractError("abort condition requires a budget or time threshold")

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_threshold": str(self.budget_threshold) if self.budget_threshold is not None else None,
            "time_threshold_s": self.time_threshold_s,
            "require_no_progress": self.require_no_progress,
        }


@dataclass(frozen=True)
class GoalContract:
    goal_id: str
    objective: str
    required_verification_ids: tuple[str, ...]
    max_iterations: int = 1
    max_wall_time_s: int = 3600
    max_cost: Decimal | None = None
    no_progress_limit: int = 2
    escalation_cooldown_period: int = 2
    abort_conditions: tuple[AbortCondition, ...] = ()
    schema_version: str = "residual.loop.goal.v1"

    def __post_init__(self) -> None:
        identifier(self.goal_id)
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ContractError("goal objective must be nonempty")
        if not self.required_verification_ids:
            raise ContractError("goal requires at least one verification id")
        if len(set(self.required_verification_ids)) != len(self.required_verification_ids):
            raise ContractError("duplicate required verification id")
        if any(not isinstance(v, str) or not v.strip() for v in self.required_verification_ids):
            raise ContractError("verification ids must be nonempty strings")
        if type(self.max_iterations) is not int or self.max_iterations < 1:
            raise ContractError("max_iterations must be positive")
        if type(self.max_wall_time_s) is not int or self.max_wall_time_s < 1:
            raise ContractError("max_wall_time_s must be positive")
        if type(self.no_progress_limit) is not int or self.no_progress_limit < 1:
            raise ContractError("no_progress_limit must be positive")
        if type(self.escalation_cooldown_period) is not int or self.escalation_cooldown_period < 0:
            raise ContractError("escalation_cooldown_period must be nonnegative")
        if self.max_cost is not None and self.max_cost < 0:
            raise ContractError("max_cost must be nonnegative")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "goal_id": self.goal_id,
            "objective": self.objective.strip(),
            "required_verification_ids": list(self.required_verification_ids),
            "max_iterations": self.max_iterations,
            "max_wall_time_s": self.max_wall_time_s,
            "max_cost": str(self.max_cost) if self.max_cost is not None else None,
            "no_progress_limit": self.no_progress_limit,
            "escalation_cooldown_period": self.escalation_cooldown_period,
            "abort_conditions": [condition.to_dict() for condition in self.abort_conditions],
        }

    @property
    def contract_hash(self) -> str:
        return digest(self.canonical_payload())
