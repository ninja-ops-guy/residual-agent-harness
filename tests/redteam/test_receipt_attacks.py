"""Redteam: receipt forgery, stale receipt replay, dependency poisoning.

Every attack is asserted blocked (ContractError / mismatch) AND recorded
with a FAIL receipt per K-R2.
"""
from __future__ import annotations

import copy
import hashlib

import pytest

from residual.core import ContractError, digest
from residual.receipts import (ReceiptReference, StationReceipt,
                               validate_receipt_graph)
from residual.verifier import CheckResult

from .attacks import ATTACK_REVISION, ATTACK_VERIFIER, attack_receipt


def _genuine_receipt(task_id: str = "task-a", value=("ok",)) -> StationReceipt:
    return StationReceipt(
        task_id=task_id,
        cache_key=hashlib.sha256(f"cache:{task_id}".encode()).hexdigest(),
        value_hash=digest(value),
        verifier_name="mechanical:unit",
        verifier_revision=hashlib.sha256(b"rev1").hexdigest(),
        verdict=CheckResult.PASS,
        engine_name="redteam", engine_version="0.1",
    )


class TestReceiptForgery:
    def test_tampered_payload_rejected(self):
        """Attack: flip the verdict inside an otherwise valid envelope."""
        receipt = _genuine_receipt()
        envelope = receipt.to_dict()
        envelope["payload"]["verdict"] = "pass"
        # attacker recomputes nothing — hash now mismatches
        envelope["payload"]["task_id"] = "task-b"
        with pytest.raises(ContractError):
            StationReceipt.from_dict(envelope)
        record = attack_receipt("atk-forgery-1", "tampered receipt payload")
        assert record.verdict is CheckResult.FAIL

    def test_recomputed_hash_with_bad_fields_rejected(self):
        """Attack: attacker recomputes the hash over an invalid payload."""
        receipt = _genuine_receipt()
        envelope = receipt.to_dict()
        envelope["payload"]["parent_receipts"] = [
            {"task_id": "task-a",  # self-dependency
             "receipt_hash": hashlib.sha256(b"x").hexdigest()}]
        import hashlib as h, json
        payload = envelope["payload"]
        envelope["receipt_hash"] = h.sha256(
            (envelope["schema_version"] + "\n"
             + json.dumps(payload, sort_keys=True, separators=(",", ":"))
             ).encode()).hexdigest()
        with pytest.raises(ContractError):
            StationReceipt.from_dict(envelope)
        assert attack_receipt("atk-forgery-2", "self-dependent receipt").verdict is CheckResult.FAIL

    def test_duplicate_json_key_rejected(self):
        """Attack: parser differential via duplicate JSON keys."""
        receipt = _genuine_receipt()
        text = receipt.to_dict()
        import json
        raw = json.dumps(text)
        forged = raw.replace('"task_id": "task-a"',
                             '"task_id": "task-b", "task_id": "task-a"', 1)
        with pytest.raises(ContractError):
            StationReceipt.from_json(forged)
        assert attack_receipt("atk-forgery-3", "duplicate JSON key").verdict is CheckResult.FAIL

    def test_extra_envelope_field_rejected(self):
        receipt = _genuine_receipt()
        envelope = receipt.to_dict()
        envelope["signature"] = "trust-me"
        with pytest.raises(ContractError):
            StationReceipt.from_dict(envelope)
        assert attack_receipt("atk-forgery-4", "extra envelope field").verdict is CheckResult.FAIL


class TestStaleReceiptReplay:
    def test_wrong_verifier_revision_not_matched(self):
        """Attack: replay a receipt from an old verifier revision."""
        receipt = _genuine_receipt()
        matched = receipt.matches(
            value=("ok",), cache_key=receipt.cache_key,
            verifier_name="mechanical:unit",
            verifier_revision=hashlib.sha256(b"rev2").hexdigest(),  # stale
            parents=())
        assert not matched
        assert attack_receipt("atk-replay-1", "stale verifier revision").verdict is CheckResult.FAIL

    def test_replay_against_different_value(self):
        """Attack: present a genuine PASS receipt for a different artifact."""
        receipt = _genuine_receipt(value=("ok",))
        assert not receipt.matches(
            value=("pwned",), cache_key=receipt.cache_key,
            verifier_name="mechanical:unit",
            verifier_revision=receipt.verifier_revision, parents=())
        assert attack_receipt("atk-replay-2", "receipt replayed for other value").verdict is CheckResult.FAIL

    def test_fail_receipt_never_grants_pass(self):
        """Attack: replay a FAIL receipt hoping it counts as coverage."""
        receipt = _genuine_receipt()
        envelope = receipt.to_dict()
        envelope["payload"]["verdict"] = "fail"
        import hashlib as h, json
        payload = envelope["payload"]
        envelope["receipt_hash"] = h.sha256(
            (envelope["schema_version"] + "\n" +
             json.dumps(payload, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
        replayed = StationReceipt.from_dict(envelope)
        assert replayed.verdict is CheckResult.FAIL
        assert not replayed.matches(
            value=("ok",), cache_key=replayed.cache_key,
            verifier_name="mechanical:unit",
            verifier_revision=replayed.verifier_revision, parents=())
        assert attack_receipt("atk-replay-3", "fail receipt replay").verdict is CheckResult.FAIL


class TestDependencyPoisoning:
    def test_swapped_parent_receipt_rejected(self):
        """Attack: swap a prerequisite receipt for an unrelated one."""
        a = _genuine_receipt("task-a")
        poisoned = _genuine_receipt("task-poison")
        b = StationReceipt(
            task_id="task-b",
            cache_key=hashlib.sha256(b"cache:task-b").hexdigest(),
            value_hash=digest(("b",)),
            verifier_name="mechanical:unit",
            verifier_revision=a.verifier_revision,
            verdict=CheckResult.PASS,
            parent_receipts=(ReceiptReference("task-poison", poisoned.receipt_hash),),
        )
        with pytest.raises(ContractError):
            validate_receipt_graph(
                {"task-a": a, "task-b": b},
                {"task-a": (), "task-b": ("task-a",)})
        assert attack_receipt("atk-poison-1", "swapped prerequisite receipt").verdict is CheckResult.FAIL

    def test_cycle_rejected(self):
        """Attack: cyclic prerequisites to launder provenance."""
        with pytest.raises(ContractError):
            StationReceipt(
                task_id="task-a", cache_key=hashlib.sha256(b"c").hexdigest(),
                value_hash=digest(1), verifier_name="mechanical:unit",
                verifier_revision=hashlib.sha256(b"r").hexdigest(),
                verdict=CheckResult.PASS,
                parent_receipts=(ReceiptReference("task-a", hashlib.sha256(b"h").hexdigest()),))
        assert attack_receipt("atk-poison-2", "self-cycle receipt").verdict is CheckResult.FAIL

    def test_poisoned_artifact_digest_mismatch(self):
        """Attack: substitute artifact bytes after verification."""
        receipt = _genuine_receipt(value=("vetted-bytes",))
        poisoned_value = ("vetted-bytes",)  # attacker claims identical
        assert receipt.matches(
            value=poisoned_value, cache_key=receipt.cache_key,
            verifier_name="mechanical:unit",
            verifier_revision=receipt.verifier_revision, parents=())
        assert not receipt.matches(
            value=("vetted-bytes\x00injected",), cache_key=receipt.cache_key,
            verifier_name="mechanical:unit",
            verifier_revision=receipt.verifier_revision, parents=())
        assert attack_receipt("atk-poison-3", "artifact substitution").verdict is CheckResult.FAIL
