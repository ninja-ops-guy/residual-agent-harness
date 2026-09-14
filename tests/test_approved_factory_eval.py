from __future__ import annotations

from dataclasses import replace

import pytest

from residual.eval.approved_factory import (
    ApprovedFactoryBindingError,
    ApprovedFactoryEvaluationAdapter,
    ApprovedFactoryRunBinding,
    ApprovedMeasuredFactoryEvaluationRunner,
    AuthoritativeFactoryRunEvidence,
    FactoryTopologyTrace,
)
from residual.eval.measured_factory import FactoryRunMeasurement
from residual.eval.spec_eval import SpecEvaluationEvidence
from residual.eval.workload import FrozenWorkload
from residual.factory.evidence_receipts import StationIdentity, WorkerReceipt
from residual.factory.m4_evidence import ReadyDagSnapshot
from residual.factory.m4_integrator import IntegrationReceipt, VerificationResult
from residual.factory.m4_scheduler import SchedulerAction, SchedulerMeasurements

H = "a" * 64
V = "b" * 64
I = "c" * 64
P = "d" * 64


def worker_receipt(identity: StationIdentity, attempt_id: str) -> WorkerReceipt:
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
    receipts = tuple(worker_receipt(identity, attempt) for attempt in attempts)
    return FactoryRunMeasurement(
        accepted_tasks=len(receipts),
        total_tasks=len(receipts),
        tokens_used=100,
        gpu_seconds=0.0,
        coordination_seconds=0.01,
        rework_tasks=0,
        merge_conflicts=0,
        verifier_rejections=0,
        verifier_outputs=len(receipts),
        tests_passed=len(receipts),
        tests_total=len(receipts),
        receipts=receipts,
    )


def topology(configuration: str, worker_count: int, *, dynamic_action: bool = False) -> FactoryTopologyTrace:
    snapshot = ReadyDagSnapshot(
        plan_hash=H,
        completed_tasks=(),
        ready_tasks=("task",),
        blocked_tasks=(),
        independence_fraction=1.0,
        receipt_hashes=(),
    )
    measured = SchedulerMeasurements(
        ready_dag_hash=snapshot.snapshot_hash,
        worker_utilization=0.5,
        blocked_task_ratio=0.0,
        verification_queue_depth=0,
        integration_conflict_rate=0.0,
        independent_tasks=1,
        blocked_tasks=0,
        active_workers=1,
        total_workers=worker_count,
        integration_conflicts=0,
        integration_attempts=1,
    )
    actions = ()
    if dynamic_action:
        actions = (
            SchedulerAction(
                "resize", "workers", 1, worker_count,
                "observed adaptive resize", measured.measurement_hash,
            ),
        )
    return FactoryTopologyTrace(configuration, H, (snapshot,), (measured,), actions)


def integration_receipt(
    identity: StationIdentity,
    receipts: tuple[WorkerReceipt, ...],
    *, evidence_level: str = "measured",
    boundary: str = "os_isolated_measured",
) -> IntegrationReceipt:
    verification = VerificationResult(
        "project", "full_test_suite", "pass", 0,
        "e" * 64, "f" * 64, "exit", boundary,
    )
    value = IntegrationReceipt(
        execution_plan_hash=H,
        integration_plan_hash=I,
        input_receipt_hashes=tuple(row.receipt_hash for row in receipts),
        output_commit="1" * 40,
        verification_results=(verification,),
        conflict_resolutions=(),
        integrated_at_ns=1,
        station_key_id=identity.key_id,
        station_signature="pending",
        verification_policy_hash=P,
        evidence_level=evidence_level,
    )
    return replace(value, station_signature=identity.sign(value.receipt_hash))


def authoritative(
    identity: StationIdentity,
    configuration: str,
    attempts: tuple[str, ...],
    *, worker_count: int,
    evidence_level: str = "measured",
    boundary: str = "os_isolated_measured",
    dynamic_action: bool = False,
) -> AuthoritativeFactoryRunEvidence:
    measured = measurement(identity, attempts)
    return AuthoritativeFactoryRunEvidence(
        measurement=measured,
        final_acceptance=integration_receipt(
            identity, measured.receipts,
            evidence_level=evidence_level, boundary=boundary,
        ),
        topology=topology(configuration, worker_count, dynamic_action=dynamic_action),
    )


def bounds(configuration: str) -> tuple[int, int]:
    if configuration == "single":
        return (1, 1)
    if configuration == "fixed":
        return (2, 2)
    return (1, 4)


def make_binding(workload, identity, config, run_index, attempts=None):
    attempts = attempts or (
        f"{config}-{run_index}-0",
        f"{config}-{run_index}-1",
    )
    workers = 1 if config == "single" else 2
    return ApprovedFactoryRunBinding(
        workload_manifest_hash=workload.manifest_hash,
        configuration=config,
        run_index=run_index,
        approval_ref=f"approval:{config}:{run_index}",
        execution_plan_hash=H,
        approved_attempt_ids=attempts,
        worker_bounds=bounds(config),
        station_public_key=identity.public_bytes(),
        execute=lambda: authoritative(
            identity, config, attempts, worker_count=workers,
            dynamic_action=(config == "dynamic"),
        ),
    )


class StepClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


def test_complete_matrix_produces_signed_report_bound_to_m4_and_scheduler_evidence():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    bindings = [
        make_binding(workload, identity, config, run_index)
        for config in ("single", "fixed", "dynamic")
        for run_index in range(3)
    ]
    adapter = ApprovedFactoryEvaluationAdapter(bindings)
    evidence = SpecEvaluationEvidence(workload, identity)
    report = ApprovedMeasuredFactoryEvaluationRunner(
        workload, evidence, adapter, clock=StepClock()
    ).run(runs=3)
    assert report.verify_signature(identity.public_bytes())
    assert report.payload["schema_version"] == "residual.eval.approved-factory-comparison.v1"
    assert len(report.payload["run_provenance"]) == 9
    first = report.payload["run_provenance"][0]["refs"]
    assert len(first["m4_integration_receipt_hash"]) == 64
    assert len(first["scheduler_topology_trace_hash"]) == 64
    assert report.payload["comparison_report"]["run_count"] == 9


def test_attempt_count_is_not_used_as_topology_evidence():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    attempts = ("a0", "a1", "a2")
    binding = make_binding(workload, identity, "fixed", 0, attempts=attempts)
    measured, provenance = binding.execute_and_validate()
    assert len(measured.receipts) == 3
    assert binding.worker_bounds == (2, 2)
    assert len(provenance["scheduler_topology_trace_hash"]) == 64


def test_fixed_topology_rejects_observed_worker_drift_even_with_approved_attempts():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    attempts = ("a0", "a1")
    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash, "fixed", 0, "approval:fixed", H, attempts,
        (2, 2), identity.public_bytes(),
        lambda: authoritative(identity, "fixed", attempts, worker_count=3),
    )
    with pytest.raises(ApprovedFactoryBindingError, match="outside approved bounds"):
        binding.execute_and_validate()


def test_development_fixture_m4_receipt_cannot_be_promoted_to_measured_evidence():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    attempts = ("a0",)
    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash, "single", 0, "approval:single", H, attempts,
        (1, 1), identity.public_bytes(),
        lambda: authoritative(
            identity, "single", attempts, worker_count=1,
            evidence_level="development_fixture",
            boundary="trusted_fixture_unsandboxed",
        ),
    )
    with pytest.raises(ApprovedFactoryBindingError, match="evidence_level=measured"):
        binding.execute_and_validate()


def test_unsandboxed_boundary_is_rejected_even_if_receipt_is_labelled_measured():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    attempts = ("a0",)
    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash, "single", 0, "approval:single", H, attempts,
        (1, 1), identity.public_bytes(),
        lambda: authoritative(
            identity, "single", attempts, worker_count=1,
            evidence_level="measured", boundary="trusted_fixture_unsandboxed",
        ),
    )
    with pytest.raises(ApprovedFactoryBindingError, match="unsandboxed"):
        binding.execute_and_validate()


def test_m4_receipt_must_bind_exact_measured_m3_receipt_set():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    attempts = ("a0", "a1")
    value = authoritative(identity, "fixed", attempts, worker_count=2)
    wrong = replace(value.final_acceptance, input_receipt_hashes=("0" * 64,))
    wrong = replace(wrong, station_signature=identity.sign(wrong.receipt_hash))
    value = replace(value, final_acceptance=wrong)
    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash, "fixed", 0, "approval:fixed", H, attempts,
        (2, 2), identity.public_bytes(), lambda: value,
    )
    with pytest.raises(ApprovedFactoryBindingError, match="does not bind"):
        binding.execute_and_validate()


def test_wrong_workload_fails_before_callback_runs():
    workload = FrozenWorkload.standard(cases=3)
    other = FrozenWorkload.standard(cases=4)
    identity = StationIdentity.generate()
    called = False

    def execute():
        nonlocal called
        called = True
        return authoritative(identity, "single", ("a0",), worker_count=1)

    binding = ApprovedFactoryRunBinding(
        workload.manifest_hash, "single", 0, "approval:1", H, ("a0",),
        (1, 1), identity.public_bytes(), execute,
    )
    adapter = ApprovedFactoryEvaluationAdapter((binding,))
    with pytest.raises(ApprovedFactoryBindingError, match="another FrozenWorkload"):
        adapter(other, "single", 0)
    assert called is False


def test_matrix_coverage_and_station_identity_fail_closed():
    workload = FrozenWorkload.standard(cases=3)
    identity = StationIdentity.generate()
    one = make_binding(workload, identity, "single", 0)
    adapter = ApprovedFactoryEvaluationAdapter((one,))
    with pytest.raises(ApprovedFactoryBindingError, match="matrix mismatch"):
        adapter.assert_complete(workload, runs=1)

    other = StationIdentity.generate()
    with pytest.raises(ApprovedFactoryBindingError, match="mix Station"):
        ApprovedFactoryEvaluationAdapter((one, make_binding(workload, other, "fixed", 0)))
