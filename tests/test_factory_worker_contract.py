"""M2 foundation tests. These do not certify OS isolation or worker execution."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from residual.factory.worker_contract import (
    AttemptGuard, ContractViolation, WorkerContract, WorkerContractError,
)


class PlanFixture:
    """Public ExecutionPlan protocol fixture; no alternative scheduling logic."""
    def __init__(self):
        self.payload = {
            "schema_version": "factory-plan-v1", "intent": "Build a test feature",
            "requirements": [
                {"id": "REQ-1", "statement": "Implement feature", "acceptance": ["unit", "types"], "depends_on": []}
            ],
            "tasks": [
                {"id": "task-1", "description": "Implement feature", "requirement_ids": ["REQ-1"],
                 "depends_on": [], "swarm": "backend"}
            ],
        }

    def canonical_payload(self):
        return self.payload

    @property
    def graph_hash(self):
        return hashlib.sha256(json.dumps(self.payload, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def contract(**overrides):
    data = dict(
        task_id="task-1", worker_id="worker-1", swarm_id="backend",
        execution_plan_hash=PlanFixture().graph_hash, attempt_id="attempt-1",
        lease_id="lease-1", lease_generation=1, input_commit="a" * 40,
        workspace_root="/tmp/residual/attempt-1", inputs=("src/", "README.md"),
        allowed_outputs=("src/", "tests/"), forbidden=("src/secrets/",),
        requirements=("REQ-1",), acceptance=("unit", "types"), dependencies=(),
        allowed_tools=("read_file", "write_file"), forbidden_tools=("shell",),
        token_budget=100, wall_clock_budget_s=10, max_tool_calls=2, max_file_writes=2,
        memory_limit_mb=16,
    )
    data.update(overrides)
    return WorkerContract(**data)


class ContractTests(unittest.TestCase):
    def test_frozen(self):
        c = contract()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            c.token_budget = 200

    def test_defensive_sequence_copy(self):
        inputs = ["src/"]
        c = contract(inputs=inputs)
        inputs.append("secret")
        self.assertEqual(c.inputs, ("src/",))

    def test_returned_payload_detached(self):
        c = contract()
        value = c.to_dict()
        value["inputs"].append("secret")
        self.assertNotIn("secret", c.inputs)

    def test_set_order_does_not_change_hash(self):
        c = contract()
        other = contract(inputs=tuple(reversed(c.inputs)), acceptance=tuple(reversed(c.acceptance)))
        self.assertEqual(c.contract_hash, other.contract_hash)

    def test_round_trip(self):
        c = contract()
        self.assertEqual(c, WorkerContract.from_dict(json.loads(json.dumps(c.to_dict()))))

    def test_every_contract_field_is_hash_bound(self):
        c = contract()
        variants = {
            "task_id": "task-2", "worker_id": "worker-2", "swarm_id": "frontend",
            "execution_plan_hash": "b" * 64, "attempt_id": "attempt-2", "lease_id": "lease-2",
            "lease_generation": 2, "input_commit": "b" * 40, "workspace_root": "/tmp/new",
            "inputs": ("new/",), "allowed_outputs": ("new/",), "forbidden": ("new/",),
            "requirements": ("REQ-2",), "acceptance": ("integration",), "dependencies": ("task-2",),
            "allowed_tools": ("read_file",), "forbidden_tools": ("network",),
            "token_budget": 101, "wall_clock_budget_s": 11, "max_tool_calls": 3,
            "max_file_writes": 3, "memory_limit_mb": 17, "engine_hint": "coder", "engine_class": "any",
        }
        for field, value in variants.items():
            with self.subTest(field=field):
                self.assertNotEqual(c.contract_hash, contract(**{field: value}).contract_hash)

    def test_unknown_and_missing_fields_rejected(self):
        c = contract().to_dict()
        with self.assertRaises(WorkerContractError):
            WorkerContract.from_dict({**c, "typo": 1})
        del c["task_id"]
        with self.assertRaises(WorkerContractError):
            WorkerContract.from_dict(c)

    def test_unsupported_schema(self):
        with self.assertRaises(WorkerContractError):
            contract(schema_version="v2")

    def test_invalid_numbers(self):
        cases = {"token_budget": [True, -1, 2.5], "wall_clock_budget_s": [0, -1, float("nan"), float("inf"), True],
                 "memory_limit_mb": [0, -1, True], "lease_generation": [0, True],
                 "max_file_writes": [-1, True], "max_tool_calls": [-1, True]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(WorkerContractError):
                    contract(**{field: value})

    def test_empty_and_duplicate_lists(self):
        for data in ({"requirements": ()}, {"acceptance": ()}, {"inputs": ("src/", "src/")},
                     {"dependencies": ("task-2", "task-2")}, {"inputs": "src/"}):
            with self.subTest(data=data), self.assertRaises(WorkerContractError):
                contract(**data)

    def test_invalid_identity_commit_and_root(self):
        for data in ({"worker_id": "bad space"}, {"input_commit": "abc123"},
                     {"execution_plan_hash": "A" * 64}, {"workspace_root": "/"},
                     {"workspace_root": "relative"}, {"workspace_root": "/tmp/../etc"},
                     {"workspace_root": "/tmp/./a"}, {"workspace_root": "//tmp/a"},
                     {"workspace_root": "/tmp/a\x00"}):
            with self.subTest(data=data), self.assertRaises(WorkerContractError):
                contract(**data)

    def test_bad_selectors(self):
        for path in ("../secret", "/etc/passwd", "src//a", "src/./a", "C:\\temp", "src/*", "", "a\n"):
            with self.subTest(path=path), self.assertRaises(WorkerContractError):
                contract(inputs=(path,))

    def test_tool_contradiction_self_dependency(self):
        with self.assertRaises(WorkerContractError):
            contract(forbidden_tools=("read_file",))
        with self.assertRaises(WorkerContractError):
            contract(dependencies=("task-1",))

    def test_exact_and_prefix_paths(self):
        c = contract()
        self.assertTrue(c.permits_path("src/a.py"))
        self.assertTrue(c.permits_path("README.md"))
        self.assertFalse(c.permits_path("README.md/other"))
        self.assertFalse(c.permits_path("src-other/a.py"))
        self.assertFalse(c.permits_path("tests/a.py"))
        self.assertTrue(c.permits_path("tests/a.py", write=True))

    def test_deny_precedence_and_git_metadata(self):
        c = contract(inputs=("src/", ".git/"), allowed_outputs=("src/", ".git/"))
        for path in ("src/secrets/key", ".git/config", "src/.GIT/config"):
            with self.subTest(path=path):
                self.assertFalse(c.permits_path(path))
                self.assertFalse(c.permits_path(path, write=True))

    def test_full_sha256_git_id(self):
        self.assertEqual(contract(input_commit="a" * 64).input_commit, "a" * 64)

    def test_plan_binding(self):
        contract().assert_matches_plan(PlanFixture())

    def test_plan_change_invalidates_contract(self):
        plan = PlanFixture()
        c = contract()
        plan.payload["intent"] = "A different project"
        with self.assertRaises(WorkerContractError):
            c.assert_matches_plan(plan)

    def test_no_weaker_acceptance_or_rebinding(self):
        for data in ({"acceptance": ("unit",)}, {"requirements": ("REQ-2",)},
                     {"dependencies": ("task-2",)}, {"swarm_id": "frontend"}, {"task_id": "task-2"}):
            with self.subTest(data=data), self.assertRaises(WorkerContractError):
                contract(**data).assert_matches_plan(PlanFixture())

    def test_stricter_acceptance_allowed(self):
        contract(acceptance=("unit", "types", "security")).assert_matches_plan(PlanFixture())


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.stops = []
        self.now = 100.0
        self.guard = AttemptGuard(contract(), observe=self.events.append,
                                  terminate=lambda: self.stops.append(True), clock=lambda: self.now)
        self.guard.start()

    def test_contract_logged_before_started(self):
        self.assertEqual([e["event"] for e in self.events], ["WorkerContractRecorded", "WorkerAttemptStarted"])
        self.assertEqual(self.events[0]["contract"], self.guard.contract.to_dict())

    def test_all_events_bind_identity(self):
        self.guard.authorize_tool("read_file")
        for event in self.events:
            self.assertEqual(event["contract_hash"], self.guard.contract.contract_hash)
            self.assertEqual(event["execution_plan_hash"], self.guard.contract.execution_plan_hash)
            self.assertEqual(event["attempt_id"], "attempt-1")

    def test_double_start_forbidden(self):
        with self.assertRaises(WorkerContractError):
            self.guard.start()

    def test_forbidden_tool_stops_attempt(self):
        with self.assertRaises(ContractViolation) as error:
            self.guard.authorize_tool("shell")
        self.assertEqual(error.exception.observation["reason"], "contract_violation")
        self.assertEqual(error.exception.observation["boundary"], "tool")
        self.assertEqual(self.guard.state, "VIOLATED")
        self.assertEqual(len(self.stops), 1)

    def test_terminal_attempt_cannot_retry(self):
        with self.assertRaises(ContractViolation):
            self.guard.authorize_tool("shell")
        for op in (self.guard.start, lambda: self.guard.authorize_tool("read_file"), self.guard.finish):
            with self.assertRaises(WorkerContractError):
                op()
        self.guard.cancel()
        self.assertEqual(len(self.stops), 1)

    def test_tool_counter(self):
        self.guard.authorize_tool("read_file")
        self.guard.authorize_tool("read_file")
        with self.assertRaises(ContractViolation):
            self.guard.authorize_tool("read_file")

    def test_traversal_is_violation(self):
        with self.assertRaises(ContractViolation) as error:
            self.guard.authorize_path("../secret")
        self.assertEqual(error.exception.observation["boundary"], "filesystem")

    def test_forbidden_prefix_is_violation(self):
        with self.assertRaises(ContractViolation):
            self.guard.authorize_path("src/secrets/key")

    def test_write_counter(self):
        self.guard.authorize_path("src/a", write=True)
        self.guard.authorize_path("src/a", write=True)
        with self.assertRaises(ContractViolation) as error:
            self.guard.authorize_path("src/a", write=True)
        self.assertEqual(error.exception.observation["field"], "max_file_writes")

    def test_reads_do_not_consume_write_budget(self):
        for _ in range(5):
            self.guard.authorize_path("src/a")
        self.assertEqual(self.guard.usage["file_writes"], 0)

    def test_token_reservation_and_settlement(self):
        a = self.guard.reserve_tokens(60)
        b = self.guard.reserve_tokens(40)
        self.guard.settle_tokens(a, 50)
        self.guard.settle_tokens(b, 40)
        c = self.guard.reserve_tokens(10)
        self.guard.settle_tokens(c, 10)
        self.assertEqual(self.guard.usage["tokens"], 100)
        self.guard.finish()
        self.assertEqual(self.guard.state, "CANDIDATE")

    def test_reservations_cannot_oversubscribe(self):
        self.guard.reserve_tokens(70)
        with self.assertRaises(ContractViolation):
            self.guard.reserve_tokens(31)
        self.assertEqual(self.guard.usage["reserved_tokens"], 70)

    def test_unknown_usage_is_not_zero(self):
        ticket = self.guard.reserve_tokens(100)
        with self.assertRaises(ContractViolation):
            self.guard.settle_tokens(ticket, None)
        self.assertEqual(self.guard.usage["reserved_tokens"], 100)

    def test_provider_reservation_overrun(self):
        ticket = self.guard.reserve_tokens(20)
        with self.assertRaises(ContractViolation):
            self.guard.settle_tokens(ticket, 21)
        self.assertEqual(self.guard.usage["tokens"], 21)

    def test_replayed_usage_rejected(self):
        ticket = self.guard.reserve_tokens(20)
        self.guard.settle_tokens(ticket, 10)
        with self.assertRaises(ContractViolation):
            self.guard.settle_tokens(ticket, 10)

    def test_cannot_finish_with_unknown_usage(self):
        self.guard.reserve_tokens(10)
        with self.assertRaises(ContractViolation):
            self.guard.finish()

    def test_usage_snapshot_is_detached(self):
        snapshot = self.guard.usage
        snapshot["tokens"] = 10000
        self.assertEqual(self.guard.usage["tokens"], 0)

    def test_memory_limit(self):
        self.guard.check_memory(16 * 1024 * 1024)
        with self.assertRaises(ContractViolation):
            self.guard.check_memory(16 * 1024 * 1024 + 1)

    def test_unknown_memory_fails_closed(self):
        with self.assertRaises(ContractViolation):
            self.guard.check_memory(None)
        self.assertEqual(self.guard.state, "VIOLATED")

    def test_invalid_clock_fails_closed(self):
        self.now = float("nan")
        with self.assertRaises(ContractViolation):
            self.guard.check_deadline()
        self.assertEqual(self.guard.state, "VIOLATED")

    def test_invalid_initial_clock_is_terminal(self):
        guard = AttemptGuard(contract(), observe=self.events.append,
                             terminate=lambda: self.stops.append(True), clock=lambda: float("nan"))
        with self.assertRaises(ContractViolation):
            guard.start()
        with self.assertRaises(WorkerContractError):
            guard.start()

    def test_deadline(self):
        self.now = 110
        with self.assertRaises(ContractViolation) as error:
            self.guard.check_deadline()
        self.assertEqual(error.exception.observation["field"], "wall_clock_budget_s")

    def test_regressing_clock(self):
        self.now = 99
        with self.assertRaises(ContractViolation):
            self.guard.authorize_tool("read_file")

    def test_stale_lease(self):
        self.guard.assert_lease("lease-1", 1)
        with self.assertRaises(ContractViolation):
            self.guard.assert_lease("lease-1", 2)

    def test_bool_lease_not_integer(self):
        with self.assertRaises(ContractViolation):
            self.guard.assert_lease("lease-1", True)

    def test_cancel_idempotent(self):
        self.guard.cancel()
        self.guard.cancel()
        self.assertEqual(self.guard.state, "CANCELLED")
        self.assertEqual(len(self.stops), 1)

    def test_failing_initial_audit_prevents_start(self):
        def failed(_):
            raise OSError("disk full")
        guard = AttemptGuard(contract(), observe=failed, terminate=lambda: self.stops.append(True))
        with self.assertRaises(OSError):
            guard.start()
        self.assertEqual(guard.state, "AUDIT_FAILED")
        with self.assertRaises(WorkerContractError):
            guard.start()

    def test_audit_failure_still_stops_violation(self):
        def failed(_):
            raise OSError("disk full")
        self.guard._observe = failed
        with self.assertRaises(ContractViolation) as error:
            self.guard.authorize_tool("shell")
        self.assertEqual(len(self.stops), 1)
        self.assertTrue(error.exception.observation["audit_failed"])

    def test_failed_kill_is_not_claimed_successful(self):
        def failed():
            raise OSError("no process handle")
        self.guard._terminate = failed
        with self.assertRaises(ContractViolation) as error:
            self.guard.authorize_tool("shell")
        self.assertEqual(error.exception.observation["stop_hook"], "failed")

    def test_concurrent_token_reservations(self):
        barrier = threading.Barrier(2)
        def call():
            barrier.wait()
            try:
                return self.guard.reserve_tokens(60)
            except WorkerContractError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: call(), range(2)))
        self.assertEqual(sum(x is not None for x in results), 1)
        self.assertEqual(self.guard.usage["reserved_tokens"], 60)
        self.assertEqual(self.guard.state, "VIOLATED")

    def test_candidates_are_not_accepted(self):
        self.guard.finish()
        self.assertEqual(self.events[-1]["event"], "WorkerCandidateReady")
        self.assertNotIn("receipt", self.events[-1])


if __name__ == "__main__":
    unittest.main()
