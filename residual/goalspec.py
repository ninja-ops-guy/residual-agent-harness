"""SPEC-001: Frozen, versioned goal specification.

A GoalSpec is the structural definition of what a run must achieve.
It is immutable after construction. Amendments produce a new instance
with an incremented version and a mandatory reason preserved in run receipts.

Design rule: the run does not define the goal; the goal defines the run.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol

from .core import ContractError, canonical, identifier, positive_int
from observation_layer.core import freeze


class CheckType(str, Enum):
    MECHANICAL = "mechanical"
    STRUCTURAL = "structural"
    JUDGE = "judge"


# Evaluation order is fixed by the enum declaration order above.
_EVALUATION_ORDER = (CheckType.MECHANICAL, CheckType.STRUCTURAL, CheckType.JUDGE)


@dataclass(frozen=True)
class SuccessCriterion:
    """One check in the GoalSpec. Evaluators are host-registered callables."""
    name: str
    check_type: CheckType
    description: str
    evaluator: str          # registered name in the check registry
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        identifier(self.name)
        try:
            object.__setattr__(self, "check_type", CheckType(self.check_type))
        except (ValueError, TypeError):
            raise ContractError("unknown criterion check type") from None
        if not isinstance(self.description, str) or not self.description.strip():
            raise ContractError("criterion requires a description")
        if not isinstance(self.evaluator, str) or not self.evaluator.strip():
            raise ContractError("criterion requires an evaluator reference")
        try:
            if not isinstance(self.parameters, dict):
                raise ValueError()
            object.__setattr__(self, "parameters", freeze(self.parameters))
        except Exception:
            raise ContractError("criterion parameters must be finite JSON object values") from None


@dataclass(frozen=True)
class AmendmentRule:
    """Who may amend the spec, under what conditions."""
    authorized_roles: tuple[str, ...]
    max_amendments: int = 3

    def __post_init__(self):
        if not isinstance(self.authorized_roles, (tuple, list)):
            raise ContractError("authorized_roles must be a sequence")
        object.__setattr__(self, "authorized_roles", tuple(self.authorized_roles))
        if not self.authorized_roles:
            raise ContractError("amendment rule requires at least one authorized role")
        for r in self.authorized_roles:
            identifier(r)
        positive_int(self.max_amendments, "max_amendments")


@dataclass(frozen=True)
class GoalSpec:
    """SPEC-001-R1: immutable after construction. SPEC-001-R2: all fields required."""
    goal_id: str
    objective: str
    success_criteria: tuple[SuccessCriterion, ...]
    max_passes: int
    token_budget: int
    wall_clock_budget_s: float
    amendment_rule: AmendmentRule
    schema_version: str = "1.0.0"
    amendment_count: int = 0
    parent_hash: Optional[str] = None
    amendment_reason: Optional[str] = None
    amended_by: Optional[str] = None

    def __post_init__(self):
        identifier(self.goal_id)
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise ContractError("goal spec requires a non-empty objective")
        if not isinstance(self.success_criteria, (tuple, list)) or not self.success_criteria or any(not isinstance(c, SuccessCriterion) for c in self.success_criteria):
            raise ContractError("goal spec requires at least one success criterion")
        object.__setattr__(self, "success_criteria", tuple(self.success_criteria))
        if not isinstance(self.amendment_rule, AmendmentRule):
            raise ContractError("goal spec requires an amendment rule")
        positive_int(self.max_passes, "max_passes")
        positive_int(self.token_budget, "token_budget")
        if type(self.wall_clock_budget_s) not in (int, float) or not math.isfinite(self.wall_clock_budget_s) or self.wall_clock_budget_s <= 0:
            raise ContractError("wall_clock_budget_s must be positive")
        if not isinstance(self.schema_version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.schema_version):
            raise ContractError("schema_version must use major.minor.patch")
        positive_int(self.amendment_count, "amendment_count", allow_zero=True)
        if self.amendment_count > self.amendment_rule.max_amendments:
            raise ContractError("maximum amendments exceeded")
        if self.amendment_count:
            if not isinstance(self.parent_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", self.parent_hash):
                raise ContractError("amended spec requires its parent hash")
            if not isinstance(self.amendment_reason, str) or not self.amendment_reason.strip() or self.amended_by not in self.amendment_rule.authorized_roles:
                raise ContractError("amended spec requires an authorized role and reason")
        elif any(x is not None for x in (self.parent_hash, self.amendment_reason, self.amended_by)):
            raise ContractError("initial spec cannot carry amendment metadata")
        # SPEC-001-R5: ordering enforced at construction.
        order_index = {ct: i for i, ct in enumerate(_EVALUATION_ORDER)}
        indices = [order_index[c.check_type] for c in self.success_criteria]
        if indices != sorted(indices):
            raise ContractError(
                "success_criteria must be ordered: mechanical before structural before judge"
            )
        names = [c.name for c in self.success_criteria]
        if len(names) != len(set(names)):
            raise ContractError("duplicate criterion name")

    def to_dict(self) -> dict:
        """Serializable contract, including evaluator identities and amendment authority."""
        return {
            "goal_id": self.goal_id,
            "objective": self.objective,
            "success_criteria": [
                {"name": c.name, "check_type": c.check_type.value,
                 "description": c.description, "evaluator": c.evaluator, "parameters": c.parameters}
                for c in self.success_criteria
            ],
            "max_passes": self.max_passes,
            "token_budget": self.token_budget,
            "wall_clock_budget_s": self.wall_clock_budget_s,
            "schema_version": self.schema_version,
            "amendment_rule": {"authorized_roles": self.amendment_rule.authorized_roles,
                               "max_amendments": self.amendment_rule.max_amendments},
            "amendment_count": self.amendment_count,
            "parent_hash": self.parent_hash,
            "amendment_reason": self.amendment_reason,
            "amended_by": self.amended_by,
        }

    @property
    def content_hash(self) -> str:
        """SHA-256 over the complete contract; host evaluator code is not serialized."""
        return hashlib.sha256(canonical(self.to_dict()).encode()).hexdigest()

    def amend(self, *, objective: Optional[str] = None,
              success_criteria: Optional[tuple[SuccessCriterion, ...]] = None,
              max_passes: Optional[int] = None,
              token_budget: Optional[int] = None,
              wall_clock_budget_s: Optional[float] = None,
              amendment_reason: str,
              amended_by: str) -> "GoalSpec":
        """SPEC-001-R7: amendments produce a new instance; original is preserved."""
        if not isinstance(amendment_reason, str) or not amendment_reason.strip():
            raise ContractError("amendment requires a reason")
        identifier(amended_by)
        if amended_by not in self.amendment_rule.authorized_roles:
            raise ContractError(f"role '{amended_by}' is not authorized to amend this spec")
        if self.amendment_count >= self.amendment_rule.max_amendments:
            raise ContractError("maximum amendments exceeded")
        major, minor, patch = (int(x) for x in self.schema_version.split("."))
        new_spec = GoalSpec(
            goal_id=self.goal_id,
            objective=objective if objective is not None else self.objective,
            success_criteria=success_criteria if success_criteria is not None else self.success_criteria,
            max_passes=max_passes if max_passes is not None else self.max_passes,
            token_budget=token_budget if token_budget is not None else self.token_budget,
            wall_clock_budget_s=(wall_clock_budget_s if wall_clock_budget_s is not None
                                 else self.wall_clock_budget_s),
            amendment_rule=self.amendment_rule,
            schema_version=f"{major}.{minor + 1}.{patch}",
            amendment_count=self.amendment_count + 1,
            parent_hash=self.content_hash,
            amendment_reason=amendment_reason,
            amended_by=amended_by,
        )
        return new_spec
