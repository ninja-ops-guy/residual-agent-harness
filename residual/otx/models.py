"""Core data models for SPEC-SWARM-OTX-003 (Orchestration Tax Controller).

Defines the decomposed phase timing model (OTX-R1), task/topology
descriptors, and the taxonomy of execution topologies the controller
chooses between.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


class Phase:
    """Decomposed orchestration phases (OTX-R1).

    ``coordination`` captures residual coordination overhead not
    attributable to any other phase (message passing, barriers,
    lease management).
    """

    PLANNING = "planning"
    SCHEDULING = "scheduling"
    CONTEXT_PACKAGING = "context_packaging"
    WORKER_EXECUTION = "worker_execution"
    VERIFICATION = "verification"
    INTEGRATION = "integration"
    COORDINATION = "coordination"

    ALL: Tuple[str, ...] = (
        PLANNING,
        SCHEDULING,
        CONTEXT_PACKAGING,
        WORKER_EXECUTION,
        VERIFICATION,
        INTEGRATION,
        COORDINATION,
    )
    # Phases that are pure orchestration overhead (everything that is not
    # productive worker execution).
    OVERHEAD: Tuple[str, ...] = (
        PLANNING,
        SCHEDULING,
        CONTEXT_PACKAGING,
        VERIFICATION,
        INTEGRATION,
        COORDINATION,
    )


@dataclass(frozen=True)
class PhaseTiming:
    """Wall-clock seconds per decomposed phase (OTX-R1).

    Every phase is measured separately; missing phases are 0.0.
    """

    seconds: Dict[str, float]

    def __post_init__(self) -> None:
        unknown = set(self.seconds) - set(Phase.ALL)
        if unknown:
            raise ValueError(f"unknown phases: {sorted(unknown)}")
        for k, v in self.seconds.items():
            if v < 0:
                raise ValueError(f"negative timing for phase {k}")

    def phase_seconds(self, phase: str) -> float:
        return float(self.seconds.get(phase, 0.0))

    @property
    def worker_execution_s(self) -> float:
        return self.phase_seconds(Phase.WORKER_EXECUTION)

    @property
    def coordination_overhead_s(self) -> float:
        """Total non-worker-execution time (OTX-R1)."""
        return sum(self.phase_seconds(p) for p in Phase.OVERHEAD)

    @property
    def total_s(self) -> float:
        return self.worker_execution_s + self.coordination_overhead_s

    def observed_tax(self) -> float:
        """Observed orchestration tax: overhead per unit of productive work."""
        base = self.worker_execution_s
        if base <= 0:
            return float("inf") if self.coordination_overhead_s > 0 else 0.0
        return self.coordination_overhead_s / base

    def breakdown(self) -> Dict[str, float]:
        return {p: self.phase_seconds(p) for p in Phase.ALL}


@dataclass(frozen=True)
class Task:
    """A unit of work presented to the controller."""

    task_id: str
    task_class: str          # e.g. "lookup", "synthesis" (OTX-R3 conditioning)
    granularity: str         # e.g. "atomic" | "composite" | "project" (OTX-R6)
    value: float = 1.0       # utility of a correct result
    size: float = 1.0        # relative work size (scales worker execution)


@dataclass(frozen=True)
class Topology:
    """An execution topology candidate.

    ``complexity_rank`` orders topologies from simplest to most complex;
    the deployment threshold (OTX-R5) walks down this order.
    """

    name: str
    complexity_rank: int
    workers: int
    phases_active: Tuple[str, ...]
    reliability_prior: float  # prior P(correct) used to seed the Beta posterior
    description: str = ""


TOPOLOGIES: Dict[str, Topology] = {
    t.name: t
    for t in (
        Topology(
            name="single",
            complexity_rank=0,
            workers=1,
            phases_active=(Phase.SCHEDULING, Phase.WORKER_EXECUTION, Phase.INTEGRATION),
            reliability_prior=0.70,
            description="one worker, no planner/verifier",
        ),
        Topology(
            name="pair",
            complexity_rank=1,
            workers=1,
            phases_active=(
                Phase.SCHEDULING,
                Phase.CONTEXT_PACKAGING,
                Phase.WORKER_EXECUTION,
                Phase.VERIFICATION,
                Phase.INTEGRATION,
            ),
            reliability_prior=0.85,
            description="worker + independent verifier",
        ),
        Topology(
            name="swarm",
            complexity_rank=2,
            workers=3,
            phases_active=Phase.ALL,
            reliability_prior=0.93,
            description="planner + scheduler + N workers + verifier + integrator",
        ),
    )
}

SIMPLEST_TOPOLOGY = "single"
