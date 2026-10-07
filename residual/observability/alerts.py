"""Alert rules as data plus evaluation (Track N, N-R3).

Additive module. Alert rules are declarative; ``evaluate_alerts`` fires rules
against a ``MetricsRegistry`` snapshot and SLO statuses. Rules are expressed
in Prometheus-like form so they can be exported verbatim to an alerting
pipeline.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from ..core import ContractError
from .metrics import MetricsRegistry
from .slo import SLOStatus


@dataclass(frozen=True)
class AlertRule:
    """One alert rule. Requirement N-R3.

    ``expr`` is a Prometheus-style expression for documentation/export;
    evaluation uses ``metric``/``comparator``/``threshold`` against the sum
    of the metric's samples (or a provided SLO status).
    """

    alert_id: str
    severity: str  # "page" | "ticket" | "info"
    metric: str
    comparator: str  # ">" | ">=" | "<" | "<="
    threshold: float
    expr: str
    summary: str
    for_seconds: int = 0

    def __post_init__(self):
        if self.severity not in ("page", "ticket", "info"):
            raise ContractError("alert severity must be page/ticket/info")
        if self.comparator not in (">", ">=", "<", "<="):
            raise ContractError("invalid alert comparator")

    def fires(self, value: float) -> bool:
        return {
            ">": value > self.threshold,
            ">=": value >= self.threshold,
            "<": value < self.threshold,
            "<=": value <= self.threshold,
        }[self.comparator]

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_ALERT_RULES: tuple[AlertRule, ...] = (
    AlertRule(
        alert_id="alert.verification.slow",
        severity="ticket",
        metric="residual_verification_duration_seconds",
        comparator=">",
        threshold=10.0,
        expr='histogram_quantile(0.99, rate(residual_verification_duration_seconds_bucket[5m])) > 10',
        summary="p99 verification latency above 10s for 5m",
        for_seconds=300,
    ),
    AlertRule(
        alert_id="alert.quarantine.denials_spike",
        severity="ticket",
        metric="residual_quarantine_denials_total",
        comparator=">",
        threshold=100.0,
        expr='increase(residual_quarantine_denials_total[1h]) > 100',
        summary="quarantine denials spiking (possible attack or misconfigured policy)",
        for_seconds=3600,
    ),
    AlertRule(
        alert_id="alert.receipt.integrity",
        severity="page",
        metric="residual_receipts_issued_total",
        comparator=">",
        threshold=0.0,
        expr='increase(residual_receipts_issued_total{verdict=~"invalid|forged|stale"}[5m]) > 0',
        summary="receipts failing integrity verification — page immediately",
        for_seconds=0,
    ),
    AlertRule(
        alert_id="alert.hitl.backlog",
        severity="info",
        metric="residual_hitl_challenges_pending",
        comparator=">",
        threshold=50.0,
        expr='residual_hitl_challenges_pending > 50',
        summary="HITL challenge backlog above 50",
        for_seconds=1800,
    ),
)


@dataclass(frozen=True)
class AlertEvent:
    alert_id: str
    severity: str
    value: float
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


def _metric_total(registry: MetricsRegistry, metric: str,
                  integrity_only: bool = False) -> float:
    obj, _labels = registry.metrics[metric]
    samples = obj.samples()
    if hasattr(obj, "buckets"):  # histogram: use observation counts
        return sum(d["count"] for d in samples.values())
    total = 0.0
    for labels, value in samples.items():
        if integrity_only:
            verdict = labels[0] if labels else ""
            if verdict not in ("invalid", "forged", "stale", "rejected"):
                continue
        total += value
    return total


def evaluate_alerts(registry: MetricsRegistry | None = None,
                    rules: tuple[AlertRule, ...] = DEFAULT_ALERT_RULES,
                    slo_statuses: list[SLOStatus] | None = None) -> list[AlertEvent]:
    """Evaluate alert rules against current samples. Requirement N-R3."""
    if registry is None:
        from . import DEFAULT_METRICS
        registry = DEFAULT_METRICS
    events: list[AlertEvent] = []
    for rule in rules:
        if rule.metric not in registry.metrics:
            continue
        integrity_only = rule.alert_id == "alert.receipt.integrity"
        value = _metric_total(registry, rule.metric, integrity_only=integrity_only)
        if rule.fires(value):
            events.append(AlertEvent(rule.alert_id, rule.severity, value, rule.summary))
    # SLO breach alerts (N-R3): any non-compliant SLO raises a ticket event.
    for status in slo_statuses or []:
        if not status.compliant:
            events.append(AlertEvent(f"alert.slo.{status.slo_id}", "ticket",
                                     status.observed,
                                     f"SLO {status.slo_id} breached: {status.detail}"))
    return events
