"""Negative regressions for pre-dispatch budget admission authority (#208).

Stress Campaign B showed that with an exhausted run budget the runner's
candidate was reviewed, integrated and exported before LoopController tripped.
These tests pin the invariant: no action capable of producing an
accepted/releasable successor may begin unless the run has sufficient
admissible budget/deadline authority for that dispatch.
"""
from __future__ import annotations

import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from residual.core import ContractError
from residual.station.models import save_settings
from residual.station.service import Station, demo_spec


TWO_TASK_SPEC = """# Budget authority regression

```json
{
  "schema_version": 1,
  "name": "Budget Authority Regression",
  "goal": "Implement two tiny calculator functions.",
  "tasks": [
    {
      "id": "CTRL-001",
      "title": "Implement addition",
      "instruction": "Create calculator.py with add(a, b) returning a + b.",
      "files": ["calculator.py"],
      "context": [],
      "depends_on": [],
      "route": "local",
      "checks": [
        {"kind": "python_compile", "path": "calculator.py"},
        {"kind": "command", "argv": ["{python}", "-c", "from calculator import add; assert add(2,3)==5"], "timeout": 30}
      ]
    },
    {
      "id": "CTRL-002",
      "title": "Implement subtraction",
      "instruction": "Create ops.py with sub(a, b) returning a - b.",
      "files": ["ops.py"],
      "context": [],
      "depends_on": [],
      "route": "local",
      "checks": [
        {"kind": "python_compile", "path": "ops.py"},
        {"kind": "command", "argv": ["{python}", "-c", "from ops import sub; assert sub(5,3)==2"], "timeout": 30}
      ]
    }
  ]
}
```
"""

RUNNER_FILES = {
    "CTRL-001": {"calculator.py": "def add(a, b):\n    return a + b\n"},
    "CTRL-002": {"ops.py": "def sub(a, b):\n    return a - b\n"},
}


def fake_model(calls, *, delay=0, usage=120, barrier=None, unknown_usage=False):
    """Deterministic provider stand-in that records durable usage receipts."""
    def invoke(store, pid, role, packet, system, schema, placement, tid, *, extensions=None):
        calls.append(role)
        if role == "runner":
            if barrier is not None:
                barrier.wait(timeout=30)
            if delay:
                time.sleep(delay)
        tokens = {"input_tokens": None, "output_tokens": None} if unknown_usage else {"input_tokens": usage, "output_tokens": 0}
        store.event(pid, "usage.recorded", {
            "role": role, "placement": placement, "model": "fake", "provider": "fake",
            **tokens, "source": "reported",
            "request_bytes": 100, "elapsed_ms": int(delay * 1000),
            "status": "completed", "request_id": f"{role}-{len(calls)}", "provider_attempt": 1,
            "error": None, "cached_input_tokens": 0, "cache_write_input_tokens": None,
        }, tid)
        if role == "runner":
            return {"files": RUNNER_FILES[tid]}
        return {"approved": True, "findings": []}
    return invoke


class BudgetAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _events(self, pid, kind):
        return [e for e in self.station.store.events(pid, 0, 100000) if e["event_type"] == kind]

    def _assert_no_authority_effects(self, pid, result):
        self.assertEqual(result["control"]["outcome"], "aborted")
        self.assertEqual(result["integrated"], 0)
        self.assertFalse(self._events(pid, "review.completed"))
        self.assertFalse(self._events(pid, "integration.completed"))
        for task in self.station.store.project(pid)["tasks"]:
            self.assertIsNone(task["head_commit"] if task["state"] == "ready" else None)
            self.assertNotIn(task["state"], {"approved", "integrated"})
        with self.assertRaises(ContractError):
            self.station.export(pid)

    def test_first_task_consumes_budget_second_task_never_dispatched(self):
        pid = self.station.create(TWO_TASK_SPEC, commands=True)["project_id"]
        save_settings(self.station.store, {"batch_token_budget": 200, "batch_wall_clock_s": 600, "workers": 1})
        calls = []
        with patch("residual.station.service.model_call", side_effect=fake_model(calls, usage=240)):
            result = self.station.batch(pid)
        # Task 1's recorded usage (240) exhausts the 200 budget; task 2 is never dispatched.
        self.assertEqual(calls, ["runner"])
        tasks = {t["id"]: t["state"] for t in self.station.store.project(pid)["tasks"]}
        self.assertEqual(tasks, {"CTRL-001": "review_ready", "CTRL-002": "ready"})
        self._assert_no_authority_effects(pid, result)
        self.assertTrue(any(e["data"].get("reason") == "token_budget_exhausted" and e["data"].get("stage") == "pre-dispatch"
                            for e in self._events(pid, "project.note")))

    def test_unknown_usage_conservative_policy_blocks_dispatch_and_effects(self):
        pid = self.station.create(TWO_TASK_SPEC, commands=True)["project_id"]
        save_settings(self.station.store, {"batch_token_budget": 100000, "batch_wall_clock_s": 600, "workers": 1})
        calls = []
        with patch("residual.station.service.model_call", side_effect=fake_model(calls, unknown_usage=True)):
            result = self.station.batch(pid)
        # Usage unknown after the first call: no further dispatch, no review/integration.
        self.assertEqual(calls, ["runner"])
        tasks = {t["id"]: t["state"] for t in self.station.store.project(pid)["tasks"]}
        self.assertEqual(tasks, {"CTRL-001": "review_ready", "CTRL-002": "ready"})
        self._assert_no_authority_effects(pid, result)
        self.assertIsNone(result["control"]["tokens"])
        self.assertTrue(any(e["data"].get("reason") == "usage_unknown_or_invalid"
                            for e in self._events(pid, "project.note")))

    def test_wall_clock_trip_racing_in_flight_dispatch_blocks_effects(self):
        pid = self.station.create(TWO_TASK_SPEC, commands=True)["project_id"]
        save_settings(self.station.store, {"batch_token_budget": 100000, "batch_wall_clock_s": 1, "workers": 1})
        calls = []
        with patch("residual.station.service.model_call", side_effect=fake_model(calls, delay=1.05)):
            result = self.station.batch(pid)
        # The deadline expired while the first dispatch was in flight; neither
        # review nor integration may follow, and the second task never dispatches.
        self.assertEqual(calls, ["runner"])
        tasks = {t["id"]: t["state"] for t in self.station.store.project(pid)["tasks"]}
        self.assertEqual(tasks, {"CTRL-001": "review_ready", "CTRL-002": "ready"})
        self._assert_no_authority_effects(pid, result)
        self.assertTrue(any(e["data"].get("reason") == "wall_clock_budget_exhausted"
                            for e in self._events(pid, "project.note")))

    def test_parallel_dispatch_first_consumes_budget_no_authority_effects(self):
        pid = self.station.create(TWO_TASK_SPEC, commands=True)["project_id"]
        save_settings(self.station.store, {"batch_token_budget": 200, "batch_wall_clock_s": 600, "workers": 2})
        calls = []
        barrier = threading.Barrier(2)
        with patch("residual.station.service.model_call", side_effect=fake_model(calls, usage=240, barrier=barrier)):
            result = self.station.batch(pid)
        # Both dispatches raced before any cost was knowable; once receipts land
        # the budget is exhausted and no review/integration/export effect follows.
        self.assertEqual(sorted(calls), ["runner", "runner"])
        for task in self.station.store.project(pid)["tasks"]:
            self.assertEqual(task["state"], "review_ready")
        self._assert_no_authority_effects(pid, result)

    def test_aborted_run_cannot_produce_releasable_successor(self):
        pid = self.station.create(demo_spec(), demo=True)["project_id"]
        result = self.station.batch(pid)
        self.assertEqual(result["control"]["outcome"], "success")
        self.station.export(pid)

        project = self.station.store.project(pid)
        last_run = dict(project["last_run"])
        # Even with every check/review receipt intact, an aborted run-control
        # result must not release the exact same integrated head.
        self.station.store.project_update(pid, last_run={**last_run, "outcome": "aborted"})
        with self.assertRaises(ContractError):
            self.station.export(pid)
        # The run-control receipt must also bind the exact current head and spec.
        self.station.store.project_update(pid, last_run={**last_run, "project_head": "0" * 40})
        with self.assertRaises(ContractError):
            self.station.export(pid)
        self.station.store.project_update(pid, last_run={**last_run, "project_spec_hash": "0" * 64})
        with self.assertRaises(ContractError):
            self.station.export(pid)
        # Restoring the exact binding releases again.
        self.station.store.project_update(pid, last_run=last_run)
        self.station.export(pid)


if __name__ == "__main__":
    unittest.main()
