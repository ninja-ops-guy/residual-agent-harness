from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite, sqrt
from typing import Iterable, Mapping, Sequence

from ..core import canonical, digest


class ExecutionStrategy(str, Enum):
    DIRECT = "direct"
    SINGLE_VERIFIED_WORKER = "single_verified_worker"
    DIRECT_STRONG_VERIFY = "direct_strong_verify"
    FIXED_SWARM = "fixed_swarm"
    DYNAMIC_SWARM = "dynamic_swarm"
    HETEROGENEOUS_SWARM = "heterogeneous_swarm"
    ENSEMBLE = "ensemble"


def _finite_nonnegative(value: object, name: str) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not isfinite(value) or value < 0):
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


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
    cost_n: int = 0

    @property
    def success_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def success_uncertainty(self) -> float:
        a, b = self.alpha, self.beta
        return sqrt((a * b) / (((a + b) ** 2) * (a + b + 1)))

    @property
    def cost_mean(self) -> float:
        return self.cost_sum / self.cost_n if self.cost_n else 0.0

    @property
    def latency_mean(self) -> float:
        return self.latency_sum / self.n if self.n else 0.0

    def update(self, *, success: bool, cost: float | None, latency_ms: float) -> None:
        if type(success) is not bool:
            raise ValueError("success must be boolean")
        latency = _finite_nonnegative(latency_ms, "latency_ms")
        normalized_cost = None if cost is None else _finite_nonnegative(cost, "cost")
        self.alpha += float(success)
        self.beta += float(not success)
        if normalized_cost is not None:
            self.cost_sum += normalized_cost
            self.cost_n += 1
        self.latency_sum += latency
        self.n += 1


@dataclass(frozen=True)
class TopologyOutcomeObservation:
    """The retained, replayable learning input for one topology run."""

    task_features: dict[str, object]
    strategy: ExecutionStrategy
    success: bool
    cost: float | None
    latency_ms: float

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "residual.topology-outcome.v1",
            "task_features": self.task_features,
            "strategy": self.strategy.value,
            "success": self.success,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class TopologyDecision:
    """Auditable topology choice; outcome is attached after execution."""

    task_features: dict[str, object]
    candidates: tuple[str, ...]
    estimates: tuple[dict[str, object], ...]
    selected_topology: str
    deployment_tax_threshold: float | None
    selected_raw_tax: float | None
    observed_result: dict[str, object] | None = None

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "residual.topology-decision.v1",
            "task_features": self.task_features,
            "candidates": list(self.candidates),
            "estimates": list(self.estimates),
            "selected_topology": self.selected_topology,
            "deployment_tax_threshold": self.deployment_tax_threshold,
            "selected_raw_tax": self.selected_raw_tax,
            "observed_result": self.observed_result,
        }

    @property
    def decision_sha256(self) -> str:
        return digest(self.payload())

    def with_result(self, outcome: TopologyOutcomeObservation) -> "TopologyDecision":
        if outcome.strategy.value != self.selected_topology:
            raise ValueError("outcome topology does not match decision")
        return TopologyDecision(
            task_features=self.task_features,
            candidates=self.candidates,
            estimates=self.estimates,
            selected_topology=self.selected_topology,
            deployment_tax_threshold=self.deployment_tax_threshold,
            selected_raw_tax=self.selected_raw_tax,
            observed_result=outcome.payload(),
        )


