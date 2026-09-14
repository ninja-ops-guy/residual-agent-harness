"""Research experiment analysis for Residual."""

from .adapters import (
    EvidenceAdapterError,
    external_market_observations,
    factory_result_observation,
    study_observations,
)
from .degradation import DegradationProfile, DegradingExecutionEngine
from .reliability import (
    ReliabilityManifest,
    TrialObservation,
    analyze_reliability,
    load_manifest,
    load_observations,
    render_markdown,
    write_artifacts,
)

__all__ = [
    "EvidenceAdapterError",
    "external_market_observations",
    "factory_result_observation",
    "study_observations",
    "DegradationProfile",
    "DegradingExecutionEngine",
    "ReliabilityManifest",
    "TrialObservation",
    "analyze_reliability",
    "load_manifest",
    "load_observations",
    "render_markdown",
    "write_artifacts",
]
