"""RUN-R2 / RUN-R3: capability-probed, fail-closed, deterministic routing.

Wraps ``residual.engines.router.CapabilityRouter`` (which already probes at
registration and prefers local engines with a name/version tie-break) and
adds an explicit pre-dispatch probe: the declared capability is re-checked
against a fresh probe at route time, and any mismatch or degraded health
fails closed with :class:`RoutingError` instead of dispatching.
"""
from __future__ import annotations

from typing import Iterable

from ..engines.probe import CapabilityProbeSuite
from ..engines.protocol import EngineHealth, ExecutionEngine
from ..engines.router import CapabilityRouter


class RoutingError(LookupError):
    """Fail-closed routing outcome: no dispatch may occur after this raise."""


class RuntimeCapabilityRouter:
    """Fail-closed router over the existing CapabilityRouter."""

    def __init__(self, probe_suite: CapabilityProbeSuite | None = None):
        self._probe_suite = probe_suite or CapabilityProbeSuite()
        self._router = CapabilityRouter(self._probe_suite)
        self._declared: dict[str, frozenset[str]] = {}

    def register(self, engine: ExecutionEngine, capabilities: Iterable[str]) -> None:
        caps = frozenset(capabilities)
        if not caps:
            raise RoutingError("declared capability set must be non-empty")
        self._router.register(engine, caps)
        self._declared[f"{engine.name}@{engine.version}"] = caps

    def route(self, capability: str) -> ExecutionEngine:
        """Probe the declared capability, then route; fail closed on mismatch."""
        if not capability or not isinstance(capability, str):
            raise RoutingError("capability must be a non-empty string")
        try:
            engine = self._router.select(capability)
        except LookupError as exc:
            raise RoutingError(str(exc)) from exc
        key = f"{engine.name}@{engine.version}"
        declared = self._declared.get(key, frozenset())
        # Pre-dispatch probe: fresh validation of the selected engine.
        probe = self._probe_suite.validate(engine, tuple(sorted(declared)))
        if not probe.healthy or engine.health() == EngineHealth.UNAVAILABLE:
            raise RoutingError(f"engine unhealthy at dispatch: {key}")
        if capability not in probe.capabilities or capability not in declared:
            raise RoutingError(f"capability probe mismatch at dispatch: {capability} vs {key}")
        return engine

    def snapshot(self):
        return self._router.snapshot()
