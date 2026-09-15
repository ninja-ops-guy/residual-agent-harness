import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("application_preflight", ROOT / "scripts/application_preflight.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_six_domains_compile_and_bind_without_accepting():
    report = app.run(ROOT / "examples/application-preflight", "1" * 40)
    assert len(report["applications"]) == 6
    assert not report["confirmatory_eligible"]
    assert report["model_calls"] == 0
    for case in report["applications"]:
        assert case["candidate_assessments"] == {"good": "PASS", "broken": "FAIL", "missing": "UNKNOWN"}
        assert case["station_acceptance"] == "NOT_REQUESTED"
        assert case["integration_receipt"] is None
        assert all(c["contract"]["execution_plan_hash"] == case["plan"]["graph_hash"]
                   for c in case["contracts"])


def test_candidate_text_cannot_gain_authority():
    case = app.load_cases(ROOT / "examples/application-preflight")[0]
    candidate = copy.deepcopy(case["expected"])
    candidate["capabilities"] = ["git.push", "git.merge"]
    assert app.assess(case, candidate) == "FAIL"
    assert app.assess(case, None) == "UNKNOWN"


def test_changed_fixture_is_rejected(tmp_path):
    source = ROOT / "examples/application-preflight"
    manifest = json.loads((source / "manifest.json").read_text())
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    first = manifest["cases"][0]["file"]
    (tmp_path / first).write_text((source / first).read_text() + " ")
    with pytest.raises(ValueError, match="hash mismatch"):
        app.load_cases(tmp_path)


def test_fixture_path_escape_is_rejected(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "schema_version": "residual.application-fixtures.v1",
        "cases": [{"file": "../escape.json", "sha256": "0" * 64}],
    }))
    with pytest.raises(ValueError, match="basename"):
        app.load_cases(tmp_path)


def test_reproduction_is_deterministic_and_different_source_changes_report():
    source = ROOT / "examples/application-preflight"
    assert app.run(source, "1" * 40) == app.run(source, "1" * 40)
    assert app.run(source, "1" * 40)["report_hash"] != app.run(source, "2" * 40)["report_hash"]
