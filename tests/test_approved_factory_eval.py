from __future__ import annotations

from dataclasses import replace

import pytest

from residual.eval.approved_factory import (
    ApprovedFactoryBindingError,
    ApprovedFactoryEvaluationAdapter,
    ApprovedFactoryRunBinding,
)
from residual.eval.measured_factory import FactoryRunMeasurement, MeasuredFactoryEvaluationRunner
from residual.eval.spec_eval import SpecEvaluationEvidence
from residual.eval.workload import FrozenWorkload
from residual.factory.evidence_receipts import StationIdentity, WorkerReceipt


H = "a" * 64
V = "b" * 64


def receipt(identity: StationIdentity, attempt_id: str) -> WorkerReceipt:
    value = WorkerReceipt(
        receipt_id=f"receipt-{attempt_id}",
        execution_plan_hash=H,
        task_id=f"task-{attempt_id}",
        worker_id=f"worker-{attempt_id}",
        swarm_id="approved-eval",
        attempt_id=attempt_id,
        engine_name="brokered-python",
        engine_version="linux-seccomp-broker-v1",
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
    return replace(value, station_signature=identity.sign(value.receipt_hash))


def measurement(identity: StationIdentity, attempts: tuple[str, ...]) -> FactoryRunMeasurement:
    receipts = tuple(receipt(identity, attempt) for attempt in attempts)
    return FactoryRunMeasurement(
        accepted_tasks=len(receipts),
        total_tasks=len(attempts),
        tokens_used=100,
        gpu_seconds=0.0,
        coordination_seconds=0.01,
        rework_tasks=0,
        merge_conflicts=0,
        verifier_rejections=0,
        verifier_outputs=len(attempts),
        tests_passed=len(attempts),
        tests_total=len(attempts),
        receipts=receipts,
    )


class StepClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


def make_binding(workload, identity, config, run_index):
    attempts = (f"{config}-{run_index}-0",) if config == "single" else (
        f"{config}-{run_index}-0",
        f"{config}-{run_index}-1",
    )
    return ApprovedFactoryRunBinding(
        workload_manifest_hash=workload.manifest_hash,
        configuration=config,
        run_index=run_index,
        approval_ref=f"approval:{config}:{run_index}",
        execution_plan_hash=H,
        approved_attempt_ids=attempts,
        execute=lambda attempts=attempts: measurement(identity, attempts),
    )


def test_complete_approved_matrix_drives_measured_runner_without_prompt_authorization():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    bindings = [
        make_binding(workload, identity, config, run_index)
        for config in ("single", "fixed", "dynamic")
        for run_index in range(3)
    ]
    adapter = ApprovedFactoryEvaluationAdapter(bindings)
    adapter.assert_complete(workload, runs=3)
    evidence = SpecEvaluationEvidence(workload, identity)
    runner = MeasuredFactoryEvaluationRunner(workload, evidence, adapter, clock=StepClock())
    report = runner.run(runs=3)
    assert report.payload["run_count"] == 9
    assert report.verify_signature(identity.public_bytes())


def test_wrong_workload_fails_before_callback_runs():
    workload = FrozenWorkload.standard(cases=3)
    other = FrozenWorkload.standard(cases=4)
    identity = StationIdentity.generate()
    called = False

    def execute():
        nonlocal called
        called = True
        return measurement(identity, ("single-0-0",))

    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash, "single", 0, "approval:1", H, ("single-0-0",), execute
    )
    adapter = ApprovedFactoryEvaluationAdapter((binding,))
    with pytest.raises(ApprovedFactoryBindingError, match="another FrozenWorkload"):
        adapter(other, "single", 0)
    assert called is False


def test_unapproved_attempt_receipt_is_rejected():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash,
        "single",
        0,
        "approval:1",
        H,
        ("approved",),
        lambda: measurement(identity, ("different",)),
    )
    adapter = ApprovedFactoryEvaluationAdapter((binding,))
    with pytest.raises(ApprovedFactoryBindingError, match="unapproved attempt"):
        adapter(workload, "single", 0)


def test_matrix_coverage_and_topology_fail_closed():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    one = make_binding(workload, identity, "single", 0)
    adapter = ApprovedFactoryEvaluationAdapter((one,))
    with pytest.raises(ApprovedFactoryBindingError, match="matrix mismatch"):
        adapter.assert_complete(workload, runs=1)
    with pytest.raises(ApprovedFactoryBindingError, match="swarm configurations"):
        ApprovedFactoryRunBinding(
            workload.manifest_hash, "fixed", 0, "approval:bad", H, ("only-one",), lambda: measurement(identity, ("only-one",))
        )


def test_duplicate_binding_key_is_rejected():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    binding = make_binding(workload, identity, "single", 0)
    with pytest.raises(ApprovedFactoryBindingError, match="duplicate"):
        ApprovedFactoryEvaluationAdapter((binding, binding))
