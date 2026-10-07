from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .probe import CapabilityProbeSuite, ProbeResult
from .protocol import ExecutionEngine

@dataclass(frozen=True)
class RegisteredEngine:
    engine: ExecutionEngine
    probe: ProbeResult

class CapabilityRouter:
    def __init__(self, probe_suite: CapabilityProbeSuite | None = None):
        self._probe = probe_suite or CapabilityProbeSuite()
        self._engines: dict[str, RegisteredEngine] = {}
    def register(self, engine: ExecutionEngine, capabilities: Iterable[str]) -> None:
        key = f"{engine.name}@{engine.version}"
        if key in self._engines: raise ValueError(f"duplicate engine registration: {key}")
        probe = self._probe.validate(engine, tuple(capabilities))
        if not probe.healthy: raise ValueError(f"engine probe failed: {key}")
        self._engines[key] = RegisteredEngine(engine, probe)
    def select(self, capability: str) -> ExecutionEngine:
        candidates = [r.engine for r in self._engines.values() if r.probe.healthy and capability in r.probe.capabilities]
        if not candidates: raise LookupError(f"no healthy engine supports {capability}")
        return sorted(candidates, key=lambda e: (0 if getattr(e, "locality", "cloud") == "local" else 1, e.name, e.version))[0]
    def snapshot(self):
        return tuple(sorted((r.engine.name, r.engine.version, r.probe.capabilities) for r in self._engines.values()))
