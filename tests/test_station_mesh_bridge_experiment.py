from residual.experiments.bridge import run_station_mesh_bridge_benchmark


def test_station_mesh_bridge_benchmark_preserves_authority_and_convergence():
    report=run_station_mesh_bridge_benchmark(member_counts=(2,),repeats=1)
    assert report["schema_version"]=="residual.station-mesh-bridge-experiment.v1"
    assert report["kind"]=="station-mesh-observability-bridge"
    run=report["runs"][0]
    assert run["members"]==2
    assert run["station_events"]==run["mirrored_messages"]
    assert run["mirror_messages_s"]>0
    assert run["mirror_replica_updates_s"]>0
    assert run["peer_note_roundtrip_ms"]>=0
    assert run["converged"] is True
    assert run["station_tasks_remained_integrated"] is True
    assert len(run["mesh_head"])==64
    assert len(run["station_event_head"])==64
    assert report["summary"][0]["all_converged"] is True
    assert report["summary"][0]["station_authority_preserved"] is True
    assert "does not measure physical transport" in report["claim_boundary"]
