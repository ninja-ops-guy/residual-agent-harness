from __future__ import annotations

import json
import tempfile
import time
import unittest
from unittest.mock import patch

from residual.core import ContractError
from residual.station.models import save_settings
from residual.station.service import Station, demo_spec


LIVE_SPEC = """# Budget authority regression

```json
{
  "schema_version": 1,
  "name": "Budget Authority Regression",
  "goal": "Implement one tiny calculator function.",
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
    }
  ]
}
```
"""


class BudgetAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _fake_model(calls, *, delay=0):
        def invoke(store, pid, role, packet, system, schema, placement, tid, *, extensions=None):
            calls.append(role)
            if delay:
                time.sleep(delay)
            store.event(pid, "usage.recorded", {
                "role": role, "placement": placement, "model": "fake", "provider": "fake",
                "input_tokens": 100, "output_tokens": 20, "source": "reported",
                "request_bytes": 100, "elapsed_ms": int(delay * 1000),
                "status": "completed", "request_id": role, "provider_attempt": 1,
                "error": None, "cached_input_tokens": 0, "cache_write_input_tokens": None,
            }, tid)
            if role == "runner":
                return {"files": {"calculator.py": "def add(a, b):\n    return a + b\n"}}
            return {"approved": True, "findings": []}
        return invoke

    def test_token_budget_blocks_review_and_integration_before_controller_abort(self):
        pid = self.station.create(LIVE_SPEC, commands=True)["project_id"]
        save_settings(self.station.store, {"batch_token_budget": 1, "batch_wall_clock_s": 600})
        calls = []
        with patch("residual.station.service.model_call", side_effect=self._fake_model(calls)):
            result = self.station.batch(pid)
        task = self.station.store.task(pid, "CTRL-001")
        self.assertEqual(result["control"]["outcome"], "aborted")
        self.assertEqual(result["integrated"], 0)
        self.assertEqual(task["state"], "review_ready")
        self.assertEqual(calls, ["runner"])
        self.assertFalse(any(e["event_type"] == "integration.completed" for e in self.station.store.events(pid, 0, 1000)))
        with self.assertRaises(ContractError):
            self.station.export(pid)

    def test_wall_clock_budget_blocks_review_and_integration_before_controller_abort(self):
        pid = self.station.create(LIVE_SPEC, commands=True)["project_id"]
        save_settings(self.station.store, {"batch_token_budget": 100000, "batch_wall_clock_s": 1})
        calls = []
        with patch("residual.station.service.model_call", side_effect=self._fake_model(calls, delay=1.05)):
            result = self.station.batch(pid)
        task = self.station.store.task(pid, "CTRL-001")
        self.assertEqual(result["control"]["outcome"], "aborted")
        self.assertEqual(result["integrated"], 0)
        self.assertEqual(task["state"], "review_ready")
        self.assertEqual(calls, ["runner"])
        with self.assertRaises(ContractError):
            self.station.export(pid)

    def test_release_export_is_bound_to_successful_run_and_exact_head(self):
        pid = self.station.create(demo_spec(), demo=True)["project_id"]
        result = self.station.batch(pid)
        self.assertEqual(result["control"]["outcome"], "success")
        self.station.export(pid)

        project = self.station.store.project(pid)
        last_run = dict(project["last_run"])
        self.station.store.project_update(pid, last_run={**last_run, "outcome": "aborted"})
        with self.assertRaises(ContractError):
            self.station.export(pid)

        self.station.store.project_update(pid, last_run={**last_run, "project_head": "0" * 40})
        with self.assertRaises(ContractError):
            self.station.export(pid)


if __name__ == "__main__":
    unittest.main()
