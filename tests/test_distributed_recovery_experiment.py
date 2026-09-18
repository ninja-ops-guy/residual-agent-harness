from residual.experiments.recovery import run_station_recovery_benchmark


def test_verifier_failure_is_repaired_and_integrated_through_worker_api():
    report = run_station_recovery_benchmark(
        bad_ms=0,
        good_ms=0,
        repeats=1,
    )
    assert report["schema_version"] == "residual.distributed-recovery-experiment.v1"
    assert report["kind"] == "station-verifier-failure-repair"
    assert report["simulation"] is True

    run = report["recovery_runs"][0]
    assert run["all_integrated"] is True
    assert run["repair_findings_retained"] is True
    assert run["attempts"] == 2
    assert run["calls"] == 2
    assert len(run["event_head"]) == 64
    assert run["event_count"] > 0

    summary = report["summary"]
    assert summary["all_recovered_and_integrated"] is True
    assert summary["all_failures_retained_findings"] is True
    assert summary["attempts_per_recovery"] == [2]
    assert summary["calls_per_recovery"] == [2]
    assert "does not simulate a crashed process" in report["claim_boundary"]


def test_recovery_benchmark_retains_baseline_and_penalty_measurement():
    report = run_station_recovery_benchmark(
        bad_ms=2,
        good_ms=2,
        repeats=1,
    )
    assert len(report["baseline_runs"]) == 1
    assert len(report["recovery_runs"]) == 1
    assert report["summary"]["baseline_full_median_ms"] > 0
    assert report["summary"]["recovery_full_median_ms"] > 0
    assert "recovery_penalty_ms" in report["summary"]
    assert "recovery_penalty_ratio" in report["summary"]
