"""SPEC-SWARM-RUNTIME-005: engine + async runtime integration.

Unifies heterogeneous execution engines behind the existing
``residual.engines`` ExecutionEngine contract and adds async-runtime
guarantees: capability-probed fail-closed routing, engine metadata in
receipts/evaluation records, Residual-authoritative HITL/policy,
staleness-aware telemetry, budgeted cancellation, and durable sinks.
"""
from .adapters import LocalDeterministicEngine, SDKFunctionEngine, build_default_adapters
from .router import RoutingError, RuntimeCapabilityRouter
from .records import EngineExecutionRecord, build_execution_record
from .policy import PolicyAuthority, PolicyDecision
from .telemetry import FreshnessGuard, TelemetryReading, TelemetryStatus
from .cancellation import CancellationBudget, CancellationController, CancellationReport
from .sinks import BufferedObservationSink
from .conformance import check_adapter_conformance, ConformanceReport

__all__ = [
    "LocalDeterministicEngine",
    "SDKFunctionEngine",
    "build_default_adapters",
    "RoutingError",
    "RuntimeCapabilityRouter",
    "EngineExecutionRecord",
    "build_execution_record",
    "PolicyAuthority",
    "PolicyDecision",
    "FreshnessGuard",
    "TelemetryReading",
    "TelemetryStatus",
    "CancellationBudget",
    "CancellationController",
    "CancellationReport",
    "BufferedObservationSink",
    "check_adapter_conformance",
    "ConformanceReport",
]
