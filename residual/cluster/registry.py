"""Track F (N9-R22, N9-R23): node registry and local-first routing.

The registry tracks every known node with its capability advertisement.
Aggregate capacity (total GPUs, models, workers, memory) MUST be
computable for ``residual cluster status``. Task routing MUST prefer
local nodes when capability is equal.
"""
from __future__ import annotations

import time
from typing import Iterable

from .capabilities import Capability, NodeRecord


class NodeRegistry:
    def __init__(self):
        self._nodes: dict[str, NodeRecord] = {}

    def upsert(self, record: NodeRecord) -> None:
        self._nodes[record.node_id] = record

    def remove(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)

    def get(self, node_id: str) -> NodeRecord | None:
        return self._nodes.get(node_id)

    def nodes(self, states: Iterable[str] = ("active",)) -> list[NodeRecord]:
        allowed = set(states)
        return [n for n in self._nodes.values() if n.state in allowed]

    def mark_state(self, node_id: str, state: str) -> None:
        rec = self._nodes.get(node_id)
        if rec is not None:
            rec.state = state

    def heartbeat(self, node_id: str, at_ns: int | None = None) -> None:
        rec = self._nodes.get(node_id)
        if rec is not None:
            rec.last_heartbeat_ns = time.time_ns() if at_ns is None else at_ns

    def aggregate_capacity(self) -> dict:
        """N9-R22: aggregate capacity across all active nodes."""
        active = self.nodes()
        models: set[str] = set()
        for n in active:
            models.update(n.capability.models)
        return {
            "nodes": len(active),
            "total_gpus": sum(n.capability.gpus for n in active),
            "total_models": len(models),
            "models": sorted(models),
            "total_workers": sum(n.capability.workers for n in active),
            "total_memory_bytes": sum(n.capability.memory_bytes for n in active),
            "total_tokens_per_second": sum(n.capability.tokens_per_second for n in active),
        }

    def find_candidates(self, required_model: str | None = None,
                        min_context_window: int = 0) -> list[NodeRecord]:
        return [
            n for n in self.nodes()
            if n.capability.supports_model(required_model)
            and n.capability.context_window >= min_context_window
        ]

    def route(self, required_model: str | None = None,
              min_context_window: int = 0) -> NodeRecord | None:
        """N9-R23: local-first routing.

        Prefer local nodes when capability is equal; otherwise pick the
        capable node with the highest throughput. Returns None when no
        active node can serve the request (capability gap).
        """
        candidates = self.find_candidates(required_model, min_context_window)
        if not candidates:
            return None
        local = [n for n in candidates if n.is_local]
        best_remote = max((n for n in candidates if not n.is_local),
                          key=lambda n: n.capability.tokens_per_second,
                          default=None)
        if local:
            best_local = max(local, key=lambda n: n.capability.tokens_per_second)
            # Prefer local when capability is equal or better.
            if best_remote is None or (
                best_local.capability.tokens_per_second
                >= best_remote.capability.tokens_per_second
            ):
                return best_local
            return best_remote
        return best_remote
