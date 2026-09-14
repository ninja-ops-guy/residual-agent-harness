from residual.assurance import (
    AdaptiveAssuranceRuntime,
    AssuranceClass,
    ExecutionStrategy,
    MarketProfile,
)
from residual.engines.protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec


class FakeEngine:
    name = "fake"
    version = "1"
    capability_class = "test"
    locality = "local"

    def execute(self, task, context):
        return EngineResult(candidate={"answer": 42}, token_usage=10, wall_clock_ms=5)

    def supports(self, capability):
        return capability == "solve"

    def health(self):
        return EngineHealth.HEALTHY

    def normalize(self, raw_output):
        return EngineResult(candidate=raw_output)


def runtime():
    r = AdaptiveAssuranceRuntime()
    r.register_engine(FakeEngine(), MarketProfile(
        engine_id="fake@1",
        capabilities=frozenset({"solve"}),
        cost_per_task=0.01,
        latency_ms=5,
        privacy_class=0,
        location="local",
    ))
    return r


def test_direct_runtime_executes_and_accepts_routine_verified_result():
    r = runtime()
    task = TaskSpec(task_id="t1", capability="solve", input={})
    outcome = r.execute(
        task=task,
        context=ContextAssembly(),
        verifier_id="host:test",
        verifier=lambda candidate: candidate["answer"] == 42,
        assurance=AssuranceClass.ROUTINE,
        required_pass_rate=0.50,
    )
    assert outcome.plan.strategy == ExecutionStrategy.DIRECT
    assert outcome.plan.engine_id == "fake@1"
    assert outcome.verifier_passed is True
    assert outcome.accepted is True
    assert r.market.profiles["fake@1"].trials == 1


def test_security_critical_low_sample_verifier_escalates_to_hitl():
    r = runtime()
    task = TaskSpec(task_id="t2", capability="solve", input={})
    outcome = r.execute(
        task=task,
        context=ContextAssembly(),
        verifier_id="host:new-security-check",
        verifier=lambda candidate: True,
        assurance=AssuranceClass.SECURITY_CRITICAL,
        required_pass_rate=0.50,
    )
    assert outcome.verifier_passed is True
    assert outcome.accepted is False
    assert outcome.escalation_reason == "verifier_quality_requires_hitl"


def test_ground_truth_updates_verifier_quality_not_execution_itself():
    r = runtime()
    task = TaskSpec(task_id="t3", capability="solve", input={})
    outcome = r.execute(
        task=task,
        context=ContextAssembly(),
        verifier_id="host:truth-check",
        verifier=lambda candidate: True,
        assurance=AssuranceClass.ROUTINE,
        required_pass_rate=0.50,
    )
    profile = r.quality.get("host:truth-check")
    assert profile.samples == 0
    r.record_ground_truth(
        verifier_id="host:truth-check",
        verifier_passed=outcome.verifier_passed,
        artifact_acceptable=False,
        confidence=0.9,
    )
    assert profile.samples == 1
    assert profile.false_accept == 1
    assert profile.posterior_mean < 0.5


def test_non_direct_strategy_requires_registered_executor_and_is_executed():
    r = runtime()
    task = TaskSpec(task_id="t4", capability="solve", input={}, metadata={"task_class": "batch"})
    try:
        r.plan(
            task=task,
            verifier_id="host:test",
            assurance=AssuranceClass.ROUTINE,
            required_pass_rate=0.50,
            strategies=(ExecutionStrategy.DYNAMIC_SWARM,),
        )
    except LookupError as exc:
        assert "strategy executor unavailable" in str(exc)
    else:
        raise AssertionError("unregistered swarm strategy must not be silently accepted")

    called = []

    def swarm(engine, task, context):
        called.append(task.task_id)
        return EngineResult(candidate={"answer": 42, "workers": 3}, token_usage=30, wall_clock_ms=8)

    r.register_strategy_executor(ExecutionStrategy.DYNAMIC_SWARM, swarm)
    outcome = r.execute(
        task=task,
        context=ContextAssembly(),
        verifier_id="host:test",
        verifier=lambda candidate: candidate["workers"] == 3,
        assurance=AssuranceClass.ROUTINE,
        required_pass_rate=0.50,
        strategies=(ExecutionStrategy.DYNAMIC_SWARM,),
    )
    assert called == ["t4"]
    assert outcome.plan.strategy == ExecutionStrategy.DYNAMIC_SWARM
    assert outcome.accepted is True


def test_observations_capture_plan_execution_and_delayed_truth():
    events = []
    r = AdaptiveAssuranceRuntime(emit=lambda kind, payload: events.append((kind, dict(payload))))
    r.register_engine(FakeEngine(), MarketProfile(
        engine_id="fake@1",
        capabilities=frozenset({"solve"}),
        cost_per_task=0.01,
        latency_ms=5,
    ))
    task = TaskSpec(task_id="t5", capability="solve", input={})
    outcome = r.execute(
        task=task,
        context=ContextAssembly(),
        verifier_id="host:test",
        verifier=lambda candidate: True,
        assurance=AssuranceClass.ROUTINE,
        required_pass_rate=0.50,
    )
    r.record_ground_truth(
        verifier_id="host:test",
        verifier_passed=outcome.verifier_passed,
        artifact_acceptable=True,
    )
    kinds = [kind for kind, _ in events]
    assert "assurance_plan" in kinds
    assert "assurance_execution" in kinds
    assert "verifier_ground_truth" in kinds
