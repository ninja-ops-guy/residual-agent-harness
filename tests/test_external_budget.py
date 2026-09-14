import unittest

from ai_providers.core import ChatResponse
from ai_providers.registry import Registry

from residual.assurance.external import (
    EvidenceBudgetExceeded,
    ExternalCase,
    ExternalEvidenceRunner,
    ExternalSuite,
    LiveEngineSpec,
)
from residual.assurance.quality import AssuranceClass
from residual.engines.provider_bridge import ProviderEngineConfig, ProviderExecutionEngine


class CountingProvider:
    calls = 0

    def __init__(self, output="YES"):
        self.output = output

    def chat(self, req):
        type(self).calls += 1
        return ChatResponse(model=req.model, content=self.output, usage={"total_tokens": 1})


class ExternalBudgetTests(unittest.TestCase):
    def setUp(self):
        CountingProvider.calls = 0

    def suite(self):
        return ExternalSuite(
            name="budget-mini",
            author="external-evaluator",
            source_uri="https://example.invalid/budget-suite",
            authored_at="2026-09-14T00:00:00Z",
            cases=(
                ExternalCase("train-1", "train", "text", AssuranceClass.ROUTINE, 0.1,
                             "q1", {"kind": "exact_text", "expected": "YES"}),
                ExternalCase("eval-1", "evaluation", "text", AssuranceClass.ROUTINE, 0.1,
                             "q2", {"kind": "exact_text", "expected": "YES"}),
            ),
        )

    def engines(self):
        registry = Registry()
        registry.register("openai", lambda: CountingProvider())
        registry.register("ollama", lambda: CountingProvider())
        one = ProviderExecutionEngine(ProviderEngineConfig("openai", "m1", ("text",)), registry=registry)
        two = ProviderExecutionEngine(ProviderEngineConfig("ollama", "m2", ("text",), locality="local"), registry=registry)
        return (LiveEngineSpec(one, 0.01), LiveEngineSpec(two, 0.02))

    def test_budget_blocks_before_first_provider_dispatch(self):
        runner = ExternalEvidenceRunner(self.suite(), self.engines(), maximum_budget_usd=0.005)
        with self.assertRaises(EvidenceBudgetExceeded):
            runner.run()
        self.assertEqual(CountingProvider.calls, 0)

    def test_exact_budget_allows_declared_calls_and_is_reported(self):
        runner = ExternalEvidenceRunner(self.suite(), self.engines(), maximum_budget_usd=0.06)
        report = runner.run()
        self.assertEqual(CountingProvider.calls, 4)
        self.assertAlmostEqual(report["budget"]["reserved_declared_cost_usd"], 0.06)
        self.assertEqual(report["budget"]["maximum_budget_usd"], 0.06)


if __name__ == "__main__":
    unittest.main()
