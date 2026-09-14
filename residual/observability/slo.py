"""SLO definitions as data plus evaluation (Track N, N-R2).

Additive module. SLOs are declarative dataclasses covering latency, error
rate, and receipt integrity; ``evaluate_slos`` computes current compliance
from a ``MetricsRegistry`` snapshot.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..core import ContractError
from .metrics import MetricsRegistry


@dataclass(frozen=True)
class SLODefinition:
    """One service-level objective. Requirement N-R2.

    kind:
      - "latency":   fraction of histogram observations at or below
                     ``threshold`` seconds must be >= ``target``.
      - "error_rate": failures / (failures + successes) must be <= ``threshold``.
      - "receipt_integrity": verified receipts / all receipts must be >= ``target``.
    """

    slo_id: str
    kind: str
    target: float
    description: str
    threshold: float = 0.0
    window_seconds: int = 86400
    metric: str = ""

    def __post_init__(self):
        if self.kind not in ("latency", "error_rate", "receipt_integrity"):
            raise ContractError(f"unknown SLO kind {self.kind!r}")
        if not (0.0 < self.target <= 1.0):
            raise ContractError("SLO target must be in (0, 1]")
        if self.threshold < 0:
            raise ContractError("SLO threshold must be nonnegative")

    def to_dict(self) -> dict:
        return asdict(self)


# Declarative SLO catalog (N-R2). Values are defaults; deployments MAY tune
# thresholds but MUST keep all three kinds defined.
DEFAULT_SLOS: tuple[SLODefinition, ...] = (
    SLODefinition(
        slo_id="slo.verification.latency",
        kind="latency",
        target=0.99,
        threshold=2.5,  # seconds
        metric="residual_verification_duration_seconds",
        description="99% of verification runs complete within 2.5s",
    ),
    SLODefinition(
        slo_id="slo.engine.error_rate",
        kind="error_rate",
        target=0.999,
        threshold=0.001,  # max allowed error fraction
        metric="residual_engine_executions_total",
        description="engine execution error rate below 0.1%",
    ),
    SLODefinition(
        slo_id="slo.receipt.integrity",
        kind="receipt_integrity",
        target=1.0,
        metric="residual_receipts_issued_total",
        description="every issued receipt verifies (no invalid verdicts)",
    ),
)


@dataclass(frozen=True)
class SLOStatus:
    slo_id: str
    kind: str
    compliant: bool
    observed: float
    target: float
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _histogram_fraction_within(registry: MetricsRegistry, metric: str,
                               threshold: float) -> tuple[float, str]:
    histogram = registry.metrics[metric][0]
    total = sum(d["count"] for d in histogram.samples().values())
    if total == 0:
        return 1.0, "no observations; vacuously compliant"
    # Buckets are cumulative: the count at the first bound >= threshold
    # already includes every observation at or below the threshold.
    within = 0.0
    for data in histogram.samples().values():
        for bound, count in zip(histogram.buckets, data["buckets"]):
            if bound >= threshold:
                within += count
                break
        else:
            within += data["count"]
    return within / total, f"{within:.0f}/{total} observations <= {threshold}s"


def _error_rate(registry: MetricsRegistry, metric: str) -> tuple[float, str]:
    counter = registry.metrics[metric][0]
    failures = successes = 0.0
    for labels, value in counter.samples().items():
        outcome = labels[-1] if labels else ""
        if outcome in ("failure", "error", "rejected", "invalid"):
            failures += value
        else:
            successes += value
    total = failures + successes
    if total == 0:
        return 1.0, "no executions; vacuously compliant"
    return successes / total, f"{failures:.0f}/{total:.0f} executions failed"


def _receipt_integrity(registry: MetricsRegistry, metric: str) -> tuple[float, str]:
    counter = registry.metrics[metric][0]
    valid = invalid = 0.0
    for labels, value in counter.samples().items():
        verdict = labels[0] if labels else ""
        if verdict in ("invalid", "forged", "stale", "rejected"):
            invalid += value
        else:
            valid += value
    total = valid + invalid
    if total == 0:
        return 1.0, "no receipts; vacuously compliant"
    return valid / total, f"{invalid:.0f}/{total:.0f} receipts failed integrity"


def evaluate_slos(registry: MetricsRegistry | None = None,
                  slos: tuple[SLODefinition, ...] = DEFAULT_SLOS) -> list[SLOStatus]:
    """Evaluate each SLO against current registry samples (N-R2)."""
    if registry is None:
        from . import DEFAULT_METRICS
        registry = DEFAULT_METRICS
    statuses: list[SLOStatus] = []
    for slo in slos:
        if slo.metric not in registry.metrics:
            statuses.append(SLOStatus(slo.slo_id, slo.kind, False, 0.0, slo.target,
                                      f"metric {slo.metric!r} not registered"))
            continue
        if slo.kind == "latency":
            observed, detail = _histogram_fraction_within(registry, slo.metric, slo.threshold)
            compliant = observed >= slo.target
        elif slo.kind == "error_rate":
            observed, detail = _error_rate(registry, slo.metric)
            compliant = (1.0 - observed) <= slo.threshold
        else:
            observed, detail = _receipt_integrity(registry, slo.metric)
            compliant = observed >= slo.target
        statuses.append(SLOStatus(slo.slo_id, slo.kind, compliant, observed, slo.target, detail))
    return statuses
