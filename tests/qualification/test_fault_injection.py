from __future__ import annotations

import errno
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from residual.station.service import Station, demo_spec


def test_claim_transaction_rolls_back_if_event_persistence_fails(tmp_path):
    station = Station(tmp_path / "station")
    pid = station.create(demo_spec(), demo=True)["project_id"]
    station.triage(pid)
    before = station.store.task(pid, "OPS-101")
    assert before["state"] == "ready" and before["attempt"] == 0

    with patch.object(station.store, "_event", side_effect=OSError(errno.EIO, "injected event persistence failure")):
        with pytest.raises(OSError):
            station.store.claim(pid, "fault-injection", "OPS-101")

    after = station.store.task(pid, "OPS-101")
    assert after["state"] == "ready"
    assert after["attempt"] == 0
    assert after["owner"] is None
    assert after["lease"] is None


def test_enospc_artifact_write_never_admits_database_metadata(tmp_path):
    station = Station(tmp_path / "station")
    pid = station.create(demo_spec(), demo=True)["project_id"]
    original = Path.write_bytes

    def fail_selected(path: Path, data: bytes):
        if "artifacts" in path.parts:
            raise OSError(errno.ENOSPC, "injected disk full")
        return original(path, data)

    with patch.object(Path, "write_bytes", fail_selected):
        with pytest.raises(OSError) as error:
            station.store.add_artifact(pid, "should-not-exist.txt", b"evidence")
    assert error.value.errno == errno.ENOSPC
    with station.store.connect() as connection:
        assert connection.execute("SELECT count(*) FROM artifacts WHERE project=?", (pid,)).fetchone()[0] == 0


def test_running_async_job_is_marked_interrupted_after_station_restart(tmp_path):
    root = tmp_path / "station"
    station = Station(root)
    jid = station.store.job("playground")
    station.store.job_update(jid, state="running", detail="provider request in progress")
    assert next(job for job in station.store.jobs() if job["id"] == jid)["state"] == "running"

    reopened = Station(root)
    job = next(job for job in reopened.store.jobs() if job["id"] == jid)
    assert job["state"] == "interrupted"
    assert "restarted" in job["detail"].lower()


def test_corrupt_artifact_bytes_are_never_returned_as_valid_evidence(tmp_path):
    station = Station(tmp_path / "station")
    pid = station.create(demo_spec(), demo=True)["project_id"]
    artifact = station.store.add_artifact(pid, "evidence.txt", b"trusted")
    stored = station.store.root / "artifacts" / pid / artifact["sha256"]
    stored.write_bytes(b"tampered")
    with pytest.raises(Exception, match="integrity"):
        station.store.artifact(artifact["id"])


def test_sigkill_during_uncommitted_sqlite_write_does_not_publish_half_state(tmp_path):
    root = tmp_path / "station"
    station = Station(root)
    pid = station.create(demo_spec(), demo=True)["project_id"]
    station.triage(pid)
    assert station.store.task(pid, "OPS-101")["state"] == "ready"

    code = r"""
import json,sqlite3,sys,time
db,pid=sys.argv[1],sys.argv[2]
c=sqlite3.connect(db,timeout=15,isolation_level=None)
c.execute("BEGIN IMMEDIATE")
row=c.execute("SELECT value FROM tasks WHERE project=? AND id='OPS-101'",(pid,)).fetchone()
task=json.loads(row[0]);task["state"]="integrated";task["owner"]="half-write"
c.execute("UPDATE tasks SET value=? WHERE project=? AND id='OPS-101'",(json.dumps(task,separators=(',',':'),sort_keys=True),pid))
print("UNCOMMITTED_READY",flush=True)
time.sleep(60)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(station.store.db), pid],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "UNCOMMITTED_READY"
        child.kill()
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill(); child.wait(timeout=10)

    reopened = Station(root)
    task = reopened.store.task(pid, "OPS-101")
    assert task["state"] == "ready"
    assert task["owner"] is None
