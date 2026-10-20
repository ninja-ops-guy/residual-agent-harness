"""Deterministic Swarm 5 economics/observability development fixture.

This exercises measurement and reconstruction code; it is not live-model
evidence and must not be used to support empirical performance claims.
"""
from __future__ import annotations

from collections import defaultdict

from ..assurance import ExecutionStrategy, OrchestrationTaxController
from ..core import digest
from ..observability import (
    CostAccounting, ReliabilityObservation, TimingBreakdown,
    build_reliability_report, pareto_inputs,
)


TOPOLOGIES = (
    ExecutionStrategy.DIRECT,
    ExecutionStrategy.SINGLE_VERIFIED_WORKER,
    ExecutionStrategy.FIXED_SWARM,
    ExecutionStrategy.DYNAMIC_SWARM,
    ExecutionStrategy.HETEROGENEOUS_SWARM,
)

PROFILES: dict[ExecutionStrategy, dict[str, object]] = {
    ExecutionStrategy.DIRECT: {
        "engine_mix": ("fixture-strong",), "worker_count": 1,
        "verifier_family": "none", "evidence_size_bytes": 4_096,
    },
    ExecutionStrategy.SINGLE_VERIFIED_WORKER: {
        "engine_mix": ("fixture-strong",), "worker_count": 1,
        "verifier_family": "mechanical", "evidence_size_bytes": 8_192,
    },
    ExecutionStrategy.FIXED_SWARM: {
        "engine_mix": ("fixture-strong",), "worker_count": 3,
        "verifier_family": "ensemble", "evidence_size_bytes": 32_768,
    },
    ExecutionStrategy.DYNAMIC_SWARM: {
        "engine_mix": ("fixture-strong",), "worker_count": 4,
        "verifier_family": "ensemble", "evidence_size_bytes": 65_536,
    },
    ExecutionStrategy.HETEROGENEOUS_SWARM: {
        "engine_mix": ("fixture-local", "fixture-strong"), "worker_count": 4,
        "verifier_family": "diverse-ensemble", "evidence_size_bytes": 98_304,
    },
}

LATENCY_MS = {
    ExecutionStrategy.DIRECT: 100.0,
    ExecutionStrategy.SINGLE_VERIFIED_WORKER: 155.0,
    ExecutionStrategy.FIXED_SWARM: 310.0,
    ExecutionStrategy.DYNAMIC_SWARM: 390.0,
    ExecutionStrategy.HETEROGENEOUS_SWARM: 430.0,
}

COST_USD = {
    ExecutionStrategy.DIRECT: 0.010,
    ExecutionStrategy.SINGLE_VERIFIED_WORKER: 0.018,
    ExecutionStrategy.FIXED_SWARM: 0.055,
    ExecutionStrategy.DYNAMIC_SWARM: 0.070,
    ExecutionStrategy.HETEROGENEOUS_SWARM: 0.095,
}

# Three calibration outcomes per task class and topology.  Small edits do not
# gain quality from swarming; wide refactors do.  This makes distinct learned
# preferences an observable result rather than a hard-coded routing rule.
SUCCESS = {
    "small-edit": {
        topology: (True, True, True) for topology in TOPOLOGIES
    },
    "wide-refactor": {
        ExecutionStrategy.DIRECT: (False, False, False),
        ExecutionStrategy.SINGLE_VERIFIED_WORKER: (True, False, False),
        ExecutionStrategy.FIXED_SWARM: (True, True, False),
        ExecutionStrategy.DYNAMIC_SWARM: (True, True, True),
        ExecutionStrategy.HETEROGENEOUS_SWARM: (True, True, True),
    },
}


def _timing(topology: ExecutionStrategy, repeat: int) -> TimingBreakdown:
    wall = LATENCY_MS[topology] + repeat * 2.0
    planning = 5.0 if topology is ExecutionStrategy.DIRECT else 20.0
    scheduling = 2.0 if topology is ExecutionStrategy.DIRECT else 12.0
    context = 4.0 if topology is ExecutionStrategy.DIRECT else 18.0
    verifier = 0.0 if topology is ExecutionStrategy.DIRECT else 25.0
    integration = 2.0 if topology is ExecutionStrategy.DIRECT else 15.0
    retry = 0.0
    coordination = 2.0 if topology is ExecutionStrategy.DIRECT else 20.0
    host = 5.0
    worker = wall - sum((planning, scheduling, context, verifier, integration,
                         retry, coordination, host))
    workers = int(PROFILES[topology]["worker_count"])
    return TimingBreakdown(
        planning_ms=planning, scheduling_ms=scheduling,
        context_packaging_ms=context, worker_execution_ms=worker,
        verifier_execution_ms=verifier, integration_ms=integration,
        retry_rework_ms=retry, coordination_ms=coordination,
        host_overhead_ms=host, wall_clock_ms=wall,
        worker_resource_ms=worker * workers,
        verifier_resource_ms=verifier,
    )


def _cost(topology: ExecutionStrategy, *, unknown: bool = False) -> CostAccounting:
    if unknown:
        return CostAccounting()
    workers = int(PROFILES[topology]["worker_count"])
    return CostAccounting(
        input_tokens=200 * workers, output_tokens=64 * workers,
        cached_tokens=0, reasoning_tokens=0,
        api_cost_usd=COST_USD[topology], local_cpu_ms=25.0 * workers,
        local_gpu_ms=0.0, retries=0, failed_call_cost_usd=0.0,
    )


