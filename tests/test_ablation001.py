"""Tests for the RESIDUAL-ABLATION-001 measured experiment contract."""
from __future__ import annotations

import copy

import pytest

from residual.core import ContractError, digest
from residual.eval.ablation001 import (
    AblationProtocol,
    ControlledFactors,
    ExecutionManifest,
    MeasuredAblationRunner,
    TaskMeasurement,
    confirmatory_analysis,
    verify_bundle,
)
from residual.eval_frozen.workload import development_workload


def _factors() -> ControlledFactors:
    return ControlledFactors(
        provider="test-provider",
        model_id="test-model",
        model_version="1.0",
        prompt_policy_sha256=digest("prompt"),
        inference_settings_sha256=digest("inference"),
        tool_environment_sha256=digest("tools"),
        grader_id="independent-grader",
        grader_version="1.0",
        environment_sha256=digest("environment"),
        budget_policy_sha256=digest("budget"),
    )


def _campaign(adapter=None):
    workload = development_workload()
    protocol = AblationProtocol(workload_sha256=workload.sha256)
    execution = ExecutionManifest(
        protocol_sha256=protocol.sha256,
        workload_sha256=workload.sha256,
        source_commit="0" * 40,
        factors=_factors(),
    )
    return workload, protocol, execution, MeasuredAblationRunner(
        workload=workload,
        protocol=protocol,
        execution=execution,
        execute=adapter or _adapter,
    )


def _adapter(workload, config, task, repeat, execution):
    first_task = workload.slice_tasks("evaluation")[0].task_id
    if repeat == 2 and task.task_id == first_task:
        return TaskMeasurement(
            state="UNKNOWN", correct=None, accepted=False, fault_caught=None,
            verifier_rejected=False, latency_ms=20.0, input_tokens=10,
            output_tokens=0, cost_usd=0.001,
            evidence_refs=(f"test://{config.config_id}/{task.task_id}/{repeat}",),
        )

    correct = task.fault_label is None and ((sum(map(ord, task.task_id)) + repeat) % 4 != 0)
    verified = config.config_id in {"R3", "R4", "R5"}
    contracted = config.config_id == "R2"
    if correct:
        accepted = not (config.config_id == "R3" and repeat == 1)
    elif verified:
        accepted = False
    elif contracted:
        accepted = repeat == 0
    else:
        accepted = True

    state = "PASS" if accepted and correct else "FAIL" if accepted else "REJECTED"
    fault_caught = None if task.fault_label is None else not accepted
    return TaskMeasurement(
        state=state, correct=correct, accepted=accepted,
        fault_caught=fault_caught,
        verifier_rejected=not accepted and config.config_id in {"R2", "R3", "R4", "R5"},
        latency_ms=100.0 + 10.0 * len(config.control_layers),
        input_tokens=100, output_tokens=50, cost_usd=0.01 + 0.001 * len(config.control_layers),
        rework_attempts=1 if not accepted and verified else 0,
        conflicts=1 if config.config_id == "R1" and repeat == 0 else 0,
        recovery_attempts=1 if config.config_id in {"R4", "R5"} and not accepted else 0,
        duplicate_work_items=1 if config.config_id == "R1" and repeat == 0 else 0,
        evidence_refs=(f"test://{config.config_id}/{task.task_id}/{repeat}",),
    )


def test_measured_runner_emits_complete_paired_r0_r5_bundle():
    workload, protocol, execution, runner = _campaign()
    bundle = runner.run(repeats=3)
    tasks = workload.slice_tasks("evaluation")
    assert bundle["schema_version"] == "residual.research.ablation001.bundle.v1"
    assert bundle["evidence_level"] == "measured_live"
    assert bundle["protocol_sha256"] == protocol.sha256
    assert bundle["execution_sha256"] == execution.sha256
    assert len(bundle["records"]) == len(tasks) * 6 * 3
    assert verify_bundle(bundle)
    for task in tasks:
        for repeat in range(3):
            arms = {
                row["config_id"] for row in bundle["records"]
                if row["task_id"] == task.task_id and row["repeat"] == repeat
            }
            assert arms == {"R0", "R1", "R2", "R3", "R4", "R5"}


def test_unknowns_remain_in_unconditional_denominators():
    _, _, _, runner = _campaign()
    bundle = runner.run(repeats=3)
    r0 = bundle["summaries"]["R0"]
    rows = [r for r in bundle["records"] if r["config_id"] == "R0"]
    assert r0["runs"] == len(rows)
    assert r0["unknown_runs"] >= 1
    accepted_sound = sum(1 for r in rows if r["accepted"] and r["correct"] is True)
    assert r0["accepted_and_sound_rate"] == pytest.approx(accepted_sound / len(rows))


def test_manifest_rejects_fixture_label_and_changed_arm_hashes():
    workload = development_workload()
    protocol = AblationProtocol(workload_sha256=workload.sha256)
    with pytest.raises(ContractError):
        ExecutionManifest(
            protocol_sha256=protocol.sha256, workload_sha256=workload.sha256,
            source_commit="0" * 40, factors=_factors(),
            evidence_level="development_fixture",
        )
    with pytest.raises(ContractError):
        ExecutionManifest(
            protocol_sha256=protocol.sha256, workload_sha256=workload.sha256,
            source_commit="0" * 40, factors=_factors(),
            config_hashes=(("R0", digest("changed")),),
        )


