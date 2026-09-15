"""Regression tests for the measured-evaluation -> M4-acceptance binding.

Each of the four evidence-integrity requirements has NEGATIVE tests:
replay rejected, unauthenticated/partial topology rejected, divergent task
population rejected, UNKNOWN verifier outcome rejects acceptance and never
attributes.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from residual.eval_frozen.acceptance_binding import (
    ACCEPTANCE_SCHEMA,
    AcceptanceBindingError,
    FreshRunRegistry,
    MeasuredRunEvidence,
    SchedulerObservation,
    SchedulerTopologyEvidence,
    VerifierQualification,
    WorkloadTaskMapping,
    validate_and_issue_acceptance,
    validate_prerequisites,
    verify_acceptance_artifact,
)
from residual.eval_frozen.workload import development_workload
from residual.factory.evidence_receipts import StationIdentity, WorkerReceipt
from residual.factory.m4_evidence import ReadyDagSnapshot
from residual.factory.m4_integrator import IntegrationReceipt, VerificationResult
from residual.factory.m4_sandbox import SANDBOX_PROFILE
from residual.factory.m4_scheduler import SchedulerMeasurements

H = "a" * 64
REPORT = "b" * 64
V = "c" * 64
P = "d" * 64
COMMIT = "e" * 40

START, END = 1_000_000_000, 2_000_000_000

CLEAN_INSTALL = {"status": "PASS", "commit": COMMIT, "tree": "f" * 40}
OWNERSHIP = {"passed": True, "pinned_at": "0" * 40, "protected_files": 32}


def make_receipt(identity: StationIdentity, task_id: str, attempt: str,
                 plan: str = H) -> WorkerReceipt:
    value = WorkerReceipt(
        receipt_id=f"receipt-{attempt}", execution_plan_hash=plan,
        task_id=task_id, worker_id="worker-1", swarm_id="measured-eval",
        attempt_id=attempt, engine_name="brokered-python",
        engine_version="linux-seccomp-broker-v1",
        input_commit="input", output_commit="output", contract_hash=H,
        artifacts=(), requirements_met=(("REQ", True),),
        verification_results=(("check", "pass"),), overall_verdict="pass",
        verifier_identity="station:test", verifier_revision=V,
        issued_at_ns=START, station_key_id=identity.key_id,
        station_signature="pending",
    )
    return replace(value, station_signature=identity.sign(value.receipt_hash))


def make_acceptance(identity: StationIdentity, receipts, *,
                    level: str = "isolated_candidate_verification",
                    status: str = "pass", reason: str = "exit",
                    returncode: int | None = 0,
                    boundary: str = SANDBOX_PROFILE,
                    plan: str = H,
                    receipt_hashes=None) -> IntegrationReceipt:
    result = VerificationResult("project", "full_test_suite", status, returncode,
                                "1" * 64, "2" * 64, reason, boundary)
    value = IntegrationReceipt(
        execution_plan_hash=plan, integration_plan_hash="9" * 64,
        input_receipt_hashes=(receipt_hashes if receipt_hashes is not None
                              else tuple(r.receipt_hash for r in receipts)),
        output_commit="1" * 40, verification_results=(result,),
        conflict_resolutions=(), integrated_at_ns=END,
        station_key_id=identity.key_id, station_signature="pending",
        verification_policy_hash=P, evidence_level=level,
    )
    return replace(value, station_signature=identity.sign(value.receipt_hash))


def make_topology(identity: StationIdentity, *, plan: str = H,
                  start: int = START, end: int = END,
                  observations=(START, END)) -> SchedulerTopologyEvidence:
    snapshot = ReadyDagSnapshot(plan_hash=plan, completed_tasks=(),
                                ready_tasks=("task",), blocked_tasks=(),
                                independence_fraction=1.0, receipt_hashes=())

    def measurement():
        return SchedulerMeasurements(
            ready_dag_hash=snapshot.snapshot_hash, worker_utilization=0.5,
            blocked_task_ratio=0.0, verification_queue_depth=0,
            integration_conflict_rate=0.0, independent_tasks=1, blocked_tasks=0,
            active_workers=1, total_workers=1, integration_conflicts=0,
            integration_attempts=1)

    return SchedulerTopologyEvidence.issue(
        identity, execution_plan_hash=plan, run_started_ns=start, run_ended_ns=end,
        snapshots=(snapshot,),
        observations=tuple(SchedulerObservation(t, measurement()) for t in observations))


def make_verifier() -> VerifierQualification:
    return VerifierQualification(
        boundary=SANDBOX_PROFILE, probe_status="pass", probe_reason="exit",
        probe_returncode=0, probe_stdout_sha256="3" * 64,
        probe_stderr_sha256="4" * 64, probed_at_ns=START)


def mapping_for(workload) -> WorkloadTaskMapping:
    return WorkloadTaskMapping.for_workload(
        workload, {t.task_id: f"factory-{t.task_id}"
                   for t in workload.slice_tasks("evaluation")})


def make_evidence(identity: StationIdentity, registry: FreshRunRegistry,
                  workload, run_id: str, **overrides) -> MeasuredRunEvidence:
    mapping = mapping_for(workload)
    receipts = tuple(make_receipt(identity, factory_id, f"attempt-{i}")
                     for i, (_, factory_id) in enumerate(mapping.entries))
    kwargs = dict(
        run_id=run_id, workload=workload, report_sha256=REPORT,
        run_started_ns=START, run_ended_ns=END, receipts=receipts,
        mapping=mapping, topology=make_topology(identity),
        final_acceptance=make_acceptance(identity, receipts),
        verifier=make_verifier(),
        clean_install_report=dict(CLEAN_INSTALL),
        ownership_report=dict(OWNERSHIP),
    )
    kwargs.update(overrides)
    return MeasuredRunEvidence(**kwargs)


def begin(registry: FreshRunRegistry, workload, run_id: str = "run-1"):
    return registry.begin_run(run_id, workload_sha256=workload.sha256,
                              report_sha256=REPORT, execution_plan_hash=H)


# --- happy path ------------------------------------------------------------

def test_full_binding_issues_signed_acceptance_artifact():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    artifact = validate_and_issue_acceptance(
        make_evidence(identity, registry, workload, "run-1"), registry, identity,
        required_commit=COMMIT)
    assert artifact["schema_version"] == ACCEPTANCE_SCHEMA
    assert artifact["attribution"] is None
    assert artifact["verifier_qualification"]["boundary"] == SANDBOX_PROFILE
    assert verify_acceptance_artifact(artifact, identity.public_bytes())
    assert not verify_acceptance_artifact(artifact, StationIdentity.generate().public_bytes())


# --- requirement 1: fresh execution identity / anti-replay -----------------

def test_replay_of_run_id_is_rejected():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    with pytest.raises(AcceptanceBindingError, match="replay"):
        begin(registry, workload)


def test_resumed_run_evidence_is_never_fresh():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    registry.resume_run("run-1")
    with pytest.raises(AcceptanceBindingError, match="non-fresh"):
        validate_and_issue_acceptance(
            make_evidence(identity, registry, workload, "run-1"), registry, identity,
            required_commit=COMMIT)


def test_unknown_run_identity_fails_closed():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    with pytest.raises(AcceptanceBindingError, match="no fresh execution identity"):
        validate_and_issue_acceptance(
            make_evidence(identity, registry, workload, "run-1"), registry, identity,
            required_commit=COMMIT)


def test_forged_identity_chain_record_is_rejected():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    record = begin(registry, workload)
    forged = replace(record, run_id="run-2")  # invalidates signature + chain
    registry._records.append(forged)
    with pytest.raises(AcceptanceBindingError):
        registry.verify_chain()


# --- requirement 2: authenticated topology over the full interval ----------

def test_unauthenticated_topology_is_rejected():
    identity = StationIdentity.generate()
    other = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    topology = make_topology(other)  # signed by a foreign Station
    with pytest.raises(AcceptanceBindingError, match="not authenticated"):
        validate_and_issue_acceptance(
            make_evidence(identity, registry, workload, "run-1", topology=topology),
            registry, identity, required_commit=COMMIT)


def test_partial_interval_topology_is_rejected():
    identity = StationIdentity.generate()
    with pytest.raises(AcceptanceBindingError, match="complete run interval"):
        make_topology(identity, observations=(START + 100, END - 100))
    with pytest.raises(AcceptanceBindingError, match="complete run interval"):
        make_topology(identity, observations=(START + 100,))


def test_topology_interval_must_match_the_run():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    topology = make_topology(identity, start=START, end=END + 1,
                             observations=(START, END + 1))
    with pytest.raises(AcceptanceBindingError, match="interval does not match"):
        validate_and_issue_acceptance(
            make_evidence(identity, registry, workload, "run-1", topology=topology),
            registry, identity, required_commit=COMMIT)


def test_topology_from_another_execution_plan_is_rejected():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    topology = make_topology(identity, plan="8" * 64)
    with pytest.raises(AcceptanceBindingError, match="another ExecutionPlan"):
        validate_and_issue_acceptance(
            make_evidence(identity, registry, workload, "run-1", topology=topology),
            registry, identity, required_commit=COMMIT)


# --- requirement 3: exact enforced workload -> task mapping ----------------

def test_divergent_task_population_is_rejected():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1")
    # Extra unmapped task in the measured population.
    receipts = evidence.receipts + (make_receipt(identity, "factory-rogue", "attempt-x"),)
    with pytest.raises(AcceptanceBindingError, match="population diverges"):
        validate_and_issue_acceptance(replace(evidence, receipts=receipts),
                                      registry, identity, required_commit=COMMIT)
    # Missing mapped task.
    with pytest.raises(AcceptanceBindingError, match="population diverges"):
        validate_and_issue_acceptance(replace(evidence, receipts=evidence.receipts[:-1]),
                                      registry, identity, required_commit=COMMIT)
    # Duplicate task.
    with pytest.raises(AcceptanceBindingError, match="duplicate"):
        validate_and_issue_acceptance(
            replace(evidence, receipts=evidence.receipts + evidence.receipts[:1]),
            registry, identity, required_commit=COMMIT)


def test_incomplete_mapping_is_rejected_at_construction():
    workload = development_workload()
    tasks = workload.slice_tasks("evaluation")
    partial = {t.task_id: f"factory-{t.task_id}" for t in tasks[:-1]}
    with pytest.raises(AcceptanceBindingError, match="does not cover"):
        WorkloadTaskMapping.for_workload(workload, partial)
    rogue = {t.task_id: f"factory-{t.task_id}" for t in tasks}
    rogue["not-a-task"] = "factory-x"
    with pytest.raises(AcceptanceBindingError, match="does not cover"):
        WorkloadTaskMapping.for_workload(workload, rogue)


# --- requirement 4: qualified verifier; UNKNOWN fails closed ---------------

def test_unknown_verifier_outcome_rejects_and_never_attributes():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1")
    unknown = make_acceptance(identity, evidence.receipts, status="unknown",
                              reason="isolation_unavailable:probe", returncode=None)
    with pytest.raises(AcceptanceBindingError, match="fails closed"):
        validate_and_issue_acceptance(replace(evidence, final_acceptance=unknown),
                                      registry, identity, required_commit=COMMIT)


def test_unqualified_verifier_probe_fails_closed():
    with pytest.raises(AcceptanceBindingError, match="fail closed"):
        VerifierQualification(boundary=SANDBOX_PROFILE, probe_status="unknown",
                              probe_reason="isolation_unavailable:platform_not_linux",
                              probe_returncode=-1, probe_stdout_sha256="3" * 64,
                              probe_stderr_sha256="4" * 64, probed_at_ns=START)
    with pytest.raises(AcceptanceBindingError, match="verifier boundary"):
        VerifierQualification(boundary="trusted_fixture_unsandboxed",
                              probe_status="pass", probe_reason="exit",
                              probe_returncode=0, probe_stdout_sha256="3" * 64,
                              probe_stderr_sha256="4" * 64, probed_at_ns=START)


def test_development_fixture_acceptance_cannot_be_relabelled():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1")
    fixture = make_acceptance(identity, evidence.receipts,
                              level="development_fixture",
                              boundary="trusted_fixture_unsandboxed")
    with pytest.raises(AcceptanceBindingError, match="development_fixture"):
        validate_and_issue_acceptance(replace(evidence, final_acceptance=fixture),
                                      registry, identity, required_commit=COMMIT)


def test_acceptance_must_bind_exact_receipt_set():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1")
    wrong = make_acceptance(identity, evidence.receipts,
                            receipt_hashes=("0" * 64,) * len(evidence.receipts))
    with pytest.raises(AcceptanceBindingError, match="exact measured M3 receipt set"):
        validate_and_issue_acceptance(replace(evidence, final_acceptance=wrong),
                                      registry, identity, required_commit=COMMIT)


# --- prerequisites ----------------------------------------------------------

def test_prerequisite_gates_fail_closed():
    with pytest.raises(AcceptanceBindingError, match="clean-install"):
        validate_prerequisites(None, OWNERSHIP, required_commit=COMMIT)
    with pytest.raises(AcceptanceBindingError, match="clean-install"):
        validate_prerequisites({"status": "FAIL"}, OWNERSHIP, required_commit=COMMIT)
    with pytest.raises(AcceptanceBindingError, match="ownership"):
        validate_prerequisites(CLEAN_INSTALL, None, required_commit=COMMIT)
    with pytest.raises(AcceptanceBindingError, match="ownership"):
        validate_prerequisites(CLEAN_INSTALL, {"passed": False}, required_commit=COMMIT)
    with pytest.raises(AcceptanceBindingError, match="another commit"):
        validate_prerequisites({"status": "PASS", "commit": "1" * 40}, OWNERSHIP,
                               required_commit=COMMIT)


def test_absent_prerequisites_reject_the_binding():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1",
                             clean_install_report={}, ownership_report={})
    with pytest.raises(AcceptanceBindingError, match="clean-install"):
        validate_and_issue_acceptance(evidence, registry, identity,
                                      required_commit=COMMIT)
