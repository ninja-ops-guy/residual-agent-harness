"""Framework-neutral execution-engine contracts."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

class EngineHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    capability: str
    input: Any
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ContextAssembly:
    values: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EngineResult:
    candidate: Any
    tool_calls: tuple[Mapping[str, Any], ...] = ()
    token_usage: int | None = None
    wall_clock_ms: int = 0
    engine_trace: tuple[Mapping[str, Any], ...] = ()
    raw_metadata: Mapping[str, Any] = field(default_factory=dict)

@runtime_checkable
class ExecutionEngine(Protocol):
    name: str
    version: str
    capability_class: str
    locality: str
    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult: ...
    def supports(self, capability: str) -> bool: ...
    def health(self) -> EngineHealth: ...
    def normalize(self, raw_output: Any) -> EngineResult: ...
