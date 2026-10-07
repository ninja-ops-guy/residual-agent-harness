"""Heuristic risk estimation for work packets.

ORCH-I-R14: Risk scoring MUST be deterministic for a fixed graph and
            partition.
ORCH-I-R15: The score MUST incorporate fan-out, protected-path proximity,
            and external-IO signals; the weights MUST be explicit module
            constants.

Scoring (per packet):
    score = FAN_OUT_WEIGHT   * total fan-out of member requirements
          + PROTECTED_WEIGHT * number of owned files under a protected prefix
          + EXTERNAL_IO_WEIGHT * number of member requirements with external IO
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core import ContractError
from .partition import WorkPacket
from .requirements import RequirementGraph

FAN_OUT_WEIGHT = 1.0
PROTECTED_WEIGHT = 3.0
EXTERNAL_IO_WEIGHT = 2.0

DEFAULT_PROTECTED_PREFIXES: tuple[str, ...] = (
    "residual/swarm/",
    "residual/evidence/",
    "residual/scheduler/",
    "residual/integrator/",
    ".git/",
    "/etc/",
)


@dataclass(frozen=True)
class RiskReport:
    packet_id: str
    fan_out: int
    protected_hits: int
    external_io_count: int
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "fan_out": self.fan_out,
            "protected_hits": self.protected_hits,
            "external_io_count": self.external_io_count,
            "score": self.score,
        }


class RiskEstimator:
    def __init__(self, protected_prefixes: tuple[str, ...] = DEFAULT_PROTECTED_PREFIXES):
        if not isinstance(protected_prefixes, (tuple, list)) or not protected_prefixes:
            raise ContractError("protected_prefixes must be a non-empty sequence")
        for prefix in protected_prefixes:
            if not isinstance(prefix, str) or not prefix:
                raise ContractError("protected prefixes must be non-empty strings")
        self._prefixes = tuple(sorted(protected_prefixes))

    def estimate(self, graph: RequirementGraph,
                 packets: tuple[WorkPacket, ...]) -> tuple[RiskReport, ...]:
        reports = []
        for packet in packets:
            fan_out = sum(len(graph.dependents(rid)) for rid in packet.requirement_ids)
            protected = sum(
                1 for f in packet.files
                if any(f.startswith(p) for p in self._prefixes))
            external = sum(
                1 for rid in packet.requirement_ids if graph.get(rid).external_io)
            score = (FAN_OUT_WEIGHT * fan_out
                     + PROTECTED_WEIGHT * protected
                     + EXTERNAL_IO_WEIGHT * external)
            reports.append(RiskReport(packet.packet_id, fan_out, protected, external, score))
        return tuple(reports)
