"""SPEC-002: Ordered verification with mechanical-first enforcement.

The Verifier evaluates checks in GoalSpec order. All checks are evaluated
regardless of early failures (R2). Judge checks skip after prior failure (R6)
and fail closed when unavailable (R7).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol

from .core import ContractError
from .goalspec import CheckType, GoalSpec


class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class CriterionResult:
    name: str
    check_type: CheckType
    result: CheckResult
    reason: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True)
class VerificationReport:
    """SPEC-002-R4: primary_failure is None iff overall is PASS."""
    goal_id: str
    overall_pass: bool
    results: tuple[CriterionResult, ...]
    primary_failure: Optional[str] = None   # name of first failing check
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.overall_pass


# Evaluator signature: (candidate, parameters) -> tuple[CheckResult, str]
Evaluator = Callable[[Any, dict], tuple[CheckResult, str]]


class Verifier:
    """SPEC-002: ordered, mechanical-first, fail-closed verification.

    Evaluators are host-registered callables — never model-supplied functions.
    The registry maps criterion.evaluator names to Evaluator callables.
    """

    def __init__(self, evaluators: dict[str, Evaluator]):
        self._evaluators = dict(evaluators)

    @property
    def evaluators(self):
        from types import MappingProxyType
        return MappingProxyType(self._evaluators)

    def verify(self, candidate: Any, spec: GoalSpec,
               emit=None) -> VerificationReport:
        """Verify candidate against spec.

        emit: optional callable(kind: str, payload: dict) -> None
              Called after each check evaluation for observation emission.
        """
        t0 = time.monotonic()
        results: list[CriterionResult] = []
        prior_failed = False
        primary_failure: Optional[str] = None

        for criterion in spec.success_criteria:
            ct0 = time.monotonic()
            result, reason = self._evaluate_one(criterion, candidate, prior_failed)
            duration_ms = (time.monotonic() - ct0) * 1000
            results.append(CriterionResult(
                name=criterion.name,
                check_type=criterion.check_type,
                result=result,
                reason=reason,
                duration_ms=round(duration_ms, 3),
            ))
            if emit:
                emit("check_evaluated", {
                    "goal_id": spec.goal_id,
                    "check_name": criterion.name,
                    "check_type": criterion.check_type.value,
                    "result": result.value,
                    "reason": reason,
                    "duration_ms": round(duration_ms, 3),
                })
            if result != CheckResult.PASS and primary_failure is None:
                primary_failure = criterion.name
            if result != CheckResult.PASS:
                prior_failed = True

        overall = all(r.result == CheckResult.PASS for r in results)
        total_ms = (time.monotonic() - t0) * 1000
        return VerificationReport(
            goal_id=spec.goal_id,
            overall_pass=overall,
            results=tuple(results),
            primary_failure=primary_failure,
            duration_ms=round(total_ms, 3),
        )

    def _evaluate_one(self, criterion, candidate, prior_failed) -> tuple[CheckResult, str]:
        # SPEC-002-R6: judge checks skip after any prior failure.
        if criterion.check_type == CheckType.JUDGE and prior_failed:
            return CheckResult.SKIPPED, "prior_check_failed"

        evaluator = self._evaluators.get(criterion.evaluator)
        if evaluator is None:
            # SPEC-002-R7: fail closed when the evaluator is unavailable.
            if criterion.check_type == CheckType.JUDGE:
                return CheckResult.FAIL, "judge_unavailable"
            return CheckResult.FAIL, f"evaluator_not_registered:{criterion.evaluator}"

        try:
            result, reason = evaluator(candidate, criterion.parameters)
        except Exception:
            # SPEC-002-R5: mechanical check exceptions return FAIL, not raise.
            return CheckResult.FAIL, "check_error"

        if not isinstance(result, CheckResult) or result not in (CheckResult.PASS, CheckResult.FAIL, CheckResult.UNKNOWN) or not isinstance(reason, str):
            return CheckResult.FAIL, "invalid_check_result"
        return result, reason[:1000]
