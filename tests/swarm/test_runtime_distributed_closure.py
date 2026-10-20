"""Closure tests for the combined runtime/distributed hardening lane."""
from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path

import pytest

from residual.dsm import DistributedStateStore, FencingError, LeaseManager
from residual.runtime import CancellationBudget, CancellationController


@pytest.mark.skipif(os.name != "posix", reason="process-group evidence is POSIX-specific")
def test_cancellation_terminates_worker_process_group_and_descendant():
    async def scenario():
        child_code = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
        parent_code = (
            "import subprocess,sys,time; "
            f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
            "print(p.pid, flush=True); time.sleep(60)"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", parent_code,
            stdout=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        descendant_pid = int((await process.stdout.readline()).decode().strip())
        controller = CancellationController(CancellationBudget(2.0))
        controller.track_process(
            process, name="worker-group", process_group_id=process.pid)
        report = await controller.abort()
        return process, descendant_pid, report

    process, descendant_pid, report = asyncio.run(scenario())
    assert process.returncode is not None
    assert report.cancelled is True
    assert report.descendants_clean is True
    assert dict(report.process_outcomes)["worker-group"] in {
        "terminated_group", "killed_group"
    }
    stat_path = f"/proc/{descendant_pid}/stat"
    if os.path.exists(stat_path):
        assert Path(stat_path).read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0] == "Z"


def test_fencing_validation_is_held_through_authoritative_append(tmp_path, monkeypatch):
    leases = LeaseManager()
    first = leases.acquire("task-1", "worker-a", ttl_ms=1_000, now_ms=0)
    store = DistributedStateStore(tmp_path, leases=leases)
    entered_append = threading.Event()
    release_append = threading.Event()
    original_append = store.journal.append

    def blocked_append(*args, **kwargs):
        entered_append.set()
        assert release_append.wait(timeout=2.0)
        return original_append(*args, **kwargs)

    monkeypatch.setattr(store.journal, "append", blocked_append)
    event = {
        "event_id": "lease-write-1", "domain": "task.lease", "entity": "task-1",
        "value": "worker-a", "writer": "scheduler", "writer_holder": "worker-a",
        "fencing_token": first["fencing_token"], "now_ms": 1,
    }
    write_result = []
    writer = threading.Thread(target=lambda: write_result.append(store.submit(event)))
    writer.start()
    assert entered_append.wait(timeout=2.0)

    reassigned = threading.Event()

    def reassign():
        leases.acquire("task-1", "worker-b", ttl_ms=1_000, now_ms=1_001)
        reassigned.set()

    lease_thread = threading.Thread(target=reassign)
    lease_thread.start()
    assert not reassigned.wait(timeout=0.05), "lease changed during authoritative append"
    release_append.set()
    writer.join(timeout=2.0)
    lease_thread.join(timeout=2.0)
    assert write_result[0]["disposition"] == "accepted"
    assert reassigned.is_set()

    with pytest.raises(FencingError):
        store.submit({**event, "event_id": "lease-write-stale", "now_ms": 1_002})


def test_preopened_store_refreshes_before_duplicate_and_collision(tmp_path):
    first = DistributedStateStore(tmp_path)
    preopened = DistributedStateStore(tmp_path)
    event = {
        "event_id": "shared-key", "domain": "receipt.publication",
        "entity": "task-a", "value": {"ok": True}, "writer": "verifier",
    }

    accepted = first.submit(event)
    duplicate = preopened.submit(event)
    assert accepted["disposition"] == "accepted"
    assert duplicate == {**accepted, "disposition": "duplicate"}

    with pytest.raises(Exception, match="transition key collision"):
        preopened.submit({**event, "entity": "task-b"})
    assert [t["event_id"] for t in first.accepted_transitions()] == ["shared-key"]


def test_same_process_store_instances_serialize_shared_journal(tmp_path, monkeypatch):
    first = DistributedStateStore(tmp_path)
    second = DistributedStateStore(tmp_path)
    entered_append = threading.Event()
    release_append = threading.Event()
    second_finished = threading.Event()
    original_append = first.journal.append
    results = []
    errors = []

    def blocked_append(*args, **kwargs):
        entered_append.set()
        assert release_append.wait(timeout=2.0)
        return original_append(*args, **kwargs)

    monkeypatch.setattr(first.journal, "append", blocked_append)

    def submit(store, event, finished=None):
        try:
            results.append(store.submit(event))
        except Exception as exc:  # surfaced below instead of lost in a thread
            errors.append(exc)
        finally:
            if finished is not None:
                finished.set()

    event_a = {
        "event_id": "concurrent-a", "domain": "receipt.publication",
        "entity": "task-a", "value": 1, "writer": "verifier",
    }
    event_b = {
        "event_id": "concurrent-b", "domain": "receipt.publication",
        "entity": "task-b", "value": 2, "writer": "verifier",
    }

    writer_a = threading.Thread(target=submit, args=(first, event_a))
    writer_a.start()
    assert entered_append.wait(timeout=2.0)

    writer_b = threading.Thread(target=submit, args=(second, event_b, second_finished))
    writer_b.start()
    assert not second_finished.wait(timeout=0.05), "sibling store bypassed process path lock"

    release_append.set()
    writer_a.join(timeout=2.0)
    writer_b.join(timeout=2.0)
    assert not writer_a.is_alive() and not writer_b.is_alive()
    assert errors == []
    assert sorted(r["seq"] for r in results) == [0, 1]

    recovered = DistributedStateStore.recover(tmp_path)
    transitions = recovered.accepted_transitions()
    assert [t["seq"] for t in transitions] == [0, 1]
    assert {t["event_id"] for t in transitions} == {"concurrent-a", "concurrent-b"}
    assert recovered.journal.verify() == 2


def test_replay_idempotence_uses_globally_unique_event_id(tmp_path):
    store = DistributedStateStore(tmp_path)
    event = {
        "event_id": "run-7:terminal:task-2:revision-1",
        "domain": "task.terminal", "entity": "task-2", "value": "running",
        "writer": "orchestrator",
    }
    accepted = store.submit(event)
    duplicate = DistributedStateStore.recover(tmp_path).submit(event)
    assert accepted["disposition"] == "accepted"
    assert duplicate == {**accepted, "disposition": "duplicate"}
    assert len(DistributedStateStore.recover(tmp_path).accepted_transitions()) == 1


def test_transition_key_collision_fails_closed(tmp_path):
    store = DistributedStateStore(tmp_path)
    first = {
        "event_id": "global-transition-1", "domain": "receipt.publication",
        "entity": "task-a", "value": {"ok": True}, "writer": "verifier",
    }
    store.submit(first)
    with pytest.raises(Exception, match="transition key collision"):
        store.submit({**first, "entity": "task-b"})
    assert len(store.accepted_transitions()) == 1
