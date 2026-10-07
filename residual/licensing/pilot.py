"""Pilot-program framework: evaluation and graduation-criteria evaluator (ENT7-R1)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError, identifier

MIN_DURATION_DAYS = 30
MAX_DURATION_DAYS = 90


@dataclass(frozen=True)
class PilotPlan:
    """Pilot scope, duration, metrics, and rollback plan (ENT7-R1)."""
    pilot_id: str
    scope: tuple[str, ...]                    # systems/teams in scope
    success_metrics: tuple[str, ...]          # named measurable metrics
    duration_days: int                        # typically 30-90 days
    rollback_plan: str                        # how to revert to pre-pilot state
    graduation_criteria: tuple[str, ...]      # criteria to enter production

    def __post_init__(self):
        identifier(self.pilot_id)
        if not self.scope:
            raise ContractError("pilot scope must not be empty (ENT7-R1)")
        if not self.success_metrics:
            raise ContractError("pilot must define success metrics (ENT7-R1)")
        if not (MIN_DURATION_DAYS <= self.duration_days <= MAX_DURATION_DAYS):
            raise ContractError(
                f"pilot duration must be {MIN_DURATION_DAYS}-{MAX_DURATION_DAYS} days (ENT7-R1)")
        if not self.rollback_plan:
            raise ContractError("pilot must define a rollback plan (ENT7-R1)")
        if not self.graduation_criteria:
            raise ContractError("pilot must define graduation criteria (ENT7-R1)")


@dataclass(frozen=True)
class MetricResult:
    """Measured outcome for one pilot success metric."""
    name: str
    target: float
    actual: float
    lower_is_better: bool = False

    @property
    def met(self) -> bool:
        return self.actual <= self.target if self.lower_is_better else self.actual >= self.target


@dataclass
class GraduationEvaluation:
    """Result of evaluating a pilot against its graduation criteria (ENT7-R1)."""
    plan: PilotPlan
    metrics: list[MetricResult] = field(default_factory=list)
    criteria_met: set[str] = field(default_factory=set)

    def record_metric(self, result: MetricResult) -> None:
        if result.name not in self.plan.success_metrics:
            raise ContractError(f"metric {result.name} not in pilot success metrics")
        self.metrics.append(result)

    def attest_criterion(self, criterion: str) -> None:
        if criterion not in self.plan.graduation_criteria:
            raise ContractError(f"unknown graduation criterion {criterion}")
        self.criteria_met.add(criterion)

    def metrics_passed(self) -> bool:
        recorded = {m.name for m in self.metrics}
        if recorded != set(self.plan.success_metrics):
            return False
        return all(m.met for m in self.metrics)

    def graduated(self) -> bool:
        """True only when every success metric passed and every graduation
        criterion is attested (ENT7-R1 graduation to production)."""
        return (self.metrics_passed()
                and self.criteria_met == set(self.plan.graduation_criteria))

    def report(self) -> dict:
        missing_metrics = sorted(set(self.plan.success_metrics)
                                 - {m.name for m in self.metrics})
        unmet_criteria = sorted(set(self.plan.graduation_criteria) - self.criteria_met)
        return {
            "pilot_id": self.plan.pilot_id,
            "graduated": self.graduated(),
            "metrics": {m.name: {"target": m.target, "actual": m.actual,
                                 "met": m.met} for m in self.metrics},
            "missing_metrics": missing_metrics,
            "unmet_criteria": unmet_criteria,
            "rollback_plan": self.plan.rollback_plan,
        }
