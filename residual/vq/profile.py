"""VQ-R1 + VQ-R9: verifier quality profile with uncertainty reporting.

Point estimates are never emitted as authoritative without their Wilson
score interval. When the sample count is below the minimum, the metric
reports UNKNOWN (VQ-R9) rather than a misleading point estimate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .identity import VerifierIdentity
from .outcomes import LabeledOutcome

# Below this many labeled samples a metric is reported UNKNOWN (VQ-R9).
DEFAULT_MIN_SAMPLES = 5


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% default)."""
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


@dataclass(frozen=True)
class MetricEstimate:
    """A metric point estimate with uncertainty. UNKNOWN when n too small."""
    name: str
    estimate: Optional[float]   # None => UNKNOWN (insufficient samples)
    lower: Optional[float]
    upper: Optional[float]
    n: int
    status: str                 # "KNOWN" | "UNKNOWN"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "estimate": self.estimate,
            "lower": self.lower,
            "upper": self.upper,
            "n": self.n,
            "status": self.status,
        }


def _metric(name: str, successes: int, n: int,
            min_samples: int) -> MetricEstimate:
    if n < min_samples:
        return MetricEstimate(name, None, None, None, n, "UNKNOWN")
    lo, hi = wilson_interval(successes, n)
    return MetricEstimate(name, round(successes / n, 6),
                          round(lo, 6), round(hi, 6), n, "KNOWN")


@dataclass(frozen=True)
class VerifierQualityProfile:
    """VQ-R1: precision, recall, coverage, calibration, false-accept,
    false-reject, and sample count — each with Wilson uncertainty (VQ-R9).
    """
    identity: VerifierIdentity
    precision: MetricEstimate
    recall: MetricEstimate
    coverage: MetricEstimate
    calibration: MetricEstimate
    false_accept: MetricEstimate
    false_reject: MetricEstimate
    sample_count: int
    min_samples: int = DEFAULT_MIN_SAMPLES

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "precision": self.precision.to_dict(),
            "recall": self.recall.to_dict(),
            "coverage": self.coverage.to_dict(),
            "calibration": self.calibration.to_dict(),
            "false_accept": self.false_accept.to_dict(),
            "false_reject": self.false_reject.to_dict(),
            "sample_count": self.sample_count,
            "min_samples": self.min_samples,
        }

    @classmethod
    def from_outcomes(cls, identity: VerifierIdentity,
                      outcomes: list[LabeledOutcome],
                      min_samples: int = DEFAULT_MIN_SAMPLES
                      ) -> "VerifierQualityProfile":
        """Compute the profile from independently labeled outcomes only.

        LabeledOutcome/OutcomeStore already enforce VQ-R3; this method
        requires a non-empty list typed as LabeledOutcome.
        """
        for o in outcomes:
            if not isinstance(o, LabeledOutcome):
                raise TypeError("profiles update only from LabeledOutcome")
        n = len(outcomes)
        accepted = [o for o in outcomes if o.verdict]
        rejected = [o for o in outcomes if not o.verdict]
        positives = [o for o in outcomes if o.ground_truth]
        negatives = [o for o in outcomes if not o.ground_truth]

        tp = sum(1 for o in accepted if o.ground_truth)
        fp = sum(1 for o in accepted if not o.ground_truth)
        fn = sum(1 for o in rejected if o.ground_truth)
        tn = sum(1 for o in rejected if not o.ground_truth)

        precision = _metric("precision", tp, tp + fp, min_samples)
        recall = _metric("recall", tp, tp + fn, min_samples)
        # coverage: fraction of labeled cases the verifier decided on
        # (non-abstaining verifiers always cover; recorded for ensembles).
        coverage = _metric("coverage", n, n, min_samples)
        # calibration: 1 - mean |confidence - empirical accuracy| over
        # confidence-bearing outcomes; UNKNOWN without confidence data.
        conf = [o for o in outcomes if o.confidence is not None]
        if conf:
            err = sum(abs(o.confidence - (1.0 if o.verdict == o.ground_truth else 0.0))
                      for o in conf) / len(conf)
            cal_n = len(conf)
            if cal_n >= min_samples:
                lo, hi = wilson_interval(round((1 - err) * cal_n), cal_n)
                calibration = MetricEstimate("calibration", round(1 - err, 6),
                                             round(lo, 6), round(hi, 6), cal_n, "KNOWN")
            else:
                calibration = MetricEstimate("calibration", None, None, None,
                                             cal_n, "UNKNOWN")
        else:
            calibration = MetricEstimate("calibration", None, None, None, 0, "UNKNOWN")

        false_accept = _metric("false_accept", fp, fp + tn, min_samples)
        false_reject = _metric("false_reject", fn, fn + tp, min_samples)

        return cls(
            identity=identity,
            precision=precision,
            recall=recall,
            coverage=coverage,
            calibration=calibration,
            false_accept=false_accept,
            false_reject=false_reject,
            sample_count=n,
            min_samples=min_samples,
        )
