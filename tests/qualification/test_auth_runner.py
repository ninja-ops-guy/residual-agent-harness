"""Unit tests for the attack-manifest qualification runner (Track B2).

The decision procedure is tested with stubbed outcomes; no Track A
emission layer is required for these tests.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

from residual.core import canonical
from residual.qualification import auth_runner as ar

try:
    from residual.authority import AuthorityCoercionRejected
except ImportError:  # Track A2 not yet delivered in this checkout
    AuthorityCoercionRejected = None


# ---------------------------------------------------------------- helpers

def _manifest_dict(**overrides):
    attack_input = {"probe": "x", "n": 1}
    base = {
        "schema": "residual.auth.manifest.v1",
        "attack_id": "AUTH-AMB-005-N01",
        "invariant_id": "INV-AUTH-AMB-005",
        "kind": "negative",
        "target_head": "a" * 40,
        "target_tree": "b" * 40,
        "target_contract_id": "c" * 64,
        "attack_input": attack_input,
        "attack_input_hash": hashlib.sha256(
            canonical(attack_input).encode("utf-8")).hexdigest(),
        "expected_fail_closed_state": "NO_EXECUTION",
        "expected_failure_code": "AMBIGUOUS_ACCEPTANCE_CONDITION",
        "description": "test",
    }
    base.update(overrides)
    return base


def _write_manifest(tmp_path: Path, **overrides) -> Path:
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_manifest_dict(**overrides)), encoding="utf-8")
    return p


def _rejected(code="AMBIGUOUS_ACCEPTANCE_CONDITION",
              state="NO_EXECUTION", triggered=None):
    return ar.Rejected(code=code,
                       triggered_codes=tuple(triggered or [code]),
                       fail_closed_state=state)


# ---------------------------------------------------------------- load_manifest

def test_load_valid_manifest(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    assert m.attack_id == "AUTH-AMB-005-N01"
    assert m.timeout_s == 300
    assert m.expected_triggered_codes == ()


def test_load_rejects_unknown_schema(tmp_path):
    with pytest.raises(ValueError, match="unknown schema"):
        ar.load_manifest(_write_manifest(tmp_path, schema="nope"))


def test_load_rejects_hash_mismatch(tmp_path):
    with pytest.raises(ValueError, match="attack_input_hash mismatch"):
        ar.load_manifest(_write_manifest(tmp_path, attack_input_hash="d" * 64))


def test_load_rejects_bad_attack_id(tmp_path):
    with pytest.raises(ValueError, match="attack_id"):
        ar.load_manifest(_write_manifest(tmp_path, attack_id="bogus"))


def test_load_rejects_bad_timeout(tmp_path):
    with pytest.raises(ValueError, match="timeout_s"):
        ar.load_manifest(_write_manifest(tmp_path, timeout_s=0))
    with pytest.raises(ValueError, match="timeout_s"):
        ar.load_manifest(_write_manifest(tmp_path, timeout_s=True))


def test_load_rejects_compound_without_triggered_codes(tmp_path):
    with pytest.raises(ValueError, match="expected_triggered_codes"):
        ar.load_manifest(_write_manifest(
            tmp_path, kind="compound",
            attack_id="AUTH-COMP-AMB-CTR-N01",
            invariant_id="INV-AUTH-AMB-005"))


def test_load_rejects_positive_without_artifact(tmp_path):
    with pytest.raises(ValueError, match="expected_success_artifact"):
        ar.load_manifest(_write_manifest(
            tmp_path, kind="positive",
            attack_id="AUTH-AMB-005-P01",
            expected_failure_code=None,
            expected_fail_closed_state=None))


def test_load_rejects_positive_with_failure_code(tmp_path):
    with pytest.raises(ValueError, match="must not name a failure code"):
        ar.load_manifest(_write_manifest(
            tmp_path, kind="positive",
            attack_id="AUTH-AMB-005-P01",
            expected_fail_closed_state=None,
            expected_success_artifact={"k": "v"}))


def test_load_accepts_compound_attack_id(tmp_path):
    m = ar.load_manifest(_write_manifest(
        tmp_path, kind="compound",
        attack_id="AUTH-COMP-IDN-AUT-N01",
        invariant_id="INV-AUTH-IDN-002",
        expected_failure_code="UNRESOLVED_AUTHORITY",
        expected_fail_closed_state="NO_AUTHORITY_CHANGE",
        expected_triggered_codes=["UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION"]))
    assert m.expected_triggered_codes == ("UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION")


# ---------------------------------------------------------------- _primary

def test_primary_single():
    assert ar._primary(("UNAPPROVED_ACTION",)) == "UNAPPROVED_ACTION"


def test_primary_precedence_not_lexicographic():
    # IDN-002 precedes AUT-006 in the pipeline even though
    # INV-AUTH-AUT-006 < INV-AUTH-IDN-002 lexicographically.
    assert ar._primary(("UNAPPROVED_ACTION", "UNRESOLVED_AUTHORITY")) == "UNRESOLVED_AUTHORITY"
    assert ar._primary(("UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION")) == "UNRESOLVED_AUTHORITY"


def test_primary_rejects_unknown_code():
    with pytest.raises(ValueError, match="unknown or generic code"):
        ar._primary(("NOT_A_CODE",))


def test_primary_rejects_generic_parent_code():
    with pytest.raises(ValueError, match="unknown or generic code"):
        ar._primary(("IMPLICIT_AUTHORITY_COERCION",))


def test_primary_rejects_empty():
    with pytest.raises(ValueError, match="empty triggered set"):
        ar._primary(())


# ---------------------------------------------------------------- decide: negative

def test_negative_exact_match_pass(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    result, notes = ar.decide(m, _rejected())
    assert result == "PASS"
    assert notes == ()


def test_negative_wrong_primary_fail(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    result, notes = ar.decide(m, _rejected(code="UNAPPROVED_ACTION",
                                          triggered=["UNAPPROVED_ACTION"]))
    assert result == "FAIL"
    assert any("expected AMBIGUOUS_ACCEPTANCE_CONDITION" in n for n in notes)


def test_negative_wrong_state_fail(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    result, notes = ar.decide(m, _rejected(state="NO_AUTHORITY_CHANGE"))
    assert result == "FAIL"
    assert any("expected state NO_EXECUTION" in n for n in notes)


def test_negative_uncoded_rejection_fail(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    result, notes = ar.decide(m, ar.UncodedRejection(info="ContractError: boom"))
    assert result == "FAIL"
    assert any("rejected without a typed failure code" in n for n in notes)


def test_negative_succeeded_fail(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    result, notes = ar.decide(m, ar.Succeeded(artifact={}))
    assert result == "FAIL"
    assert any("not rejected" in n for n in notes)


def test_negative_unknown_code_in_triggered_fail(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    result, notes = ar.decide(m, _rejected(code="UNAPPROVED_ACTION",
                                          triggered=["UNAPPROVED_ACTION", "BOGUS"]))
    assert result == "FAIL"
    assert any("unknown or generic code" in n for n in notes)


# ---------------------------------------------------------------- decide: compound

def _compound_manifest(tmp_path):
    return ar.load_manifest(_write_manifest(
        tmp_path, kind="compound",
        attack_id="AUTH-COMP-IDN-AUT-N01",
        invariant_id="INV-AUTH-IDN-002",
        expected_failure_code="UNRESOLVED_AUTHORITY",
        expected_fail_closed_state="NO_AUTHORITY_CHANGE",
        expected_triggered_codes=["UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION"]))


def test_compound_full_match_pass(tmp_path):
    m = _compound_manifest(tmp_path)
    outcome = _rejected(code="UNRESOLVED_AUTHORITY", state="NO_AUTHORITY_CHANGE",
                        triggered=["UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION"])
    result, notes = ar.decide(m, outcome)
    assert result == "PASS", notes


def test_compound_silent_trigger_fail(tmp_path):
    # The implementation only raised UNRESOLVED_AUTHORITY; the manifest
    # expected UNAPPROVED_ACTION too -> silent trigger.
    m = _compound_manifest(tmp_path)
    outcome = _rejected(code="UNRESOLVED_AUTHORITY", state="NO_AUTHORITY_CHANGE",
                        triggered=["UNRESOLVED_AUTHORITY"])
    result, notes = ar.decide(m, outcome)
    assert result == "FAIL"
    assert any("triggered set mismatch" in n for n in notes)


def test_compound_extra_trigger_fail(tmp_path):
    m = _compound_manifest(tmp_path)
    outcome = _rejected(code="UNRESOLVED_AUTHORITY", state="NO_AUTHORITY_CHANGE",
                        triggered=["UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION",
                                   "UNBOUND_EVIDENCE_SOURCE"])
    result, notes = ar.decide(m, outcome)
    assert result == "FAIL"
    assert any("triggered set mismatch" in n for n in notes)


# ---------------------------------------------------------------- decide: positive

def _positive_manifest(tmp_path, **overrides):
    kw = dict(kind="positive", attack_id="AUTH-AMB-005-P01",
              expected_failure_code=None, expected_fail_closed_state=None,
              expected_success_artifact={"admitted": True, "scope": "read"})
    kw.update(overrides)
    return ar.load_manifest(_write_manifest(tmp_path, **kw))


def test_positive_exact_artifact_pass(tmp_path):
    m = _positive_manifest(tmp_path)
    result, notes = ar.decide(m, ar.Succeeded(
        artifact={"admitted": True, "scope": "read", "extra": "ignored"}))
    assert result == "PASS", notes


def test_positive_artifact_mismatch_fail(tmp_path):
    m = _positive_manifest(tmp_path)
    result, notes = ar.decide(m, ar.Succeeded(
        artifact={"admitted": True, "scope": "write"}))
    assert result == "FAIL"
    assert any("artifact mismatch" in n for n in notes)


def test_positive_missing_key_fail(tmp_path):
    m = _positive_manifest(tmp_path)
    result, notes = ar.decide(m, ar.Succeeded(artifact={"admitted": True}))
    assert result == "FAIL"


def test_positive_with_typed_rejection_fail(tmp_path):
    m = _positive_manifest(tmp_path)
    result, notes = ar.decide(m, _rejected())
    assert result == "FAIL"
    assert any("rejects everything" in n for n in notes)


def test_positive_with_uncoded_rejection_fail(tmp_path):
    m = _positive_manifest(tmp_path)
    result, notes = ar.decide(m, ar.UncodedRejection(info="timeout"))
    assert result == "FAIL"


# ---------------------------------------------------------------- execute

def test_execute_typed_rejection():
    if AuthorityCoercionRejected is None:
        pytest.skip("Track A2 emission layer absent")
    def fn(_input):
        raise AuthorityCoercionRejected(
            code="UNAPPROVED_ACTION", fail_closed_state="NO_EXECUTION",
            triggered_codes=["UNAPPROVED_ACTION"], reason="t")
    outcome = ar.execute(fn, {}, timeout_s=5)
    assert isinstance(outcome, ar.Rejected)
    assert outcome.code == "UNAPPROVED_ACTION"
    assert outcome.fail_closed_state == "NO_EXECUTION"


def test_execute_uncoded_exception():
    def fn(_input):
        raise ValueError("bare failure")
    outcome = ar.execute(fn, {}, timeout_s=5)
    assert isinstance(outcome, ar.UncodedRejection)
    assert "ValueError" in outcome.info


def test_execute_success_artifact():
    outcome = ar.execute(lambda _i: {"k": "v"}, {}, timeout_s=5)
    assert isinstance(outcome, ar.Succeeded)
    assert outcome.artifact == {"k": "v"}


def test_execute_success_non_dict_coerced():
    outcome = ar.execute(lambda _i: None, {}, timeout_s=5)
    assert isinstance(outcome, ar.Succeeded)
    assert outcome.artifact == {}


def test_execute_timeout():
    def fn(_input):
        time.sleep(30)
    outcome = ar.execute(fn, {}, timeout_s=1)
    assert isinstance(outcome, ar.UncodedRejection)
    assert outcome.info == "timeout"


# ---------------------------------------------------------------- receipts

def test_receipt_seal_and_verify(tmp_path):
    m = ar.load_manifest(_write_manifest(tmp_path))
    r = ar.AuthQualificationReceipt(
        schema=ar.RECEIPT_SCHEMA, invariant_id=m.invariant_id,
        attack_id=m.attack_id, kind=m.kind, result="PASS",
        candidate_head=m.target_head, candidate_tree=m.target_tree,
        contract_id=m.target_contract_id, kernel_revision=None,
        source_type="AMBIGUOUS_INTENT", target_type="EXECUTABLE_AUTHORITY",
        expected_failure_code=m.expected_failure_code,
        observed_failure_code="AMBIGUOUS_ACCEPTANCE_CONDITION",
        observed_failure_codes=("AMBIGUOUS_ACCEPTANCE_CONDITION",),
        expected_fail_closed_state="NO_EXECUTION",
        observed_fail_closed_state="NO_EXECUTION",
        notes=(),
    ).sealed()
    assert r.evidence_receipt_hash
    assert r.verify()
    tampered = replace(r, result="FAIL")
    assert not tampered.verify()


# ---------------------------------------------------------------- identity

def test_capture_candidate_real_repo():
    head, tree, dirty = ar.capture_candidate(Path(__file__).resolve().parents[2])
    assert len(head) == 40 and len(tree) == 40
    assert isinstance(dirty, bool)


def test_kernel_revision_absent_returns_none():
    krev = ar.kernel_revision()
    assert krev is None or (isinstance(krev, str) and len(krev) == 64)
