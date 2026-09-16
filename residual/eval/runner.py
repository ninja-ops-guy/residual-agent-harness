"""Evaluation runner: single-agent / fixed-swarm / dynamic-swarm configs.

T10-R1: the three configurations MUST be executed with n >= 10 runs per
configuration. Swarm execution backends are stubbed behind the
``SwarmBackend`` protocol: the bundled backends are deterministic
seeded simulators so the harness itself is fully reproducible and
testable offline; real backends can be plugged in without changing the
runner, stats, or report layers.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence

from .ablations import Ablation
from .faults import FaultInjector
from .workload import FrozenWorkload, WorkloadTask


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    repeat: int
    success: bool
    elapsed_ms: float
    tokens_used: int
    cache_hit: bool
    escalated: bool
    fault: Optional[str] = None  # fault kind if one was injected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "repeat": self.repeat,
            "success": self.success,
            "elapsed_ms": self.elapsed_ms,
            "tokens_used": self.tokens_used,
            "cache_hit": self.cache_hit,
            "escalated": self.escalated,
            "fault": self.fault,
        }


class SwarmBackend(Protocol):
    """Protocol for task execution backends (real or simulated)."""

    name: str

    def run_task(self, task: WorkloadTask, rng: random.Random, fault: Optional[str],
                 ablation: Ablation) -> TaskResult:
        ...


def _difficulty_factor(task: WorkloadTask) -> float:
    return {"low": 0.8, "medium": 1.0, "high": 1.3}.get(task.metadata.get("difficulty", "medium"), 1.0)


class _SimulatedBackend:
    """Shared deterministic simulation core for the stubbed backends."""

    name = "simulated"
    parallelism: float = 1.0  # elapsed-time divisor from parallelism
    coordination_overhead: float = 0.0  # additive token overhead fraction
    cache_effectiveness: float = 0.7  # probability a repeat run is served from cache

    def run_task(self, task: WorkloadTask, rng: random.Random, fault: Optional[str],
                 ablation: Ablation) -> TaskResult:
        difficulty = _difficulty_factor(task)
        base_tokens = int(4000 * difficulty * (1.0 + self.coordination_overhead))
        base_ms = 800.0 * difficulty / self.parallelism

        cache_hit = False
        if not ablation.disables("cache") and rng.random() < self.cache_effectiveness:
            cache_hit = True
            base_tokens = int(base_tokens * 0.3)
            base_ms *= 0.5

        escalated = False
        success_p = 0.9
        if fault is not None:
            success_p -= 0.25
            base_ms *= 1.5
        if ablation.disables("brakes") and fault == "adversarial_input":
            success_p -= 0.3  # brakes normally catch these
        if task.metadata.get("difficulty") == "high" and not ablation.disables("escalation"):
            if rng.random() < 0.15:
                escalated = True
                base_ms *= 2.0
                success_p += 0.05

        jitter = rng.uniform(0.9, 1.1)
        return TaskResult(
            task_id=task.task_id,
            repeat=-1,  # filled in by the runner
            success=rng.random() < min(success_p, 1.0),
            elapsed_ms=round(base_ms * jitter, 3),
            tokens_used=int(base_tokens * jitter),
            cache_hit=cache_hit,
            escalated=escalated,
            fault=fault,
        )


class SingleAgentBackend(_SimulatedBackend):
    """One agent, no parallelism, no coordination cost."""

    name = "single_agent"
    parallelism = 1.0
    coordination_overhead = 0.0
    cache_effectiveness = 0.5


class FixedSwarmBackend(_SimulatedBackend):
    """Fixed-size swarm with constant parallelism and small overhead."""

    name = "fixed_swarm"
    coordination_overhead = 0.10
    cache_effectiveness = 0.7

    def __init__(self, size: int = 4):
        if size < 1:
            raise ValueError("fixed swarm size must be >= 1")
        self.size = size
        self.parallelism = max(1.0, size * 0.7)
        self.name = f"fixed_swarm_{size}"


class DynamicSwarmBackend(_SimulatedBackend):
    """Elastic swarm: parallelism scales with task difficulty."""

    name = "dynamic_swarm"
    coordination_overhead = 0.15
    cache_effectiveness = 0.8

    def __init__(self, min_size: int = 1, max_size: int = 8):
        if min_size < 1 or max_size < min_size:
            raise ValueError("invalid dynamic swarm bounds")
        self.min_size = min_size
        self.max_size = max_size

    def run_task(self, task: WorkloadTask, rng: random.Random, fault: Optional[str],
                 ablation: Ablation) -> TaskResult:
        difficulty = _difficulty_factor(task)
        size = min(self.max_size, max(self.min_size, round(self.min_size * difficulty * 3)))
        self.parallelism = max(1.0, size * 0.75)
        return super().run_task(task, rng, fault, ablation)


@dataclass(frozen=True)
class RunConfiguration:
    """One evaluated configuration (T10-R1: single/fixed/dynamic)."""

    name: str
    backend_kind: str  # "single_agent" | "fixed_swarm" | "dynamic_swarm"
    ablation: str = "full"
    backend_options: Dict[str, Any] = field(default_factory=dict)
    seed: int = 20260914

    def build_backend(self) -> SwarmBackend:
        if self.backend_kind == "single_agent":
            return SingleAgentBackend()
        if self.backend_kind == "fixed_swarm":
            return FixedSwarmBackend(**self.backend_options)
        if self.backend_kind == "dynamic_swarm":
            return DynamicSwarmBackend(**self.backend_options)
        raise ValueError(f"unknown backend kind: {self.backend_kind}")


DEFAULT_CONFIGURATIONS: Sequence[RunConfiguration] = (
    RunConfiguration(name="single_agent", backend_kind="single_agent"),
    RunConfiguration(name="fixed_swarm", backend_kind="fixed_swarm",
                     backend_options={"size": 4}),
    RunConfiguration(name="dynamic_swarm", backend_kind="dynamic_swarm",
                     backend_options={"min_size": 1, "max_size": 8}),
)


class EvaluationRunner:
    """Executes configurations against a FrozenWorkload, n runs each."""

    def __init__(self, workload: FrozenWorkload, ablations: Dict[str, Ablation],
                 fault_injector: Optional[FaultInjector] = None):
        self.workload = workload
        self.ablations = ablations
        self.fault_injector = fault_injector

    def run_configuration(self, config: RunConfiguration, repeats: int = 10) -> Dict[str, Any]:
        """Run one configuration ``repeats`` times over the full workload.

        T10-R1 requires n >= 10; the runner enforces that floor.
        """
        if repeats < 10:
            raise ValueError("T10-R1 requires n >= 10 runs per configuration")
        if config.ablation not in self.ablations:
            raise ValueError(f"unknown ablation: {config.ablation}")
        ablation = self.ablations[config.ablation]
        backend = config.build_backend()

        results: List[TaskResult] = []
        for repeat in range(repeats):
            for task in self.workload.tasks:
                rng = random.Random(f"{config.seed}:{config.name}:{task.task_id}:{repeat}")
                fault = None
                if self.fault_injector is not None:
                    f = self.fault_injector.inject(task.task_id, repeat)
                    fault = f.kind if f else None
                result = backend.run_task(task, rng, fault, ablation)
                results.append(TaskResult(
                    task_id=result.task_id, repeat=repeat, success=result.success,
                    elapsed_ms=result.elapsed_ms, tokens_used=result.tokens_used,
                    cache_hit=result.cache_hit, escalated=result.escalated,
                    fault=result.fault,
                ))
        return {
            "configuration": config.name,
            "backend_kind": config.backend_kind,
            "ablation": config.ablation,
            "repeats": repeats,
            "backend_name": backend.name,
            "runs": [r.to_dict() for r in results],
        }
