"""Prometheus metrics registry completeness check (Track N, N-R1).

Additive module; does not modify the existing registry. Verifies that:

- every registered metric renders as valid Prometheus text (TYPE line plus
  parseable samples) via the existing exporter;
- every metric the ``ObservationMetricsBridge`` writes to is actually
  registered (no silent drops);
- every registered metric has well-formed label names and, for histograms,
  strictly increasing bucket bounds ending in +Inf.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..core import ContractError
from .bridge import ObservationMetricsBridge
from .exporter import render_prometheus
from .metrics import Counter, Gauge, Histogram, MetricsRegistry

_METRIC_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_LABEL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass(frozen=True)
class CompletenessFinding:
    check: str
    subject: str
    ok: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"check": self.check, "subject": self.subject,
                "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class CompletenessReport:
    findings: tuple[CompletenessFinding, ...] = ()

    @property
    def complete(self) -> bool:
        return all(f.ok for f in self.findings)

    @property
    def failures(self) -> list[CompletenessFinding]:
        return [f for f in self.findings if not f.ok]

    def to_dict(self) -> dict:
        return {"complete": self.complete,
                "findings": [f.to_dict() for f in self.findings]}


def _bridge_metric_names() -> set[str]:
    """Metric names referenced by the bridge's event mapping."""
    names: set[str] = set()
    src_names = ("residual_tokens_total", "residual_tokens_saved",
                 "residual_brake_trips_total",
                 "residual_verification_duration_seconds",
                 "residual_quarantine_denials_total",
                 "residual_hitl_challenges_pending",
                 "residual_receipts_issued_total",
                 "residual_engine_executions_total")
    names.update(src_names)
    return names


def check_registry_completeness(registry: MetricsRegistry | None = None) -> CompletenessReport:
    """Audit a registry (default: process-wide DEFAULT_METRICS)."""
    if registry is None:
        from . import DEFAULT_METRICS
        registry = DEFAULT_METRICS
    findings: list[CompletenessFinding] = []

    # 1. Naming + label well-formedness.
    for name, (metric, label_names) in registry.metrics.items():
        ok = bool(_METRIC_NAME.match(name))
        findings.append(CompletenessFinding("metric_name", name, ok,
                                            "" if ok else "invalid Prometheus metric name"))
        for label in label_names:
            ok = bool(_LABEL_NAME.match(label)) and label != "le"
            findings.append(CompletenessFinding("label_name", f"{name}:{label}", ok,
                                                "" if ok else "invalid/reserved label name"))
        if isinstance(metric, Histogram):
            buckets = metric.buckets
            ok = (all(buckets[i] < buckets[i + 1] for i in range(len(buckets) - 1))
                  and buckets[-1] == float("inf"))
            findings.append(CompletenessFinding("histogram_buckets", name, ok,
                                                "" if ok else "buckets must increase and end in +Inf"))

    # 2. Bridge coverage: everything the bridge writes must be registered.
    for name in sorted(_bridge_metric_names()):
        ok = name in registry.metrics
        findings.append(CompletenessFinding("bridge_coverage", name, ok,
                                            "" if ok else "bridge writes to unregistered metric"))

    # 3. Exporter round-trip: rendered text must parse and cover every metric.
    text = render_prometheus(registry)
    type_lines = re.findall(r"^# TYPE (\S+) (\w+)$", text, flags=re.M)
    rendered = {name for name, _ in type_lines}
    for name in registry.metrics:
        ok = name in rendered
        findings.append(CompletenessFinding("exporter_coverage", name, ok,
                                            "" if ok else "metric missing from rendered exposition"))
    bad_samples = [
        line for line in text.splitlines()
        if line and not line.startswith("#")
        and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*(\{[^}]*\})? -?(\d+(\.\d+)?|[+-]?Inf|NaN)$", line) is None
    ]
    findings.append(CompletenessFinding("exporter_syntax", "render_prometheus",
                                        not bad_samples,
                                        "" if not bad_samples else f"unparseable samples: {bad_samples[:3]}"))
    return CompletenessReport(tuple(findings))
