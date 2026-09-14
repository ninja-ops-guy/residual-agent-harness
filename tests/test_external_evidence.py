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
            LiveEngineSpec(strong, cost_per_task=0.02, location="cloud"),
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
        # Training evidence favors strong; eval truth favors local. If eval truth leaked,
        # the market would pick local and match the oracle instead of failing this case.
        self.assertIn("openai", row["engine_id"])
        self.assertFalse(row["passed"])
        self.assertEqual(report["market"]["evaluation_successes"], 0)
        self.assertEqual(report["market"]["oracle_successes"], 1)

    def test_suite_hash_binds_external_provenance_and_cases(self):
        a = self.suite()
        b = ExternalSuite(a.name, "different-author", a.source_uri, a.authored_at, a.cases)
        self.assertNotEqual(a.sha256, b.sha256)

    def test_loader_requires_external_provenance_and_split(self):
        payload = {
            "schema_version": "residual.external-suite.v1",
            "name": "external",
            "provenance": {
                "evidence_level": "externally_authored",
                "author": "someone-else",
                "source_uri": "https://example.invalid/suite",
                "authored_at": "2026-09-13T00:00:00Z",
            },
            "cases": [c.payload() for c in self.suite().cases],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "suite.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_external_suite(path)
            self.assertEqual(loaded.sha256, self.suite().sha256)

    def test_declarative_graders(self):
        self.assertTrue(grade_external("alpha beta", {"kind": "contains_all", "values": ["alpha", "beta"]}))
        self.assertTrue(grade_external('{"x":1}', {"kind": "json_exact", "expected": {"x": 1}}))
        self.assertTrue(grade_external("ABC-12", {"kind": "regex", "pattern": r"ABC-\d{2}"}))


if __name__ == "__main__":
    unittest.main()
