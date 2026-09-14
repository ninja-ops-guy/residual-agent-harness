import json
import tempfile
import unittest
from pathlib import Path

from ai_providers.core import ChatResponse
from ai_providers.registry import Registry

from residual.assurance.external import (
    ExternalCase,
    ExternalEvidenceRunner,
    ExternalSuite,
    LiveEngineSpec,
    grade_external,
    load_external_suite,
    wilson_interval,
)
from residual.assurance.quality import AssuranceClass
from residual.engines.provider_bridge import ProviderEngineConfig, ProviderExecutionEngine


class FakeProvider:
    def __init__(self, name, outputs):
        self.name = name
        self.outputs = outputs

    def chat(self, req):
        prompt = req.messages[-1].content
        return ChatResponse(model=req.model, content=self.outputs[(req.model, prompt)], usage={"total_tokens": 7})


class ExternalEvidenceTests(unittest.TestCase):
    def registry(self):
        reg = Registry()
        reg.register("openai", lambda: FakeProvider("openai", {
            ("strong", "train-question"): "YES",
            ("strong", "eval-question"): "NO",
        }))
        reg.register("ollama", lambda: FakeProvider("ollama", {
            ("local", "train-question"): "NO",
            ("local", "eval-question"): "YES",
        }))
        return reg

    def suite(self):
        return ExternalSuite(
            name="independent-mini",
            author="external-evaluator",
            source_uri="https://example.invalid/frozen-suite",
            authored_at="2026-09-13T00:00:00Z",
            cases=(
                ExternalCase("train-1", "train", "text", AssuranceClass.ROUTINE, 0.10,
                             "train-question", {"kind": "exact_text", "expected": "YES"}),
                ExternalCase("eval-1", "evaluation", "text", AssuranceClass.ROUTINE, 0.10,
                             "eval-question", {"kind": "exact_text", "expected": "YES"}),
            ),
        )

    def engines(self):
        reg = self.registry()
        strong = ProviderExecutionEngine(ProviderEngineConfig("openai", "strong", ("text",)), registry=reg)
        local = ProviderExecutionEngine(ProviderEngineConfig("ollama", "local", ("text",), locality="local"), registry=reg)
        return (
            # Make the train-favored engine also the deterministic lower-cost choice
            # while profiles are still low-sample. Evaluation truth must not alter
            # this pre-decision state.
            LiveEngineSpec(strong, cost_per_task=0.01, location="cloud"),
            LiveEngineSpec(local, cost_per_task=0.02, location="local"),
        )

    def test_provider_bridge_executes_normalized_provider(self):
        engine = self.engines()[0].engine
        from residual.engines.protocol import ContextAssembly, TaskSpec
        result = engine.execute(TaskSpec("x", "text", "train-question"), ContextAssembly())
        self.assertEqual(result.candidate, "YES")
        self.assertEqual(result.token_usage, 7)
        self.assertEqual(result.raw_metadata["provider"], "openai")

    def test_evaluation_outcomes_do_not_leak_into_initial_market_decision(self):
        report = ExternalEvidenceRunner(self.suite(), self.engines()).run()
        row = report["evaluation_rows"][0]
        # Training evidence + predeclared cost favors strong; eval truth favors local.
        # If eval truth leaked into the profile before the decision, the runner could
        # select local and match the oracle instead of preserving the frozen choice.
        self.assertIn("openai", row["engine_id"])
        self.assertFalse(row["passed"])
        self.assertEqual(report["market"]["evaluation_successes"], 0)
        self.assertEqual(report["market"]["oracle_successes"], 1)

    def test_repeated_trials_are_independent_and_report_fixed_baselines(self):
        report = ExternalEvidenceRunner(self.suite(), self.engines(), trials=3).run()
        self.assertEqual(report["trials"], 3)
        self.assertEqual(report["evaluation_attempts"], 3)
        self.assertEqual([row["trial"] for row in report["evaluation_rows"]], [1, 2, 3])
        self.assertEqual(report["market"]["evaluation_successes"], 0)
        self.assertEqual(report["market"]["oracle_successes"], 3)
        self.assertEqual(report["baselines"]["cheapest_eligible"]["evaluation_successes"], 0)
        local = next(key for key in report["per_engine"] if key.startswith("ollama"))
        self.assertEqual(report["baselines"]["fixed_engine"][local]["success_rate"], 1.0)
        self.assertEqual(report["per_engine"][local]["evaluation_successes"], 3)
        self.assertLess(report["market"]["success_ci95"]["upper"], 1.0)
        self.assertGreater(report["per_engine"][local]["evaluation_success_ci95"]["lower"], 0.0)

    def test_wilson_interval_validates_counts(self):
        interval = wilson_interval(8, 10)
        self.assertLess(interval["lower"], 0.8)
        self.assertGreater(interval["upper"], 0.8)
        with self.assertRaises(ValueError):
            wilson_interval(2, 1)

    def test_suite_hash_binds_external_provenance_and_cases(self):
        a = self.suite()
        b = ExternalSuite(a.name, "different-author", a.source_uri, a.authored_at, a.cases)
        self.assertNotEqual(a.sha256, b.sha256)

    def test_loader_requires_external_provenance_and_split(self):
        source = self.suite()
        payload = {
            "schema_version": "residual.external-suite.v1",
            "name": source.name,
            "provenance": {
                "evidence_level": "externally_authored",
                "author": source.author,
                "source_uri": source.source_uri,
                "authored_at": source.authored_at,
            },
            "cases": [c.payload() for c in source.cases],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "suite.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_external_suite(path)
            self.assertEqual(loaded.sha256, source.sha256)

    def test_declarative_graders(self):
        self.assertTrue(grade_external("alpha beta", {"kind": "contains_all", "values": ["alpha", "beta"]}))
        self.assertTrue(grade_external('{"x":1}', {"kind": "json_exact", "expected": {"x": 1}}))
        self.assertTrue(grade_external("ABC-12", {"kind": "regex", "pattern": r"ABC-\d{2}"}))


if __name__ == "__main__":
    unittest.main()
