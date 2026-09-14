from .metrics import Counter, Gauge, Histogram, MetricsRegistry
from .exporter import render_prometheus
from .bridge import ObservationMetricsBridge
from .logging import structured_event
from .http import MetricsEndpoint
from .completeness import (
    CompletenessFinding, CompletenessReport, check_registry_completeness,
)
from .slo import DEFAULT_SLOS, SLODefinition, SLOStatus, evaluate_slos
from .alerts import DEFAULT_ALERT_RULES, AlertEvent, AlertRule, evaluate_alerts
from .correlation import (
    CorrelationContext, TraceReceiptIndex, new_span_id, new_trace_id,
)

# Process-wide station registry. It is updated only by observation/lifecycle events;
# core control decisions never consult these metrics.
DEFAULT_METRICS = MetricsRegistry()
DEFAULT_BRIDGE = ObservationMetricsBridge(DEFAULT_METRICS)

__all__ = [
    "Counter", "Gauge", "Histogram", "MetricsRegistry", "render_prometheus",
    "ObservationMetricsBridge", "structured_event", "MetricsEndpoint",
    "DEFAULT_METRICS", "DEFAULT_BRIDGE",
    "CompletenessFinding", "CompletenessReport", "check_registry_completeness",
    "DEFAULT_SLOS", "SLODefinition", "SLOStatus", "evaluate_slos",
    "DEFAULT_ALERT_RULES", "AlertEvent", "AlertRule", "evaluate_alerts",
    "CorrelationContext", "TraceReceiptIndex", "new_span_id", "new_trace_id",
]
