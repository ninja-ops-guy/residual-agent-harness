from __future__ import annotations

from scripts.qualification_active_workload import run_campaign


def test_active_workload_campaign_includes_real_repair_restart_integration_and_export(tmp_path):
    report = run_campaign(cycles=2, root=tmp_path / "station")
    assert report["result"] == "PASS", report
    assert report["cycles_completed"] == 2
    assert all(record["repair_attempt"] >= 2 for record in report["records"])
    assert all(record["events"] > 0 for record in report["records"])
