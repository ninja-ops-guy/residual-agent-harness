import pytest

from residual.self_maintenance import (
    CandidateProposal,
    CandidateState,
    MaintenanceContract,
    ProtectedSelfMaintenanceController,
    SelfMaintenanceError,
    VerificationState,
)


def contract(**changes):
    values = dict(
        mission_id="selfhost-1",
        base_commit="0123456789abcdef",
        issue_ref="#35",
        objective="repair evidence reproducibility",
        writable_paths=("a.py", "docs.md"),
        verifier_ids=("scope", "behavior"),
        proposer_id="worker",
        max_generations=4,
    )
    values.update(changes)
    return MaintenanceContract(**values)


def passers():
    return {
        "scope": lambda p, c: (VerificationState.PASS, "scope_ok"),
        "behavior": lambda p, c: (VerificationState.PASS, "behavior_ok"),
    }


def proposal(controller, generation=1, **changes):
    values = dict(
        generation=generation,
        parent_receipt_hash=controller.last_receipt_hash,
        files={"a.py": "x=1\n"},
        requested_actions=("file.write", "git.commit", "pull_request.create"),
        proposer_id="worker",
    )
    values.update(changes)
    return CandidateProposal(**values)


def test_candidate_can_be_pr_ready_but_never_merge_authorized():
    controller = ProtectedSelfMaintenanceController(contract())
    result = controller.evaluate(proposal(controller), passers())
    assert result.state == CandidateState.PR_READY
    assert result.merge_authorized is False
    assert controller.verify_receipt_chain()


def test_authority_escalation_and_write_escape_rejected_before_verification():
    controller = ProtectedSelfMaintenanceController(contract())
    called = []
    verifiers = {
        key: (lambda p, c, key=key: (called.append(key), (VerificationState.PASS, "ok"))[1])
        for key in passers()
    }
    result = controller.evaluate(
        proposal(controller, requested_actions=("file.write", "git.merge")),
        verifiers,
    )
    assert result.state == CandidateState.REJECTED
    assert called == []

    controller = ProtectedSelfMaintenanceController(contract())
    called = []
    verifiers = {
        key: (lambda p, c, key=key: (called.append(key), (VerificationState.PASS, "ok"))[1])
        for key in passers()
    }
    result = controller.evaluate(
        proposal(controller, files={"residual/control_plane/policy.py": "bad\n"}),
        verifiers,
    )
    assert result.state == CandidateState.REJECTED
    assert called == []


@pytest.mark.parametrize(
    "bad_path",
    [
        "../main",
        "./a.py",
        "a//b.py",
        "C:\\outside.py",
        "safe\\..\\outside.py",
        "C:/outside.py",
        ".git/config",
    ],
)
def test_candidate_rejects_noncanonical_or_host_ambiguous_paths(bad_path):
    with pytest.raises(SelfMaintenanceError):
        CandidateProposal(
            generation=1,
            parent_receipt_hash=None,
            files={bad_path: "bad\n"},
            proposer_id="worker",
        )


@pytest.mark.parametrize(
    "protected_path",
    [
        ".github/workflows/self.yml",
        "residual/control_plane/policy.py",
        "residual/factory/m4_safety.py",
        "residual/verifier.py",
        "residual/goalspec.py",
        "residual/loop.py",
    ],
)
def test_contract_cannot_whitelist_protected_authority_paths(protected_path):
    with pytest.raises(SelfMaintenanceError, match="protected write scope"):
        contract(writable_paths=(protected_path,))


def test_unknown_fail_exception_and_missing_independence_do_not_accept():
    cases = [
        {
            "scope": lambda p, c: (VerificationState.UNKNOWN, "missing evidence"),
            "behavior": passers()["behavior"],
        },
        {
            "scope": lambda p, c: (VerificationState.FAIL, "wrong"),
            "behavior": passers()["behavior"],
        },
        {
            "scope": lambda p, c: (_ for _ in ()).throw(RuntimeError("boom")),
            "behavior": passers()["behavior"],
        },
        {"scope": passers()["scope"]},
        {"scope": passers()["scope"], "behavior": object()},
    ]
    for verifiers in cases:
        controller = ProtectedSelfMaintenanceController(contract())
        result = controller.evaluate(proposal(controller), verifiers)
        assert result.state == CandidateState.REJECTED
        assert result.merge_authorized is False


def test_lineage_requires_exact_parent_and_monotonic_generation():
    controller = ProtectedSelfMaintenanceController(contract())
    first = controller.evaluate(proposal(controller), passers())
    assert first.state == CandidateState.PR_READY
    wrong = CandidateProposal(
        2,
        "0" * 64,
        {"a.py": "x=2\n"},
        proposer_id="worker",
    )
    second = controller.evaluate(wrong, passers())
    assert second.state == CandidateState.REJECTED
    assert controller.verify_receipt_chain()


def test_contract_cannot_grant_unknown_merge_or_use_proposer_as_verifier():
    for actions in (
        ("file.write", "git.merge"),
        ("file.write", "shell.exec"),
        ("file.write", "git.push.main"),
    ):
        with pytest.raises(SelfMaintenanceError):
            contract(allowed_actions=actions)
    with pytest.raises(SelfMaintenanceError):
        contract(verifier_ids=("worker", "behavior"))
    with pytest.raises(SelfMaintenanceError):
        contract(require_external_merge=False)


def test_action_and_verifier_collections_are_strict_immutable_tuples():
    with pytest.raises(SelfMaintenanceError):
        contract(allowed_actions=["file.write"])  # type: ignore[arg-type]
    with pytest.raises(SelfMaintenanceError):
        contract(verifier_ids=["scope", "behavior"])  # type: ignore[arg-type]
    controller = ProtectedSelfMaintenanceController(contract())
    with pytest.raises(SelfMaintenanceError):
        proposal(controller, requested_actions=["file.write"])  # type: ignore[arg-type]
    with pytest.raises(SelfMaintenanceError):
        proposal(controller, requested_actions=("file.write", "file.write"))


def test_parent_hash_and_metadata_fail_closed_before_receipt_hashing():
    with pytest.raises(SelfMaintenanceError, match="parent_receipt_hash"):
        CandidateProposal(2, "not-a-digest", {"a.py": "x=2\n"}, proposer_id="worker")
    with pytest.raises(SelfMaintenanceError, match="metadata"):
        CandidateProposal(
            1,
            None,
            {"a.py": "x=1\n"},
            proposer_id="worker",
            metadata={"bad": float("nan")},
        )
