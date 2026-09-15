"""Executable subset and strict expected failures for independently found gaps."""
from dataclasses import replace
import hashlib
import os
from pathlib import Path
from unittest.mock import patch
import pytest


@pytest.mark.parametrize("status", ["unknown", "error", "fail", "skipped", "PASS", "", None])
def test_only_exact_pass_can_authorize_integration(api, status):
    m4 = api("residual.factory.m4_integrator", "VerificationResult", "DeterministicIntegrator")
    r = m4.VerificationResult("unit", "full_test_suite", status, 0, "0" * 64, "0" * 64)
    assert not m4.DeterministicIntegrator._passes((r,))
    assert not m4.DeterministicIntegrator._passes(())


def test_unknown_isolation_does_not_launch_a_process(api, tmp_path):
    sandbox = api("residual.factory.m4_sandbox", "run_isolated")
    with patch.object(sandbox, "probe_isolation", return_value=(False, "injected_unavailable")), \
         patch.object(sandbox.subprocess, "Popen", side_effect=AssertionError("unauthorized launch")):
        result = sandbox.run_isolated(("/usr/bin/python3", "-c", "raise SystemExit(0)"), tmp_path,
                                      timeout_s=1., output_limit=1024)
    assert result.status == "unknown" and result.returncode is None


@pytest.mark.parametrize("reason,returncode", [("timeout", -9), ("output_limit", -9), ("exit", -11), ("launch_failed", 125)])
def test_execution_failures_cannot_support_candidate_attribution(api, reason, returncode):
    m4 = api("residual.factory.m4_integrator", "VerificationResult", "DeterministicIntegrator._verification_available")
    r = m4.VerificationResult("unit", "full_test_suite", "fail", returncode, "0" * 64, "0" * 64, reason)
    assert not m4.DeterministicIntegrator._verification_available((r,))


def test_toctou_leaf_swap_is_actually_injected_and_never_follows_link(api, tmp_path):
    safety = api("residual.factory.m4_safety", "apply_artifact")
    work = tmp_path / "work"; work.mkdir()
    sentinel = tmp_path / "sentinel"; sentinel.write_bytes(b"intact")
    target = work / "candidate"; target.write_bytes(b"original")
    real = safety._regular_entry
    injected = []
    def swap(fd, name):
        prior = real(fd, name)
        os.unlink(name, dir_fd=fd)
        os.symlink(sentinel, name, dir_fd=fd)
        injected.append(True)
        return prior
    with patch.object(safety, "_regular_entry", side_effect=swap):
        safety.apply_artifact(work, "candidate", b"replacement")
    assert injected == [True]
    assert sentinel.read_bytes() == b"intact"
    assert target.read_bytes() == b"replacement" and not target.is_symlink()


def test_sparse_files_hash_logical_bytes_under_small_bound(api, tmp_path):
    safety = api("residual.factory.m4_safety", "snapshot")
    target = tmp_path / "sparse"
    with target.open("wb") as stream:
        stream.seek(1024 * 1024); stream.write(b"x")
    assert safety.snapshot(tmp_path)["sparse"][2] == hashlib.sha256(b"\0" * (1024 * 1024) + b"x").hexdigest()


def test_oversized_name_is_rejected_without_partial_artifact(api, tmp_path):
    safety = api("residual.factory.m4_safety", "apply_artifact")
    with pytest.raises(safety.M4SafetyError):
        safety.apply_artifact(tmp_path, "x" * 300, b"candidate")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.xfail(strict=True, reason="TRUST-002: cat-file size parsing ValueError escapes typed ERROR")
def test_malformed_git_size_has_typed_error(api):
    git = api("residual.factory.m4_git_evidence", "read_base_blob")
    commit = "a" * 40
    responses = [(0, commit.encode()), (0, b"100644 blob " + b"b" * 40 + b"\tx\0"), (0, b"not-a-size")]
    with patch.object(git, "_run", side_effect=responses):
        result = git.read_base_blob(Path("."), commit, "x")
    assert result.state is git.GitEvidenceState.ERROR


@pytest.mark.xfail(strict=True, reason="TRUST-003: VerificationDecision truthiness-coerces non-boolean requirements")
def test_string_false_requirement_is_rejected(api):
    e = api("residual.factory.evidence_receipts", "VerificationDecision")
    with pytest.raises(e.EvidenceError):
        e.VerificationDecision((("R1", "false"),), (("unit", "pass"),), "pass", "station:test", "0" * 64)


@pytest.mark.xfail(strict=True, reason="TRUST-004: SchedulerPolicy accepts NaN imbalance threshold")
def test_scheduler_nonfinite_policy_is_rejected(api):
    s = api("residual.factory.m4_scheduler", "SchedulerPolicy")
    with pytest.raises(s.M4SchedulerError):
        s.SchedulerPolicy(imbalance_ratio=float("nan"))
