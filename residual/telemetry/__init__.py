"""Reliability telemetry for SPEC-SWARM-OBS-006.

Raw observations are authoritative; metrics and Prometheus exports are
derived, non-authoritative views (OBS-R2). Reliability reports recompute
all paper-facing metrics from raw observations alone (OBS-R4).
"""
from .schema import (
    ALL_KINDS,
    ALL_PHASES,
    OBSERVATION_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    EvidenceError,
    hash_observations,
    validate_observation,
)
from .labels import LabelCardinalityError, LabelSanitizer
from .metric_families import TelemetryCollector, build_telemetry_registry
from .report import build_reliability_report
from .exporter import render_telemetry_prometheus
from .fixtures import FIXTURE_ID, build_fixture_observations

__all__ = [
    "ALL_KINDS", "ALL_PHASES", "OBSERVATION_SCHEMA_VERSION",
    "REPORT_SCHEMA_VERSION", "EvidenceError", "hash_observations",
    "validate_observation", "LabelCardinalityError", "LabelSanitizer",
    "TelemetryCollector", "build_telemetry_registry",
    "build_reliability_report", "render_telemetry_prometheus",
    "FIXTURE_ID", "build_fixture_observations",
]
