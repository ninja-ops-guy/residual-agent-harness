"""Acceptance suite for SPEC-SWARM-OTX-003 and SPEC-SWARM-OBS-006."""
from __future__ import annotations

import copy

import pytest

from residual.assurance import (
    ExecutionStrategy, OrchestrationTaxController, UtilityWeights,
)
from residual.core import ContractError, canonical, digest
from residual.observability import (
    CostAccounting, MetricsRegistry, ReliabilityMetricsProjection,
    ReliabilityObservation, TimingBreakdown, build_reliability_report,
    pareto_inputs, render_prometheus,
)
from residual.eval_frozen.economics import build_swarm5_evidence


COMMIT = "1" * 40
TREE = "2" * 40


def observation(index: int, *, task_class: str = "small-edit",
                topology: str = "direct", correct=True, accepted=True,
                complete=True, known_cost=True, latency=100.0,
                verifier_rejected=False, fault=False):
    # Exclusive buckets sum exactly to latency.  Resource time is separate and
    # may be greater than the critical-path worker duration.
    timing = TimingBreakdown(
        planning_ms=10, scheduling_ms=5, context_packaging_ms=5,
        worker_execution_ms=latency - 40, verifier_execution_ms=5,
        integration_ms=5, retry_rework_ms=0, coordination_ms=5,
        host_overhead_ms=5, wall_clock_ms=latency,
        worker_resource_ms=max(latency - 20, 0), verifier_resource_ms=5,
    )
    cost = CostAccounting(
        input_tokens=100 if known_cost else None,
        output_tokens=20 if known_cost else None,
        cached_tokens=0 if known_cost else None,
        reasoning_tokens=0 if known_cost else None,
        api_cost_usd=0.01 if known_cost else None,
        local_cpu_ms=20 if known_cost else None,
        local_gpu_ms=0 if known_cost else None,
        retries=1 if verifier_rejected else 0,
        failed_call_cost_usd=0.0 if known_cost else None,
    )
    terminal = "UNKNOWN" if correct is None else (
        "PASS" if correct and accepted else "FAIL" if accepted else "REJECTED")
    return ReliabilityObservation(
        observation_id=f"obs-{index}", task_id=f"task-{index}",
        task_class=task_class, topology=topology, engine_mix=("fixture",),
        worker_count=1, verifier_family="fixture-verifier",
        evidence_size_bytes=100, terminal_state=terminal, correct=correct,
        accepted=accepted, verifier_rejected=verifier_rejected,
        fault_label="known-defect" if fault else None,
        fault_caught=(not accepted) if fault else None, conflicts=0,
        evidence_complete=complete, commit_sha=COMMIT, tree_sha=TREE,
        timing=timing, cost=cost,
    )


def test_timing_conservation_and_parallel_resource_accounting():
    row = observation(1, latency=100)
    assert row.timing.exclusive_total_ms == row.timing.wall_clock_ms
    assert row.timing.worker_resource_ms != row.timing.worker_execution_ms
    with pytest.raises(ContractError, match="must equal"):
        TimingBreakdown(planning_ms=1, wall_clock_ms=2)


def test_unknown_usage_and_cost_remain_null_and_in_denominator():
    rows = [observation(1), observation(2, correct=None, accepted=False,
                        complete=False, known_cost=False)]
    report = build_reliability_report(rows)
    overall = report["overall"]
    assert overall["runs"] == 2
    assert overall["P_X"] == 0.5
    assert overall["P_A"] == 0.5
    assert overall["input_tokens"] is None
    assert overall["cost_usd_total"] is None
    assert overall["completeness"] == {
        "evidence_complete": 1, "evidence_missing": 1, "missing_grades": 1,
        "unknown_usage": 1, "unknown_cost": 1,
    }


def test_all_paper_metrics_rebuilt_from_observations():
    rows = [
        observation(1, correct=True, accepted=True),
        observation(2, correct=False, accepted=True, fault=True),
        observation(3, correct=False, accepted=False, verifier_rejected=True,
                    fault=True),
        observation(4, correct=True, accepted=False, verifier_rejected=True),
        observation(5, correct=None, accepted=False, complete=False),
    ]
    metrics = build_reliability_report(rows)["overall"]
    required = {
        "P_X", "P_A", "P_X_given_A", "aer_far", "isr", "assr",
        "acceptance_coverage", "false_rejection_rate", "fcr",
        "throughput_runs_per_sec", "latency_ms_mean", "rework_per_run",
        "conflicts_total", "verifier_rejection_rate", "input_tokens",
        "output_tokens", "cached_tokens", "reasoning_tokens",
        "cost_usd_total", "timing_totals_ms", "completeness",
    }
    assert required <= set(metrics)
    assert metrics["P_X"] == 0.4
    assert metrics["P_A"] == 0.4
    assert metrics["P_X_given_A"] == 0.5
    assert metrics["aer_far"] == 0.5
    assert metrics["isr"] == 0.5
    assert metrics["assr"] == 0.2
    assert metrics["false_rejection_rate"] == 0.5
    assert metrics["fcr"] == 0.5


def test_report_is_canonical_deterministic_and_identity_bound():
    rows = [observation(2), observation(1)]
    first = build_reliability_report(rows)
    second = build_reliability_report(list(reversed(rows)))
    assert canonical(first) == canonical(second)
    assert first["report_sha256"] == second["report_sha256"]
    body = dict(first)
    claimed = body.pop("report_sha256")
    assert claimed == digest(body)
    assert first["source_identities"] == [{"commit_sha": COMMIT, "tree_sha": TREE}]


