from residual.experiments.lease_recovery import run_station_lease_recovery_benchmark


def test_lease_expiry_recovery_rejects_stale_worker_and_reintegrates():
    report=run_station_lease_recovery_benchmark(work_ms=0,repeats=1)
    assert report["schema_version"]=="residual.distributed-lease-recovery.v1"
    assert report["kind"]=="station-lease-expiry-recovery"
    run=report["recovery_runs"][0]
    assert run["stale_result_rejected"] is True
    assert run["all_integrated"] is True
    assert run["attempts"]==2
    assert run["expired_event_count"]==1
    assert run["expired_worker_expirations"]==1
    assert run["healthy_inference_median_ms"]==0.0
    summary=report["summary"]
    assert summary["all_integrated"] is True
    assert summary["all_stale_results_rejected"] is True
    assert summary["all_expirations_attributed"] is True
    assert summary["attempts"]==[2]
    assert "Only lease time passage is fault-injected" in report["claim_boundary"]


def test_lease_recovery_report_retains_baseline_and_penalty():
    report=run_station_lease_recovery_benchmark(work_ms=1,repeats=1)
    assert len(report["baseline_runs"])==1
    assert len(report["recovery_runs"])==1
    assert report["summary"]["baseline_full_median_ms"]>0
    assert report["summary"]["lease_recovery_full_median_ms"]>0
    assert "lease_recovery_penalty_ms" in report["summary"]
    assert "lease_recovery_penalty_ratio" in report["summary"]
