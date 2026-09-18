from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_providers import ChatResponse
from residual.cluster.transport import LoopbackTransport
from residual.eval import ollama_gauntlet as g
from residual.factory.models import FrozenPlan
from residual.factory.runtime import RuntimeResult
from residual.factory.runtime_workspace import CandidateTree


class FakeProvider:
    name = "ollama"

    def list_models(self):
        return ["tiny:test"]

    def chat(self, req):
        answer = {
            "Compute 17 + 25. Return only the answer.": "42",
            "Compute 99 + 1. Return only the answer.": "100",
            "Reverse the string residual. Return only the reversed string.": "laudiser",
            "Reverse the string harness. Return only the reversed string.": "ssenrah",
            "Return exactly the text RESIDUAL_OK.": "RESIDUAL_OK",
        }[req.messages[-1].content]
        return ChatResponse(
            model=req.model,
            content=answer,
            usage={"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8},
        )


class FakeRegistry:
    def get(self, name):
        if name != "ollama":
            raise AssertionError(name)
        return FakeProvider()


class ProviderSuiteTests(unittest.TestCase):
    def test_provider_suite_uses_real_provider_boundary_and_usage(self):
        with patch.object(g, "DEFAULT_REGISTRY", FakeRegistry()):
            result = g.provider_live_suite(provider="ollama", model="tiny:test", repeats=2)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["summary"]["observations"], 10)
        self.assertEqual(result["summary"]["correct"], 10)
        self.assertEqual(result["summary"]["input_tokens"], 70)
        self.assertEqual(result["summary"]["output_tokens"], 10)

    def test_missing_ollama_model_fails_closed(self):
        with patch.object(g, "DEFAULT_REGISTRY", FakeRegistry()):
            with self.assertRaisesRegex(ValueError, "not installed"):
                g.provider_live_suite(provider="ollama", model="missing:test", repeats=1)


class ClusterSuiteTests(unittest.TestCase):
    def tearDown(self):
        LoopbackTransport.reset_registry()

    def test_loopback_suite_exercises_failure_receipt_and_reassignment(self):
        result = g.cluster_loopback_suite(model="tiny:test")
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["wan_claim"])
        self.assertEqual(result["initial_route"], "remote-fast")
        self.assertIn("remote-fast", result["failed_nodes"])
        self.assertTrue(result["failure_receipt_captured"])
        self.assertEqual(result["after_failure"]["state"], "completed")
        self.assertNotEqual(result["after_failure"]["assigned_node"], "remote-fast")


class FactoryBindingTests(unittest.TestCase):
    def test_contracts_bind_exact_plan_and_provider_engine(self):
        cases = g.DEFAULT_CASES[:2]
        plan = g._plan_for_cases(cases)
        approval = FrozenPlan.approve(plan, "test")
        approval.assert_matches(plan)
        with tempfile.TemporaryDirectory() as tmp:
            contracts = g._contracts_for_cases(
                cases=cases,
                plan=plan,
                input_commit="a" * 40,
                work_root=Path(tmp),
                engine_id="provider:ollama:tiny@test@provider-bridge-v1",
                attempt_prefix="unit",
            )
        self.assertEqual(len(contracts), 2)
        for contract in contracts:
            contract.assert_matches_plan(plan)
            self.assertEqual(
                contract.engine_hint,
                "provider:ollama:tiny@test@provider-bridge-v1",
            )
            self.assertEqual(contract.acceptance, ("exact-output",))
            self.assertIn("secret.txt", contract.forbidden)

    def test_exact_file_verifier_refuses_wrong_candidate(self):
        case = g.DEFAULT_CASES[0]
        plan = g._plan_for_cases((case,))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = g._contracts_for_cases(
                cases=(case,),
                plan=plan,
                input_commit="a" * 40,
                work_root=root,
                engine_id="provider:ollama:tiny@test@provider-bridge-v1",
                attempt_prefix="verify",
            )[0]
            workspace = Path(contract.workspace_root)
            workspace.mkdir(parents=True)
            output = contract.allowed_outputs[0]
            (workspace / output).write_text("41", encoding="utf-8")
            candidate = CandidateTree(
                contract.input_commit,
                "b" * 40,
                "c" * 40,
                ((output, "d" * 64),),
            )
            result = RuntimeResult(
                contract.attempt_id,
                "CANDIDATE",
                contract.contract_hash,
                contract.execution_plan_hash,
                0,
                True,
                {},
                candidate,
                "awaiting_station_verification",
            )
            decision = g._decision_for(contract, result, case.expected)
        self.assertEqual(decision.verdict, "fail")
        self.assertEqual(decision.results, (("exact-output", "fail"),))


if __name__ == "__main__":
    unittest.main()