def test_corrupt_observation_rejected():
    raw = observation(1).payload()
    raw["accepted"] = False
    with pytest.raises(ContractError, match="hash mismatch"):
        ReliabilityObservation.from_dict(raw)
    malformed = copy.deepcopy(observation(2).payload())
    malformed["timing"].pop("planning_ms")
    with pytest.raises(ContractError, match="fields"):
        ReliabilityObservation.from_dict(malformed)


def test_pareto_inputs_cover_requested_axes():
    report = build_reliability_report([
        observation(1, topology="direct"),
        observation(2, topology="dynamic_swarm", latency=200),
    ])
    result = pareto_inputs(report)
    assert result["source_report_sha256"] == report["report_sha256"]
    assert {"reliability", "cost_usd", "latency_ms", "accepted_throughput"} \
        <= set(result["points"][0])


def test_prometheus_projection_covers_families_and_bounds_labels():
    registry = MetricsRegistry()
    projection = ReliabilityMetricsProjection(registry, max_dynamic_values=1)
    projection.observe(observation(1, task_class="class-a"))
    projection.observe(observation(2, task_class="class-b",
                                   verifier_rejected=True))
    rendered = render_prometheus(registry)
    for family in ("runs_total", "acceptance_total", "verifier_rejections_total",
                   "integration_conflicts_total", "retries_total",
                   "phase_seconds", "cost_usd_total", "evidence_total"):
        assert f"residual_reliability_{family}" in rendered
    assert 'task_class="__other__"' in rendered
    assert "task-1" not in rendered and COMMIT not in rendered


def test_controller_learns_distinct_topologies_and_replays_decision():
    controller = OrchestrationTaxController(exploration_bonus=0.0)
    strategies = (ExecutionStrategy.DIRECT, ExecutionStrategy.DYNAMIC_SWARM)
    shared = {"engine_mix": ("fixture",), "worker_count": 1,
              "verifier_family": "fixture-verifier", "evidence_size_bytes": 100}
    for task_class in ("small-edit", "wide-refactor"):
        features = {"task_class": task_class, **shared}
        for _ in range(20):
            controller.observe(
                features, ExecutionStrategy.DIRECT,
                success=task_class == "small-edit", cost=0.01, latency_ms=100)
            controller.observe(
                features, ExecutionStrategy.DYNAMIC_SWARM,
                success=task_class == "wide-refactor", cost=0.02, latency_ms=200)
    small = {"task_class": "small-edit", **shared}
    wide = {"task_class": "wide-refactor", **shared}
    assert controller.choose(small, strategies) is ExecutionStrategy.DIRECT
    assert controller.choose(wide, strategies) is ExecutionStrategy.DYNAMIC_SWARM
    retained = controller.retained_observations()
    replayed = OrchestrationTaxController.replay(
        retained, exploration_bonus=0.0)
    assert replayed.decide(small, strategies).decision_sha256 == \
        controller.decide(small, strategies).decision_sha256
    assert replayed.choose(wide, strategies) is ExecutionStrategy.DYNAMIC_SWARM


def test_decision_carries_predictions_and_eventual_observed_result():
    controller = OrchestrationTaxController(exploration_bonus=0.0)
    features = {"task_class": "small-edit"}
    controller.observe(features, ExecutionStrategy.DIRECT,
                       success=True, cost=0.01, latency_ms=100)
    controller.observe(features, ExecutionStrategy.FIXED_SWARM,
                       success=False, cost=0.2, latency_ms=500)
    decision = controller.decide(
        features, (ExecutionStrategy.DIRECT, ExecutionStrategy.FIXED_SWARM))
    outcome = controller.observe(
        features, ExecutionStrategy.DIRECT,
        success=True, cost=0.01, latency_ms=90)
    completed = decision.with_result(outcome).payload()
    assert completed["estimates"]
    assert completed["selected_topology"] == "direct"
    assert completed["observed_result"]["success"] is True


def test_deployment_tax_threshold_can_force_simpler_topology():
    controller = OrchestrationTaxController(
        weights=UtilityWeights(success_value=10.0),
        exploration_bonus=0.0, deployment_tax_threshold=0.001)
    features = {"task_class": "medium"}
    # Make swarm quality high enough to win utility, while its raw overhead is
    # above the explicit deployment threshold.
    for _ in range(20):
        controller.observe(features, ExecutionStrategy.DIRECT,
                           success=False, cost=0.01, latency_ms=100)
        controller.observe(features, ExecutionStrategy.DYNAMIC_SWARM,
                           success=True, cost=0.02, latency_ms=110)
    assert controller.choose(
        features, (ExecutionStrategy.DIRECT, ExecutionStrategy.DYNAMIC_SWARM)
    ) is ExecutionStrategy.DIRECT


def test_fixture_evidence_covers_handoff_and_is_deterministic():
    first = build_swarm5_evidence(COMMIT, TREE)
    second = build_swarm5_evidence(COMMIT, TREE)
    assert canonical(first) == canonical(second)
    assert first["evidence_sha256"] == second["evidence_sha256"]
    assert len(first["raw_timing_observations"]) == 30
    choices = {row["task_features"]["task_class"]: row["selected_topology"]
               for row in first["topology_decision_log"]}
    assert choices == {"small-edit": "direct", "wide-refactor": "dynamic_swarm"}
    assert all(row["observed_result"] is not None
               for row in first["topology_decision_log"])
    assert first["report_sha256"] == first["aggregate_report"]["report_sha256"]
    assert first["accounting_gaps"] == {
        "unknown_usage_runs": 1, "unknown_cost_runs": 1}
