from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_site_run_command_matches_cli_contract():
    site = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    command = "residual run examples/incident/task.json --config examples/demo.toml"
    assert command in site
    assert "residual run examples/demo.toml --json" not in site
    assert "residual run examples/demo.toml</code>" not in site


def test_current_status_does_not_present_historical_sha_as_live_main():
    status = (ROOT / "docs" / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    assert "Live-state rule" in status
    assert "Historical snapshot" in status
    assert "Current `main` is **`4608afab" not in status
