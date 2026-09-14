from .metrics import Counter, Gauge, Histogram, MetricsRegistry
from .exporter import render_prometheus
from .bridge import ObservationMetricsBridge
from .logging import structured_event
from .http import MetricsEndpoint

# Process-wide station registry. It is updated only by observation/lifecycle events;
# core control decisions never consult these metrics.
DEFAULT_METRICS = MetricsRegistry()
DEFAULT_BRIDGE = ObservationMetricsBridge(DEFAULT_METRICS)

__all__ = [
    "Counter", "Gauge", "Histogram", "MetricsRegistry", "render_prometheus",
    "ObservationMetricsBridge", "structured_event", "MetricsEndpoint",
    "DEFAULT_METRICS", "DEFAULT_BRIDGE",
]
