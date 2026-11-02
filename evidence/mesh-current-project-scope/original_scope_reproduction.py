"""Minimal stale-worker project-scope reproduction, without provider execution."""
import json
import os
from pathlib import Path

from residual.core import ContractError, canonical
from residual.station.service import Station, demo_spec
from tests.station.test_sc_mesh_001 import enrollment


def test_stale_worker_handle_cannot_retain_removed_project_scope(tmp_path):
    station = Station(tmp_path)
    pid = station.create(demo_spec(), demo=True)["project_id"]
    enrolled = station.mesh.enroll(enrollment(pid),
        allowed_capabilities=station.store.settings()["mesh_allowed_capabilities"])
    stale = station.mesh.authenticate(enrolled["token"])
    station.mesh.snapshot(stale, pid)
    assert station.mesh.authorize(stale, pid)[0]["project_ids"] == [pid]
    with station.store.transaction() as connection:
        current = json.loads(connection.execute("SELECT value FROM mesh_workers WHERE worker_id=?", (stale["worker_id"],)).fetchone()[0])
        current["project_ids"] = []  # Disposable fixture models persisted scope narrowing.
        connection.execute("UPDATE mesh_workers SET value=? WHERE worker_id=?", (canonical(current), stale["worker_id"]))
    outcomes = {}
    for name, worker in (("stale", stale), ("fresh", station.mesh.authenticate(enrolled["token"]))):
        try:
            authorized, _ = station.mesh.authorize(worker, pid)
        except ContractError as error:
            outcomes[name] = {"rejected": True, "error": str(error)}
        else:
            outcomes[name] = {"rejected": False, "current_project_ids": authorized["project_ids"]}
    path = Path(os.environ["MESH_REVIEW_EVIDENCE"])
    path.mkdir(parents=True, exist_ok=True)
    (path / "minimal-scope.json").write_text(json.dumps(outcomes, indent=2), encoding="utf-8")
    assert outcomes["fresh"]["rejected"]
    assert outcomes["stale"]["rejected"], outcomes
