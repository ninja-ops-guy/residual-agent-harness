from __future__ import annotations

import hashlib

import pytest

from residual.authority_qualification import (
    AUTH_CHILDREN,
    AttackExecutionReceipt,
    AttackManifest,
    FailClosedState,
    qualify,
    qualification_report,
)
from residual.core import ContractError


HEAD = "1" * 40
TREE = "2" * 40
CONTRACT = "3" * 64
INPUT = "4" * 64
EVIDENCE = "5" * 64


def state(**values: str) -> FailClosedState:
    return FailClosedState.from_mapping(values)


def manifest(
    invariant_id: str = "INV-AUTH-AMB-005",
    *,
    attack_id: str = "AUTH-AMB-005-N01",
    head: str = HEAD,
    tree: str = TREE,
    contract: str = CONTRACT,
    failure_code: str = "AMBIGUOUS_ACCEPTANCE_CONDITION",
    expected: FailClosedState | None = None,
) -> AttackManifest:
    return AttackManifest(
        attack_id=attack_id,
        invariant_id=invariant_id,
        target_head=head,
        target_tree=tree,
        target_contract_id=contract,
        attack_input_hash=INPUT,
        expected_fail_closed_state=expected or state(
            execution="NONE",
            authority_change="NONE",
            promotion="NONE",
            implicit_default="NONE",
        ),
        expected_failure_code=failure_code,
    )


def receipt(
    attack: AttackManifest,
    *,
    head: str | None = None,
    tree: str | None = None,
    contract: str | None = None,
    failure_code: str | None = None,
    observed: FailClosedState | None = None,
) -> AttackExecutionReceipt:
    return AttackExecutionReceipt(
        attack_manifest_hash=attack.manifest_hash,
        candidate_head=head or attack.target_head,
        candidate_tree=tree or attack.target_tree,
        contract_id=contract or attack.target_contract_id,
        runner_identity="authority-qualification-runner",
        observed_failure_code=failure_code or attack.expected_failure_code,
        observed_fail_closed_state=observed or attack.expected_fail_closed_state,
        evidence_hashes=(EVIDENCE,),
        issued_at_ns=1,
    )


def test_attack_manifest_hash_binds_candidate_contract_and_input():
    attack = manifest()
    base = attack.manifest_hash

    changed_head = manifest(head="a" * 40)
    changed_tree = manifest(tree="b" * 40)
    changed_contract = manifest(contract="c" * 64)
    changed_input = AttackManifest(
        **{
            **attack.unsigned_payload(),
            "attack_input_hash": "d" * 64,
            "expected_fail_closed_state": attack.expected_fail_closed_state,
        }
    )

    assert len({base, changed_head.manifest_hash, changed_tree.manifest_hash,
                changed_contract.manifest_hash, changed_input.manifest_hash}) == 5

    raw = attack.to_dict()
    raw["target_head"] = "e" * 40
    with pytest.raises(ContractError, match="manifest hash mismatch"):
        AttackManifest.from_dict(raw)


def test_attack_receipt_hash_is_not_self_referential_and_detects_tamper():
    attack = manifest()
    observed = receipt(attack)
    raw = observed.to_dict()

    assert "receipt_hash" not in observed.unsigned_payload()
    assert raw["receipt_hash"] == observed.receipt_hash
    assert AttackExecutionReceipt.from_dict(raw) == observed

    raw["candidate_head"] = "f" * 40
    with pytest.raises(ContractError, match="receipt hash mismatch"):
        AttackExecutionReceipt.from_dict(raw)


def test_negative_attack_pass_requires_expected_reason_and_safe_state():
    attack = manifest()
    observed = receipt(
        attack,
        observed=state(
            execution="NONE",
            authority_change="NONE",
            promotion="NONE",
            implicit_default="NONE",
            diagnostic="RECORDED",
        ),
    )
    result = qualify(attack, observed)

    assert result.result == "PASS"
    assert result.failure_reasons == ()
    assert result.expected_failure_code == result.observed_failure_code
    assert result.evidence_receipt_hash == observed.receipt_hash


def test_matching_failure_code_does_not_hide_unsafe_state():
    attack = manifest()
    observed = receipt(
        attack,
        observed=state(
            execution="STARTED",
            authority_change="NONE",
            promotion="NONE",
            implicit_default="NONE",
        ),
    )
    result = qualify(attack, observed)

    assert result.result == "FAIL"
    assert result.observed_failure_code == "AMBIGUOUS_ACCEPTANCE_CONDITION"
    assert "FAIL_CLOSED_STATE_MISMATCH" in result.failure_reasons


def test_right_attack_against_wrong_candidate_cannot_qualify_release():
    attack = manifest()
    observed = receipt(attack, head="a" * 40)
    result = qualify(attack, observed)

    assert result.result == "FAIL"
    assert "TARGET_HEAD_MISMATCH" in result.failure_reasons


def test_wrong_rejection_reason_is_not_a_pass():
    attack = manifest()
    observed = receipt(attack, failure_code="UNRESOLVED_AUTHORITY")
    result = qualify(attack, observed)

    assert result.result == "FAIL"
    assert "FAILURE_CODE_MISMATCH" in result.failure_reasons


def _passing_record(index: int, invariant_id: str):
    codes = {
        "INV-AUTH-EVD-001": "UNBOUND_EVIDENCE_SOURCE",
        "INV-AUTH-IDN-002": "UNRESOLVED_AUTHORITY",
        "INV-AUTH-ACC-003": "UNPROVEN_ACCEPTANCE",
        "INV-AUTH-CTR-004": "UNAUTHORIZED_CONTRACT_REINTERPRETATION",
        "INV-AUTH-AMB-005": "AMBIGUOUS_ACCEPTANCE_CONDITION",
        "INV-AUTH-AUT-006": "UNAPPROVED_ACTION",
    }
    attack = manifest(
        invariant_id,
        attack_id=f"AUTH-{index:02d}-N01",
        failure_code=codes[invariant_id],
        expected=state(authority_change="NONE"),
    )
    return qualify(attack, receipt(attack))


def test_parent_is_derived_only_from_exact_six_child_results():
    records = [
        _passing_record(index, invariant_id)
        for index, invariant_id in enumerate(AUTH_CHILDREN, start=1)
    ]
    report = qualification_report(records)

    assert report["child_result"] == "6/6"
    assert report["parent_invariant"] == "INV-AUTH-000"
    assert report["parent_result"] == "PASS"
    assert report["candidate_head"] == HEAD
    assert report["candidate_tree"] == TREE
    assert report["contract_id"] == CONTRACT

    missing = qualification_report(records[:-1])
    assert missing["parent_result"] == "FAIL"
    assert missing["missing_invariants"]

    duplicate = qualification_report(records + [records[0]])
    assert duplicate["parent_result"] == "FAIL"
    assert duplicate["duplicate_invariant"] is True


def test_parent_fails_when_child_records_target_different_candidate():
    records = [
        _passing_record(index, invariant_id)
        for index, invariant_id in enumerate(AUTH_CHILDREN, start=1)
    ]

    changed_attack = manifest(
        "INV-AUTH-AUT-006",
        attack_id="AUTH-06-N02",
        head="a" * 40,
        failure_code="UNAPPROVED_ACTION",
        expected=state(authority_change="NONE"),
    )
    records[-1] = qualify(changed_attack, receipt(changed_attack))
    report = qualification_report(records)

    assert report["parent_result"] == "FAIL"
    assert report["candidate_head"] is None
    assert report["candidate_tree"] is None
    assert report["contract_id"] is None
