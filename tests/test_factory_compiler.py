import json
import tempfile
import unittest
from pathlib import Path

from residual.core import ContractError
from residual.factory.cli import main as factory_main
from residual.factory.compiler import RequirementCompiler
from residual.factory.models import ExecutionPlan, FrozenPlan


DOC = {
    "intent": "Implement the factory runtime",
    "requirements": [
        {"id": "REQ-2", "statement": "Integrate verified output", "acceptance": ["integration check passes"], "depends_on": ["REQ-1"]},
        {"id": "REQ-1", "statement": "Compile requirements", "acceptance": ["plan hash is stable"]},
    ],
}


class FactoryCompilerTests(unittest.TestCase):
    def test_compiles_and_derives_dependency_tasks(self):
        result = RequirementCompiler().compile(DOC)
        self.assertTrue(result.ready)
        self.assertEqual([task.id for task in result.plan.tasks], ["task.REQ-1", "task.REQ-2"])
        self.assertEqual(result.plan.tasks[1].depends_on, ("task.REQ-1",))

    def test_hash_is_order_independent_for_requirements(self):
        first = RequirementCompiler().compile(DOC).plan
        reordered = dict(DOC)
        reordered["requirements"] = list(reversed(DOC["requirements"]))
        second = RequirementCompiler().compile(reordered).plan
        self.assertEqual(first.graph_hash, second.graph_hash)

    def test_ambiguity_is_surfaced_not_guessed(self):
        result = RequirementCompiler().compile({"intent": "build it", "requirements": [{"id": "REQ-1", "statement": "x"}]})
        self.assertFalse(result.ready)
        self.assertTrue(any("acceptance criteria" in question for question in result.questions))

    def test_cycle_is_rejected(self):
        doc = {
            "intent": "cycle",
            "requirements": [
                {"id": "A", "statement": "a", "acceptance": ["a"], "depends_on": ["B"]},
                {"id": "B", "statement": "b", "acceptance": ["b"], "depends_on": ["A"]},
            ],
        }
        with self.assertRaises(ContractError):
            RequirementCompiler().compile(doc)

    def test_plan_hash_detects_tamper(self):
        plan = RequirementCompiler().compile(DOC).plan
        data = plan.to_dict()
        data["intent"] = "changed"
        with self.assertRaises(ContractError):
            ExecutionPlan.from_dict(data)

    def test_approval_binds_exact_plan(self):
        plan = RequirementCompiler().compile(DOC).plan
        approval = FrozenPlan.approve(plan, "operator")
        approval.assert_matches(plan)
        other = RequirementCompiler().compile({**DOC, "intent": "different"}).plan
        with self.assertRaises(ContractError):
            approval.assert_matches(other)

    def test_cli_plan_approve_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "intent.json"
            plan = root / "plan.json"
            approval = root / "approval.json"
            source.write_text(json.dumps(DOC), encoding="utf-8")
            self.assertEqual(factory_main(["plan", str(source), "--output", str(plan)]), 0)
            self.assertEqual(factory_main(["approve", str(plan), "--by", "operator", "--output", str(approval)]), 0)
            self.assertEqual(factory_main(["verify-approval", str(plan), str(approval)]), 0)


if __name__ == "__main__":
    unittest.main()