def _observation(index: int, task_class: str, topology: ExecutionStrategy,
                 repeat: int, success: bool | None, *, commit_sha: str,
                 tree_sha: str, development_unknown: bool = False
                 ) -> ReliabilityObservation:
    accepted = success is True
    terminal = "UNKNOWN" if success is None else "PASS" if success else "REJECTED"
    profile = PROFILES[topology]
    return ReliabilityObservation(
        observation_id=f"swarm5-{index:04d}",
        task_id=f"{task_class}-{topology.value}-{repeat}",
        task_class=task_class, topology=topology.value,
        engine_mix=tuple(profile["engine_mix"]),
        worker_count=int(profile["worker_count"]),
        verifier_family=str(profile["verifier_family"]),
        evidence_size_bytes=int(profile["evidence_size_bytes"]),
        terminal_state=terminal, correct=success, accepted=accepted,
        verifier_rejected=success is False and topology is not ExecutionStrategy.DIRECT,
        fault_label=None, fault_caught=None, conflicts=0,
        evidence_complete=not development_unknown,
        commit_sha=commit_sha, tree_sha=tree_sha,
        timing=_timing(topology, repeat),
        cost=_cost(topology, unknown=development_unknown),
    )


def fixture_observations(commit_sha: str, tree_sha: str) -> list[ReliabilityObservation]:
    rows = []
    index = 0
    for task_class in sorted(SUCCESS):
        for topology in TOPOLOGIES:
            for repeat, success in enumerate(SUCCESS[task_class][topology]):
                index += 1
                # One explicit UNKNOWN proves missing usage is retained.  It
                # replaces, rather than deletes, its calibration run.
                unknown = task_class == "small-edit" and topology is \
                    ExecutionStrategy.HETEROGENEOUS_SWARM and repeat == 2
                rows.append(_observation(
                    index, task_class, topology, repeat,
                    None if unknown else success,
                    commit_sha=commit_sha, tree_sha=tree_sha,
                    development_unknown=unknown,
                ))
    return rows


def _tax_snapshot(controller: OrchestrationTaxController,
                  rows: list[ReliabilityObservation]) -> dict[str, object]:
    grouped: dict[tuple[str, ExecutionStrategy], list[ReliabilityObservation]] = defaultdict(list)
    for row in rows:
        grouped[(row.task_class, ExecutionStrategy(row.topology))].append(row)
    entries = []
    for task_class in sorted(SUCCESS):
        direct_rows = grouped[(task_class, ExecutionStrategy.DIRECT)]
        for topology in TOPOLOGIES:
            current = grouped[(task_class, topology)]
            predicted = controller.orchestration_tax(
                {"task_class": task_class}, topology,
                direct_features=PROFILES[ExecutionStrategy.DIRECT],
                swarm_features=PROFILES[topology])
            for row in current:
                direct = next(item for item in direct_rows
                              if item.task_id.rsplit("-", 1)[-1] ==
                              row.task_id.rsplit("-", 1)[-1])
                observed = None
                if (row.correct is not None and direct.correct is not None
                        and row.cost.cost_complete and direct.cost.cost_complete):
                    row_success = float(row.correct is True and row.accepted)
                    direct_success = float(direct.correct is True and direct.accepted)
                    row_cost = (row.cost.api_cost_usd or 0.0) + (
                        row.cost.failed_call_cost_usd or 0.0)
                    direct_cost = (direct.cost.api_cost_usd or 0.0) + (
                        direct.cost.failed_call_cost_usd or 0.0)
                    observed = (
                        controller.weights.success_value * (direct_success - row_success)
                        - controller.weights.cost * (direct_cost - row_cost)
                        - controller.weights.latency * (
                            direct.timing.wall_clock_ms - row.timing.wall_clock_ms))
                entries.append({
                    "observation_id": row.observation_id,
                    "task_class": task_class,
                    "topology": topology.value,
                    "predicted_quality_adjusted_tax": round(predicted, 9),
                    "observed_quality_adjusted_tax": (
                        None if observed is None else round(observed, 9)),
                })
    body = {"schema_version": "residual.orchestration-tax-snapshot.v1",
            "baseline_topology": "direct", "entries": entries}
    return {**body, "snapshot_sha256": digest(body)}


def build_swarm5_evidence(commit_sha: str, tree_sha: str) -> dict[str, object]:
    rows = fixture_observations(commit_sha, tree_sha)
    controller = OrchestrationTaxController(exploration_bonus=0.0)
    for row in rows:
        controller.observe_reliability(row)

    decisions = []
    for task_class in sorted(SUCCESS):
        decision = controller.decide(
            {"task_class": task_class}, TOPOLOGIES,
            candidate_features=PROFILES)
        selected = ExecutionStrategy(decision.selected_topology)
        selected_rows = [r for r in rows if r.task_class == task_class
                         and r.topology == selected.value]
        exemplar = selected_rows[0]
        outcome = controller.observe_reliability(exemplar)
        decisions.append(decision.with_result(outcome).payload())

    report = build_reliability_report(rows)
    pareto = pareto_inputs(report)
    body: dict[str, object] = {
        "schema_version": "residual.swarm5-evidence.v1",
        "evidence_level": "development_fixture",
        "claim_limit": "deterministic fixture; not live-model performance evidence",
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "raw_timing_observations": [row.payload() for row in rows],
        "topology_decision_log": decisions,
        "orchestration_tax_snapshot": _tax_snapshot(controller, rows),
        "aggregate_report": report,
        "report_sha256": report["report_sha256"],
        "pareto_inputs": pareto,
        "accounting_gaps": {
            "unknown_usage_runs": report["overall"]["completeness"]["unknown_usage"],
            "unknown_cost_runs": report["overall"]["completeness"]["unknown_cost"],
        },
    }
    body["evidence_sha256"] = digest(body)
    return body