def test_runner_rejects_below_preregistered_repeat_floor():
    _, _, _, runner = _campaign()
    with pytest.raises(ContractError):
        runner.run(repeats=2)


@pytest.mark.parametrize("kwargs", [
    dict(state="PASS", correct=False, accepted=True),
    dict(state="FAIL", correct=True, accepted=True),
    dict(state="UNKNOWN", correct=True, accepted=False),
    dict(state="REJECTED", correct=False, accepted=True),
    dict(state="REJECTED", correct=None, accepted=False),
])
def test_task_measurement_rejects_state_inconsistency(kwargs):
    base = dict(
        fault_caught=None, verifier_rejected=False, latency_ms=1.0,
        input_tokens=1, output_tokens=1, cost_usd=0.0,
        evidence_refs=("test://evidence",),
    )
    with pytest.raises(ContractError):
        TaskMeasurement(**base, **kwargs)


def test_task_measurement_rejects_acceptance_after_verifier_rejection():
    with pytest.raises(ContractError):
        TaskMeasurement(
            state="PASS", correct=True, accepted=True, fault_caught=None,
            verifier_rejected=True, latency_ms=1.0, input_tokens=1,
            output_tokens=1, cost_usd=0.0, evidence_refs=("test://evidence",),
        )


def test_task_measurement_rejects_impossible_recovery_count():
    with pytest.raises(ContractError):
        TaskMeasurement(
            state="PASS", correct=True, accepted=True, fault_caught=None,
            verifier_rejected=False, latency_ms=1.0, input_tokens=1,
            output_tokens=1, cost_usd=0.0, recovery_attempts=0,
            recovered_failures=1, evidence_refs=("test://evidence",),
        )


def test_task_measurement_requires_retained_evidence_reference():
    with pytest.raises(ContractError):
        TaskMeasurement(
            state="PASS", correct=True, accepted=True, fault_caught=None,
            verifier_rejected=False, latency_ms=1.0, input_tokens=1,
            output_tokens=1, cost_usd=0.0,
        )


def test_bundle_hash_detects_tampering():
    _, _, _, runner = _campaign()
    bundle = runner.run(repeats=3)
    tampered = copy.deepcopy(bundle)
    tampered["summaries"]["R0"]["accepted_and_sound_rate"] = 1.0
    assert not verify_bundle(tampered)


def test_fault_labeled_completed_run_requires_fault_capture_verdict():
    def bad_adapter(workload, config, task, repeat, execution):
        if task.fault_label is not None:
            return TaskMeasurement(
                state="FAIL", correct=False, accepted=True, fault_caught=None,
                verifier_rejected=False, latency_ms=1.0, input_tokens=1,
                output_tokens=1, cost_usd=0.0, evidence_refs=("test://bad",),
            )
        return _adapter(workload, config, task, repeat, execution)

    _, _, _, runner = _campaign(bad_adapter)
    with pytest.raises(ContractError):
        runner.run(repeats=3)


def test_confirmatory_analysis_clusters_repeats_by_task():
    _, _, _, runner = _campaign()
    bundle = runner.run(repeats=3)
    from residual.eval.ablation001 import MeasuredObservation

    rows = [
        MeasuredObservation(
            record_id=r["record_id"],
            protocol_sha256=r["protocol_sha256"],
            execution_sha256=r["execution_sha256"],
            workload_sha256=r["workload_sha256"],
            task_id=r["task_id"],
            slice=r["slice"],
            config_id=r["config_id"],
            repeat=r["repeat"],
            state=r["state"],
            correct=r["correct"],
            accepted=r["accepted"],
            fault_label=r["fault_label"],
            fault_caught=r["fault_caught"],
            verifier_rejected=r["verifier_rejected"],
            latency_ms=r["latency_ms"],
            input_tokens=r["input_tokens"],
            output_tokens=r["output_tokens"],
            cost_usd=r["cost_usd"],
            rework_attempts=r["rework_attempts"],
            conflicts=r["conflicts"],
            operator_interventions=r["operator_interventions"],
            recovery_attempts=r["recovery_attempts"],
            recovered_failures=r["recovered_failures"],
            duplicate_work_items=r["duplicate_work_items"],
            unauthorized_actions=r["unauthorized_actions"],
            evidence_refs=tuple(r["evidence_refs"]),
        )
        for r in bundle["records"]
    ]
    analysis = confirmatory_analysis(rows, bootstrap_iterations=200)
    assert analysis["analysis_unit"] == "task_cluster_mean_across_repeats"
    assert analysis["familywise_method"] == "holm_bonferroni"
    assert set(analysis["comparisons"]) == {
        "accepted_and_sound_rate:R4-vs-R0",
        "accepted_and_sound_rate:R5-vs-R4",
        "unsafe_acceptance_rate:R4-vs-R0",
        "unsafe_acceptance_rate:R5-vs-R4",
    }
    for result in analysis["comparisons"].values():
        assert result["n_pairs"] == 6
        assert "holm_adjusted_p_value" in result
