from __future__ import annotations

from dataclasses import replace

import pytest

from residual.eval.measured_factory import (
    FactoryRunMeasurement,
    MeasuredFactoryEvaluationRunner,
)
from residual.eval.spec_eval import CostRates, SpecEvalError, SpecEvaluationEvidence
from residual.eval.workload import FrozenWorkload
from residual.factory.evidence_receipts import StationIdentity, WorkerReceipt


H = "a" * 64
V = "b" * 64


def signed_receipt(identity: StationIdentity, suffix: str, *, engine_version: str = "1") -> WorkerReceipt:
    receipt = WorkerReceipt(
        receipt_id=f"receipt-{suffix}",
        execution_plan_hash=H,
        task_id=f"task-{suffix}",
        worker_id=f"worker-{suffix}",
        swarm_id="eval-swarm",
        attempt_id=f"attempt-{suffix}",
        engine_name="measured-engine",
        engine_version=engine_version,
        input_commit="input",
        output_commit="output",
        contract_hash=H,
        artifacts=(),
        requirements_met=(("REQ", True),),
        verification_results=(("check", "pass"),),
        overall_verdict="pass",
        verifier_identity="station:test",
        verifier_revision=V,
        issued_at_ns=1,
        station_key_id=identity.key_id,
        station_signature="pending",
    )
    return replace(receipt, station_signature=identity.sign(receipt.receipt_hash))


def measurement(identity: StationIdentity, configuration: str, run_index: int) -> FactoryRunMeasurement:
    return FactoryRunMeasurement(
        accepted_tasks=3,
        total_tasks=3,
        tokens_used=1000 + run_index,
        gpu_seconds=0.25,
        coordination_seconds=0.1,
        rework_tasks=0,
        merge_conflicts=0,
        verifier_rejections=0,
        verifier_outputs=3,
        tests_passed=3,
        tests_total=3,
        receipts=(signed_receipt(identity, f"{configuration}-{run_index}"),),
    )


class StepClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


def test_measured_runner_builds_signed_measured_report_from_real_adapter_contract():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)

    def execute(wl, configuration, run_index):
        assert wl.manifest_hash == workload.manifest_hash
        return measurement(identity, configuration, run_index)

    runner = MeasuredFactoryEvaluationRunner(
        workload,
        evidence,
        execute,
        rates=CostRates(api_cost_per_1k_tokens=0.01),
        clock=StepClock(),
    )
    report = runner.run(runs=3)
    assert report.verify_signature(identity.public_bytes())
    assert report.payload["run_count"] == 9
    for summary in report.payload["summaries"].values():
        assert summary["evidence_modes"] == ["measured"]
    assert report.payload["controls"]["engine_ids"] == ["measured-engine@1"]


def test_runner_uses_outer_clock_not_adapter_elapsed_claim():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)
    runner = MeasuredFactoryEvaluationRunner(
        workload,
        evidence,
        lambda _w, config, index: measurement(identity, config, index),
        clock=StepClock(),
    )
    run = runner.run_one("single", 0)
    assert run.counters.elapsed_seconds == 1.0
    assert run.metrics.elapsed_time_minutes == pytest.approx(1.0 / 60.0)


def test_foreign_or_forged_receipt_fails_closed():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    foreign = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)

    bad = measurement(foreign, "single", 0)
    runner = MeasuredFactoryEvaluationRunner(
        workload,
        evidence,
        lambda *_: bad,
        clock=StepClock(),
    )
    with pytest.raises(SpecEvalError, match="forged or foreign"):
        runner.run_one("single", 0)


def test_engine_revision_drift_fails_report_controls():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)

    def execute(_w, configuration, run_index):
        value = measurement(identity, configuration, run_index)
        if configuration == "dynamic" and run_index == 2:
            return replace(
                value,
                receipts=(signed_receipt(identity, "drift", engine_version="2"),),
            )
        return value

    runner = MeasuredFactoryEvaluationRunner(
        workload, evidence, execute, clock=StepClock()
    )
    with pytest.raises(SpecEvalError, match="controls differ"):
        runner.run(runs=3)


def test_coordination_measurement_cannot_exceed_trusted_wall_clock():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    evidence = SpecEvaluationEvidence(workload, identity)
    value = replace(measurement(identity, "single", 0), coordination_seconds=2.0)
    runner = MeasuredFactoryEvaluationRunner(
        workload, evidence, lambda *_: value, clock=StepClock()
    )
    with pytest.raises(SpecEvalError, match="coordination time exceeds"):
        runner.run_one("single", 0)
