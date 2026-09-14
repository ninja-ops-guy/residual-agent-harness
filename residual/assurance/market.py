from __future__ import annotations

from dataclasses import dataclass, field
from math import log, sqrt
from typing import Mapping


@dataclass
class MarketProfile:
    engine_id: str
    capabilities: frozenset[str]
    cost_per_task: float
    latency_ms: float
    availability: float = 1.0
    privacy_class: int = 0
    location: str = "unknown"
    alpha: float = 1.0
    beta: float = 1.0
    trials: int = 0
    retired: bool = False

    @property
    def pass_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def lower_bound(self, z: float = 1.64) -> float:
        a, b = self.alpha, self.beta
        mean = a / (a + b)
        var = (a * b) / (((a + b) ** 2) * (a + b + 1))
        return max(0.0, mean - z * sqrt(var))

    def update(self, quality_adjusted_success: float) -> None:
        s = min(1.0, max(0.0, quality_adjusted_success))
        self.alpha += s
        self.beta += 1.0 - s
        self.trials += 1


@dataclass(frozen=True)
class MarketRequest:
    capability: str
    required_pass_rate: float
    max_privacy_class: int = 99
    max_latency_ms: float | None = None
    allow_exploration: bool = True


@dataclass(frozen=True)
class MarketDecision:
    engine_id: str
    score: float
    reason: str
    profile_snapshot: Mapping[str, object]


@dataclass
class VerifiedComputeMarket:
    profiles: dict[str, MarketProfile] = field(default_factory=dict)
    exploration_strength: float = 0.05
    retire_min_trials: int = 30
    retire_floor: float = 0.50

    def register(self, profile: MarketProfile) -> None:
        if profile.engine_id in self.profiles:
            raise ValueError(f"duplicate engine profile: {profile.engine_id}")
        self.profiles[profile.engine_id] = profile

    def update(self, engine_id: str, *, verifier_passed: bool, verifier_reliability: float) -> None:
        p = self.profiles[engine_id]
        reliability = min(1.0, max(0.0, verifier_reliability))
        adjusted = reliability if verifier_passed else (1.0 - reliability)
        p.update(adjusted)
        if p.trials >= self.retire_min_trials and p.pass_rate < self.retire_floor:
            p.retired = True

    def _eligible(self, p: MarketProfile, r: MarketRequest) -> bool:
        return (
            not p.retired
            and r.capability in p.capabilities
            and p.availability > 0
            and p.privacy_class <= r.max_privacy_class
            and (r.max_latency_ms is None or p.latency_ms <= r.max_latency_ms)
        )

    def select(self, request: MarketRequest) -> MarketDecision:
        eligible = [p for p in self.profiles.values() if self._eligible(p, request)]
        if not eligible:
            raise LookupError(f"no market engine supports {request.capability}")

        total_trials = max(1, sum(p.trials for p in eligible))
        constrained = [p for p in eligible if p.lower_bound() >= request.required_pass_rate]
        pool = constrained or eligible

        def score(p: MarketProfile) -> float:
            exploration = 0.0
            if request.allow_exploration:
                exploration = self.exploration_strength * sqrt(log(total_trials + 1.0) / (p.trials + 1.0))
            quality_penalty = max(0.0, request.required_pass_rate - p.lower_bound()) * 100.0
            return p.cost_per_task + p.latency_ms * 1e-6 + quality_penalty - exploration

        best = min(pool, key=lambda p: (score(p), p.engine_id))
        return MarketDecision(
            engine_id=best.engine_id,
            score=score(best),
            reason="meets_quality_constraint" if best in constrained else "best_available_below_constraint",
            profile_snapshot={
                "pass_rate": best.pass_rate,
                "lower_bound": best.lower_bound(),
                "trials": best.trials,
                "cost_per_task": best.cost_per_task,
                "latency_ms": best.latency_ms,
                "privacy_class": best.privacy_class,
                "location": best.location,
            },
        )
