"""Metric families required by OBS-R1, built on residual.observability.

Families:
  execution, acceptance, rejection, verification, integration, conflicts,
  retries, resource consumption, orchestration timing.

These metrics are a derived, non-authoritative view (OBS-R2). The raw
observations retained by TelemetryCollector are the authoritative input
for reliability reports.
"""
from __future__ import annotations

from residual.observability.metrics import Counter, Gauge, Histogram, MetricsRegistry

from .labels import LabelSanitizer
from .schema import (
    ALL_KINDS,
    KIND_ACCEPTANCE,
    KIND_CONFLICT,
    KIND_EXECUTION,
    KIND_INTEGRATION,
    KIND_ORCHESTRATION_TIMING,
    KIND_REJECTION,
    KIND_RESOURCE,
    KIND_RETRY,
    KIND_VERIFICATION,
)

PHASE_BUCKETS = (0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 30.0, 120.0, float("inf"))

METRIC_PREFIX = "residual_obs"


def build_telemetry_registry() -> MetricsRegistry:
    """Create a registry containing every OBS-R1 metric family."""
    registry = MetricsRegistry()
    registry.metrics.update({
        # execution
        f"{METRIC_PREFIX}_executions_total": (Counter(), ("task_class", "outcome")),
        # acceptance
        f"{METRIC_PREFIX}_acceptances_total": (Counter(), ("task_class",)),
        # rejection
        f"{METRIC_PREFIX}_rejections_total": (Counter(), ("task_class", "reason")),
        # verification
        f"{METRIC_PREFIX}_verifications_total": (Counter(), ("task_class", "verdict")),
        f"{METRIC_PREFIX}_verification_seconds": (Histogram(PHASE_BUCKETS), ("task_class",)),
        # integration
        f"{METRIC_PREFIX}_integrations_total": (Counter(), ("result",)),
        # conflicts
        f"{METRIC_PREFIX}_conflicts_total": (Counter(), ("conflict_kind",)),
        # retries
        f"{METRIC_PREFIX}_retries_total": (Counter(), ("task_class",)),
        # resource consumption
        f"{METRIC_PREFIX}_resource_units_total": (Counter(), ("resource",)),
        # orchestration timing (OBS-R5: one series per phase)
        f"{METRIC_PREFIX}_phase_seconds": (Histogram(PHASE_BUCKETS), ("phase",)),
        # evidence completeness (OBS-R6)
        f"{METRIC_PREFIX}_observations_complete_total": (Gauge(), ("kind",)),
        f"{METRIC_PREFIX}_observations_missing_fields_total": (Gauge(), ("kind",)),
    })
    return registry


class TelemetryCollector:
    """Ingests raw observations, updates bounded-cardinality metrics, and
    retains the raw observations as authoritative evidence for reporting."""

    def __init__(self, registry=None, sanitizer=None):
        from .schema import validate_observation

        self.registry = registry or build_telemetry_registry()
        self.sanitizer = sanitizer or LabelSanitizer()
        self.observations = []  # authoritative raw evidence
        self._validate = validate_observation

    def _lv(self, metric_name: str, labels: dict) -> tuple:
        """Sanitize label dict and return values in declared label order."""
        clean = self.sanitizer.sanitize(labels)
        return tuple(clean[k] for k in self.registry.label_names(metric_name))

    def ingest(self, observation: dict) -> dict:
        """Validate + record one raw observation and update derived metrics."""
        obs = self._validate(observation)
        self.observations.append(dict(obs))
        kind = obs["kind"]
        m = self.registry.metrics
        if kind == KIND_EXECUTION:
            m[f"{METRIC_PREFIX}_executions_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_executions_total", {"task_class": obs["task_class"], "outcome": obs["outcome"]}))
        elif kind == KIND_ACCEPTANCE:
            m[f"{METRIC_PREFIX}_acceptances_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_acceptances_total", {"task_class": obs["task_class"]}))
        elif kind == KIND_REJECTION:
            m[f"{METRIC_PREFIX}_rejections_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_rejections_total", {"task_class": obs["task_class"], "reason": obs["reason"]}))
        elif kind == KIND_VERIFICATION:
            m[f"{METRIC_PREFIX}_verifications_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_verifications_total", {"task_class": obs["task_class"], "verdict": obs["verdict"]}))
            m[f"{METRIC_PREFIX}_verification_seconds"][0].observe(
                self._lv(f"{METRIC_PREFIX}_verification_seconds", {"task_class": obs["task_class"]}),
                obs["verification_seconds"])
        elif kind == KIND_INTEGRATION:
            m[f"{METRIC_PREFIX}_integrations_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_integrations_total", {"result": obs["result"]}))
        elif kind == KIND_CONFLICT:
            m[f"{METRIC_PREFIX}_conflicts_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_conflicts_total", {"conflict_kind": obs["conflict_kind"]}))
        elif kind == KIND_RETRY:
            m[f"{METRIC_PREFIX}_retries_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_retries_total", {"task_class": obs["task_class"]}))
        elif kind == KIND_RESOURCE:
            m[f"{METRIC_PREFIX}_resource_units_total"][0].inc(
                self._lv(f"{METRIC_PREFIX}_resource_units_total", {"resource": obs["resource"]}), obs["amount"])
        elif kind == KIND_ORCHESTRATION_TIMING:
            m[f"{METRIC_PREFIX}_phase_seconds"][0].observe(
                self._lv(f"{METRIC_PREFIX}_phase_seconds", {"phase": obs["phase"]}), obs["seconds"])
        # evidence completeness gauges (per kind)
        missing = sum(1 for f in _tracked_optional(kind) if f not in obs)
        complete_key = self._lv(f"{METRIC_PREFIX}_observations_complete_total", {"kind": kind})
        m[f"{METRIC_PREFIX}_observations_complete_total"][0].inc(complete_key)
        if missing:
            m[f"{METRIC_PREFIX}_observations_missing_fields_total"][0].inc(
                complete_key, missing)
        return obs


def _tracked_optional(kind: str) -> tuple:
    """Optional fields tracked for missing-data accounting, per kind."""
    return {
        KIND_EXECUTION: ("correct", "tokens_input", "tokens_output"),
        KIND_ACCEPTANCE: ("correct",),
        KIND_REJECTION: (),
        KIND_VERIFICATION: ("verifier_identity",),
        KIND_INTEGRATION: ("strategy",),
        KIND_CONFLICT: ("resolution",),
        KIND_RETRY: ("cause",),
        KIND_RESOURCE: (),
        KIND_ORCHESTRATION_TIMING: (),
    }.get(kind, ())


assert set(ALL_KINDS) == {
    KIND_EXECUTION, KIND_ACCEPTANCE, KIND_REJECTION, KIND_VERIFICATION,
    KIND_INTEGRATION, KIND_CONFLICT, KIND_RETRY, KIND_RESOURCE,
    KIND_ORCHESTRATION_TIMING,
}
