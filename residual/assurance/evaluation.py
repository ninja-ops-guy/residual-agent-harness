from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Mapping

from ..core import digest
from .market import MarketProfile, MarketRequest, VerifiedComputeMarket
from .orchestration import ExecutionStrategy, OrchestrationTaxController
from .quality import AssuranceClass, VerifierQualityRegistry


@dataclass(frozen=True)
class FrozenAssuranceCase:
    case_id: str
    task_class: str
    capability: str
    assurance: AssuranceClass
    required_pass_rate: float
    direct_success: bool
    swarm_success: bool
    direct_cost: float
    swarm_cost: float
    direct_latency_ms: float
    swarm_latency_ms: float
    preferred_engine: str
    engine_outcomes: Mapping[str, bool]
    split: str = "evaluation"

    def __post_init__(self) -> None:
        if not self.case_id or not self.task_class or not self.capability:
            raise ValueError("case identity fields are required")
        if self.split not in {"training", "evaluation"}:
            raise ValueError("split must be training or evaluation")
        if not 0.0 <= self.required_pass_rate <= 1.0:
            raise ValueError("required_pass_rate must be in [0, 1]")
        for value in (self.direct_cost, self.swarm_cost, self.direct_latency_ms, self.swarm_latency_ms):
            if value < 0:
                raise ValueError("cost and latency must be nonnegative")
        if self.preferred_engine not in self.engine_outcomes:
            raise ValueError("preferred_engine must appear in engine_outcomes")

    def payload(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "task_class": self.task_class,
            "capability": self.capability,
            "assurance": self.assurance.value,
            "required_pass_rate": self.required_pass_rate,
            "direct_success": self.direct_success,
            "swarm_success": self.swarm_success,
            "direct_cost": self.direct_cost,
            "swarm_cost": self.swarm_cost,
            "direct_latency_ms": self.direct_latency_ms,
            "swarm_latency_ms": self.swarm_latency_ms,
            "preferred_engine": self.preferred_engine,
            "engine_outcomes": dict(sorted(self.engine_outcomes.items())),
            "split": self.split,
        }


@dataclass(frozen=True)
class FrozenAssuranceWorkload:
    name: str
    cases: tuple[FrozenAssuranceCase, ...]
    seed: int = 42

    def __post_init__(self) -> None:
        if not self.name or not self.cases:
            raise ValueError("workload requires a name and cases")
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate assurance case id")
        if not self.training_cases or not self.evaluation_cases:
            raise ValueError("workload requires both training and evaluation cases")
        training_classes = {case.task_class for case in self.training_cases}
        evaluation_classes = {case.task_class for case in self.evaluation_cases}
        if not evaluation_classes <= training_classes:
            raise ValueError("every evaluation task class requires training observations")

    @property
    def training_cases(self) -> tuple[FrozenAssuranceCase, ...]:
        return tuple(case for case in self.cases if case.split == "training")

    @property
    def evaluation_cases(self) -> tuple[FrozenAssuranceCase, ...]:
        return tuple(case for case in self.cases if case.split == "evaluation")

    @property
    def sha256(self) -> str:
        return digest({"name": self.name, "seed": self.seed, "cases": [case.payload() for case in self.cases]})


@dataclass(frozen=True)
class PolicyResult:
    policy: str
    successes: int
    total: int
    total_cost: float
    total_latency_ms: float
    engine_matches: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.total if self.total else 0.0

    @property
    def cost_per_success(self) -> float | None:
        return self.total_cost / self.successes if self.successes else None


@dataclass(frozen=True)
class VerifierDefect:
    defect_id: str
    artifact_acceptable: bool
    verifier_passed: bool
    confidence: float = 1.0
    covered: bool = True


@dataclass(frozen=True)
class VerifierCampaignResult:
    samples: int
    false_accepts: int
    false_rejects: int
    defect_recall: float
    false_accept_rate: float
    posterior_mean: float
    lower_credible_bound: float
    requires_hitl: bool


