"""Framework-neutral execution-engine contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable

from ..core import ContractError, digest
from ..receipts import StationReceipt


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


@dataclass(frozen=True)
class EngineExecutionReceipt:
    """Engine provenance bound to an otherwise unchanged StationReceipt.

    Optional outer provenance for historical v1 and current v2 StationReceipts.
    New v2 station receipts also bind engine identity in their own payload.
    Neither envelope makes an engine result authoritative.
    """
    station_receipt: StationReceipt
    engine_name: str
    engine_version: str

    def __post_init__(self):
        if not isinstance(self.station_receipt, StationReceipt):
            raise ContractError("engine receipt requires a StationReceipt")
        for field_name, value in (("engine_name", self.engine_name), ("engine_version", self.engine_version)):
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{field_name} is required")

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.engine.receipt.v1",
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "station_receipt_hash": self.station_receipt.receipt_hash,
        }

    @property
    def receipt_hash(self) -> str:
        return digest(self.payload())


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
