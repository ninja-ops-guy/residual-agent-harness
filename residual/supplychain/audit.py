"""Third-party security audit tracking. Implements ENT5-R4.

Residual MUST undergo annual third-party security audit by a
recognized firm (NCC Group, Trail of Bits, Cure53, or equivalent),
covering code review, penetration testing, architecture review, and
compliance verification. Results MUST be published. This module
tracks audits and enforces the annual cadence and required scope.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from residual.core import ContractError

RECOGNIZED_FIRMS = frozenset({"NCC Group", "Trail of Bits", "Cure53"})
REQUIRED_SCOPES = frozenset(
    {"code_review", "penetration_testing", "architecture_review", "compliance_verification"}
)
AUDIT_INTERVAL_DAYS = 365


class AuditScope:
    """Audit scope constants. Implements ENT5-R4."""

    CODE_REVIEW = "code_review"
    PENETRATION_TESTING = "penetration_testing"
    ARCHITECTURE_REVIEW = "architecture_review"
    COMPLIANCE_VERIFICATION = "compliance_verification"

    ALL = REQUIRED_SCOPES


@dataclass(frozen=True)
class ThirdPartyAudit:
    """Record of one third-party security audit. Implements ENT5-R4.

    ``recognized_equivalent`` may justify a firm outside the named
    recognized list; without it the firm MUST be recognized.
    Results MUST be published (``published=True``).
    """

    firm: str
    completed_day: int  # days since epoch; deterministic offline clock
    scopes: frozenset[str]
    published: bool
    report_url: str = ""
    recognized_equivalent: str = ""

    def __post_init__(self):
        if not isinstance(self.firm, str) or not self.firm:
            raise ContractError("audit firm required")
        if self.firm not in RECOGNIZED_FIRMS and not self.recognized_equivalent.strip():
            raise ContractError(
                "ENT5-R4: firm must be recognized (NCC Group, Trail of Bits, Cure53) "
                "or documented as equivalent"
            )
        if type(self.completed_day) is not int or self.completed_day < 0:
            raise ContractError("completed_day must be a nonnegative int")
        if not isinstance(self.scopes, frozenset):
            raise ContractError("scopes must be a frozenset")
        unknown = self.scopes - REQUIRED_SCOPES
        if unknown:
            raise ContractError(f"unknown audit scopes: {sorted(unknown)}")
        missing = REQUIRED_SCOPES - self.scopes
        if missing:
            raise ContractError(f"ENT5-R4: audit scope incomplete, missing {sorted(missing)}")
        if type(self.published) is not bool:
            raise ContractError("published flag must be bool")

    @property
    def firm_recognized(self) -> bool:
        return self.firm in RECOGNIZED_FIRMS


@dataclass
class AuditTracker:
    """Tracks audit history and enforces annual cadence. Implements ENT5-R4."""

    audits: list[ThirdPartyAudit] = field(default_factory=list)

    def record(self, audit: ThirdPartyAudit) -> None:
        """Record a completed audit. Implements ENT5-R4."""
        if not isinstance(audit, ThirdPartyAudit):
            raise ContractError("audit must be a ThirdPartyAudit")
        if any(a.firm == audit.firm and a.completed_day == audit.completed_day for a in self.audits):
            raise ContractError("duplicate audit record")
        self.audits.append(audit)
        self.audits.sort(key=lambda a: a.completed_day)

    def latest(self) -> ThirdPartyAudit | None:
        return self.audits[-1] if self.audits else None

    def next_due_day(self, current_day: int) -> int:
        """Day by which the next annual audit is due. Implements ENT5-R4."""
        if type(current_day) is not int or current_day < 0:
            raise ContractError("current_day must be a nonnegative int")
        latest = self.latest()
        base = latest.completed_day if latest else 0
        return base + AUDIT_INTERVAL_DAYS

    def is_current(self, current_day: int) -> bool:
        """True if an audit exists and is not older than one year. Implements ENT5-R4."""
        if type(current_day) is not int or current_day < 0:
            raise ContractError("current_day must be a nonnegative int")
        latest = self.latest()
        return latest is not None and current_day - latest.completed_day <= AUDIT_INTERVAL_DAYS

    def unpublished(self) -> list[ThirdPartyAudit]:
        """Audits whose results are not yet published. Implements ENT5-R4."""
        return [a for a in self.audits if not a.published]
