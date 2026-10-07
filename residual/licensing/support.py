"""Support-tier SLA tracker with P1 response timers (ENT8-R2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..core import ContractError, identifier


class SupportTier(str, Enum):
    STANDARD = "standard"    # business hours, 24h response, email only
    PREMIUM = "premium"      # 24/7, 4h response, email + phone
    ENTERPRISE = "enterprise"  # 24/7, 1h P1 response, dedicated engineer


class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Channel(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    ONSITE = "onsite"


# Response-time SLAs in seconds, per tier and severity (ENT8-R2).
RESPONSE_SLA_SECONDS = {
    SupportTier.STANDARD: {Severity.P1: 24 * 3600, Severity.P2: 24 * 3600,
                           Severity.P3: 24 * 3600},
    SupportTier.PREMIUM: {Severity.P1: 4 * 3600, Severity.P2: 4 * 3600,
                          Severity.P3: 8 * 3600},
    SupportTier.ENTERPRISE: {Severity.P1: 3600, Severity.P2: 4 * 3600,
                             Severity.P3: 8 * 3600},
}

ALLOWED_CHANNELS = {
    SupportTier.STANDARD: frozenset({Channel.EMAIL}),
    SupportTier.PREMIUM: frozenset({Channel.EMAIL, Channel.PHONE}),
    SupportTier.ENTERPRISE: frozenset({Channel.EMAIL, Channel.PHONE, Channel.ONSITE}),
}


@dataclass
class SupportCase:
    case_id: str
    severity: Severity
    opened_at: float            # epoch seconds
    channel: Channel = Channel.EMAIL
    first_response_at: float | None = None
    resolved_at: float | None = None

    def __post_init__(self):
        identifier(self.case_id)
        if self.first_response_at is not None and self.first_response_at < self.opened_at:
            raise ContractError("response precedes case open time")


@dataclass
class SlaTracker:
    """Tracks support cases against tier SLAs (ENT8-R2)."""
    tier: SupportTier
    cases: dict[str, SupportCase] = field(default_factory=dict)

    def open_case(self, case_id: str, severity: Severity, opened_at: float,
                  channel: Channel = Channel.EMAIL) -> SupportCase:
        if channel not in ALLOWED_CHANNELS[self.tier]:
            raise ContractError(
                f"channel {channel.value} not available on {self.tier.value} tier (ENT8-R2)")
        if case_id in self.cases:
            raise ContractError(f"duplicate case {case_id}")
        case = SupportCase(case_id=case_id, severity=severity,
                           opened_at=float(opened_at), channel=channel)
        self.cases[case_id] = case
        return case

    def record_first_response(self, case_id: str, responded_at: float) -> None:
        case = self._case(case_id)
        case.first_response_at = float(responded_at)
        if case.first_response_at < case.opened_at:
            raise ContractError("response precedes case open time")

    def resolve(self, case_id: str, resolved_at: float) -> None:
        case = self._case(case_id)
        if resolved_at < case.opened_at:
            raise ContractError("resolution precedes case open time")
        case.resolved_at = float(resolved_at)

    def response_sla(self, severity: Severity) -> int:
        return RESPONSE_SLA_SECONDS[self.tier][severity]

    def breached(self, case_id: str) -> bool:
        case = self._case(case_id)
        if case.first_response_at is None:
            return False
        return (case.first_response_at - case.opened_at) > self.response_sla(case.severity)

    def overdue(self, case_id: str, now: float) -> bool:
        """True when an unanswered case has already exceeded its SLA timer."""
        case = self._case(case_id)
        if case.first_response_at is not None:
            return False
        return (float(now) - case.opened_at) > self.response_sla(case.severity)

    def compliance_report(self) -> dict:
        total = len(self.cases)
        answered = [c for c in self.cases.values() if c.first_response_at is not None]
        breaches = [c.case_id for c in answered
                    if (c.first_response_at - c.opened_at)
                    > self.response_sla(c.severity)]
        return {
            "tier": self.tier.value,
            "cases": total,
            "answered": len(answered),
            "breaches": sorted(breaches),
            "within_sla": len(answered) - len(breaches),
        }

    def _case(self, case_id: str) -> SupportCase:
        try:
            return self.cases[case_id]
        except KeyError:
            raise ContractError(f"unknown case {case_id}") from None
