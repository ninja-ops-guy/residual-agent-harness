from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import sqrt
from typing import Iterable, Mapping


class ExecutionStrategy(str, Enum):
    DIRECT = "direct"
    DIRECT_STRONG_VERIFY = "direct_strong_verify"
    FIXED_SWARM = "fixed_swarm"
    DYNAMIC_SWARM = "dynamic_swarm"
    ENSEMBLE = "ensemble"


@dataclass(frozen=True)
class StrategyEstimate:
    strategy: ExecutionStrategy
    expected_success: float
    expected_cost: float
    expected_latency_ms: float
    integration_risk: float = 0.0
    disclosure_risk: float = 0.0


@dataclass(frozen=True)
class UtilityWeights:
    success_value: float = 1.0
    cost: float = 1.0
    latency: float = 0.0001
    integration_risk: float = 1.0
    disclosure_risk: float = 1.0


@dataclass
class BetaObservation:
    alpha: float = 1.0
    beta: float = 1.0
    cost_sum: float = 0.0
    latency_sum: float = 0.0
    n: int = 0

    @property
    def success_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def success_uncertainty(self) -> float:
        a, b = self.alpha, self.beta
        return sqrt((a * b) / (((a + b) ** 2) * (a + b + 1)))

    @property
    def cost_mean(self) -> float:
        return self.cost_sum / self.n if self.n else 0.0

    @property
    def latency_mean(self) -> float:
        return self.latency_sum / self.n if self.n else 0.0

    def update(self, *, success: bool, cost: float, latency_ms: float) -> None:
        self.alpha += float(success)
        self.beta += float(not success)
        self.cost_sum += max(0.0, cost)
        self.latency_sum += max(0.0, latency_ms)
        self.n += 1


@dataclass
class OrchestrationTaxController:
    """Learns when orchestration overhead is justified instead of assuming swarm=better."""

    weights: UtilityWeights = field(default_factory=UtilityWeights)
    exploration_bonus: float = 0.05
    _history: dict[tuple[str, ExecutionStrategy], BetaObservation] = field(default_factory=dict)

    def _bucket(self, task_features: Mapping[str, object]) -> str:
        return str(task_features.get("task_class") or task_features.get("capability") or "default")

    def observe(self, task_features: Mapping[str, object], strategy: ExecutionStrategy, *, success: bool, cost: float, latency_ms: float) -> None:
        key = (self._bucket(task_features), strategy)
        self._history.setdefault(key, BetaObservation()).update(success=success, cost=cost, latency_ms=latency_ms)

    def estimate(self, task_features: Mapping[str, object], strategy: ExecutionStrategy, *, fallback_cost: float = 0.0, fallback_latency_ms: float = 0.0) -> StrategyEstimate:
        obs = self._history.get((self._bucket(task_features), strategy))
        if obs is None:
            return StrategyEstimate(strategy, 0.5 + self.exploration_bonus, fallback_cost, fallback_latency_ms)
        optimistic_success = min(1.0, obs.success_mean + self.exploration_bonus * obs.success_uncertainty)
        return StrategyEstimate(strategy, optimistic_success, obs.cost_mean, obs.latency_mean)

    def utility(self, estimate: StrategyEstimate) -> float:
        w = self.weights
        return (
            w.success_value * estimate.expected_success
            - w.cost * estimate.expected_cost
            - w.latency * estimate.expected_latency_ms
            - w.integration_risk * estimate.integration_risk
            - w.disclosure_risk * estimate.disclosure_risk
        )

    def choose(self, task_features: Mapping[str, object], strategies: Iterable[ExecutionStrategy]) -> ExecutionStrategy:
        estimates = [self.estimate(task_features, s) for s in strategies]
        if not estimates:
            raise ValueError("at least one strategy is required")
        return max(estimates, key=lambda e: (self.utility(e), e.strategy.value)).strategy

    def orchestration_tax(self, task_features: Mapping[str, object], swarm_strategy: ExecutionStrategy = ExecutionStrategy.DYNAMIC_SWARM) -> float:
        direct = self.estimate(task_features, ExecutionStrategy.DIRECT)
        swarm = self.estimate(task_features, swarm_strategy)
        return self.utility(direct) - self.utility(swarm)
