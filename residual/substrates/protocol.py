"""Execution-substrate contracts for RESIDUAL.

Execution engines answer "which agent/framework performs the work?"
Execution substrates answer "under which independently enforced runtime boundary
does that work execute?"  The distinction prevents a sandbox vendor from
becoming an authority source and lets RESIDUAL qualify multiple substrates.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from ..core import ContractError


class SubstrateHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SubstrateRuntimeIdentity:
    """Observed runtime identity independent of qualification verdicts."""

    name: str
    version: str
    source_identity: str
    driver: str
    platform_class: str
    locality: str = "local"

    def __post_init__(self) -> None:
        for field_name in (
            "name", "version", "source_identity", "driver", "platform_class", "locality",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{field_name} is required")
        if self.locality not in {"local", "cluster", "cloud"}:
            raise ContractError("substrate locality must be local, cluster, or cloud")


@runtime_checkable
class ExecutionSubstrate(Protocol):
    """Minimal substrate surface consumed by qualification-aware routing.

    Concrete execution APIs remain adapter-specific. The generic control plane
    intentionally requires only identity and health so it cannot accidentally
    infer authority or capabilities from vendor-specific success responses.
    """

    name: str
    version: str
    locality: str

    def substrate_identity(self) -> SubstrateRuntimeIdentity: ...
    def substrate_health(self) -> SubstrateHealth: ...
