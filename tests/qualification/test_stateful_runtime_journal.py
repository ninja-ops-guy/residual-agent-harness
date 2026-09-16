from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from hypothesis import settings
    from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule
except ImportError:  # ordinary repository suites do not require qualification extras
    HYPOTHESIS_AVAILABLE = False
else:
    HYPOTHESIS_AVAILABLE = True

from residual.factory.runtime_journal import JournalError, RuntimeJournal
from residual.factory.worker_contract import WorkerContract


def make_contract(index: int, generation: int) -> WorkerContract:
    return WorkerContract(
        task_id="TaskA",
        worker_id=f"Worker{index}",
        swarm_id="SwarmA",
        execution_plan_hash="a" * 64,
        attempt_id=f"Attempt{index}",
        lease_id=f"Lease{index}",
        lease_generation=generation,
        input_commit="b" * 40,
        workspace_root=f"/tmp/residual-stateful-{index}",
        inputs=("input.txt",),
        allowed_outputs=("output.txt",),
        forbidden=("secret/",),
        requirements=("ReqA",),
        acceptance=("CheckA",),
        dependencies=(),
        allowed_tools=("python",),
        forbidden_tools=("shell",),
        token_budget=1000,
        wall_clock_budget_s=5.0,
        max_tool_calls=5,
        max_file_writes=5,
        memory_limit_mb=128,
    )


def expect_journal_error(callable_) -> None:
    try:
        callable_()
    except JournalError:
        return
    raise AssertionError("invalid lifecycle operation was accepted")


if HYPOTHESIS_AVAILABLE:
    class RuntimeJournalMachine(RuleBasedStateMachine):
        """Model-check RuntimeJournal lifecycle invariants over generated operation sequences."""

        def __init__(self):
            super().__init__()
            self._temp = tempfile.TemporaryDirectory(prefix="residual-stateful-")
            self.path = Path(self._temp.name) / "journal.sqlite3"
            self.trace_id = "qualification-stateful"
            self.journal = RuntimeJournal(self.path, trace_id=self.trace_id)
            self.contract: WorkerContract | None = None
            self.state: str | None = None
            self.revoked = False
            self.generation = 0
            self.index = 0
            self.old_contracts: list[WorkerContract] = []

        def teardown(self):
            self._temp.cleanup()

        @property
        def claimable(self) -> bool:
            return self.state is None or self.state in {"VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED", "PURGED"}

        @precondition(lambda self: self.claimable)
        @rule()
        def claim(self):
            self.index += 1
            self.generation += 1
            contract = make_contract(self.index, self.generation)
            self.journal.claim(contract, source_hash="c" * 64, approval={"approved_by": "qualification"})
            self.contract = contract
            self.old_contracts.append(contract)
            self.state = "RESERVED"
            self.revoked = False
            assert self.journal.lease_state(contract) == "current"

        @precondition(lambda self: self.contract is not None and self.state == "RESERVED" and not self.revoked)
        @rule()
        def start(self):
            assert self.contract is not None
            self.journal.started(self.contract, 12345 + self.index)
            self.state = "RUNNING"

        @precondition(lambda self: self.contract is not None and self.state in {"RESERVED", "RUNNING"} and not self.revoked)
        @rule()
        def revoke(self):
            assert self.contract is not None
            self.journal.revoke(self.contract.attempt_id)
            self.revoked = True
            assert self.journal.lease_state(self.contract) == "revoked"

        @precondition(lambda self: self.contract is not None and self.state in {"RESERVED", "RUNNING"})
        @rule()
        def finish_failure(self):
            assert self.contract is not None
            self.journal.finish(self.contract, "FAILED", reason="stateful")
            self.state = "FAILED"

        @precondition(lambda self: self.contract is not None and self.state in {"RESERVED", "RUNNING"} and not self.revoked)
        @rule()
        def finish_candidate(self):
            assert self.contract is not None
            self.journal.finish(self.contract, "CANDIDATE", reason="stateful")
            self.state = "CANDIDATE"

        @precondition(lambda self: self.contract is not None and self.state == "CANDIDATE")
        @rule()
        def purge_candidate(self):
            assert self.contract is not None
            self.journal.mark_purged(self.contract.attempt_id)
            self.state = "PURGED"

        @precondition(lambda self: self.contract is not None and self.state in {"RESERVED", "RUNNING"} and self.revoked)
        @rule()
        def revoked_candidate_must_fail(self):
            assert self.contract is not None
            expect_journal_error(lambda: self.journal.finish(self.contract, "CANDIDATE"))

        @precondition(lambda self: self.contract is not None and self.state in {"CANDIDATE", "VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED", "PURGED"})
        @rule()
        def terminal_finish_is_rejected(self):
            assert self.contract is not None
            expect_journal_error(lambda: self.journal.finish(self.contract, "FAILED"))

        @rule()
        def restart_and_replay(self):
            self.journal = RuntimeJournal(self.path, trace_id=self.trace_id)
            self.journal.observations()

        @invariant()
        def authoritative_attempt_state_matches_model(self):
            rows = self.journal.attempts()
            assert len({row["attempt_id"] for row in rows}) == len(rows)
            if self.contract is None:
                return
            latest = [row for row in rows if row["attempt_id"] == self.contract.attempt_id]
            assert len(latest) == 1
            assert latest[0]["state"] == self.state
            expected_lease = "current" if self.state in {"RESERVED", "RUNNING"} and not self.revoked else "revoked"
            assert self.journal.lease_state(self.contract) == expected_lease
            for old in self.old_contracts[:-1]:
                assert self.journal.lease_state(old) == "revoked"

    RuntimeJournalStatefulTest = RuntimeJournalMachine.TestCase
    RuntimeJournalStatefulTest.settings = settings(max_examples=75, stateful_step_count=40, deadline=None)
else:
    class RuntimeJournalStatefulTest(unittest.TestCase):
        @unittest.skip("qualification extra 'hypothesis' is not installed")
        def test_hypothesis_qualification_extra_required(self):
            pass
