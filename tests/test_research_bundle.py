import json
from pathlib import Path
import pytest
from residual.research_bundle import MetricSpec, ResearchBundleError, freeze_bundle, json_pointer, render_metric_table, verify_bundle

def fixture(tmp_path: Path):
    (tmp_path / "results.json").write_text(json.dumps({"trials": 50, "nested": {"false_accepts": 0}})); (tmp_path / "recovery.json").write_text(json.dumps({"ok": True, "scenarios": [1,2,3]}))
    metrics=[MetricSpec("Trials","results.json","/trials","runs"),MetricSpec("False accepts","results.json","/nested/false_accepts","cases"),MetricSpec("Recovery scenarios","recovery.json","/scenarios","")]
    return freeze_bundle(tmp_path,experiment_id="study-1",source_commit="0123456789abcdef",artifacts=["recovery.json","results.json"],metrics=metrics,metadata={"seed":7})

def test_freeze_is_deterministic_and_sorted(tmp_path):
    first=fixture(tmp_path); second=fixture(tmp_path); assert first==second; assert [r["path"] for r in first["artifacts"]]==["recovery.json","results.json"]; assert verify_bundle(tmp_path,first)["verified"] is True

def test_artifact_mutation_is_detected(tmp_path):
    manifest=fixture(tmp_path); (tmp_path/"results.json").write_text('{"trials":51,"nested":{"false_accepts":0}}')
    with pytest.raises(ResearchBundleError,match="artifact integrity mismatch"): verify_bundle(tmp_path,manifest)

def test_manifest_mutation_is_detected_before_artifact_checks(tmp_path):
    manifest=fixture(tmp_path); manifest["metrics"][0]["value"]=999
    with pytest.raises(ResearchBundleError,match="manifest bundle hash mismatch"): verify_bundle(tmp_path,manifest)

def test_metric_is_recomputed_from_frozen_source(tmp_path):
    import hashlib
    from residual.research_bundle import canonical_json
    manifest=fixture(tmp_path); manifest["metrics"][0]["value"]=999; unsigned=dict(manifest); unsigned.pop("bundle_sha256"); manifest["bundle_sha256"]=hashlib.sha256(canonical_json(unsigned).encode()).hexdigest()
    with pytest.raises(ResearchBundleError,match="metric value drift"): verify_bundle(tmp_path,manifest)

def test_path_escape_and_missing_source_rejected(tmp_path):
    outside=tmp_path.parent/"outside.json"; outside.write_text("{}")
    with pytest.raises(ResearchBundleError,match="escapes"): freeze_bundle(tmp_path,experiment_id="x",source_commit="1234567",artifacts=["../outside.json"])
    (tmp_path/"results.json").write_text("{}")
    with pytest.raises(ResearchBundleError,match="not a frozen artifact"): freeze_bundle(tmp_path,experiment_id="x",source_commit="1234567",artifacts=["results.json"],metrics=[MetricSpec("x","other.json","/x")])

def test_json_pointer_and_table_bind_evidence(tmp_path):
    manifest=fixture(tmp_path); assert json_pointer({"a/b":{"~x":3}},"/a~1b/~0x")==3; table=render_metric_table(manifest); assert "False accepts" in table; assert "results.json" in table; assert manifest["artifacts"][1]["sha256"][:12] in table
