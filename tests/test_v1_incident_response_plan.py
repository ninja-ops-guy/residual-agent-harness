import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_v1_incident_response_plan",
    ROOT / "scripts" / "validate_v1_incident_response_plan.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class IncidentResponsePlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(
            (ROOT / "docs" / "v1" / "V1_INCIDENT_RESPONSE_PLAN.json").read_text(encoding="utf-8")
        )

    def test_reference_plan_passes_and_is_deterministic(self):
        first = module.validate_plan(copy.deepcopy(self.plan))
        second = module.validate_plan(copy.deepcopy(self.plan))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["scenario_count"], 5)
        self.assertEqual(first["execution_claim"], "NONE")

    def test_missing_required_scenario_blocks(self):
        self.plan["scenarios"] = [
            s for s in self.plan["scenarios"] if s["id"] != "IR-EVIDENCE-BREACH"
        ]
        with self.assertRaisesRegex(module.PlanError, "missing required scenarios"):
            module.validate_plan(self.plan)

    def test_duplicate_scenario_blocks(self):
        self.plan["scenarios"].append(copy.deepcopy(self.plan["scenarios"][0]))
        with self.assertRaisesRegex(module.PlanError, "duplicate"):
            module.validate_plan(self.plan)

    def test_secret_bearing_key_blocks(self):
        self.plan["api_key"] = "do-not-store"
        with self.assertRaisesRegex(module.PlanError, "secret-bearing key"):
            module.validate_plan(self.plan)

    def test_execution_claim_blocks(self):
        self.plan["execution_status"] = "PASS"
        with self.assertRaisesRegex(module.PlanError, "must remain PLANNED"):
            module.validate_plan(self.plan)

    def test_human_authority_is_required(self):
        self.plan["scenarios"][0]["human_authorities"] = []
        with self.assertRaisesRegex(module.PlanError, "expected non-empty array"):
            module.validate_plan(self.plan)

    def test_evidence_preservation_is_required(self):
        self.plan["scenarios"][0]["evidence_preservation"] = ["inspect system"]
        with self.assertRaisesRegex(module.PlanError, "explicitly preserve evidence"):
            module.validate_plan(self.plan)

    def test_source_revision_must_be_exact_git_identity(self):
        self.plan["source_revision"] = "main"
        with self.assertRaisesRegex(module.PlanError, "40-hex"):
            module.validate_plan(self.plan)


if __name__ == "__main__":
    unittest.main()
