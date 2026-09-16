"""Track F (N9-R18, N9-R22): node capability advertisement.

Each node MUST advertise models, throughput (tok/s), context window,
memory, and GPU count. Aggregate capacity MUST be computable across the
registry for ``residual cluster status``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    models: tuple[str, ...] = ()
    tokens_per_second: float = 0.0
    context_window: int = 0
    memory_bytes: int = 0
    gpus: int = 0
    workers: int = 1

    def to_dict(self) -> dict:
        return {
            "models": list(self.models),
            "tokens_per_second": self.tokens_per_second,
            "context_window": self.context_window,
            "memory_bytes": self.memory_bytes,
            "gpus": self.gpus,
            "workers": self.workers,
        }

    @classmethod
    def from_dict(cls, obj: dict) -> "Capability":
        if not isinstance(obj, dict):
            raise ValueError("capability must be an object")
        return cls(
            models=tuple(str(m) for m in obj.get("models", ())),
            tokens_per_second=float(obj.get("tokens_per_second", 0.0)),
            context_window=int(obj.get("context_window", 0)),
            memory_bytes=int(obj.get("memory_bytes", 0)),
            gpus=int(obj.get("gpus", 0)),
            workers=int(obj.get("workers", 1)),
        )

    def supports_model(self, model: str | None) -> bool:
        return model is None or model in self.models


@dataclass
class NodeRecord:
    node_id: str
    address: str
    capability: Capability
    is_local: bool = False
    joined_at_ns: int = field(default_factory=time.time_ns)
    last_heartbeat_ns: int = field(default_factory=time.time_ns)
    state: str = "active"  # active | leaving | failed
    schema_versions: tuple[int, ...] = ()

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "capability": self.capability.to_dict(),
            "is_local": self.is_local,
            "joined_at_ns": self.joined_at_ns,
            "last_heartbeat_ns": self.last_heartbeat_ns,
            "state": self.state,
            "schema_versions": list(self.schema_versions),
        }

    @classmethod
    def from_dict(cls, obj: dict) -> "NodeRecord":
        return cls(
            node_id=str(obj["node_id"]),
            address=str(obj.get("address", "")),
            capability=Capability.from_dict(obj.get("capability", {})),
            is_local=bool(obj.get("is_local", False)),
            joined_at_ns=int(obj.get("joined_at_ns", 0)),
            last_heartbeat_ns=int(obj.get("last_heartbeat_ns", 0)),
            state=str(obj.get("state", "active")),
            schema_versions=tuple(int(v) for v in obj.get("schema_versions", ())),
        )
