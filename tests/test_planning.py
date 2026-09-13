import dataclasses
import json
import unittest
from pathlib import Path

from residual.core import Artifact, Registry, Task, canonical, register_builtins
from residual.engine import Harness, Limits
from residual.providers import CallableProvider, Reply


ROOT = Path(__file__).resolve().parents[1]
GOOD_PLAN = ["backup", "drain", "stop", "patch", "start", "health"]


class PlanTests(unittest.TestCase):
    def run_plan(self, plan, task=None):
        task = task or Task.load(ROOT / "examples/maintenance/task.json")
        registry = Registry()
        register_builtins(registry)
        provider = CallableProvider("planner", lambda p, m: Reply(canonical({"updates": {"plan": plan}, "requests": []})))
        return Harness(registry, provider, None, Limits(local_rounds=1)).run(task)

    def test_valid_plan_and_derived_count(self):
        result = self.run_plan(GOOD_PLAN)
        self.assertTrue(result["success"])
        self.assertEqual(result["values"]["step_count"], 6)

    def test_bad_order_has_specific_counterexample(self):
        result = self.run_plan(["patch", "backup", "drain", "stop", "start", "health"])
        self.assertFalse(result["success"])
        self.assertEqual(result["unresolved"]["plan"]["code"], "precondition_failed")
        self.assertIn("Step 1", result["unresolved"]["plan"]["message"])

    def test_forbidden_state_rejected_even_when_action_allows_it(self):
        task = Task.load(ROOT / "examples/maintenance/task.json")
        spec = json.loads(task.artifacts["model"].text)
        spec["actions"]["stop"]["requires"] = {}
        task = dataclasses.replace(task, artifacts={"model": Artifact("model", canonical(spec), True)})
        result = self.run_plan(["stop", "patch", "start", "health"], task)
        self.assertEqual(result["unresolved"]["plan"]["code"], "forbidden_state")

    def test_valid_prefix_is_not_full_success(self):
        result = self.run_plan(GOOD_PLAN[:-1])
        self.assertFalse(result["success"])
        self.assertEqual(result["unresolved"]["plan"]["code"], "goal_unsatisfied")

    def test_nonexistent_action_cannot_execute(self):
        result = self.run_plan(["shell:delete_everything"])
        self.assertEqual(result["unresolved"]["plan"]["code"], "unknown_action")

    def test_empty_and_excessively_long_plans_rejected(self):
        for plan in ([], GOOD_PLAN * 20):
            result = self.run_plan(plan)
            self.assertEqual(result["unresolved"]["plan"]["code"], "plan_length")

    def test_partial_repair_from_counterexample(self):
        task = Task.load(ROOT / "examples/maintenance/task.json")
        registry = Registry()
        register_builtins(registry)
        def expert(packet, maximum):
            self.assertEqual(packet["counterexamples"]["plan"]["code"], "precondition_failed")
            return Reply(canonical({"updates": {"plan": GOOD_PLAN}, "requests": []}))
        local = CallableProvider("local", lambda p, m: Reply(canonical({"updates": {"plan": ["patch"]}, "requests": []})))
        result = Harness(registry, local, CallableProvider("expert", expert, "remote"), Limits(local_rounds=1)).run(task)
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
