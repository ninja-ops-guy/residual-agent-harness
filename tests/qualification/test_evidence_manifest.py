from __future__ import annotations

import json
from pathlib import Path

import pytest

from residual.qualification.evidence import EvidenceEnvelope, GateResult, write_envelope
from residual.qualification.failures import FailureClass, FailureObservation, append_failure, load_failures
from residual.qualification.manifest import aggregate_manifest, write_manifest


def envelope(gate: str, result: GateResult = GateResult.PASS, *, commit: str = "a" * 40,
             tree: str = "b" * 40, skips: int = 0, unknowns: int = 0) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        gate_id=gate,
        result=result,
        started_at="2026-09-16T00:00:00Z",
        finished_at="2026-09-16T00:00:01Z",
        source={"commit": commit, "tree": tree, "tracked_source_dirty": False},
        environment={"python": "fixture"},
        skip_count=skips,
        unknown_count=unknowns,
    )


def test_manifest_passes_only_complete_same_revision_pass_evidence(tmp_path: Path):
    paths = []
    for gate in ("deterministic", "stateful", "mutation"):
        path = tmp_path / f"{gate}.json"
        write_envelope(envelope(gate), path)
        paths.append(path)
    artifact = tmp_path / "residual.whl"
    artifact.write_bytes(b"exact artifact")
    manifest = aggregate_manifest(paths, required_gates=("deterministic", "stateful", "mutation"),
                                  artifact_paths=(artifact,))
    assert manifest.result == GateResult.PASS
    assert manifest.missing_gates == []
    assert str(artifact) in manifest.artifact_hashes
    out = write_manifest(manifest, tmp_path / "manifest.json")
    assert json.loads(out.read_text())["result"] == "PASS"


@pytest.mark.parametrize("bad", [GateResult.FAIL, GateResult.UNKNOWN, GateResult.SKIP])
def test_manifest_fails_closed_on_non_pass_required_gate(tmp_path: Path, bad: GateResult):
    p = tmp_path / "gate.json"
    write_envelope(envelope("required", bad), p)
    manifest = aggregate_manifest([p], required_gates=["required"])
    assert manifest.result == GateResult.FAIL
    assert any(f"required={bad.value}" in reason for reason in manifest.reasons)


def test_manifest_fails_closed_on_missing_skip_unknown_and_missing_artifact(tmp_path: Path):
    p = tmp_path / "gate.json"
    write_envelope(envelope("gate", skips=1, unknowns=2), p)
    manifest = aggregate_manifest([p], required_gates=["gate", "missing"],
                                  artifact_paths=[tmp_path / "missing.whl"])
    assert manifest.result == GateResult.FAIL
    assert "missing" in manifest.missing_gates
    assert any("skipped" in r for r in manifest.reasons)
    assert any("UNKNOWN" in r for r in manifest.reasons)
    assert any("missing artifact" in r for r in manifest.reasons)


def test_manifest_rejects_cross_revision_evidence(tmp_path: Path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    write_envelope(envelope("a"), a)
    write_envelope(envelope("b", commit="c" * 40), b)
    with pytest.raises(ValueError, match="one commit/tree"):
        aggregate_manifest([a, b], required_gates=["a", "b"])


def test_failure_ledger_preserves_original_and_linked_rerun(tmp_path: Path):
    path = tmp_path / "failures.jsonl"
    first = FailureObservation("stateful", FailureClass.UNCLASSIFIED, "first failure", {"seed": 9})
    append_failure(path, first)
    rerun = FailureObservation("stateful", FailureClass.TEST_DEFECT, "classified after rerun",
                               {"seed": 9, "rerun": "pass"}, predecessor_id=first.observation_id)
    append_failure(path, rerun)
    rows = load_failures(path)
    assert [row.observation_id for row in rows] == [first.observation_id, rerun.observation_id]
    assert rows[1].predecessor_id == rows[0].observation_id
    assert rows[0].classification == FailureClass.UNCLASSIFIED
    assert rows[1].classification == FailureClass.TEST_DEFECT
