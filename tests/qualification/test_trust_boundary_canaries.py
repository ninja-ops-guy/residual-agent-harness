from __future__ import annotations

from pathlib import Path

import pytest

from residual.factory.runtime_journal import JournalError, RuntimeJournal
from residual.factory.worker_contract import WorkerContract


def contract(*, generation: int = 1, attempt: str = "AttemptA", worker: str = "WorkerA",
             lease: str = "LeaseA") -> WorkerContract:
    return WorkerContract(
        task_id="TaskA", worker_id=worker, swarm_id="SwarmA",
        execution_plan_hash="a" * 64, attempt_id=attempt, lease_id=lease,
        lease_generation=generation, input_commit="b" * 40,
        workspace_root=f"/tmp/{attempt}", inputs=("src/",), allowed_outputs=("out/",),
        forbidden=("src/secret/",), requirements=("ReqA",), acceptance=("CheckA",),
        dependencies=(), allowed_tools=("python",), forbidden_tools=("shell",),
        token_budget=100, wall_clock_budget_s=5, max_tool_calls=2, max_file_writes=2,
        memory_limit_mb=128,
    )


def journal(tmp_path: Path) -> RuntimeJournal:
    return RuntimeJournal(tmp_path / "journal.sqlite3", trace_id="qualification-canary")


def test_revoked_attempt_can_never_publish_candidate(tmp_path: Path):
    j = journal(tmp_path)
    c = contract()
    j.claim(c, source_hash="c" * 64, approval={"approved_by": "qualification"})
    j.revoke(c.attempt_id)
    with pytest.raises(JournalError, match="revoked attempt"):
        j.finish(c, "CANDIDATE")


def test_candidate_is_no_longer_an_authoritative_current_lease(tmp_path: Path):
    j = journal(tmp_path)
    c = contract()
    j.claim(c, source_hash="c" * 64, approval={"approved_by": "qualification"})
    assert j.lease_state(c) == "current"
    j.finish(c, "CANDIDATE")
    assert j.lease_state(c) == "revoked"


def test_git_metadata_is_never_permitted_by_worker_path_policy():
    c = contract()
    assert c.permits_path("src/code.py")
    assert not c.permits_path("src/.git/config")
    assert not c.permits_path("out/.git/index", write=True)


def test_forbidden_prefix_wins_over_read_allowlist():
    c = contract()
    assert not c.permits_path("src/secret/value.txt")
