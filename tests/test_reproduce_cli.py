"""The public CLI must reach offline replay without building a provider harness."""
import json
from pathlib import Path
from unittest.mock import patch

from residual.cli import main


def test_cli_reproduction_is_offline_and_preserves_provenance(tmp_path):
    runs_dir = Path(__file__).resolve().parents[1] / "examples/reproduction"
    output = tmp_path / "report.json"
    with patch("residual.cli.build_harness", side_effect=AssertionError("provider harness forbidden")), \
         patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
        assert main(["reproduce", "synthetic-demo", "--runs-dir", str(runs_dir), "--output", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["run_id"] == "synthetic-demo"
    assert report["publication_ready"] is False


def test_cli_missing_run_fails_closed_without_provider_fallback(tmp_path):
    with patch("residual.cli.build_harness", side_effect=AssertionError("provider harness forbidden")):
        assert main(["reproduce", "missing-run", "--runs-dir", str(tmp_path)]) != 0
