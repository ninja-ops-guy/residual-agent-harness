"""Bundled measurement data is candidate-bound; never a runtime-code substitute."""
import hashlib
import json
from pathlib import Path

import pytest

from residual import authority_kernel as ak


def install_fixture(root):
    folder = root / "residual" / "_authority_inputs"
    folder.mkdir(parents=True)
    hashes = {}
    for rel, name in ak._PACKAGED_INPUT_NAMES.items():
        content = (ak.REPO_ROOT / rel).read_bytes()
        (folder / name).write_bytes(content)
        hashes[rel] = hashlib.sha256(content).hexdigest()
    (folder / "manifest.json").write_text(json.dumps({"schema": "residual.authority-inputs.v1", "sha256": hashes}))
    return folder


def test_installed_and_source_inputs_produce_identical_revision(tmp_path, monkeypatch):
    expected = ak.revision()
    folder = install_fixture(tmp_path)
    for rel in ak.KERNEL_MODULES:
        if rel not in ak._PACKAGED_INPUT_NAMES:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ak.REPO_ROOT / rel).read_bytes())
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    assert ak.revision() == expected
    assert ak.spec_path() == folder / ak.SPEC_FILENAME
    # Root-level decoys must not replace the explicitly selected packaged inputs.
    (tmp_path / ak.SPEC_FILENAME).write_text("wrong root spec")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/check_maintainer_approval.py").write_text("wrong root gate")
    assert ak.revision() == expected
    # Real runtime code remains part of measurement, not a bundled copy.
    runtime = tmp_path / ak.KERNEL_MODULES[0]
    runtime.write_bytes(runtime.read_bytes() + b"\n# changed runtime\n")
    assert ak.revision() != expected


@pytest.mark.parametrize("filename", ["AUTH_INVARIANTS.md", "check_maintainer_approval.py", "manifest.json"])
def test_missing_packaged_input_has_no_root_fallback(tmp_path, monkeypatch, filename):
    folder = install_fixture(tmp_path)
    (tmp_path / ak.SPEC_FILENAME).write_text("decoy fallback")
    (folder / filename).unlink()
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        ak.spec_path()


def test_tampered_input_rejected(tmp_path, monkeypatch):
    folder = install_fixture(tmp_path)
    (folder / ak.SPEC_FILENAME).write_text("tampered")
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        ak.spec_path()


def test_duplicate_manifest_key_rejected(tmp_path, monkeypatch):
    folder = install_fixture(tmp_path)
    manifest = folder / "manifest.json"
    manifest.write_text(manifest.read_text().replace('{"schema":', '{"schema":"decoy","schema":', 1))
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        ak.spec_path()


def test_packaged_resource_symlink_rejected(tmp_path, monkeypatch):
    folder = install_fixture(tmp_path)
    spec = folder / ak.SPEC_FILENAME
    other = tmp_path / "other.md"
    other.write_bytes(spec.read_bytes())
    spec.unlink()
    spec.symlink_to(other)
    monkeypatch.setattr(ak, "REPO_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        ak.spec_path()
