from __future__ import annotations

import concurrent.futures
import threading
from pathlib import Path

import pytest

from residual.factory.runtime_journal import JournalError, RuntimeJournal
from residual.factory.worker_contract import WorkerContract


def contract(index: int) -> WorkerContract:
    return WorkerContract(
        task_id=f"Task{index}", worker_id=f"Worker{index}", swarm_id="ConcurrencyLab",
        execution_plan_hash="a" * 64, attempt_id=f"Attempt{index}", lease_id=f"Lease{index}",
        lease_generation=1, input_commit="b" * 40,
        workspace_root=f"/tmp/residual-concurrency-{index}", inputs=("src/",),
        allowed_outputs=("out/",), forbidden=("src/secret/",),
        requirements=("ReqA",), acceptance=("CheckA",), dependencies=(),
        allowed_tools=("python",), forbidden_tools=("shell",), token_budget=1000,
        wall_clock_budget_s=5.0, max_tool_calls=5, max_file_writes=5, memory_limit_mb=128,
    )


def race(barrier: threading.Barrier, fn):
    barrier.wait(timeout=5)
    try:
        fn()
        return "PASS"
    except JournalError:
        return "REJECTED"


@pytest.mark.parametrize("round_index", range(12))
def test_duplicate_claim_race_has_exactly_one_authoritative_winner(tmp_path: Path, round_index: int):
    journal = RuntimeJournal(tmp_path / f"claim-{round_index}.sqlite3", trace_id=f"claim-race-{round_index}")
    candidate = contract(1000 + round_index)
    workers = 8
    barrier = threading.Barrier(workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(
            lambda _i: race(
                barrier,
                lambda: journal.claim(candidate, source_hash="c" * 64, approval={"approved_by": "race-lab"}),
            ),
            range(workers),
        ))
    assert results.count("PASS") == 1
    assert results.count("REJECTED") == workers - 1
    rows = [row for row in journal.attempts() if row["attempt_id"] == candidate.attempt_id]
    assert len(rows) == 1
    assert rows[0]["state"] == "RESERVED"
    assert journal.lease_state(candidate) == "current"


@pytest.mark.parametrize("round_index", range(24))
def test_revoke_vs_candidate_race_is_serializable_and_never_accepts_revoked_candidate(
    tmp_path: Path, round_index: int
):
    journal = RuntimeJournal(tmp_path / f"revoke-finish-{round_index}.sqlite3", trace_id=f"revoke-finish-{round_index}")
    candidate = contract(2000 + round_index)
    journal.claim(candidate, source_hash="c" * 64, approval={"approved_by": "race-lab"})
    journal.started(candidate, 30000 + round_index)

    barrier = threading.Barrier(2)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(race, barrier, lambda: journal.revoke(candidate.attempt_id)),
            pool.submit(race, barrier, lambda: journal.finish(candidate, "CANDIDATE", race=round_index)),
        ]
        results = [future.result(timeout=10) for future in futures]

    assert results.count("PASS") == 1
    row = next(row for row in journal.attempts() if row["attempt_id"] == candidate.attempt_id)
    if row["state"] == "CANDIDATE":
        assert not row["revoked"]
    else:
        assert row["state"] == "RUNNING"
        assert row["revoked"]
    assert journal.lease_state(candidate) == "revoked"


@pytest.mark.parametrize("round_index", range(12))
def test_duplicate_terminal_write_race_emits_one_terminal_transition(tmp_path: Path, round_index: int):
    journal = RuntimeJournal(tmp_path / f"finish-{round_index}.sqlite3", trace_id=f"finish-race-{round_index}")
    candidate = contract(3000 + round_index)
    journal.claim(candidate, source_hash="c" * 64, approval={"approved_by": "race-lab"})
    journal.started(candidate, 40000 + round_index)

    workers = 8
    barrier = threading.Barrier(workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(
            lambda _i: race(barrier, lambda: journal.finish(candidate, "FAILED", race=round_index)),
            range(workers),
        ))
    assert results.count("PASS") == 1
    assert results.count("REJECTED") == workers - 1
    row = next(row for row in journal.attempts() if row["attempt_id"] == candidate.attempt_id)
    assert row["state"] == "FAILED"
    terminal = [
        observation for observation in journal.observations()
        if observation.payload.get("event") == "RuntimeAttemptFinished"
        and observation.payload.get("attempt_id") == candidate.attempt_id
    ]
    assert len(terminal) == 1


def test_revoked_lease_never_resurrects_during_concurrent_restart_reads(tmp_path: Path):
    path = tmp_path / "restart.sqlite3"
    journal = RuntimeJournal(path, trace_id="restart-race")
    candidate = contract(4000)
    journal.claim(candidate, source_hash="c" * 64, approval={"approved_by": "race-lab"})
    journal.started(candidate, 50000)

    revoked = threading.Event()
    stop = threading.Event()
    violations: list[str] = []
    lock = threading.Lock()

    def reader() -> None:
        local = RuntimeJournal(path, trace_id="restart-race")
        while not stop.is_set():
            state = local.lease_state(candidate)
            if revoked.is_set() and state != "revoked":
                with lock:
                    violations.append(state)
                return
            # Reopen frequently to exercise connection creation/replay under reads.
            local = RuntimeJournal(path, trace_id="restart-race")

    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        futures = [pool.submit(reader) for _ in range(6)]
        journal.revoke(candidate.attempt_id)
        revoked.set()
        for _ in range(100):
            assert RuntimeJournal(path, trace_id="restart-race").lease_state(candidate) == "revoked"
        stop.set()
        for future in futures:
            future.result(timeout=10)

    assert violations == []
    assert journal.lease_state(candidate) == "revoked"
    journal.observations()