@dataclass
class AdaptiveEvaluation:
    workload: FrozenAssuranceWorkload
    engines: tuple[MarketProfile, ...]
    warmup_repeats: int = 3

    def _new_market(self) -> VerifiedComputeMarket:
        market = VerifiedComputeMarket(exploration_strength=0.0)
        for source in self.engines:
            market.register(MarketProfile(
                engine_id=source.engine_id,
                capabilities=source.capabilities,
                cost_per_task=source.cost_per_task,
                latency_ms=source.latency_ms,
                availability=source.availability,
                privacy_class=source.privacy_class,
                location=source.location,
                alpha=source.alpha,
                beta=source.beta,
                trials=source.trials,
                retired=source.retired,
            ))
        return market

    def _train_controller(self) -> OrchestrationTaxController:
        controller = OrchestrationTaxController(exploration_bonus=0.0)
        for _ in range(max(1, self.warmup_repeats)):
            for case in self.workload.training_cases:
                features = {"task_class": case.task_class, "capability": case.capability}
                controller.observe(features, ExecutionStrategy.DIRECT,
                                   success=case.direct_success, cost=case.direct_cost,
                                   latency_ms=case.direct_latency_ms)
                controller.observe(features, ExecutionStrategy.DYNAMIC_SWARM,
                                   success=case.swarm_success, cost=case.swarm_cost,
                                   latency_ms=case.swarm_latency_ms)
        return controller

    def run(self) -> dict[str, object]:
        rng = random.Random(self.workload.seed)
        cases = list(self.workload.evaluation_cases)
        rng.shuffle(cases)
        adaptive = self._run_adaptive(cases)
        baselines = [
            self._run_fixed(cases, ExecutionStrategy.DIRECT),
            self._run_fixed(cases, ExecutionStrategy.DYNAMIC_SWARM),
        ]
        return {
            "schema_version": "residual.assurance-evaluation.v1",
            "workload_name": self.workload.name,
            "workload_sha256": self.workload.sha256,
            "seed": self.workload.seed,
            "training_cases": len(self.workload.training_cases),
            "evaluation_cases": len(cases),
            "adaptive": self._result_payload(adaptive),
            "baselines": [self._result_payload(result) for result in baselines],
            "deltas": {
                result.policy: {
                    "success_rate": adaptive.success_rate - result.success_rate,
                    "total_cost": adaptive.total_cost - result.total_cost,
                    "total_latency_ms": adaptive.total_latency_ms - result.total_latency_ms,
                }
                for result in baselines
            },
        }

    def _run_fixed(self, cases: Iterable[FrozenAssuranceCase], strategy: ExecutionStrategy) -> PolicyResult:
        cases = tuple(cases)
        successes = 0
        total_cost = 0.0
        total_latency = 0.0
        for case in cases:
            if strategy == ExecutionStrategy.DIRECT:
                successes += int(case.direct_success)
                total_cost += case.direct_cost
                total_latency += case.direct_latency_ms
            else:
                successes += int(case.swarm_success)
                total_cost += case.swarm_cost
                total_latency += case.swarm_latency_ms
        return PolicyResult(strategy.value, successes, len(cases), total_cost, total_latency)

    def _run_adaptive(self, cases: Iterable[FrozenAssuranceCase]) -> PolicyResult:
        cases = tuple(cases)
        controller = self._train_controller()
        market = self._new_market()
        successes = 0
        total_cost = 0.0
        total_latency = 0.0
        engine_matches = 0
        for case in cases:
            features = {"task_class": case.task_class, "capability": case.capability}
            strategy = controller.choose(features, (ExecutionStrategy.DIRECT, ExecutionStrategy.DYNAMIC_SWARM))
            decision = market.select(MarketRequest(
                capability=case.capability,
                required_pass_rate=case.required_pass_rate,
                allow_exploration=False,
            ))
            engine_matches += int(decision.engine_id == case.preferred_engine)
            engine_ok = bool(case.engine_outcomes.get(decision.engine_id, False))
            if strategy == ExecutionStrategy.DIRECT:
                strategy_ok = case.direct_success
                total_cost += case.direct_cost
                total_latency += case.direct_latency_ms
            else:
                strategy_ok = case.swarm_success
                total_cost += case.swarm_cost
                total_latency += case.swarm_latency_ms
            success = bool(strategy_ok and engine_ok)
            successes += int(success)
            market.update(decision.engine_id, verifier_passed=success, verifier_reliability=1.0)
        return PolicyResult("adaptive", successes, len(cases), total_cost, total_latency, engine_matches)

    @staticmethod
    def _result_payload(result: PolicyResult) -> dict[str, object]:
        return {
            "policy": result.policy,
            "successes": result.successes,
            "total": result.total,
            "success_rate": result.success_rate,
            "total_cost": result.total_cost,
            "cost_per_success": result.cost_per_success,
            "total_latency_ms": result.total_latency_ms,
            "engine_matches": result.engine_matches,
        }


def evaluate_verifier_campaign(
    verifier_id: str,
    defects: Iterable[VerifierDefect],
    *,
    assurance: AssuranceClass = AssuranceClass.SECURITY_CRITICAL,
) -> VerifierCampaignResult:
    registry = VerifierQualityRegistry()
    profile = registry.get(verifier_id)
    defects = tuple(defects)
    if not defects:
        raise ValueError("verifier campaign requires cases")
    ids = [defect.defect_id for defect in defects]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate verifier defect id")
    for defect in defects:
        profile.record_outcome(
            verifier_passed=defect.verifier_passed,
            artifact_acceptable=defect.artifact_acceptable,
            confidence=defect.confidence,
            covered=defect.covered,
        )
    return VerifierCampaignResult(
        samples=profile.samples,
        false_accepts=profile.false_accept,
        false_rejects=profile.false_reject,
        defect_recall=profile.recall,
        false_accept_rate=profile.false_accept_rate,
        posterior_mean=profile.posterior_mean,
        lower_credible_bound=profile.lower_credible_bound(),
        requires_hitl=profile.requires_hitl(assurance, min_samples=min(20, max(1, profile.samples))),
    )
