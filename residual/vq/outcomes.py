"""VQ-R3: profiles are updated ONLY from independently labeled outcomes.

Worker self-reports are structurally rejected: a LabeledOutcome whose
label_source is WORKER_SELF_REPORT cannot be constructed, and the
OutcomeStore rejects any non-independent label at admission time.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional

from residual.core import ContractError


class SelfReportRejected(ContractError):
    """Raised when a worker self-report is presented as an outcome label."""


class LabelSource(str, Enum):
    """Provenance of an outcome's ground-truth label."""
    INDEPENDENT_AUDIT = "independent_audit"   # human or oracle audit
    FROZEN_WORKLOAD = "frozen_workload"       # known label from frozen fixture
    EXTERNAL_ORACLE = "external_oracle"       # trusted external grader
    WORKER_SELF_REPORT = "worker_self_report" # NEVER admissible (VQ-R3)


INDEPENDENT_SOURCES = frozenset({
    LabelSource.INDEPENDENT_AUDIT,
    LabelSource.FROZEN_WORKLOAD,
    LabelSource.EXTERNAL_ORACLE,
})


@dataclass(frozen=True)
class LabeledOutcome:
    """One verified outcome with an independent ground-truth label.

    verifier_id:     name of the verifier that produced the verdict.
    verdict:         True = verifier accepted, False = verifier rejected.
    ground_truth:    True = outcome was actually correct, False = defective.
    confidence:      optional verifier-reported confidence in [0, 1],
                     used for calibration measurement (VQ-R1).
    safety_critical: whether this outcome is under a safety-critical policy.
    """
    case_id: str
    verifier_id: str
    verdict: bool
    ground_truth: bool
    label_source: LabelSource
    confidence: Optional[float] = None
    safety_critical: bool = False

    def __post_init__(self):
        object.__setattr__(self, "label_source", LabelSource(self.label_source))
        if self.label_source not in INDEPENDENT_SOURCES:
            raise SelfReportRejected(
                "VQ-R3: worker self-report is not an admissible outcome label")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ContractError("confidence must be in [0, 1]")
        if not self.case_id or not self.verifier_id:
            raise ContractError("case_id and verifier_id are required")

    @property
    def is_false_accept(self) -> bool:
        return self.verdict and not self.ground_truth

    @property
    def is_false_reject(self) -> bool:
        return (not self.verdict) and self.ground_truth

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "verifier_id": self.verifier_id,
            "verdict": self.verdict,
            "ground_truth": self.ground_truth,
            "label_source": self.label_source.value,
            "confidence": self.confidence,
            "safety_critical": self.safety_critical,
        }


class OutcomeStore:
    """Append-only store of independently labeled outcomes (raw evidence)."""

    def __init__(self):
        self._outcomes: list[LabeledOutcome] = []
        self._case_ids: set[str] = set()

    def add(self, outcome: LabeledOutcome) -> None:
        # Construction already rejects self-reports; enforce again at the
        # boundary so deserialized/mocked objects cannot bypass VQ-R3.
        if outcome.label_source not in INDEPENDENT_SOURCES:
            raise SelfReportRejected(
                "VQ-R3: worker self-report is not an admissible outcome label")
        if outcome.case_id in self._case_ids:
            raise ContractError(f"duplicate case_id: {outcome.case_id}")
        self._case_ids.add(outcome.case_id)
        self._outcomes.append(outcome)

    def __iter__(self) -> Iterator[LabeledOutcome]:
        return iter(self._outcomes)

    def __len__(self) -> int:
        return len(self._outcomes)

    def for_verifier(self, verifier_id: str) -> list[LabeledOutcome]:
        return [o for o in self._outcomes if o.verifier_id == verifier_id]

    def to_dicts(self) -> list[dict]:
        return [o.to_dict() for o in self._outcomes]
