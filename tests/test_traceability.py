"""Traceability tests (Swarm 1, tracks A+P).

These tests MUST keep implementation-status.yaml, the generated
docs/status/IMPLEMENTATION_STATUS.md and scripts/status_check.py
consistent with each other and with the repository on disk.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "implementation-status.yaml"
SCRIPT = ROOT / "scripts" / "status_check.py"
GENERATED = ROOT / "docs" / "status" / "IMPLEMENTATION_STATUS.md"

sys.path.insert(0, str(ROOT / "scripts"))
import status_check  # noqa: E402

REQUIRED_FAMILIES = {
    "SPEC-001", "SPEC-002", "SPEC-003", "SPEC-004", "SPEC-005", "SPEC-006",
    "SPEC-007", "SPEC-008", "NETOPS", "SECOPS", "MODULE", "VRB", "REG",
    "HITL", "MEM", "TRJ", "TUI", "GAP1", "GAP2", "GAP3", "GAP4", "GAP5",
    "GAP6", "ECO", "PROD", "PQC", "MAI", "FMV", "APC", "FED", "MESH",
    "STUDIO", "M2", "M3", "M4", "EVAL", "CP", "N9", "T10",
}


@pytest.fixture(scope="module")
def manifest():
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_schema_valid(manifest):
    status_check.validate_manifest(manifest, source="implementation-status.yaml")


def test_manifest_covers_all_required_families(manifest):
    present = {f["family"] for f in manifest["families"]}
    missing = REQUIRED_FAMILIES - present
    assert not missing, f"manifest is missing requirement families: {missing}"


def test_manifest_paths_exist(manifest):
    problems = status_check.check_manifest_paths(manifest, ROOT)
    assert not problems, "manifest references missing paths: " + "; ".join(problems)


def test_implemented_families_have_code_and_tests(manifest):
    for fam in manifest["families"]:
        if fam["status"] == "implemented":
            assert fam["code_paths"], fam["family"]
            assert fam["test_paths"], fam["family"]
        if fam["status"] == "not_started":
            assert fam["code_paths"] == [], fam["family"]


def test_status_values_valid(manifest):
    for fam in manifest["families"]:
        assert fam["status"] in status_check.VALID_STATUSES


def test_checker_script_is_executable():
    # The exec bit MUST be set. On filesystems that cannot represent exec
    # bits (some mounted volumes), fall back to the git index mode (100755),
    # which is the source of truth once committed.
    mode = SCRIPT.stat().st_mode
    if not mode & stat.S_IXUSR:
        import subprocess
        entry = subprocess.run(
            ["git", "ls-files", "-s", "scripts/status_check.py"],
            capture_output=True, text=True, check=True,
            cwd=SCRIPT.parent.parent,
        ).stdout.split()[0]
        assert entry == "100755", "status_check.py MUST be executable (git mode 100755)"
    assert SCRIPT.read_text(encoding="utf-8").splitlines()[0].startswith("#!")


def test_generated_doc_is_up_to_date(manifest):
    assert GENERATED.exists(), "run: python3 scripts/status_check.py --generate"
    expected = status_check.render_status_doc(manifest)
    actual = GENERATED.read_text(encoding="utf-8")
    assert actual == expected, (
        "docs/status/IMPLEMENTATION_STATUS.md is stale; regenerate with "
        "python3 scripts/status_check.py --generate")


def test_generated_doc_lists_every_family(manifest):
    text = GENERATED.read_text(encoding="utf-8")
    for fam in manifest["families"]:
        assert fam["family"] in text


def test_historical_documents_are_marked(manifest):
    for rel in ("harness_specs/V040_ASSESSMENT.md", "harness_specs/GAP_ANALYSIS.md"):
        assert rel in manifest["historical_documents"]
        head = (ROOT / rel).read_text(encoding="utf-8")[:600]
        assert "HISTORICAL SNAPSHOT" in head, f"{rel} lacks the historical banner"


def test_checker_passes_on_repo():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _make_tree(tmp_path: Path, readme_body: str) -> Path:
    """Build a minimal fake repo tree with the real manifest."""
    (tmp_path / "implementation-status.yaml").write_text(
        MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "README.md").write_text(readme_body, encoding="utf-8")
    # create every path the manifest references so path checks pass
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for fam in data["families"]:
        for rel in [fam["spec"], *fam["code_paths"], *fam["test_paths"]]:
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
    for rel in data["historical_documents"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    return tmp_path


def test_checker_flags_stale_not_implemented_claim(tmp_path):
    root = _make_tree(
        tmp_path,
        "# Demo\n\nThe GoalSpec layer is not implemented yet.\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True, text=True)
    assert result.returncode == 1
    assert "SPEC-001" in result.stderr


def test_checker_ignores_historical_documents(tmp_path):
    root = _make_tree(tmp_path, "# Demo\n\nEverything is fine here.\n")
    # plant a stale claim inside a historical snapshot; must be skipped
    hist = root / "harness_specs" / "GAP_ANALYSIS.md"
    hist.write_text("has no goal-specification layer, no brake system\n",
                    encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_checker_ignores_partial_and_not_started_families(tmp_path):
    root = _make_tree(
        tmp_path,
        "# Demo\n\nThe mesh transport and soak test are not implemented.\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_generator_is_deterministic(tmp_path):
    root = _make_tree(tmp_path, "# Demo\n")
    first = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--generate"],
        capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    out = root / "docs" / "status" / "IMPLEMENTATION_STATUS.md"
    one = out.read_text(encoding="utf-8")
    second = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--generate"],
        capture_output=True, text=True)
    assert second.returncode == 0
    assert out.read_text(encoding="utf-8") == one


def test_validate_manifest_rejects_bad_status(manifest):
    bad = {"families": [dict(manifest["families"][0], status="done")]}
    with pytest.raises(status_check.ManifestError):
        status_check.validate_manifest(bad)


def test_validate_manifest_rejects_implemented_without_paths():
    fam = dict(family="X", title="x", spec="s.md", status="implemented",
               code_paths=[], test_paths=[], keywords=[], notes="n")
    with pytest.raises(status_check.ManifestError):
        status_check.validate_manifest({"families": [fam]})
