from residual.experiments.distributed import (
    SCHEMA,
    run_mesh_protocol_benchmark,
    run_station_distributed_benchmark,
)


def test_mesh_protocol_benchmark_preserves_verified_head():
    report = run_mesh_protocol_benchmark(messages=20, repeats=1)
    assert report["schema_version"] == SCHEMA
    assert report["kind"] == "mesh-protocol"
    assert report["simulation"] is False
    assert report["runs"][0]["messages"] == 20
    assert report["runs"][0]["produce_messages_s"] > 0
    assert report["runs"][0]["catchup_messages_s"] > 0
    assert report["summary"]["verified_join_ms"] >= 0
    assert "physical LAN" in report["claim_boundary"]


def test_station_distributed_benchmark_runs_real_worker_api_to_integration():
    report = run_station_distributed_benchmark(
        worker_counts=(1, 2),
        tasks=4,
        work_ms=5,
        repeats=1,
    )
    assert report["schema_version"] == SCHEMA
    assert report["kind"] == "station-distributed-worker"
    assert report["simulation"] is True
    assert len(report["runs"]) == 2

    for run in report["runs"]:
        assert run["all_integrated"] is True
        assert run["reported_worker_calls"] == 4
        assert sum(run["worker_distribution"].values()) == 4
        assert run["candidate_wall_ms"] > 0
        assert run["full_workflow_ms"] >= run["candidate_wall_ms"]
        assert run["events"] > 0
        assert len(run["event_head"]) == 64

    assert {row["workers"] for row in report["summary"]} == {1, 2}
    assert all(row["all_integrated"] for row in report["summary"])
    assert "real Station HTTP worker API" in report["claim_boundary"]


def test_station_benchmark_hash_is_configuration_bound():
    one = run_station_distributed_benchmark(
        worker_counts=(1,), tasks=2, work_ms=0, repeats=1
    )
    two = run_station_distributed_benchmark(
        worker_counts=(1,), tasks=3, work_ms=0, repeats=1
    )
    assert one["benchmark_hash"] != two["benchmark_hash"]
