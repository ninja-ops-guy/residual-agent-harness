from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import sqrt
from typing import Mapping


class AssuranceClass(str, Enum):
    ROUTINE = "routine"
    IMPORTANT = "important"
    SECURITY_CRITICAL = "security_critical"
    SAFETY_CRITICAL = "safety_critical"


DEFAULT_THRESHOLDS: Mapping[AssuranceClass, float] = {
    AssuranceClass.ROUTINE: 0.90,
    AssuranceClass.IMPORTANT: 0.95,
    AssuranceClass.SECURITY_CRITICAL: 0.985,
    AssuranceClass.SAFETY_CRITICAL: 0.995,
}


@dataclass
class VerifierQualityProfile:
    verifier_id: str
    true_accept: int = 0
    false_accept: int = 0
    true_reject: int = 0
    false_reject: int = 0
    unknown: int = 0
    skipped: int = 0
    coverage_hits: int = 0
    coverage_total: int = 0
    brier_sum: float = 0.0
    calibrated_samples: int = 0
    alpha: float = 1.0
    beta: float = 1.0

    @property
    def samples(self) -> int:
        return self.true_accept + self.false_accept + self.true_reject + self.false_reject

    @property
    def precision(self) -> float:
        denom = self.true_accept + self.false_accept
        return self.true_accept / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_reject + self.false_accept
        return self.true_reject / denom if denom else 0.0

    @property
    def false_accept_rate(self) -> float:
        denom = self.true_reject + self.false_accept
        return self.false_accept / denom if denom else 0.0

    @property
    def coverage(self) -> float:
        return self.coverage_hits / self.coverage_total if self.coverage_total else 0.0

    @property
    def calibration_error(self) -> float:
        return self.brier_sum / self.calibrated_samples if self.calibrated_samples else 0.0

    @property
    def posterior_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def lower_credible_bound(self, z: float = 1.96) -> float:
        a, b = self.alpha, self.beta
        mean = a / (a + b)
        var = (a * b) / (((a + b) ** 2) * (a + b + 1))
        return max(0.0, mean - z * sqrt(var))

    def record_outcome(
        self,
        *,
        verifier_passed: bool,
        artifact_acceptable: bool,
        confidence: float | None = None,
        covered: bool = True,
    ) -> None:
        if verifier_passed and artifact_acceptable:
            self.true_accept += 1
        elif verifier_passed and not artifact_acceptable:
            self.false_accept += 1
        elif not verifier_passed and not artifact_acceptable:
            self.true_reject += 1
        else:
            self.false_reject += 1

        decision_correct = verifier_passed == artifact_acceptable
        if decision_correct:
            self.alpha += 1.0
        else:
            self.beta += 1.0

        self.coverage_total += 1
        self.coverage_hits += int(covered)

        if confidence is not None:
            p = min(1.0, max(0.0, float(confidence)))
            self.brier_sum += (p - float(decision_correct)) ** 2
            self.calibrated_samples += 1

    def record_abstention(self, *, skipped: bool = False) -> None:
        if skipped:
            self.skipped += 1
        else:
            self.unknown += 1

    def requires_hitl(
        self,
        assurance: AssuranceClass,
        thresholds: Mapping[AssuranceClass, float] = DEFAULT_THRESHOLDS,
        min_samples: int = 20,
    ) -> bool:
        if self.samples < min_samples:
            return assurance in {AssuranceClass.SECURITY_CRITICAL, AssuranceClass.SAFETY_CRITICAL}
        return self.lower_credible_bound() < thresholds[assurance]

    def receipt_payload(self) -> dict[str, float | int | str]:
        return {
            "schema_version": "residual.verifier-quality.v1",
            "verifier_id": self.verifier_id,
            "samples": self.samples,
            "precision": self.precision,
            "defect_recall": self.recall,
            "false_accept_rate": self.false_accept_rate,
            "coverage": self.coverage,
            "calibration_error": self.calibration_error,
            "posterior_mean": self.posterior_mean,
            "lower_credible_bound": self.lower_credible_bound(),
        }


@dataclass
class VerifierQualityRegistry:
    profiles: dict[str, VerifierQualityProfile] = field(default_factory=dict)

    def get(self, verifier_id: str) -> VerifierQualityProfile:
        return self.profiles.setdefault(verifier_id, VerifierQualityProfile(verifier_id))
