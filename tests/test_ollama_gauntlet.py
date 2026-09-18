from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_providers import ChatResponse, ProviderError
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
            with self.assertRaises(ProviderError) as caught:
                g.provider_live_suite(provider="ollama", model="missing:test", repeats=1)
        self.assertEqual(caught.exception.code, "model_not_found")

    def test_provider_scaling_reports_real_concurrency_curve(self):
        with patch.object(g, "DEFAULT_REGISTRY", FakeRegistry()):
            result = g.provider_scaling_suite(
                provider="ollama", model="tiny:test", repeats=1,
                concurrencies=(1, 2),
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([p["concurrency"] for p in result["points"]], [1, 2])
        self.assertTrue(all(p["summary"]["correct"] == 5 for p in result["points"]))
        self.assertTrue(all(p["requests_per_second"] > 0 for p in result["points"]))



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
    def test_repeated_factory_suite_aggregates_without_hiding_inconclusive_trials(self):
        rows = [
            {
                "suite": "factory_live_fixed", "status": "PASS",
                "wall_clock_seconds": 2.0, "accepted": 5, "workers": 5,
                "unsafe_acceptances": 0, "author_tokens": 10,
            },
            {
                "suite": "factory_live_fixed", "status": "INCONCLUSIVE",
                "wall_clock_seconds": 3.0, "accepted": 2, "workers": 5,
                "unsafe_acceptances": 0, "author_tokens": 12,
            },
        ]
        with patch.object(g, "factory_live_suite", side_effect=rows):
            result = g.factory_live_repeated_suite(
                provider="ollama", model="tiny:test", output_root=Path("/tmp/unused"),
                strategy="fixed", repeats=2,
            )
        self.assertEqual(result["status"], "INCONCLUSIVE")
        self.assertEqual(result["repeat_count"], 2)
        self.assertEqual(result["accepted"], 7)
        self.assertEqual(result["workers"], 10)
        self.assertEqual(result["wall_clock_seconds_mean"], 2.5)
        self.assertEqual(result["unsafe_acceptances"], 0)


    def test_frozen_source_corpus_is_hash_bound_and_provenanced(self):
        authored_source = "write_file('answer-001.txt','42')"
        with patch.object(g, "_author_source", return_value=(authored_source, 11, 7)):
            result = g.author_frozen_source_corpus(
                provider="ollama", model="tiny:test", cases=g.DEFAULT_CASES[:1],
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["metadata"][0]["source_origin"], "paired_corpus_authoring")
        self.assertEqual(
            result["metadata"][0]["source_sha256"],
            __import__("hashlib").sha256(authored_source.encode()).hexdigest(),
        )
        self.assertEqual(
            result["source_corpus_sha256"],
            g.digest({"arith-01": authored_source}),
        )

    def test_paired_scheduler_reuses_identical_source_corpus_for_all_strategies(self):
        frozen = {
            "status": "PASS",
            "provider": "ollama",
            "model": "tiny:test",
            "sources": {"arith-01": "write_file('answer-001.txt','42')"},
            "metadata": [{"case_id": "arith-01", "source_sha256": "a" * 64,
                          "tokens": 11, "wall_clock_ms": 7, "error": None}],
            "source_corpus_sha256": "b" * 64,
            "author_tokens": 11,
            "author_wall_clock_ms": 7,
        }
        timings = {"single": 4.0, "fixed": 2.0, "dynamic": 3.0}

        def fake_run(**kwargs):
            strategy = kwargs["strategy"]
            wall = timings[strategy]
            return {
                "suite": f"factory_live_{strategy}",
                "status": "PASS",
                "wall_clock_seconds_mean": wall,
                "verified_useful_throughput_per_second": 5.0 / wall,
            }

        with patch.object(g, "author_frozen_source_corpus", return_value=frozen), \
             patch.object(g, "factory_live_repeated_suite", side_effect=fake_run) as run:
            result = g.factory_paired_scheduler_suite(
                provider="ollama", model="tiny:test", output_root=Path("/tmp/unused"),
                repeats=3, cases=g.DEFAULT_CASES[:1],
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_corpus_sha256"], "b" * 64)
        self.assertEqual(result["speedup_vs_single"]["fixed"], 2.0)
        self.assertAlmostEqual(result["speedup_vs_single"]["dynamic"], 4.0 / 3.0)
        self.assertEqual(len(run.call_args_list), 3)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["preauthored_sources"], frozen["sources"])
            self.assertEqual(call.kwargs["source_corpus_sha256"], "b" * 64)
            self.assertEqual(call.kwargs["run_label"], "paired")

    def test_gauntlet_rejects_zero_repeats_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bad"
            with self.assertRaisesRegex(ValueError, "positive integer"):
                g.run_gauntlet(output=out, provider="ollama", model="tiny:test", repeats=0)
            self.assertFalse(out.exists())

    def test_gauntlet_report_hash_binds_report_body(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(g, "provider_live_suite",
                          return_value={"suite": "provider_live", "status": "PASS"}), \
             patch.object(g, "provider_scaling_suite",
                          return_value={"suite": "provider_scaling", "status": "PASS", "points": []}), \
             patch.object(g, "cluster_loopback_suite",
                          return_value={"suite": "cluster_loopback", "status": "PASS"}):
            report = g.run_gauntlet(
                output=Path(tmp) / "run", provider="ollama", model="tiny:test",
                repeats=1, include_factory=False,
            )
        body = dict(report)
        recorded = body.pop("report_sha256")
        self.assertEqual(recorded, g.digest(body))

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