@dataclass
class OrchestrationTaxController:
    """Learns when orchestration overhead is justified instead of assuming swarm=better."""

    weights: UtilityWeights = field(default_factory=UtilityWeights)
    exploration_bonus: float = 0.05
    deployment_tax_threshold: float | None = None
    _history: dict[tuple[str, ExecutionStrategy], BetaObservation] = field(default_factory=dict)
    _retained: list[TopologyOutcomeObservation] = field(default_factory=list)

    def _bucket(self, task_features: Mapping[str, object]) -> str:
        """Condition on every declared OTX factor, with a bounded evidence bucket."""
        evidence_size = task_features.get("evidence_size_bytes", 0)
        if not isinstance(evidence_size, (int, float)) or evidence_size < 0:
            evidence_size = 0
        evidence_bucket = (
            "small" if evidence_size < 16_384 else
            "medium" if evidence_size < 262_144 else "large")
        conditioned = {
            "task_class": str(task_features.get("task_class") or
                              task_features.get("capability") or "default"),
            "engine_mix": sorted(set(str(v) for v in task_features.get("engine_mix", ()))),
            "worker_count": int(task_features.get("worker_count", 1)),
            "verifier_family": str(task_features.get("verifier_family", "default")),
            "evidence_size_bucket": evidence_bucket,
        }
        return canonical(conditioned)

    def observe(self, task_features: Mapping[str, object], strategy: ExecutionStrategy, *,
                success: bool, cost: float | None, latency_ms: float,
                retain: bool = True) -> TopologyOutcomeObservation:
        # Validate before mutating learned state or retaining an outcome.  In
        # particular NaN/inf must never poison utility comparisons during replay.
        if type(success) is not bool:
            raise ValueError("success must be boolean")
        normalized_cost = None if cost is None else _finite_nonnegative(cost, "cost")
        normalized_latency = _finite_nonnegative(latency_ms, "latency_ms")
        key = (self._bucket(task_features), strategy)
        self._history.setdefault(key, BetaObservation()).update(
            success=success, cost=normalized_cost, latency_ms=normalized_latency)
        outcome = TopologyOutcomeObservation(
            task_features=dict(task_features), strategy=strategy, success=success,
            cost=normalized_cost, latency_ms=normalized_latency)
        if retain:
            self._retained.append(outcome)
        return outcome

    def observe_reliability(self, observation) -> TopologyOutcomeObservation:
        """Learn directly from the authoritative reliability observation."""
        features = {
            "task_class": observation.task_class,
            "engine_mix": observation.engine_mix,
            "worker_count": observation.worker_count,
            "verifier_family": observation.verifier_family,
            "evidence_size_bytes": observation.evidence_size_bytes,
        }
        try:
            strategy = ExecutionStrategy(observation.topology)
        except ValueError as exc:
            raise ValueError("unsupported reliability topology") from exc
        complete_cost = None
        if observation.cost.cost_complete:
            complete_cost = (observation.cost.api_cost_usd or 0.0) + (
                observation.cost.failed_call_cost_usd or 0.0)
        return self.observe(
            features, strategy,
            success=observation.correct is True and observation.accepted,
            cost=complete_cost,
            latency_ms=observation.timing.wall_clock_ms,
        )

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

    def choose(self, task_features: Mapping[str, object],
               strategies: Iterable[ExecutionStrategy], *,
               candidate_features: Mapping[ExecutionStrategy, Mapping[str, object]] | None = None
               ) -> ExecutionStrategy:
        return ExecutionStrategy(self.decide(
            task_features, strategies,
            candidate_features=candidate_features).selected_topology)

    def decide(self, task_features: Mapping[str, object],
               strategies: Iterable[ExecutionStrategy], *,
               candidate_features: Mapping[ExecutionStrategy, Mapping[str, object]] | None = None
               ) -> TopologyDecision:
        candidates = tuple(sorted(set(strategies), key=lambda s: s.value))
        def features_for(strategy: ExecutionStrategy) -> dict[str, object]:
            result = dict(task_features)
            if candidate_features and strategy in candidate_features:
                result.update(candidate_features[strategy])
            return result

        estimates = [self.estimate(features_for(strategy), strategy)
                     for strategy in candidates]
        if not estimates:
            raise ValueError("at least one strategy is required")
        selected = max(estimates, key=lambda e: (self.utility(e), e.strategy.value))
        direct = next((e for e in estimates if e.strategy is ExecutionStrategy.DIRECT), None)
        raw_tax = None
        if direct is not None and selected.strategy is not ExecutionStrategy.DIRECT:
            raw_tax = (
                selected.expected_cost - direct.expected_cost
                + self.weights.latency * (
                    selected.expected_latency_ms - direct.expected_latency_ms))
            if (self.deployment_tax_threshold is not None
                    and raw_tax > self.deployment_tax_threshold):
                selected = direct
                raw_tax = 0.0
        estimate_payloads = tuple({
            "topology": estimate.strategy.value,
            "expected_success": estimate.expected_success,
            "expected_cost": estimate.expected_cost,
            "expected_latency_ms": estimate.expected_latency_ms,
            "predicted_utility": self.utility(estimate),
        } for estimate in estimates)
        return TopologyDecision(
            task_features={
                **dict(task_features),
                "candidate_features": {
                    strategy.value: dict(candidate_features[strategy])
                    for strategy in candidates
                    if candidate_features and strategy in candidate_features
                },
            },
            candidates=tuple(s.value for s in candidates),
            estimates=estimate_payloads,
            selected_topology=selected.strategy.value,
            deployment_tax_threshold=self.deployment_tax_threshold,
            selected_raw_tax=raw_tax,
        )

    def orchestration_tax(
            self, task_features: Mapping[str, object],
            swarm_strategy: ExecutionStrategy = ExecutionStrategy.DYNAMIC_SWARM, *,
            direct_features: Mapping[str, object] | None = None,
            swarm_features: Mapping[str, object] | None = None) -> float:
        direct_input = {**dict(task_features), **dict(direct_features or {})}
        swarm_input = {**dict(task_features), **dict(swarm_features or {})}
        direct = self.estimate(direct_input, ExecutionStrategy.DIRECT)
        swarm = self.estimate(swarm_input, swarm_strategy)
        return self.utility(direct) - self.utility(swarm)

    def retained_observations(self) -> tuple[dict[str, object], ...]:
        return tuple(item.payload() for item in self._retained)

    @classmethod
    def replay(cls, observations: Sequence[Mapping[str, object]], **kwargs) -> "OrchestrationTaxController":
        """Reproduce learned state from stored outcome observations only."""
        controller = cls(**kwargs)
        for raw in observations:
            if raw.get("schema_version") != "residual.topology-outcome.v1":
                raise ValueError("unsupported topology outcome schema")
            features = raw.get("task_features")
            if not isinstance(features, Mapping):
                raise ValueError("topology outcome task_features required")
            controller.observe(
                features,
                ExecutionStrategy(str(raw["strategy"])),
                success=raw["success"],
                cost=raw.get("cost"),
                latency_ms=raw["latency_ms"],
            )
        return controller
