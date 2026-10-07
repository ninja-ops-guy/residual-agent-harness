"""VQ-R4: fail-closed HITL escalation gate.

A safety-critical verifier whose measured precision falls below the
threshold (default 0.95) MUST NOT silently accept: the gate either
escalates to HITL or raises EscalationError. Degraded precision closes
the acceptance path; it never reopens it without a human decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from residual.core import ContractError
from .profile import VerifierQualityProfile

SAFETY_PRECISION_THRESHOLD = 0.95


class GateDecision(str, Enum):
    ACCEPT = "accept"                     # quality adequate, may accept
    ESCALATE_HITL = "escalate_hitl"       # fail closed to human review
    UNKNOWN = "unknown"                   # insufficient samples => fail closed


class EscalationError(ContractError):
    """Raised when acceptance is attempted through a degraded verifier.

    Fail-closed: this exception is the mechanism that prevents silent
    acceptance (VQ-R4).
    """

    def __init__(self, message: str, decision: "GateResult" = None):
        super().__init__(message)
        self.decision = decision


@dataclass(frozen=True)
class GateResult:
    decision: GateDecision
    reason: str
    precision: Optional[float]
    precision_lower: Optional[float]
    threshold: float
    safety_critical: bool

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "precision": self.precision,
            "precision_lower": self.precision_lower,
            "threshold": self.threshold,
            "safety_critical": self.safety_critical,
        }


class QualityGate:
    """Gates acceptance on the verifier's measured quality profile."""

    def __init__(self, threshold: float = SAFETY_PRECISION_THRESHOLD):
        if not (0.0 < threshold <= 1.0):
            raise ContractError("threshold must be in (0, 1]")
        self.threshold = threshold

    def evaluate(self, profile: VerifierQualityProfile,
                 safety_critical: bool) -> GateResult:
        """Decide whether this verifier may accept, must escalate, or is UNKNOWN."""
        if not safety_critical:
            return GateResult(GateDecision.ACCEPT, "not_safety_critical",
                              profile.precision.estimate,
                              profile.precision.lower,
                              self.threshold, False)
        if profile.precision.status == "UNKNOWN":
            # VQ-R9 + VQ-R4: unknown precision on a safety-critical
            # verifier fails closed rather than trusting a point estimate.
            return GateResult(GateDecision.UNKNOWN,
                              "insufficient_samples: precision UNKNOWN on "
                              "safety-critical verifier; failing closed to HITL",
                              None, None, self.threshold, True)
        # Gate on the lower Wilson bound: optimistic point estimates do
        # not excuse uncertainty (VQ-R9).
        if profile.precision.lower is not None and profile.precision.lower < self.threshold:
            return GateResult(
                GateDecision.ESCALATE_HITL,
                f"precision lower bound {profile.precision.lower} < "
                f"{self.threshold}: degraded verifier; fail-closed HITL escalation",
                profile.precision.estimate, profile.precision.lower,
                self.threshold, True)
        return GateResult(GateDecision.ACCEPT, "precision_within_threshold",
                          profile.precision.estimate, profile.precision.lower,
                          self.threshold, True)

    def accept_or_escalate(self, profile: VerifierQualityProfile,
                           safety_critical: bool) -> GateResult:
        """Fail-closed acceptance: returns ACCEPT decision or raises.

        ESCALATE_HITL and UNKNOWN both raise EscalationError; there is no
        path by which a degraded or unmeasured safety-critical verifier
        silently accepts (VQ-R4).
        """
        result = self.evaluate(profile, safety_critical)
        if result.decision == GateDecision.ACCEPT:
            return result
        raise EscalationError(
            f"VQ-R4: HITL escalation required — {result.reason}", result)
