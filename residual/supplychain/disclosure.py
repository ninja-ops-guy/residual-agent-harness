"""Vulnerability disclosure program SLA tracker. Implements ENT5-R5.

Security researchers MUST be able to report issues responsibly.
Reports MUST be acknowledged within 72 hours. Critical vulnerabilities
MUST be patched within 14 days. All times are deterministic integers
(hours since report receipt) so the tracker runs fully offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from residual.core import ContractError

ACK_SLA_HOURS = 72
CRITICAL_PATCH_SLA_HOURS = 14 * 24  # 336 hours


class Severity:
    """Disclosure severity constants. Implements ENT5-R5."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    ALL = frozenset({LOW, MEDIUM, HIGH, CRITICAL})


@dataclass(frozen=True)
class DisclosureReport:
    """A responsibly disclosed vulnerability report. Implements ENT5-R5."""

    report_id: str
    severity: str
    summary: str
    reporter: str

    def __post_init__(self):
        if not isinstance(self.report_id, str) or not self.report_id:
            raise ContractError("report_id required")
        if self.severity not in Severity.ALL:
            raise ContractError(f"severity must be one of {sorted(Severity.ALL)}")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ContractError("summary required")
        if not isinstance(self.reporter, str) or not self.reporter.strip():
            raise ContractError("reporter required")


@dataclass
class _Record:
    report: DisclosureReport
    received_hour: int
    acknowledged_hour: int | None = None
    patched_hour: int | None = None


@dataclass
class DisclosureTracker:
    """Tracks disclosure reports and SLA compliance. Implements ENT5-R5.

    SLA rules:
    - every report MUST be acknowledged within 72 hours of receipt;
    - CRITICAL reports MUST be patched within 14 days of receipt.
    """

    records: dict[str, _Record] = field(default_factory=dict)

    def receive(self, report: DisclosureReport, hour: int) -> None:
        """Register an incoming report from a security researcher. Implements ENT5-R5."""
        if not isinstance(report, DisclosureReport):
            raise ContractError("report must be a DisclosureReport")
        _check_hour(hour)
        if report.report_id in self.records:
            raise ContractError("duplicate report_id")
        self.records[report.report_id] = _Record(report=report, received_hour=hour)

    def acknowledge(self, report_id: str, hour: int) -> None:
        """Acknowledge a report (72-hour SLA). Implements ENT5-R5."""
        rec = self._record(report_id)
        _check_hour(hour)
        if hour < rec.received_hour:
            raise ContractError("acknowledgement before receipt")
        if rec.acknowledged_hour is not None:
            raise ContractError("report already acknowledged")
        rec.acknowledged_hour = hour

    def mark_patched(self, report_id: str, hour: int) -> None:
        """Mark a report patched (14-day SLA for CRITICAL). Implements ENT5-R5."""
        rec = self._record(report_id)
        _check_hour(hour)
        if hour < rec.received_hour:
            raise ContractError("patch before receipt")
        if rec.patched_hour is not None:
            raise ContractError("report already patched")
        rec.patched_hour = hour

    def ack_sla_met(self, report_id: str) -> bool:
        """True if acknowledged within 72 hours. Implements ENT5-R5."""
        rec = self._record(report_id)
        return (
            rec.acknowledged_hour is not None
            and rec.acknowledged_hour - rec.received_hour <= ACK_SLA_HOURS
        )

    def patch_sla_met(self, report_id: str) -> bool:
        """True if patched within SLA (14 days for CRITICAL). Implements ENT5-R5."""
        rec = self._record(report_id)
        if rec.report.severity != Severity.CRITICAL:
            return rec.patched_hour is not None
        return (
            rec.patched_hour is not None
            and rec.patched_hour - rec.received_hour <= CRITICAL_PATCH_SLA_HOURS
        )

    def overdue_acknowledgements(self, current_hour: int) -> list[str]:
        """Report IDs past the 72-hour ack SLA. Implements ENT5-R5."""
        _check_hour(current_hour)
        return sorted(
            rid
            for rid, rec in self.records.items()
            if rec.acknowledged_hour is None
            and current_hour - rec.received_hour > ACK_SLA_HOURS
        )

    def overdue_critical_patches(self, current_hour: int) -> list[str]:
        """CRITICAL report IDs past the 14-day patch SLA. Implements ENT5-R5."""
        _check_hour(current_hour)
        return sorted(
            rid
            for rid, rec in self.records.items()
            if rec.report.severity == Severity.CRITICAL
            and rec.patched_hour is None
            and current_hour - rec.received_hour > CRITICAL_PATCH_SLA_HOURS
        )

    def compliance_report(self, current_hour: int) -> dict:
        """Summary of disclosure-program SLA compliance. Implements ENT5-R5."""
        _check_hour(current_hour)
        return {
            "total_reports": len(self.records),
            "ack_sla_hours": ACK_SLA_HOURS,
            "critical_patch_sla_hours": CRITICAL_PATCH_SLA_HOURS,
            "ack_sla_met": {
                rid: self.ack_sla_met(rid) for rid in sorted(self.records)
            },
            "patch_sla_met": {
                rid: self.patch_sla_met(rid)
                for rid in sorted(self.records)
                if self.records[rid].patched_hour is not None
            },
            "overdue_acknowledgements": self.overdue_acknowledgements(current_hour),
            "overdue_critical_patches": self.overdue_critical_patches(current_hour),
        }

    def _record(self, report_id: str) -> _Record:
        try:
            return self.records[report_id]
        except KeyError:
            raise ContractError(f"unknown report_id {report_id!r}")


def _check_hour(hour: int) -> None:
    if type(hour) is not int or hour < 0:
        raise ContractError("hour must be a nonnegative int")
