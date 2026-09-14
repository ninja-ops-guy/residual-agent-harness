from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from observation_layer import ObservationBus
from observation_layer.sinks import InMemorySink
from residual.cli import main as residual_main
from residual.eval.replay import signed_report_from_observations
from residual.eval.spec_eval import (
    CostRates,
    ExecutionControls,
    REPORT_EVENT,
    RunCounters,
    SpecEvalError,
    SpecEvaluationEvidence,
    SystemMetrics,
)
from residual.eval.workload import FrozenWorkload
from residual.factory.evidence_receipts import StationIdentity


def counters(scale: int = 1) -> RunCounters:
    return RunCounters(
        elapsed_seconds=60.0 * scale,
        accepted_tasks=8,
        total_tasks=10,
        tokens_used=1000 * scale,
        gpu_seconds=30.0 * scale,
        coordination_seconds=6.0 * scale,
        rework_tasks=2,
        merge_conflicts=1,
        verifier_rejections=2,
        verifier_outputs=10,
        tests_passed=9,
        tests_total=10,
    )


def controls() -> ExecutionControls:
    return ExecutionControls(
        engine_ids=("engine@1",),
        model_versions=("1",),
        temperatures=(0.0,),
        seed=20260914,
    )


def test_metric_formulas_and_cost_accounting():
    c = counters()
    metrics = SystemMetrics.from_counters(c)
    assert metrics.elapsed_time_minutes == 1.0
    assert metrics.accepted_tasks_per_hour == 480.0
    assert metrics.token_cost_total == 1000
    assert metrics.gpu_time_minutes == 0.5
    assert metrics.coordination_overhead_pct == 10.0
    assert metrics.rework_rate_pct == 20.0
    assert metrics.merge_conflicts == 1
    assert metrics.verifier_rejection_rate_pct == 20.0
    assert metrics.final_test_pass_rate_pct == 90.0

    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)
    run = evidence.record_run(
        "single", 0, c, controls(),
        rates=CostRates(api_cost_per_1k_tokens=2.0, gpu_cost_per_hour=12.0,
                       infrastructure_cost_per_run=1.0),
    )
    assert run.costs.api_cost == 2.0
    assert run.costs.gpu_cost == 0.1
    assert run.costs.infrastructure_cost == 1.0
    assert run.costs.total_cost == pytest.approx(3.1)
    assert run.costs.cost_per_accepted_task == pytest.approx(3.1 / 8)


def test_signed_report_replays_from_observation_log_and_stays_small():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    sink = InMemorySink()
    bus = ObservationBus(sink=sink, trace_id="spec-eval-test")
    evidence = SpecEvaluationEvidence(workload, identity, observation_bus=bus)
    for config_index, configuration in enumerate(("single", "fixed", "dynamic"), 1):
        for run_index in range(3):
            evidence.record_run(
                configuration,
                run_index,
                counters(config_index + run_index),
                controls(),
                rates=CostRates(api_cost_per_1k_tokens=0.01),
            )
    report = evidence.build_report()
    assert report.verify_signature(identity.public_bytes())
    assert report.payload["run_count"] == 9
    assert report.payload["summaries"]["single"]["aggregate_cost_per_accepted_task"] is not None

    terminal = [obs for obs in sink.events if obs.payload.get("event") == REPORT_EVENT]
    assert len(terminal) == 1
    assert "report" not in terminal[0].payload
    assert len(terminal[0].canonical_bytes()) < 24_000

    replayed = signed_report_from_observations(workload, sink.events)
    assert replayed.report_hash == report.report_hash
    assert replayed.station_signature == report.station_signature
    assert replayed.station_key_id == report.station_key_id
    assert replayed.verify_signature(identity.public_bytes())


def test_report_rejects_changed_controls_and_insufficient_runs():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)
    for config in ("single", "fixed", "dynamic"):
        evidence.record_run(config, 0, counters(), controls())
    with pytest.raises(SpecEvalError, match="insufficient runs"):
        evidence.build_report()

    evidence = SpecEvaluationEvidence(workload, identity)
    for config in ("single", "fixed", "dynamic"):
        for run_index in range(3):
            c = controls()
            if config == "dynamic" and run_index == 2:
                c = ExecutionControls(("other@1",), ("1",), (0.0,), 20260914)
            evidence.record_run(config, run_index, counters(run_index + 1), c)
    with pytest.raises(SpecEvalError, match="controls differ"):
        evidence.build_report()


def test_cli_exact_spec_shape_writes_signed_simulated_report():
    workload = FrozenWorkload.standard(cases=3)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workload_path = root / "workload.json"
        report_path = root / "report.json"
        obs_path = root / "observations.jsonl"
        workload_path.write_text(workload.to_json(), encoding="utf-8")

        rc = residual_main([
            "evaluate",
            "--workload", str(workload_path),
            "--configs", "single,fixed,dynamic",
            "--runs", "3",
            "--output", str(report_path),
            "--observations", str(obs_path),
        ])
        assert rc == 0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["schema_version"] == "residual.eval.comparison-report.v1"
        assert report["run_count"] == 9
        assert report["identity_mode"] == "ephemeral-evaluation-only"
        assert "simulated" in report["evidence_notice"]
        assert len(report["station_public_key_hex"]) == 64
        assert obs_path.read_text(encoding="utf-8").count("\n") == 10


def test_cli_rejects_less_than_three_runs():
    workload = FrozenWorkload.standard(cases=3)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "workload.json"
        path.write_text(workload.to_json(), encoding="utf-8")
        with pytest.raises(ValueError, match="at least three"):
            residual_main([
                "evaluate", "--workload", str(path),
                "--configs", "single,fixed,dynamic", "--runs", "2",
            ])
