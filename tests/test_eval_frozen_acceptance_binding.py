"""Regression tests for the measured-evaluation -> M4-acceptance binding.

Each evidence-integrity requirement has NEGATIVE tests covering the seams
found in adversarial review: replay rejected, endpoint-only topology
interval rejected, forged/unsigned verifier qualification rejected,
mismatched/weaker ownership pin rejected, and freshness not verifiable
without the retained run-identity chain.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from residual.eval_frozen.acceptance_binding import (
    ACCEPTANCE_SCHEMA,
    CHAIN_SCHEMA,
    AcceptanceBindingError,
    FreshRunRegistry,
    MeasuredRunEvidence,
    SchedulerObservation,
    SchedulerTopologyEvidence,
    VerifierQualification,
    WorkloadTaskMapping,
    _ISSUANCE_TOKEN,
    validate_and_issue_acceptance,
    validate_prerequisites,
    verify_acceptance_artifact,
    verify_run_identity_chain,
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

START, MID, END = 1_000_000_000, 1_500_000_000, 2_000_000_000

CLEAN_INSTALL = {"status": "PASS", "commit": COMMIT, "tree": "f" * 40}
# Mirrors the on-repo #95 baseline pin and protected-file count; the binding
# cross-checks both against verifier/v3/factory_ownership_baseline.json.
OWNERSHIP = {"passed": True, "pinned_at": "0" * 40, "protected_files": 32}
BASELINE = {"pinned_at": "0" * 40, "files": {f"path/{i}": str(i).zfill(40)[:40] for i in range(32)}}


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
                  observations=(START, MID, END)) -> SchedulerTopologyEvidence:
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


def make_verifier(identity: StationIdentity, run_id: str = "run-1",
                  probed_at_ns: int = MID) -> VerifierQualification:
    return VerifierQualification.issue(
        identity, run_id=run_id, probe_status="pass", probe_reason="exit",
        probe_returncode=0, probe_stdout_sha256="3" * 64,
        probe_stderr_sha256="4" * 64, probed_at_ns=probed_at_ns)


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
        verifier=make_verifier(identity, run_id),
        clean_install_report=dict(CLEAN_INSTALL),
        ownership_report=dict(OWNERSHIP),
    )
    kwargs.update(overrides)
    return MeasuredRunEvidence(**kwargs)


def begin(registry: FreshRunRegistry, workload, run_id: str = "run-1"):
    return registry.begin_run(run_id, workload_sha256=workload.sha256,
                              report_sha256=REPORT, execution_plan_hash=H)


def issue(identity, registry, workload, evidence, **kw):
    return validate_and_issue_acceptance(
        evidence, registry, identity, required_commit=COMMIT,
        ownership_baseline=dict(BASELINE), **kw)


# --- happy path ------------------------------------------------------------

def test_full_binding_issues_signed_acceptance_artifact():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    artifact = issue(identity, registry, workload,
                     make_evidence(identity, registry, workload, "run-1"))
    assert artifact["schema_version"] == ACCEPTANCE_SCHEMA
    assert artifact["attribution"] is None
    assert artifact["verifier_qualification"]["boundary"] == SANDBOX_PROFILE
    assert artifact["verifier_qualification"]["run_id"] == "run-1"
    assert artifact["run_identity_chain"]["schema_version"] == CHAIN_SCHEMA
    assert verify_acceptance_artifact(artifact, identity.public_bytes())
    assert not verify_acceptance_artifact(artifact, StationIdentity.generate().public_bytes())
    # Freshness verifiable out of process with the exported chain.
    chain = registry.export_chain()
    assert verify_acceptance_artifact(artifact, identity.public_bytes(), chain=chain)


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
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1"))


def test_unknown_run_identity_fails_closed():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    with pytest.raises(AcceptanceBindingError, match="no fresh execution identity"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1"))


def test_forged_identity_chain_record_is_rejected():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    record = begin(registry, workload)
    forged = replace(record, run_id="run-2")  # invalidates signature + chain
    registry._records.append(forged)
    with pytest.raises(AcceptanceBindingError):
        registry.verify_chain()


def test_exported_chain_verifies_out_of_process_and_detects_tampering():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    chain = registry.export_chain()
    records = verify_run_identity_chain(chain, identity.public_bytes())
    assert len(records) == 1 and records[0].run_id == "run-1"
    # Wrong key fails closed.
    with pytest.raises(AcceptanceBindingError, match="signature"):
        verify_run_identity_chain(chain, StationIdentity.generate().public_bytes())
    # Tampered record content fails closed (hash and/or signature mismatch).
    tampered = copy.deepcopy(chain)
    tampered["records"][0]["run_id"] = "run-evil"
    with pytest.raises(AcceptanceBindingError):
        verify_run_identity_chain(tampered, identity.public_bytes())
    # Reordered/relinked chain fails closed.
    registry.begin_run("run-2", workload_sha256=workload.sha256,
                       report_sha256=REPORT, execution_plan_hash=H)
    two = registry.export_chain()
    broken = copy.deepcopy(two)
    broken["records"] = list(reversed(broken["records"]))
    with pytest.raises(AcceptanceBindingError):
        verify_run_identity_chain(broken, identity.public_bytes())


def test_resumed_run_fails_freshness_in_exported_chain():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    registry.resume_run("run-1")
    chain = registry.export_chain()
    records = verify_run_identity_chain(chain, identity.public_bytes())
    from residual.eval_frozen.acceptance_binding import chain_fresh_record
    with pytest.raises(AcceptanceBindingError, match="non-fresh"):
        chain_fresh_record(records, "run-1")


# --- requirement 2: authenticated topology spanning the run -----------------

def test_unauthenticated_topology_is_rejected():
    identity = StationIdentity.generate()
    other = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    topology = make_topology(other)  # signed by a foreign Station
    with pytest.raises(AcceptanceBindingError, match="not authenticated"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1", topology=topology))


def test_partial_interval_topology_is_rejected():
    identity = StationIdentity.generate()
    with pytest.raises(AcceptanceBindingError, match="span the run interval"):
        make_topology(identity, observations=(START + 100, END - 100))
    with pytest.raises(AcceptanceBindingError, match="span the run interval"):
        make_topology(identity, observations=(START + 100,))


def test_endpoint_only_interval_is_rejected():
    """Adversarial seam: observations exactly at both endpoints but ZERO
    observations inside the run must NOT satisfy interval coverage."""
    identity = StationIdentity.generate()
    with pytest.raises(AcceptanceBindingError, match="strictly inside"):
        make_topology(identity, observations=(START, END))
    # Also rejected with duplicate boundary-only observations.
    with pytest.raises(AcceptanceBindingError, match="strictly inside"):
        make_topology(identity, observations=(START, START, END, END))
    # One interior observation satisfies the floor.
    make_topology(identity, observations=(START, START + 1, END))


def test_topology_interval_must_match_the_run():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    topology = make_topology(identity, start=START, end=END + 1,
                             observations=(START, MID, END + 1))
    with pytest.raises(AcceptanceBindingError, match="interval does not match"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1", topology=topology))


def test_topology_from_another_execution_plan_is_rejected():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    topology = make_topology(identity, plan="8" * 64)
    with pytest.raises(AcceptanceBindingError, match="another ExecutionPlan"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1", topology=topology))


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
        issue(identity, registry, workload, replace(evidence, receipts=receipts))
    # Missing mapped task.
    with pytest.raises(AcceptanceBindingError, match="population diverges"):
        issue(identity, registry, workload,
              replace(evidence, receipts=evidence.receipts[:-1]))
    # Duplicate task.
    with pytest.raises(AcceptanceBindingError, match="duplicate"):
        issue(identity, registry, workload,
              replace(evidence, receipts=evidence.receipts + evidence.receipts[:1]))


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


# --- requirement 4: Station-signed verifier probe receipt ------------------

def test_unknown_verifier_outcome_rejects_and_never_attributes():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1")
    unknown = make_acceptance(identity, evidence.receipts, status="unknown",
                              reason="isolation_unavailable:probe", returncode=None)
    with pytest.raises(AcceptanceBindingError, match="fails closed"):
        issue(identity, registry, workload,
              replace(evidence, final_acceptance=unknown))


def test_unqualified_verifier_probe_fails_closed():
    identity = StationIdentity.generate()
    with pytest.raises(AcceptanceBindingError, match="fail closed"):
        VerifierQualification.issue(
            identity, run_id="run-1", probe_status="unknown",
            probe_reason="isolation_unavailable:platform_not_linux",
            probe_returncode=-1, probe_stdout_sha256="3" * 64,
            probe_stderr_sha256="4" * 64, probed_at_ns=MID)
    with pytest.raises(AcceptanceBindingError, match="verifier boundary"):
        VerifierQualification.issue(
            identity, run_id="run-1", boundary="trusted_fixture_unsandboxed",
            probe_status="pass", probe_reason="exit",
            probe_returncode=0, probe_stdout_sha256="3" * 64,
            probe_stderr_sha256="4" * 64, probed_at_ns=MID)


def test_directly_constructed_qualification_is_blocked():
    """Adversarial seam: fabricated, directly constructed qualifications."""
    with pytest.raises(AcceptanceBindingError, match="issuance path"):
        VerifierQualification(
            boundary=SANDBOX_PROFILE, probe_status="pass", probe_reason="exit",
            probe_returncode=0, probe_stdout_sha256="3" * 64,
            probe_stderr_sha256="4" * 64, probed_at_ns=MID, run_id="run-1",
            station_key_id="0" * 64, station_signature="0" * 128)


def test_forged_unsigned_qualification_is_rejected_by_the_binding():
    """Adversarial seam: a qualification minted with the private token but
    NOT signed by the run's Station fails signature verification."""
    identity = StationIdentity.generate()
    forger = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    forged = make_verifier(forger, "run-1")  # signed by a foreign Station
    with pytest.raises(AcceptanceBindingError, match="not authenticated"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1", verifier=forged))
    # Token-bypassed, self-signed-by-nobody fabrication also fails.
    honest = make_verifier(identity, "run-1")
    fabricated = VerifierQualification(
        boundary=SANDBOX_PROFILE, probe_status="pass", probe_reason="exit",
        probe_returncode=0, probe_stdout_sha256="3" * 64,
        probe_stderr_sha256="4" * 64, probed_at_ns=MID, run_id="run-1",
        station_key_id=identity.key_id, station_signature="0" * 128,
        _token=_ISSUANCE_TOKEN)
    assert not fabricated.verify_signature(identity.public_bytes())
    assert honest.verify_signature(identity.public_bytes())


def test_qualification_must_bind_this_run_and_run_interval():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    # Bound to another run id.
    other_run = make_verifier(identity, "run-2")
    with pytest.raises(AcceptanceBindingError, match="another run id"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1", verifier=other_run))
    # Probed outside the run interval.
    late = make_verifier(identity, "run-1", probed_at_ns=END + 1)
    with pytest.raises(AcceptanceBindingError, match="outside the run interval"):
        issue(identity, registry, workload,
              make_evidence(identity, registry, workload, "run-1", verifier=late))


def test_from_isolated_result_requires_typed_pass_probe():
    identity = StationIdentity.generate()
    ok = SimpleNamespace(status="pass", reason="exit", returncode=0,
                         stdout_sha256="3" * 64, stderr_sha256="4" * 64,
                         execution_boundary=SANDBOX_PROFILE)
    qual = VerifierQualification.from_isolated_result(identity, ok, run_id="run-1",
                                                      probed_at_ns=MID)
    assert qual.verify_signature(identity.public_bytes())
    bad = SimpleNamespace(status="unknown", reason="isolation_unavailable:probe",
                          returncode=None, stdout_sha256="3" * 64,
                          stderr_sha256="4" * 64, execution_boundary=SANDBOX_PROFILE)
    with pytest.raises(AcceptanceBindingError, match="failing closed"):
        VerifierQualification.from_isolated_result(identity, bad, run_id="run-1",
                                                   probed_at_ns=MID)


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
        issue(identity, registry, workload,
              replace(evidence, final_acceptance=fixture))


def test_acceptance_must_bind_exact_receipt_set():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1")
    wrong = make_acceptance(identity, evidence.receipts,
                            receipt_hashes=("0" * 64,) * len(evidence.receipts))
    with pytest.raises(AcceptanceBindingError, match="exact measured M3 receipt set"):
        issue(identity, registry, workload,
              replace(evidence, final_acceptance=wrong))


# --- prerequisites ----------------------------------------------------------

def test_prerequisite_gates_fail_closed():
    with pytest.raises(AcceptanceBindingError, match="clean-install"):
        validate_prerequisites(None, OWNERSHIP, required_commit=COMMIT,
                               ownership_baseline=BASELINE)
    with pytest.raises(AcceptanceBindingError, match="clean-install"):
        validate_prerequisites({"status": "FAIL"}, OWNERSHIP, required_commit=COMMIT,
                               ownership_baseline=BASELINE)
    with pytest.raises(AcceptanceBindingError, match="ownership"):
        validate_prerequisites(CLEAN_INSTALL, None, required_commit=COMMIT,
                               ownership_baseline=BASELINE)
    with pytest.raises(AcceptanceBindingError, match="ownership"):
        validate_prerequisites(CLEAN_INSTALL, {"passed": False}, required_commit=COMMIT,
                               ownership_baseline=BASELINE)
    with pytest.raises(AcceptanceBindingError, match="another commit"):
        validate_prerequisites({"status": "PASS", "commit": "1" * 40}, OWNERSHIP,
                               required_commit=COMMIT, ownership_baseline=BASELINE)


def test_mismatched_ownership_pin_fails_closed():
    """Adversarial seam: an ownership report pinned somewhere other than the
    current #95 baseline must fail, not merely be non-None."""
    stale = {"passed": True, "pinned_at": "1" * 40, "protected_files": 32}
    with pytest.raises(AcceptanceBindingError, match="baseline pin"):
        validate_prerequisites(CLEAN_INSTALL, stale, required_commit=COMMIT,
                               ownership_baseline=BASELINE)
    no_pin = {"passed": True, "pinned_at": None, "protected_files": 32}
    with pytest.raises(AcceptanceBindingError, match="no valid pin"):
        validate_prerequisites(CLEAN_INSTALL, no_pin, required_commit=COMMIT,
                               ownership_baseline=BASELINE)


def test_weaker_ownership_pin_fails_closed():
    """Adversarial seam: a report covering FEWER protected paths than the
    baseline must fail even with the correct pin."""
    weaker = {"passed": True, "pinned_at": "0" * 40, "protected_files": 10}
    with pytest.raises(AcceptanceBindingError, match="weaker"):
        validate_prerequisites(CLEAN_INSTALL, weaker, required_commit=COMMIT,
                               ownership_baseline=BASELINE)
    mismatched_count = {"passed": True, "pinned_at": "0" * 40, "protected_files": 33}
    with pytest.raises(AcceptanceBindingError, match="weaker"):
        validate_prerequisites(CLEAN_INSTALL, mismatched_count, required_commit=COMMIT,
                               ownership_baseline=BASELINE)


def test_prerequisites_default_to_on_repo_baseline():
    # Without an explicit baseline the binding loads the on-repo #95 manifest.
    import json
    from pathlib import Path
    from residual.eval_frozen import acceptance_binding as ab
    manifest = json.loads(Path(ab.DEFAULT_OWNERSHIP_BASELINE_PATH).read_text())
    report = {"passed": True, "pinned_at": manifest["pinned_at"],
              "protected_files": len(manifest["files"])}
    out = validate_prerequisites(CLEAN_INSTALL, report, required_commit=COMMIT)
    assert out["ownership_pinned_at"] == manifest["pinned_at"]


def test_absent_prerequisites_reject_the_binding():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    evidence = make_evidence(identity, registry, workload, "run-1",
                             clean_install_report={}, ownership_report={})
    with pytest.raises(AcceptanceBindingError, match="clean-install"):
        issue(identity, registry, workload, evidence)


# --- freshness verifiability (artifact + chain) ------------------------------

def test_freshness_not_verified_without_chain():
    """Adversarial seam: signature-only verification cannot check freshness.

    An artifact for a run that was later RESUMED still passes
    signature-only verification; only presenting the retained chain exposes
    the resume and fails verification.
    """
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    artifact = issue(identity, registry, workload,
                     make_evidence(identity, registry, workload, "run-1"))
    # Without a chain: signature valid, freshness UNVERIFIED (documented).
    assert verify_acceptance_artifact(artifact, identity.public_bytes())
    # Resume after issuance: the artifact still verifies signature-only...
    registry.resume_run("run-1")
    assert verify_acceptance_artifact(artifact, identity.public_bytes())
    # ...but with the retained chain, freshness fails closed.
    assert not verify_acceptance_artifact(artifact, identity.public_bytes(),
                                          chain=registry.export_chain())


def test_chain_reference_mismatch_is_rejected():
    identity = StationIdentity.generate()
    other = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    foreign_registry = FreshRunRegistry(other)
    workload = development_workload()
    begin(registry, workload)
    foreign_registry.begin_run("run-1", workload_sha256=workload.sha256,
                               report_sha256=REPORT, execution_plan_hash=H)
    artifact = issue(identity, registry, workload,
                     make_evidence(identity, registry, workload, "run-1"))
    # A chain from another Station / another chain head must not satisfy the
    # artifact's chain reference.
    assert not verify_acceptance_artifact(artifact, identity.public_bytes(),
                                          chain=foreign_registry.export_chain())


def test_artifact_documents_operator_asserted_and_registry_enforced_fields():
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    artifact = issue(identity, registry, workload,
                     make_evidence(identity, registry, workload, "run-1"))
    assert any("issued_at_ns" in f for f in artifact["operator_asserted_fields"])
    assert any("uniqueness" in f for f in artifact["registry_enforced_fields"])
    assert "retention_requirement" in artifact["run_identity_chain"]
