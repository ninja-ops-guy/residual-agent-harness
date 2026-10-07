"""Gate B/C: machine-readable RUNTIME-005 evidence artifact generation.

Runs the conformance suite against the default adapters plus deterministic
fault scenarios (stale telemetry, cancellation within/over budget,
capability mismatch, provider-authority leak) and emits a JSON artifact with
commit/tree identity, raw observations, per-scenario results, and a
reproducible scenario hash. ``reproduce`` recomputes the scenario section
from the retained fixture definition and verifies the hash matches (Gate C).
"""
from __future__ import annotations

import asyncio
import json
import platform
import subprocess
from typing import Any

from ..core import digest
from ..engines.protocol import ContextAssembly, TaskSpec
from .adapters import LocalDeterministicEngine, SDKFunctionEngine, build_default_adapters
from .cancellation import CancellationBudget, CancellationController
from .conformance import check_adapter_conformance
from .policy import PolicyAuthority
from .router import RoutingError, RuntimeCapabilityRouter
from .telemetry import FreshnessGuard, TelemetryStatus

ARTIFACT_SCHEMA = "residual.swarm.runtime005.evidence.v1"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              check=True, timeout=30).stdout.strip()
    except Exception:
        return "unknown"


class _FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _scenario_stale_telemetry() -> dict[str, Any]:
    clock = _FakeClock()
    guard = FreshnessGuard(max_age_s=5.0, clock=clock)
    guard.update({"cpu": 0.5})
    fresh = guard.read()
    clock.now += 6.0  # exceed max_age_s
    stale = guard.read()
    return {
        "scenario": "stale_telemetry_returns_unknown",
        "observations": [
            {"status": fresh.status.value, "reason": fresh.reason},
            {"status": stale.status.value, "reason": stale.reason,
             "value_suppressed": stale.value is None},
        ],
        "expected": "unknown_when_stale",
        "pass": (fresh.status == TelemetryStatus.CURRENT
                 and stale.status == TelemetryStatus.UNKNOWN and stale.value is None),
    }


def _scenario_cancellation_within_budget() -> dict[str, Any]:
    async def run():
        controller = CancellationController(CancellationBudget(2.0))

        async def worker():
            await asyncio.sleep(60)

        controller.track(asyncio.create_task(worker()), name="op-1")
        controller.track(asyncio.create_task(worker()), name="op-2")
        await asyncio.sleep(0.01)
        return await controller.abort()

    report = asyncio.run(run())
    return {
        "scenario": "cancellation_within_budget",
        "observations": [{"outcomes": list(report.outcomes), "survived": list(report.survived)}],
        "expected": "all_cancelled_within_budget",
        "pass": report.cancelled and report.propagated == 2 and not report.survived,
    }


def _scenario_cancellation_budget_exceeded() -> dict[str, Any]:
    async def run():
        controller = CancellationController(CancellationBudget(0.05))

        async def stubborn():
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                await asyncio.sleep(60)  # swallow cancel; outlives budget

        controller.track(asyncio.create_task(stubborn()), name="stubborn-op")
        await asyncio.sleep(0.01)
        report = await controller.abort()
        return report

    report = asyncio.run(run())
    return {
        "scenario": "cancellation_budget_exceeded_fails_closed",
        "observations": [{"cancelled": report.cancelled, "survived": list(report.survived),
                          "reason": report.reason}],
        "expected": "report_not_cancelled_survivor_listed",
        "pass": (not report.cancelled and report.survived == ("stubborn-op",)
                 and report.reason == "cancellation_budget_exceeded"),
    }


def _scenario_capability_mismatch() -> dict[str, Any]:
    local, sdk = build_default_adapters()
    router = RuntimeCapabilityRouter()
    router.register(local, ("text", "agent"))
    router.register(sdk, ("agent",))
    selected = router.route("agent")
    fail_closed = False
    try:
        router.route("__unsupported__")
    except RoutingError:
        fail_closed = True
    return {
        "scenario": "capability_probe_fail_closed_and_local_preferred",
        "observations": [{"selected": f"{selected.name}@{selected.version}",
                          "locality": selected.locality,
                          "unsupported_route_raised": fail_closed}],
        "expected": "local_preferred_and_routing_error_on_mismatch",
        "pass": selected.locality == "local" and fail_closed,
    }


def _scenario_provider_authority_leak() -> dict[str, Any]:
    authority = PolicyAuthority()
    engine = LocalDeterministicEngine()
    task = TaskSpec(task_id="leak-1", capability="agent", input={})
    result = engine.execute(task, ContextAssembly(values={}))
    leaked = type(result)(candidate=result.candidate,
                          raw_metadata={"provider_approved": True})
    blocked = False
    try:
        authority.apply(leaked)
    except Exception:
        blocked = True
    sanitized = authority.sanitize_dispatch_config(
        {"auto_approve": True, "hitl": True, "yolo": True})
    decision = authority.decide("agent", {"provider_approved": True})
    return {
        "scenario": "provider_native_authority_never_overrides_residual",
        "observations": [{"leak_blocked": blocked, "sanitized": sanitized,
                          "decision": decision.verdict, "authority": decision.authority}],
        "expected": "leak_blocked_and_residual_authoritative",
        "pass": (blocked and decision.authority == "residual"
                 and sanitized["auto_approve"] is False and sanitized["hitl"] is False),
    }


def run_scenarios() -> dict[str, Any]:
    """Run conformance + fault scenarios deterministically (Gate B/C core)."""
    adapters = build_default_adapters()
    conformance = []
    for engine in adapters:
        report = check_adapter_conformance(engine)
        conformance.append({
            "engine_name": report.engine_name,
            "engine_version": report.engine_version,
            "passed": report.passed,
            "checks": list(report.checks),
        })
    scenarios = [
        _scenario_stale_telemetry(),
        _scenario_cancellation_within_budget(),
        _scenario_cancellation_budget_exceeded(),
        _scenario_capability_mismatch(),
        _scenario_provider_authority_leak(),
    ]
    return {
        "conformance": conformance,
        "fault_scenarios": scenarios,
        "all_pass": all(s["pass"] for s in scenarios) and all(c["passed"] for c in conformance),
    }


def scenario_hash(scenarios_section: dict[str, Any]) -> str:
    return digest(json.loads(json.dumps(scenarios_section, sort_keys=True)))


def build_artifact() -> dict[str, Any]:
    scenarios = run_scenarios()
    artifact = {
        "schema_version": ARTIFACT_SCHEMA,
        "spec": "SPEC-SWARM-RUNTIME-005",
        "identity": {
            "commit": _git("rev-parse", "HEAD"),
            "tree": _git("rev-parse", "HEAD^{tree}"),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "scenarios": scenarios,
        "scenario_hash": scenario_hash(scenarios),
    }
    return artifact


def reproduce(artifact: dict[str, Any]) -> dict[str, Any]:
    """Gate C: rerun scenarios from the retained fixture and compare hashes."""
    rerun = run_scenarios()
    rerun_hash = scenario_hash(rerun)
    return {
        "retained_hash": artifact.get("scenario_hash"),
        "rerun_hash": rerun_hash,
        "match": rerun_hash == artifact.get("scenario_hash"),
    }
