"""SLM-06 economic telemetry: per-call cost/latency/energy instrumentation
and routing decision-context capture with labeled counterfactual estimates.

Aligned to eval-protocol-v1.0.0 (frozen metric names) and slm-observation-v0
cost block field names. Config-gated, fail-open, every degradation logged.
"""
from .recorder import (
    FROZEN_METRIC_NAMES,
    PRICE_TABLE_VERSION_DEFAULT,
    SLM_TELEMETRY_SCHEMA_VERSION,
    PriceTable,
    Recorder,
    TelemetryConfig,
)
from .decision import DecisionContextRecorder
from .power import (
    NoneSampler,
    NvidiaSmiPowerSampler,
    NvmlPowerSampler,
    default_power_sampler,
)

__all__ = [
    "FROZEN_METRIC_NAMES", "PRICE_TABLE_VERSION_DEFAULT",
    "SLM_TELEMETRY_SCHEMA_VERSION", "PriceTable", "Recorder",
    "TelemetryConfig", "DecisionContextRecorder",
    "NoneSampler", "NvidiaSmiPowerSampler", "NvmlPowerSampler",
    "default_power_sampler",
]
