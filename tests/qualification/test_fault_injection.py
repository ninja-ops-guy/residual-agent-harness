from __future__ import annotations

import errno
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
