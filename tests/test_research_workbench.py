import json
from pathlib import Path
import pytest
from unittest.mock import patch
from residual import research

def test_get_experiment_exact():
    c={"experiments":[{"id":"M6-X"}]}
    assert research.get_experiment("M6-X",c)["id"]=="M6-X"

def test_missing_experiment_fails_closed():
    with pytest.raises(ValueError): research.get_experiment("missing",{"experiments":[]})

def test_duplicate_experiment_fails_closed():
    with pytest.raises(ValueError): research.get_experiment("x",{"experiments":[{"id":"x"},{"id":"x"}]})

def test_current_detects_cache_tamper(tmp_path,monkeypatch):
    monkeypatch.setattr(research,"state_root",lambda:tmp_path)
    commit="abc"; d=tmp_path/"catalogs"/commit; d.mkdir(parents=True)
    raw=b'{"schema_version":1,"experiments":[]}\n'; (d/"catalog.json").write_bytes(raw)
    (tmp_path/"current.json").write_text(json.dumps({"commit":commit,"branch":"x","catalog_sha256":"0"*64}))
    with pytest.raises(ValueError): research.current()

def test_sync_uses_exact_http_fallback_outside_git(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "state_root", lambda: tmp_path)
    raw = b'{"schema_version":1,"experiments":[{"id":"M6-WB-001"}]}\n'
    with patch("residual.research.repo_root", side_effect=RuntimeError("not a checkout")), \
         patch("residual.research._http_catalog", return_value=("a" * 40, raw)):
        catalog, commit = research.sync()
    assert commit == "a" * 40
    assert catalog["experiments"][0]["id"] == "M6-WB-001"
    cached, cached_commit = research.current()
    assert cached_commit == commit
    assert cached == catalog

def test_sync_rejects_duplicate_experiment_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "state_root", lambda: tmp_path)
    raw = b'{"schema_version":1,"experiments":[{"id":"M6-X"},{"id":"M6-X"}]}\n'
    with patch("residual.research.repo_root", side_effect=RuntimeError("not a checkout")), \
         patch("residual.research._http_catalog", return_value=("b" * 40, raw)):
        with pytest.raises(ValueError, match="unique"):
            research.sync()
