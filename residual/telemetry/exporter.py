"""Prometheus-compatible text export (OBS-R2).

IMPORTANT: the Prometheus exposition is a derived, best-effort view of the
telemetry registry. It is NOT authoritative state; the raw observations
retained by TelemetryCollector are the only authoritative evidence. Control
decisions and reliability reports MUST NOT consume this export.
"""
from __future__ import annotations

from residual.observability.exporter import render_prometheus

from .metric_families import TelemetryCollector, build_telemetry_registry

AUTHORITATIVE = False  # Prometheus export is never authoritative state.


def render_telemetry_prometheus(collector: TelemetryCollector) -> str:
    """Render the collector's registry in Prometheus text exposition format."""
    return render_prometheus(collector.registry)


__all__ = ["render_telemetry_prometheus", "render_prometheus",
           "build_telemetry_registry", "AUTHORITATIVE"]
