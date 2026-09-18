from residual.experiments.transport_faults import (
    SCENARIOS,
    run_mesh_transport_fault_benchmark,
)


def test_transport_fault_scenarios_converge_after_verified_catchup():
    report=run_mesh_transport_fault_benchmark(
        messages=12,
        scenarios=("clean","duplicate","reverse","gap","partition"),
        repeats=1,
    )
    assert report["schema_version"]=="residual.mesh-transport-fault-experiment.v1"
    assert report["kind"]=="mesh-delivery-faults"
    assert report["simulation"] is True
    assert {row["scenario"] for row in report["summary"]}==set(SCENARIOS)
    assert all(row["all_converged"] for row in report["summary"])
    assert all(row["all_replays_idempotent"] for row in report["summary"])


def test_duplicate_and_reorder_faults_are_detected_before_catchup():
    report=run_mesh_transport_fault_benchmark(
        messages=8,
        scenarios=("duplicate","reverse"),
        repeats=1,
    )
    runs={row["scenario"]:row for row in report["runs"]}
    assert runs["duplicate"]["pre_sync_rejected"]>0
    assert runs["reverse"]["pre_sync_rejected"]>0
    assert runs["duplicate"]["converged"] is True
    assert runs["reverse"]["converged"] is True


def test_partition_requires_full_verified_history_replay():
    report=run_mesh_transport_fault_benchmark(
        messages=7,
        scenarios=("partition",),
        repeats=1,
    )
    run=report["runs"][0]
    assert run["scheduled_deliveries"]==0
    assert run["pre_sync_accepted"]==0
    assert run["pre_sync_message_count"]==0
    assert run["sync_appended"]==7
    assert run["replay_idempotent"] is True


def test_transport_fault_hash_binds_scenario_set():
    a=run_mesh_transport_fault_benchmark(
        messages=2,scenarios=("clean",),repeats=1
    )
    b=run_mesh_transport_fault_benchmark(
        messages=2,scenarios=("partition",),repeats=1
    )
    assert a["benchmark_hash"]!=b["benchmark_hash"]
