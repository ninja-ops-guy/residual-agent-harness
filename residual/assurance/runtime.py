from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from ..engines.protocol import ContextAssembly, EngineResult, ExecutionEngine, TaskSpec
from .market import MarketDecision, MarketProfile, MarketRequest, VerifiedComputeMarket
from .orchestration import ExecutionStrategy, OrchestrationTaxController
from .quality import AssuranceClass, VerifierQualityRegistry


ObservationSink = Callable[[str, Mapping[str, object]], None]
VerifierCallable = Callable[[Any], bool]
StrategyExecutor = Callable[[ExecutionEngine, TaskSpec, ContextAssembly], EngineResult]


@dataclass(frozen=True)
class ExecutionPlan:
    strategy: ExecutionStrategy
    engine_id: str
    verifier_id: str
    assurance: AssuranceClass
    market_decision: MarketDecision
    requires_hitl: bool


@dataclass(frozen=True)
class ExecutionOutcome:
    plan: ExecutionPlan
    result: EngineResult
    verifier_passed: bool
    accepted: bool
    escalation_reason: str | None = None


@dataclass
class AdaptiveAssuranceRuntime:
    """Closed-loop runtime binding OTX, VQ, and VCM without replacing engine contracts.

    DIRECT execution is available out of the box. Swarm/ensemble execution is wired
    through strategy executors so the assurance layer can adopt M2 runtimes without
    coupling itself to a particular swarm implementation.
    """

    quality: VerifierQualityRegistry = field(default_factory=VerifierQualityRegistry)
    orchestration: OrchestrationTaxController = field(default_factory=OrchestrationTaxController)
    market: VerifiedComputeMarket = field(default_factory=VerifiedComputeMarket)
    emit: ObservationSink | None = None
    _engines: dict[str, ExecutionEngine] = field(default_factory=dict)
    _strategy_executors: dict[ExecutionStrategy, StrategyExecutor] = field(default_factory=dict)

    def register_engine(self, engine: ExecutionEngine, profile: MarketProfile) -> None:
        engine_id = f"{engine.name}@{engine.version}"
        if profile.engine_id != engine_id:
            raise ValueError(f"profile engine_id must be {engine_id}")
        if not profile.capabilities:
            raise ValueError("market profile requires capabilities")
        if engine_id in self._engines:
            raise ValueError(f"duplicate engine registration: {engine_id}")
        self._engines[engine_id] = engine
        self.market.register(profile)
        self._observe("assurance_engine_registered", {
            "engine_id": engine_id,
            "capabilities": sorted(profile.capabilities),
        })

    def register_strategy_executor(self, strategy: ExecutionStrategy, executor: StrategyExecutor) -> None:
        if strategy == ExecutionStrategy.DIRECT:
            raise ValueError("DIRECT uses the engine's native execute contract")
        self._strategy_executors[strategy] = executor

    def plan(
        self,
        *,
        task: TaskSpec,
        verifier_id: str,
        assurance: AssuranceClass,
        required_pass_rate: float,
        max_privacy_class: int = 99,
        max_latency_ms: float | None = None,
        strategies: Iterable[ExecutionStrategy] = (ExecutionStrategy.DIRECT,),
    ) -> ExecutionPlan:
        allowed = tuple(strategies)
        if not allowed:
            raise ValueError("at least one strategy is required")
        for strategy in allowed:
            if strategy != ExecutionStrategy.DIRECT and strategy not in self._strategy_executors:
                raise LookupError(f"strategy executor unavailable: {strategy.value}")

        task_features = {
            "task_class": str(task.metadata.get("task_class") or task.capability),
            "capability": task.capability,
        }
        strategy = self.orchestration.choose(task_features, allowed)
        market_decision = self.market.select(MarketRequest(
            capability=task.capability,
            required_pass_rate=required_pass_rate,
            max_privacy_class=max_privacy_class,
            max_latency_ms=max_latency_ms,
            allow_exploration=assurance in {AssuranceClass.ROUTINE, AssuranceClass.IMPORTANT},
        ))
        profile = self.quality.get(verifier_id)
        requires_hitl = profile.requires_hitl(assurance)
        plan = ExecutionPlan(
            strategy=strategy,
            engine_id=market_decision.engine_id,
            verifier_id=verifier_id,
            assurance=assurance,
            market_decision=market_decision,
            requires_hitl=requires_hitl,
        )
        self._observe("assurance_plan", {
            "task_id": task.task_id,
            "capability": task.capability,
            "strategy": strategy.value,
            "engine_id": market_decision.engine_id,
            "verifier_id": verifier_id,
            "assurance": assurance.value,
            "requires_hitl": requires_hitl,
            "market_reason": market_decision.reason,
        })
        return plan

    def execute(
        self,
        *,
        task: TaskSpec,
        context: ContextAssembly,
        verifier_id: str,
        verifier: VerifierCallable,
        assurance: AssuranceClass,
        required_pass_rate: float,
        max_privacy_class: int = 99,
        max_latency_ms: float | None = None,
        strategies: Iterable[ExecutionStrategy] = (ExecutionStrategy.DIRECT,),
    ) -> ExecutionOutcome:
        plan = self.plan(
            task=task,
            verifier_id=verifier_id,
            assurance=assurance,
            required_pass_rate=required_pass_rate,
            max_privacy_class=max_privacy_class,
            max_latency_ms=max_latency_ms,
            strategies=strategies,
        )
        engine = self._engines.get(plan.engine_id)
        if engine is None:
            raise LookupError(f"market selected unregistered engine: {plan.engine_id}")
        if not engine.supports(task.capability):
            raise LookupError(f"selected engine no longer supports {task.capability}")

        if plan.strategy == ExecutionStrategy.DIRECT:
            result = engine.execute(task, context)
        else:
            result = self._strategy_executors[plan.strategy](engine, task, context)

        try:
            verifier_passed = bool(verifier(result.candidate))
        except Exception:
            verifier_passed = False

        quality_profile = self.quality.get(verifier_id)
        verifier_reliability = quality_profile.posterior_mean
        self.market.update(
            plan.engine_id,
            verifier_passed=verifier_passed,
            verifier_reliability=verifier_reliability,
        )

        accepted = verifier_passed and not plan.requires_hitl
        escalation_reason = None
        if plan.requires_hitl:
            accepted = False
            escalation_reason = "verifier_quality_requires_hitl"
        elif not verifier_passed:
            escalation_reason = "verification_failed"

        self._observe("assurance_execution", {
            "task_id": task.task_id,
            "strategy": plan.strategy.value,
            "engine_id": plan.engine_id,
            "verifier_id": verifier_id,
            "verifier_passed": verifier_passed,
            "verifier_reliability": verifier_reliability,
            "accepted": accepted,
            "escalation_reason": escalation_reason,
        })
        return ExecutionOutcome(
            plan=plan,
            result=result,
            verifier_passed=verifier_passed,
            accepted=accepted,
            escalation_reason=escalation_reason,
        )

    def record_ground_truth(
        self,
        *,
        verifier_id: str,
        verifier_passed: bool,
        artifact_acceptable: bool,
        confidence: float | None = None,
        covered: bool = True,
    ) -> None:
        """Apply delayed ground truth to VQ; verification itself is not ground truth."""
        profile = self.quality.get(verifier_id)
        profile.record_outcome(
            verifier_passed=verifier_passed,
            artifact_acceptable=artifact_acceptable,
            confidence=confidence,
            covered=covered,
        )
        self._observe("verifier_ground_truth", {
            "verifier_id": verifier_id,
            "verifier_passed": verifier_passed,
            "artifact_acceptable": artifact_acceptable,
            "samples": profile.samples,
            "posterior_mean": profile.posterior_mean,
            "false_accept_rate": profile.false_accept_rate,
        })

    def record_strategy_outcome(
        self,
        *,
        task: TaskSpec,
        strategy: ExecutionStrategy,
        success: bool,
        cost: float,
        latency_ms: float,
    ) -> None:
        self.orchestration.observe(
            {
                "task_class": str(task.metadata.get("task_class") or task.capability),
                "capability": task.capability,
            },
            strategy,
            success=success,
            cost=cost,
            latency_ms=latency_ms,
        )
        self._observe("orchestration_outcome", {
            "task_id": task.task_id,
            "strategy": strategy.value,
            "success": success,
            "cost": cost,
            "latency_ms": latency_ms,
        })

    def _observe(self, kind: str, payload: Mapping[str, object]) -> None:
        if self.emit is not None:
            self.emit(kind, payload)
