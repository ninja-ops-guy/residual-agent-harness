from residual.experiments.matrix import run_experiment_matrix


def test_matrix_composes_independent_pipeline_and_recovery_evidence():
    report=run_experiment_matrix(
        worker_counts=(1,),
        latencies_ms=(0.0,),
        independent_tasks=2,
        pipeline_width=1,
        pipeline_depth=1,
        repeats=1,
        include_recovery=True,
    )
    assert report["schema_version"]=="residual.distributed-experiment-matrix.v1"
    assert report["simulation"] is True
    assert len(report["cells"])==1
    cell=report["cells"][0]
    assert cell["independent"]["summary"][0]["all_integrated"] is True
    assert cell["pipeline"]["summary"][0]["all_integrated"] is True
    assert cell["recovery"]["summary"]["all_recovered_and_integrated"] is True
    assert cell["derived"]["independent_best_workers"]==1
    assert cell["derived"]["pipeline_best_workers"]==1
    assert len(report["matrix_hash"])==64


def test_matrix_hash_changes_when_latency_grid_changes():
    one=run_experiment_matrix(
        worker_counts=(1,),latencies_ms=(0.0,),independent_tasks=1,
        pipeline_width=1,pipeline_depth=1,repeats=1,include_recovery=False,
    )
    two=run_experiment_matrix(
        worker_counts=(1,),latencies_ms=(1.0,),independent_tasks=1,
        pipeline_width=1,pipeline_depth=1,repeats=1,include_recovery=False,
    )
    assert one["matrix_hash"]!=two["matrix_hash"]
