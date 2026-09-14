from __future__ import annotations
from dataclasses import dataclass
from .protocol import EngineHealth, ExecutionEngine

@dataclass(frozen=True)
class ProbeResult:
    engine_name: str
    engine_version: str
    capabilities: tuple[str, ...]
    healthy: bool

class CapabilityProbeSuite:
    def validate(self, engine: ExecutionEngine, capabilities: tuple[str, ...]) -> ProbeResult:
        ordered = tuple(sorted(set(capabilities)))
        accepted = tuple(c for c in ordered if engine.supports(c))
        return ProbeResult(engine.name, engine.version, accepted, engine.health() != EngineHealth.UNAVAILABLE)
