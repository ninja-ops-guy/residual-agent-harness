"""Development benchmark for the Orca-derived staged flow layer.

Measured metrics are real local CPU timings. Efficiency comparisons are explicitly
counterfactual/model-based because the staged flow is not yet the runtime executor.

Do not cite this fixture as live-provider or production performance evidence.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Callable, Any

from ..core import digest
from .compiler import RequirementCompiler
from .flow import ExecutionProfile, FlowCompiler, ResidualFlow, StageKind
from .intent import Intent
from .pipeline import Orchestrator
from .requirements import Requirement

BENCHMARK_SCHEMA = "residual.orchestrator.flow-benchmark.v1"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    requirements: tuple[Requirement, ...]

    def orchestrator(self) -> Orchestrator:
        requirements = self.requirements
        return Orchestrator(compiler=RequirementCompiler(lambda _: requirements))


def _requirement(
    requirement_id: str,
    *,
    depends_on: tuple[str, ...] = (),
    files: tuple[str, ...] = (),
    external_io: bool = False,
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        description=f"complete {requirement_id}",
        depends_on=depends_on,
        owner="benchmark",
        acceptance_criteria=("fixture check passes",),
        measurable_condition="fixture check exits zero",
        files=files,
        external_io=external_io,
    )


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            "single",
            (_requirement("single", files=("src/single.py",)),),
        ),
        BenchmarkCase(
            "reviewed",
            (
                _requirement("left", files=("src/left.py",)),
                _requirement("right", files=("src/right.py",)),
            ),
        ),
        BenchmarkCase(
            "swarm",
            tuple(
                _requirement(f"lane-{i}", files=(f"src/lane_{i}.py",))
                for i in range(4)
            ),
        ),
        BenchmarkCase(
            "network-reviewed",
            (
                _requirement("local", files=("src/local.py",)),
                _requirement("remote", files=("src/remote.py",), external_io=True),
            ),
        ),
    )


def _timing(fn: Callable[[], Any], iterations: int) -> dict[str, float]:
    if iterations < 5:
        raise ValueError("benchmark iterations must be >= 5")
    for _ in range(min(10, iterations)):
        fn()
    samples = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        fn()
        samples.append(time.perf_counter_ns() - start)
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return {
        "median_us": statistics.median(samples) / 1000.0,
        "p95_us": ordered[p95_index] / 1000.0,
        "min_us": min(samples) / 1000.0,
        "max_us": max(samples) / 1000.0,
    }


def _profile_uniform_budget(profile: ExecutionProfile) -> int:
    return {
        ExecutionProfile.SINGLE: 2500,
        ExecutionProfile.REVIEWED: 4000,
        ExecutionProfile.SWARM: 8000,
    }[profile]


def _flow_metrics(flow: ResidualFlow) -> dict[str, Any]:
    model_kinds = {StageKind.AGENT, StageKind.REVIEW, StageKind.SWARM}
    non_human = [s for s in flow.stages if s.kind is not StageKind.HUMAN_GATE]
    model_stages = [s for s in flow.stages if s.kind in model_kinds]
    deterministic = [s for s in flow.stages if s.kind is StageKind.DETERMINISTIC]

    uniform_budget = _profile_uniform_budget(flow.profile)
    counterfactual_calls = len(non_human)
    staged_calls = len(model_stages)
    counterfactual_tokens = counterfactual_calls * uniform_budget
    staged_tokens = sum(s.budget.max_tokens for s in model_stages)

    tool_universe = sorted({tool for s in flow.stages for tool in s.capability.tools})
    unrestricted_tool_stage_pairs = len(tool_universe) * len(flow.stages)
    granted_tool_stage_pairs = sum(len(s.capability.tools) for s in flow.stages)

    return {
        "profile": flow.profile.value,
        "stage_count": len(flow.stages),
        "deterministic_stage_count": len(deterministic),
        "model_stage_count": staged_calls,
        "declared_model_token_ceiling": staged_tokens,
        "counterfactual": {
            "name": "uniform-model-every-nonhuman-stage",
            "model_call_count": counterfactual_calls,
            "model_token_ceiling": counterfactual_tokens,
            "note": (
                "Synthetic comparison only: assumes each non-HITL stage used the "
                "profile execution-stage token ceiling."
            ),
        },
        "modeled_model_call_reduction_pct": (
            100.0 * (counterfactual_calls - staged_calls) / counterfactual_calls
            if counterfactual_calls else 0.0
        ),
        "modeled_token_ceiling_reduction_pct": (
            100.0 * (counterfactual_tokens - staged_tokens) / counterfactual_tokens
            if counterfactual_tokens else 0.0
        ),
        "capability_surface": {
            "tool_universe_size": len(tool_universe),
            "unrestricted_tool_stage_pairs": unrestricted_tool_stage_pairs,
            "granted_tool_stage_pairs": granted_tool_stage_pairs,
            "reduction_pct": (
                100.0 * (unrestricted_tool_stage_pairs - granted_tool_stage_pairs)
                / unrestricted_tool_stage_pairs
                if unrestricted_tool_stage_pairs else 0.0
            ),
        },
    }


def run_flow_benchmark(*, iterations: int = 250) -> dict[str, Any]:
    cases = []
    all_hash_stable = True

    for case in benchmark_cases():
        orch = case.orchestrator()
        intent = Intent(f"benchmark {case.case_id}")
        plan = orch.plan(intent)
        compiler = FlowCompiler()
        flow = compiler.compile(plan)

        plan_timing = _timing(lambda: orch.plan(intent), iterations)
        flow_only_timing = _timing(lambda: compiler.compile(plan), iterations)
        combined_timing = _timing(lambda: orch.flow(intent), iterations)

        hashes = {compiler.compile(plan).flow_hash for _ in range(20)}
        hash_stable = len(hashes) == 1 and flow.flow_hash in hashes
        all_hash_stable = all_hash_stable and hash_stable

        metrics = _flow_metrics(flow)
        cases.append({
            "case_id": case.case_id,
            "plan_hash": plan.plan_hash,
            "flow_hash": flow.flow_hash,
            "flow_hash_stable": hash_stable,
            "timing": {
                "plan_compile": plan_timing,
                "flow_increment": flow_only_timing,
                "plan_plus_flow": combined_timing,
            },
            **metrics,
        })

    modeled_call_reductions = [c["modeled_model_call_reduction_pct"] for c in cases]
    modeled_token_reductions = [c["modeled_token_ceiling_reduction_pct"] for c in cases]
    flow_overheads = [c["timing"]["flow_increment"]["median_us"] for c in cases]

    thresholds = {
        "min_modeled_model_call_reduction_pct": 25.0,
        "min_modeled_token_ceiling_reduction_pct": 20.0,
        "max_flow_compile_median_us": 5000.0,
    }
    threshold_results = {
        "model_calls": min(modeled_call_reductions) >= thresholds["min_modeled_model_call_reduction_pct"],
        "token_ceiling": min(modeled_token_reductions) >= thresholds["min_modeled_token_ceiling_reduction_pct"],
        "compile_overhead": max(flow_overheads) <= thresholds["max_flow_compile_median_us"],
        "determinism": all_hash_stable,
    }

    return {
        "schema_version": BENCHMARK_SCHEMA,
        "evidence_level": "development_fixture",
        "simulation": True,
        "iterations_per_timing": iterations,
        "cases": cases,
        "thresholds": thresholds,
        "threshold_results": threshold_results,
        "summary": {
            "min_modeled_model_call_reduction_pct": min(modeled_call_reductions),
            "min_modeled_token_ceiling_reduction_pct": min(modeled_token_reductions),
            "max_flow_compile_median_us": max(flow_overheads),
            "all_flow_hashes_stable": all_hash_stable,
            "material_architecture_efficiency_signal": all(threshold_results.values()),
            "live_execution_improvement_proven": False,
            "claim_boundary": (
                "Real timings cover plan/flow compilation only. Model-call/token and "
                "capability reductions are synthetic counterfactuals, not observed "
                "provider usage. End-to-end runtime improvement remains unproven "
                "until a staged executor is connected and measured."
            ),
        },
        "benchmark_hash": digest({
            "schema_version": BENCHMARK_SCHEMA,
            "iterations": iterations,
            "case_ids": [c.case_id for c in benchmark_cases()],
            "thresholds": thresholds,
        }),
    }
