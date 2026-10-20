"""Regression tests for the fail-closed corpus manifest checker.

These tests validate the frozen preparation manifest and exercise rejection
paths. They produce no experiment results and make no model calls.
"""
import copy
import json
from pathlib import Path

import pytest

from scripts.check_corpus_manifest import check_manifest, main

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/corpus/manifest.v1.json"


def write(tmp_path, mutate, *, rehash=True):
    from residual.core import digest
    manifest = json.loads(MANIFEST.read_text())
    mutate(manifest)
    if rehash:
        # Simulate an attacker who rewrites the manifest AND its self-hash;
        # item-level bindings must still fail closed.
        manifest["manifest_sha256"] = digest(
            {k: v for k, v in manifest.items() if k != "manifest_sha256"})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_committed_manifest_passes():
    report = check_manifest(MANIFEST, ROOT)
    assert report["status"] == "PASS"
    assert report["results_produced"] is False
    assert report["held_out"] > 0 and report["development"] > 0


def test_cli_exit_codes(tmp_path):
    assert main(["--manifest", str(MANIFEST), "--root", str(ROOT)]) == 0
    bad = write(tmp_path, lambda m: m["items"][0].update(family="tampered"))
    assert main(["--manifest", str(bad), "--root", str(ROOT)]) == 2


@pytest.mark.parametrize("field", ["content_sha256", "fault_label", "split"])
def test_hash_and_field_tamper_fails(tmp_path, field):
    bad = write(tmp_path, lambda m: m["items"][1].update(
        **{field: "tampered" if field != "fault_label" else "bogus_fault"}))
    with pytest.raises(ValueError):
        check_manifest(bad, ROOT)


def test_manifest_self_hash_tamper_fails(tmp_path):
    bad = write(tmp_path, lambda m: m.update(status="launch_ready"), rehash=False)
    with pytest.raises(ValueError, match="manifest_sha256|claim"):
        check_manifest(bad, ROOT)


def test_split_leakage_fails(tmp_path):
    def leak(m):
        held_out = m["splits"]["held_out"]["task_ids"]
        m["splits"]["development"]["task_ids"].append(held_out[0])
    bad = write(tmp_path, leak)
    with pytest.raises(ValueError, match="leakage|contradicts"):
        check_manifest(bad, ROOT)


def test_split_reassignment_fails(tmp_path):
    def reassign(m):
        moved = m["splits"]["held_out"]["task_ids"].pop()
        m["splits"]["development"]["task_ids"].append(moved)
    bad = write(tmp_path, reassign)
    with pytest.raises(ValueError, match="contradicts"):
        check_manifest(bad, ROOT)


def test_missing_provenance_fails(tmp_path):
    def strip(m):
        del m["items"][0]["provenance"]["public_exposure"]
    bad = write(tmp_path, strip)
    with pytest.raises(ValueError, match="provenance"):
        check_manifest(bad, ROOT)


def test_unknown_or_dropped_task_fails(tmp_path):
    bad = write(tmp_path, lambda m: m["items"].append(copy.deepcopy(m["items"][0])))
    with pytest.raises(ValueError, match="duplicate"):
        check_manifest(bad, ROOT)
    bad = write(tmp_path, lambda m: m["items"].pop())
    with pytest.raises(ValueError, match="omits"):
        check_manifest(bad, ROOT)


def test_arm_and_workload_binding_fails_on_tamper(tmp_path):
    bad = write(tmp_path, lambda m: m["arms"][0].update(config_sha256="0" * 64))
    with pytest.raises(ValueError, match="config hash"):
        check_manifest(bad, ROOT)
    bad = write(tmp_path, lambda m: m["frozen_workload"].update(workload_sha256="0" * 64))
    with pytest.raises(ValueError, match="workload hash"):
        check_manifest(bad, ROOT)
