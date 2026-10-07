"""SPEC-SWARM-RUNTIME-005 tests: RUN-R1..R9 + cancellation/staleness faults."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from residual.core import ContractError
from residual.engines.protocol import (
    ContextAssembly,
    EngineHealth,
    EngineResult,
    TaskSpec,
)
from residual.runtime import (
    BufferedObservationSink,
    CancellationBudget,
    CancellationController,
    FreshnessGuard,
    LocalDeterministicEngine,
    PolicyAuthority,
    SDKFunctionEngine,
    TelemetryStatus,
    build_default_adapters,
    build_execution_record,
    check_adapter_conformance,
)
from residual.runtime import evidence as runtime_evidence
from residual.runtime.router import RoutingError, RuntimeCapabilityRouter


class FakeClock:
    def __init__(self):
        self.now = 5000.0

    def __call__(self):
        return self.now


def echo_fn(task_input, context):
    return {"output": {"echo": task_input, "context": context}}


def make_adapters():
    return (
        LocalDeterministicEngine(version="1.0.0", capabilities=("agent", "text")),
        SDKFunctionEngine(echo_fn, name="claude-sdk", version="fixture-1",
                          capabilities=("agent",)),
    )


# ---------------------------------------------------------------- RUN-R1

def test_r1_adapters_conform_to_execution_engine_protocol():
    local, sdk = make_adapters()
    from residual.engines.protocol import ExecutionEngine
    assert isinstance(local, ExecutionEngine)
    assert isinstance(sdk, ExecutionEngine)
    assert local.locality == "local"
    assert sdk.locality == "cloud"


def test_r1_sdk_wrapper_delegates_to_existing_sdk_adapter():
    sdk = SDKFunctionEngine(echo_fn, name="claude-sdk", version="v9",
                            capabilities=("agent",))
    assert sdk.name == "claude-sdk" and sdk.version == "v9"
    result = sdk.execute(TaskSpec("t1", "agent", {"a": 1}), ContextAssembly(values={}))
    assert result.candidate == {"echo": {"a": 1}, "context": {}}


def test_r1_local_engine_is_deterministic():
    local = LocalDeterministicEngine()
    task = TaskSpec("t", "agent", {"x": 1})
    ctx = ContextAssembly(values={"c": 2})
    r1 = local.execute(task, ctx)
    r2 = local.execute(task, ctx)
    assert r1.candidate == r2.candidate


# ---------------------------------------------------------------- RUN-R2

def test_r2_router_probes_declared_capability_before_routing():
    local, sdk = make_adapters()
    router = RuntimeCapabilityRouter()
    router.register(local, ("text", "agent"))
    router.register(sdk, ("agent",))
    engine = router.route("agent")
    assert engine.supports("agent")


def test_r2_router_fails_closed_on_capability_mismatch():
    local, _sdk = make_adapters()
    router = RuntimeCapabilityRouter()
    router.register(local, ("text",))
    with pytest.raises(RoutingError):
        router.route("vision")


def test_r2_router_rejects_unhealthy_engine_at_registration():
    class DeadEngine(LocalDeterministicEngine):
        def health(self):
            return EngineHealth.UNAVAILABLE

    router = RuntimeCapabilityRouter()
    with pytest.raises(ValueError):
        router.register(DeadEngine(), ("agent",))


def test_r2_router_fails_closed_when_engine_degrades_after_registration():
    local, _sdk = make_adapters()
    router = RuntimeCapabilityRouter()
    router.register(local, ("agent",))
    local_supports = local.supports
    local.supports = lambda cap: False  # degrade post-registration
    try:
        with pytest.raises(RoutingError):
            router.route("agent")
    finally:
        local.supports = local_supports


# ---------------------------------------------------------------- RUN-R3

def test_r3_local_preferred_when_capability_equivalent():
    local, sdk = make_adapters()
    router = RuntimeCapabilityRouter()
    router.register(sdk, ("agent",))
    router.register(local, ("agent",))
    selected = router.route("agent")
    assert selected.locality == "local"


def test_r3_deterministic_tie_break_for_equal_scores():
    a = LocalDeterministicEngine(version="1.0.0")
    b = LocalDeterministicEngine(version="1.0.0")
    # Distinct names, both local: name tie-break must be stable.
    a.name = "alpha-local"
    b.name = "beta-local"
    router = RuntimeCapabilityRouter()
    router.register(b, ("agent",))
    router.register(a, ("agent",))
    first = router.route("agent")
    second = router.route("agent")
    assert first.name == "alpha-local" and second.name == "alpha-local"


# ---------------------------------------------------------------- RUN-R4

def test_r4_engine_metadata_enters_execution_record_and_receipt():
    local, _sdk = make_adapters()
    task = TaskSpec("t-r4", "agent", {"q": 1})
    result = local.execute(task, ContextAssembly(values={}))
    record = build_execution_record(local, task, result)
    payload = record.payload()
    assert payload["engine_name"] == "local-deterministic"
    assert payload["engine_version"] == "1.0.0"
    assert payload["engine_provider"]
    receipt = payload["station_receipt"]
    assert receipt["engine_name"] == "local-deterministic"
    assert receipt["engine_version"] == "1.0.0"
    assert receipt["engine_provider"] == payload["engine_provider"]
    assert len(record.record_hash) == 64


def test_r4_provider_engine_metadata_includes_provider_name():
    from residual.engines.provider_bridge import ProviderEngineConfig, ProviderExecutionEngine

    cfg = ProviderEngineConfig(provider="openai", model="gpt-fixture")
    engine = ProviderExecutionEngine(cfg)
    task = TaskSpec("t-prov", "text", "hi")
    result = EngineResult(candidate="ok")
    record = build_execution_record(engine, task, result)
    assert record.engine_provider == "openai"
    assert record.engine_name == "provider:openai:gpt-fixture"


# ---------------------------------------------------------------- RUN-R5

def test_r5_sanitize_disables_provider_native_autonomy_and_hitl():
    authority = PolicyAuthority()
    sanitized = authority.sanitize_dispatch_config(
        {"auto_approve": True, "hitl": True, "yolo": True,
         "human_input": True, "autonomous": True})
    for key in ("auto_approve", "hitl", "yolo", "human_input", "autonomous"):
        assert sanitized[key] is False
    assert sanitized["residual_policy_authoritative"] is True


def test_r5_provider_authority_metadata_never_overrides_residual_policy():
    authority = PolicyAuthority()
    decision = authority.decide("agent", {"provider_approved": True,
                                          "self_approved": True})
    assert decision.authority == "residual"
    assert "ignored" in decision.reason


def test_r5_residual_deny_and_escalate_are_authoritative():
    authority = PolicyAuthority({"deny_capabilities": ("shell",),
                                 "escalate_capabilities": ("deploy",)})
    assert authority.decide("shell", {}).verdict == "deny"
    assert authority.decide("deploy", {}).verdict == "escalate"
    # Provider approval cannot flip a residual deny.
    assert authority.decide("shell", {"provider_approved": True}).verdict == "deny"


def test_r5_apply_fails_closed_on_provider_authority_leak():
    authority = PolicyAuthority()
    result = EngineResult(candidate="x", raw_metadata={"provider_approved": True})
    with pytest.raises(ContractError):
        authority.apply(result)
    clean = authority.apply(EngineResult(candidate="x", raw_metadata={}))
    assert clean.raw_metadata["residual_policy_authoritative"] is True


# ---------------------------------------------------------------- RUN-R6

def test_r6_fresh_read_returns_current_with_age():
    clock = FakeClock()
    guard = FreshnessGuard(max_age_s=5.0, clock=clock)
    guard.update({"m": 1})
    clock.now += 2.0
    reading = guard.read()
    assert reading.status == TelemetryStatus.CURRENT
    assert reading.value == {"m": 1}
    assert 1.9 < reading.age_s < 2.1


def test_r6_stale_read_returns_unknown_and_suppresses_value():
    clock = FakeClock()
    guard = FreshnessGuard(max_age_s=5.0, clock=clock)
    guard.update({"m": 1})
    clock.now += 10.0
    reading = guard.read()
    assert reading.status == TelemetryStatus.UNKNOWN
    assert reading.value is None
    assert reading.reason == "telemetry_stale"


def test_r6_absent_telemetry_is_unknown():
    guard = FreshnessGuard(max_age_s=5.0, clock=FakeClock())
    reading = guard.read()
    assert reading.status == TelemetryStatus.UNKNOWN
    assert reading.reason == "telemetry_absent"


def test_r6_async_telemetry_client_stale_read_is_unknown():
    from residual.async_io.telemetry import AsyncTelemetryClient
    from residual.verifier import CheckResult

    async def fetch():
        return {"m": 1}

    client = AsyncTelemetryClient(fetch, refresh_interval_s=0.01,
                                  max_telemetry_age_s=0.000001)
    client._value = {"m": 1}
    client._updated_at = 0.0  # ancient
    result, reason = client.verify_cached(lambda v, p: (CheckResult.PASS, "ok"))
    assert result == CheckResult.UNKNOWN
    assert reason == "telemetry_stale"


# ---------------------------------------------------------------- RUN-R7

def test_r7_abort_propagates_within_budget():
    async def run():
        controller = CancellationController(CancellationBudget(2.0))

        async def op():
            await asyncio.sleep(60)

        controller.track(asyncio.create_task(op()), name="op-a")
        controller.track(asyncio.create_task(op()), name="op-b")
        await asyncio.sleep(0.01)
        return await controller.abort()

    report = asyncio.run(run())
    assert report.cancelled is True
    assert report.propagated == 2
    assert report.survived == ()
    assert dict(report.outcomes) == {"op-a": "cancelled", "op-b": "cancelled"}


def test_r7_budget_exceeded_is_fail_closed_with_survivors():
    async def run():
        controller = CancellationController(CancellationBudget(0.05))

        async def stubborn():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                await asyncio.sleep(60)

        controller.track(asyncio.create_task(stubborn()), name="stubborn")
        await asyncio.sleep(0.01)
        return await controller.abort()

    report = asyncio.run(run())
    assert report.cancelled is False
    assert report.reason == "cancellation_budget_exceeded"
    assert report.survived == ("stubborn",)


def test_r7_abort_with_no_active_operations_is_clean():
    async def run():
        controller = CancellationController(CancellationBudget(1.0))
        return await controller.abort()

    report = asyncio.run(run())
    assert report.cancelled and report.reason == "no_active_operations"


# ---------------------------------------------------------------- RUN-R8

def test_r8_buffered_async_flush_delivers_events():
    delivered = []

    async def run():
        sink = BufferedObservationSink(downstream=lambda b: delivered.extend(b),
                                       flush_interval_s=0.01)
        sink.start()
        for i in range(5):
            sink.emit("obs", {"i": i})
        await asyncio.sleep(0.05)
        await sink.close()
        return sink

    sink = asyncio.run(run())
    assert len(delivered) == 5
    assert sink.flushed_events == 5
    assert sink.dropped_events == 0


def test_r8_terminal_flush_is_durable(tmp_path: Path):
    path = tmp_path / "observations.jsonl"

    async def run():
        sink = BufferedObservationSink(flush_interval_s=60.0, durable_path=path)
        # Background interval far in the future: only close() may flush.
        sink.start()
        for i in range(3):
            sink.emit("terminal", {"i": i})
        return await sink.close()

    flushed = asyncio.run(run())
    assert flushed == 3
    lines = [json.loads(l) for l in path.read_text().splitlines()]
    assert [l["payload"]["i"] for l in lines] == [0, 1, 2]


def test_r8_emit_after_close_is_rejected():
    async def run():
        sink = BufferedObservationSink(flush_interval_s=0.01)
        sink.start()
        await sink.close()
        return sink.emit("late", {})

    assert asyncio.run(run()) is False


def test_r8_sink_satisfies_run_coordinator_cancel_contract():
    from residual.async_io.coordinator import AsyncRunCoordinator

    async def run():
        coordinator = AsyncRunCoordinator()
        sink = BufferedObservationSink(flush_interval_s=0.01)
        sink.start()
        coordinator.register(sink)  # raises unless async cancel(timeout_s=...)
        sink.emit("obs", {"x": 1})
        await coordinator.cancel_all()
        return sink

    sink = asyncio.run(run())
    assert sink.flushed_events == 1


# ---------------------------------------------------------------- RUN-R9

ADAPTERS = make_adapters()


@pytest.mark.parametrize("engine", ADAPTERS, ids=lambda e: e.name)
def test_r9_adapter_conformance_suite_passes(engine):
    report = check_adapter_conformance(engine)
    assert report.passed, [n for n, ok in report.checks if not ok]


def test_r9_same_conformance_checks_for_all_adapters():
    reports = [check_adapter_conformance(e) for e in make_adapters()]
    names = [r.check_names() for r in reports]
    assert names[0] == names[1]
    assert len(names[0]) >= 10


def test_r9_conformance_detects_contract_violation():
    class BadEngine(LocalDeterministicEngine):
        def supports(self, capability):
            return True  # claims everything: must fail rejection check

    report = check_adapter_conformance(BadEngine())
    assert not report.passed
    failed = [n for n, ok in report.checks if not ok]
    assert "rejects_undeclared_capability" in failed


# ------------------------------------------------- fault scenarios (R6/R7)

def test_fault_scenarios_deterministic_fail_closed():
    scenarios = runtime_evidence.run_scenarios()
    assert scenarios["all_pass"] is True
    # rerun is byte-identical
    again = runtime_evidence.run_scenarios()
    assert runtime_evidence.scenario_hash(scenarios) == runtime_evidence.scenario_hash(again)


def test_gate_c_reproduction_matches_evidence_hash():
    artifact = runtime_evidence.build_artifact()
    reproduction = runtime_evidence.reproduce(artifact)
    assert reproduction["match"] is True
    assert reproduction["rerun_hash"] == artifact["scenario_hash"]
