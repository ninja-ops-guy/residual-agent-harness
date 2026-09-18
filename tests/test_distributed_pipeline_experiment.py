from residual.experiments.pipeline import run_station_pipeline_benchmark


def test_dependency_pipeline_reaches_full_integration():
    report = run_station_pipeline_benchmark(
        worker_counts=(1, 2),
        width=2,
        depth=2,
        work_ms=5,
        repeats=1,
    )
    assert report["schema_version"] == "residual.distributed-pipeline-experiment.v1"
    assert report["kind"] == "station-dependency-pipeline"
    assert report["simulation"] is True
    assert report["workload"]["tasks"] == 4
    assert len(report["runs"]) == 2

    for run in report["runs"]:
        assert run["all_integrated"] is True
        assert run["integration_count"] == 4
        assert run["reported_worker_calls"] == 4
        assert sum(run["worker_distribution"].values()) == 4
        assert run["wall_ms"] > 0
        assert run["throughput_tasks_s"] > 0
        assert len(run["event_head"]) == 64
        assert run["critical_path_work_ms"] == 10
        assert run["serial_worker_work_ms"] == 20

    assert {row["workers"] for row in report["summary"]} == {1, 2}
    assert all(row["all_integrated"] for row in report["summary"])
    assert "real Station HTTP worker lease/submit path" in report["claim_boundary"]


def test_pipeline_benchmark_hash_binds_graph_shape():
    narrow = run_station_pipeline_benchmark(
        worker_counts=(1,), width=1, depth=2, work_ms=0, repeats=1
    )
    wide = run_station_pipeline_benchmark(
        worker_counts=(1,), width=2, depth=1, work_ms=0, repeats=1
    )
    assert narrow["benchmark_hash"] != wide["benchmark_hash"]


def test_pipeline_does_not_assert_speedup_as_acceptance_condition():
    report = run_station_pipeline_benchmark(
        worker_counts=(1, 2), width=2, depth=1, work_ms=0, repeats=1
    )
    # CI host timing is evidence to inspect, not a flaky pass/fail oracle.
    assert all("speedup_vs_min_workers" in row for row in report["summary"])
    assert all(row["all_integrated"] for row in report["summary"])
