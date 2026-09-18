from residual.experiments.straggler import run_straggler_benchmark


def test_straggler_benchmark_registers_all_workers_and_integrates():
    report=run_straggler_benchmark(
        latencies_ms=(1.0,2.0,10.0),
        tasks=6,
        repeats=1,
    )
    assert report["schema_version"]=="residual.distributed-straggler-experiment.v1"
    assert report["kind"]=="station-heterogeneous-workers"
    assert report["simulation"] is True
    run=report["runs"][0]
    assert run["all_integrated"] is True
    assert run["registered_worker_instances"]==3
    assert sum(item["tasks"] for item in run["distribution"].values())==6
    assert run["workers_used"]>=1
    assert run["candidate_wall_ms"]>0
    assert run["full_workflow_ms"]>=run["candidate_wall_ms"]
    assert run["greedy_synthetic_floor_ms"]>0
    assert run["worker_inference_elapsed_ms"]>=0
    assert report["summary"]["registered_worker_instances_min"]==3
    assert report["summary"]["all_integrated"] is True
    assert "Task-share differences are observations" in report["claim_boundary"]


def test_straggler_distribution_is_measurement_not_acceptance_threshold():
    report=run_straggler_benchmark(
        latencies_ms=(0.0,0.0,5.0),
        tasks=3,
        repeats=1,
    )
    summary=report["summary"]
    assert 0 <= summary["fastest_worker_task_share_median"] <= 1
    assert 0 <= summary["slowest_worker_task_share_median"] <= 1
    assert summary["workers_used_min"]>=1
    assert summary["all_integrated"] is True


def test_straggler_benchmark_hash_binds_latency_profile():
    a=run_straggler_benchmark(latencies_ms=(0.0,),tasks=1,repeats=1)
    b=run_straggler_benchmark(latencies_ms=(1.0,),tasks=1,repeats=1)
    assert a["benchmark_hash"]!=b["benchmark_hash"]
