"""Track A3: authority kernel revision identity."""
import pytest

from residual import authority_kernel as ak


def test_kernel_modules_all_exist():
    for rel in ak.KERNEL_MODULES:
        assert (ak.REPO_ROOT / rel).is_file(), f"kernel module missing: {rel}"


def test_revision_is_deterministic_64_hex():
    r1 = ak.revision()
    r2 = ak.revision()
    assert r1 == r2
    assert len(r1) == 64 and all(c in "0123456789abcdef" for c in r1)


def test_revision_sensitive_to_spec(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("spec A")
    b.write_text("spec B")
    assert ak.revision(spec=a) != ak.revision(spec=b)


def test_revision_sensitive_to_kernel_content(tmp_path, monkeypatch):
    # Same spec, different kernel bytes -> different revision.
    mod = tmp_path / "mod.py"
    mod.write_text("x = 1\n")
    monkeypatch.setattr(ak, "KERNEL_MODULES", ("mod.py",))
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("spec")
    r1 = ak.revision(spec=spec)
    mod.write_text("x = 2\n")
    r2 = ak.revision(spec=spec)
    assert r1 != r2


def test_missing_module_raises_not_skips(tmp_path, monkeypatch):
    monkeypatch.setattr(ak, "KERNEL_MODULES", ("nope.py",))
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("spec")
    with pytest.raises(FileNotFoundError):
        ak.revision(spec=spec)


def test_missing_spec_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ak.revision(spec=tmp_path / "nope.md")


def test_spec_path_env_override(tmp_path, monkeypatch):
    spec = tmp_path / "custom.md"
    spec.write_text("custom spec")
    monkeypatch.setenv(ak.SPEC_ENV_VAR, str(spec))
    assert ak.spec_path() == spec
    # And revision() honors it.
    r = ak.revision()
    assert len(r) == 64


def test_receipt_carries_kernel_revision():
    from residual.core import digest
    from residual.receipts import StationReceipt
    from residual.verifier import CheckResult

    krev = ak.revision()
    receipt = StationReceipt(
        task_id="task-k", cache_key=digest("c"), value_hash=digest("v"),
        verifier_name="mechanical:unit",
        verifier_revision=digest("r"), verdict=CheckResult.PASS,
        kernel_revision=krev,
    )
    assert receipt.payload()["kernel_revision"] == krev
    # The kernel revision is inside the integrity domain, not alongside it.
    assert receipt.receipt_hash != StationReceipt(
        task_id="task-k", cache_key=digest("c"), value_hash=digest("v"),
        verifier_name="mechanical:unit",
        verifier_revision=digest("r"), verdict=CheckResult.PASS,
        kernel_revision="0" * 64,
    ).receipt_hash
    # Round-trip through the envelope preserves it.
    import json
    assert StationReceipt.from_json(json.dumps(receipt.to_dict())) == receipt


def test_legacy_v2_envelope_still_verifies():
    # A v2 envelope (no kernel_revision) deserializes with an explicitly
    # unbound kernel_revision ("") and still verifies its own hash.
    from residual.core import digest
    from residual.receipts import StationReceipt, RECEIPT_SCHEMA_V2
    from residual.verifier import CheckResult

    receipt = StationReceipt(
        task_id="task-old", cache_key=digest("c"), value_hash=digest("v"),
        verifier_name="mechanical:unit",
        verifier_revision=digest("r"), verdict=CheckResult.PASS,
        kernel_revision="0" * 64,
    )
    object.__setattr__(receipt, "_schema_version", RECEIPT_SCHEMA_V2)
    envelope = receipt.to_dict()
    assert "kernel_revision" not in envelope["payload"]
    back = StationReceipt.from_dict(envelope)
    assert back.kernel_revision == ""
    assert back.receipt_hash == envelope["receipt_hash"]
