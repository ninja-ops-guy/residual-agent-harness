"""Monitoring connectors: Datadog, New Relic, Dynatrace, Prometheus.

Implements ENT6-R3: metrics export, health check endpoints, alert
generation on brake trips and HITL escalations, and distributed tracing
context propagation.
Implements ENT6-R6 (bidirectional) and ENT6-R7 (via IntegrationConnector).
"""
from __future__ import annotations

import uuid
from typing import Any

from ..core import ContractError
from .base import IntegrationConnector, ConnectorReceipt, TransportResponse


class MonitoringConnector(IntegrationConnector):
    """Generic monitoring connector. Implements ENT6-R3, ENT6-R6, ENT6-R7."""

    system_name = "monitoring"
    metrics_path = "/api/v1/metrics"
    events_path = "/api/v1/events"

    def new_trace_context(self) -> dict:
        """Create a distributed tracing context. Implements ENT6-R3."""
        return {"trace_id": uuid.uuid4().hex, "span_id": uuid.uuid4().hex[:16]}

    def _trace_headers(self, trace_context: dict | None) -> dict[str, str]:
        if not trace_context:
            return {}
        ctx = dict(trace_context)
        ctx.setdefault("trace_id", uuid.uuid4().hex)
        ctx.setdefault("span_id", uuid.uuid4().hex[:16])
        return {"traceparent": f"00-{ctx['trace_id']}-{ctx['span_id']}-01"}

    def export_metrics(self, metrics: list[dict],
                       trace_context: dict | None = None) -> TransportResponse:
        """Export metrics with tracing context propagation. Implements ENT6-R3."""
        if not isinstance(metrics, list) or not metrics:
            raise ContractError("metrics export requires a nonempty list")
        resp = self.call("POST", self.metrics_path, {"series": metrics},
                         headers=self._trace_headers(trace_context))
        self.require_ok(resp, "metrics export")
        return resp

    def health_check(self) -> dict:
        """Query the platform health endpoint. Implements ENT6-R3 and ENT6-R6."""
        body = self.require_ok(self.call("GET", "/api/v1/health"), "health check")
        return {"system": self.system_name, "status": (body or {}).get("status", "unknown"),
                "raw": body}

    def alert_brake_trip(self, brake_id: str, detail: dict,
                         trace_context: dict | None = None) -> TransportResponse:
        """Generate an alert on a brake trip. Implements ENT6-R3."""
        return self._alert(f"Residual brake trip: {brake_id}", "error", detail, trace_context)

    def alert_hitl_escalation(self, escalation_id: str, detail: dict,
                              trace_context: dict | None = None) -> TransportResponse:
        """Generate an alert on a HITL escalation. Implements ENT6-R3."""
        return self._alert(f"Residual HITL escalation: {escalation_id}", "warning",
                           detail, trace_context)

    def _alert(self, title: str, severity: str, detail: dict,
               trace_context: dict | None) -> TransportResponse:
        resp = self.call("POST", self.events_path,
                         {"title": title, "alert_type": severity, "tags": detail},
                         headers=self._trace_headers(trace_context))
        self.require_ok(resp, "alert generation")
        return resp

    def import_task(self, external_id: str) -> dict:
        body = self.require_ok(self.call("GET", f"{self.events_path}/{external_id}"),
                               "event fetch")
        return {"external_id": external_id, "source": self.system_name,
                "goal": (body or {}).get("title", ""), "raw": body}

    def post_receipt(self, external_id: str, receipt: ConnectorReceipt) -> TransportResponse:
        resp = self.call("POST", self.events_path,
                         {"title": f"Residual receipt for {external_id}",
                          "alert_type": "info", "receipt": receipt.to_dict()})
        self.require_ok(resp, "receipt event")
        return resp

    def sync_status(self, external_id: str, task_status: str) -> TransportResponse:
        return self.call("POST", self.events_path,
                         {"title": f"Residual task {external_id} status",
                          "alert_type": "info", "tags": {"status": task_status}})


class DatadogConnector(MonitoringConnector):
    """Datadog connector. Implements ENT6-R3, ENT6-R6, ENT6-R7."""

    system_name = "datadog"
    metrics_path = "/api/v2/series"
    events_path = "/api/v1/events"


class NewRelicConnector(MonitoringConnector):
    """New Relic connector. Implements ENT6-R3, ENT6-R6, ENT6-R7."""

    system_name = "newrelic"
    metrics_path = "/metric/v1"
    events_path = "/v2/events"


class DynatraceConnector(MonitoringConnector):
    """Dynatrace connector. Implements ENT6-R3, ENT6-R6, ENT6-R7."""

    system_name = "dynatrace"
    metrics_path = "/api/v2/metrics/ingest"
    events_path = "/api/v1/events"


class PrometheusConnector(MonitoringConnector):
    """Prometheus connector. Implements ENT6-R3, ENT6-R6, ENT6-R7."""

    system_name = "prometheus"
    metrics_path = "/api/v1/write"
    events_path = "/api/v1/alerts"

    def health_check(self) -> dict:
        body = self.require_ok(self.call("GET", "/-/healthy"), "prometheus health")
        return {"system": self.system_name,
                "status": (body or {}).get("status", "ok") if isinstance(body, dict) else "ok",
                "raw": body}
