import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

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

    def __init__(self, name, output="YES"):
        self.name = name
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
        registry.register("openai", lambda: CountingProvider("openai"))
        registry.register("ollama", lambda: CountingProvider("ollama"))
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

    def test_budget_covers_every_trial_before_dispatch(self):
        runner = ExternalEvidenceRunner(self.suite(), self.engines(), trials=3,
                                        maximum_budget_usd=0.07)
        with self.assertRaises(EvidenceBudgetExceeded):
            runner.run()
        self.assertEqual(CountingProvider.calls, 5)
        self.assertAlmostEqual(float(runner._reserved_cost_usd), 0.07)

    def test_exact_decimal_budget_allows_all_trials(self):
        runner = ExternalEvidenceRunner(self.suite(), self.engines(), trials=3,
                                        maximum_budget_usd=0.18)
        report = runner.run()
        self.assertEqual(CountingProvider.calls, 12)
        self.assertEqual(report["trials"], 3)
        self.assertEqual(report["evaluation_attempts"], 3)
        self.assertEqual(report["budget"]["reserved_declared_cost_usd"], 0.18)

    def test_zero_budget_cannot_use_epsilon_to_buy_a_call(self):
        engines = tuple(replace(e, cost_per_task=5e-13) for e in self.engines())
        with self.assertRaises(EvidenceBudgetExceeded):
            ExternalEvidenceRunner(self.suite(), engines, maximum_budget_usd=0).run()
        self.assertEqual(CountingProvider.calls, 0)

    def test_preregistration_cannot_use_epsilon_to_freeze_overspend(self):
        from residual.assurance.preregistered import preregister_from_files
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            suite_path = root / "suite.json"
            engines_path = root / "engines.json"
            suite_path.write_text(json.dumps({
                "schema_version": "residual.external-suite.v1",
                "name": "epsilon-budget",
                "author": "external-evaluator",
                "source_uri": "https://example.invalid/epsilon-budget",
                "authored_at": "2026-09-16T00:00:00Z",
                "cases": [
                    {
                        "case_id": "train-1", "split": "train", "capability": "text",
                        "assurance": "routine", "difficulty": 0.1, "prompt": "q1",
                        "grader": {"kind": "exact_text", "expected": "YES"},
                    },
                    {
                        "case_id": "eval-1", "split": "evaluation", "capability": "text",
                        "assurance": "routine", "difficulty": 0.1, "prompt": "q2",
                        "grader": {"kind": "exact_text", "expected": "YES"},
                    },
                ],
            }), encoding="utf-8")
            engines_path.write_text(json.dumps({
                "schema_version": "residual.external-engines.v1",
                "engines": [
                    {"provider": "openai", "model": "m1", "cost_per_task": 1e-13},
                    {"provider": "ollama", "model": "m2", "cost_per_task": 1e-13},
                ],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preregistered budget"):
                preregister_from_files(
                    study_id="epsilon-budget", registered_at="2026-09-16T00:00:00Z",
                    suite_path=suite_path, engines_path=engines_path,
                    hypotheses=("budget remains bounded",),
                    primary_metric="market_success_rate", secondary_metrics=(),
                    maximum_budget_usd=0.0, runner_revision="test-only", trials=1,
                )
        self.assertEqual(CountingProvider.calls, 0)

    def test_failed_dispatch_keeps_its_reservation(self):
        runner = ExternalEvidenceRunner(self.suite(), self.engines(), maximum_budget_usd=0.01)
        with patch.object(CountingProvider, "chat", side_effect=RuntimeError("provider failed")) as call:
            with self.assertRaises(EvidenceBudgetExceeded):
                runner.run()
        self.assertEqual(call.call_count, 1)
        with self.assertRaises(EvidenceBudgetExceeded):
            runner.run()
        self.assertEqual(CountingProvider.calls, 0)

    def test_nonfinite_or_negative_costs_and_limits_are_refused(self):
        for value in [float("nan"), float("inf"), -float("inf"), -1.0]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ExternalEvidenceRunner(self.suite(), self.engines(), maximum_budget_usd=value)
                engines = tuple(replace(e, cost_per_task=value) for e in self.engines())
                with self.assertRaises(ValueError):
                    ExternalEvidenceRunner(self.suite(), engines)
        self.assertEqual(CountingProvider.calls, 0)

    def test_engine_budget_stop_is_not_relabelled_as_candidate_failure(self):
        runner = ExternalEvidenceRunner(self.suite(), self.engines(), maximum_budget_usd=1)
        with patch.object(CountingProvider, "chat", side_effect=EvidenceBudgetExceeded("adapter ceiling")) as call:
            with self.assertRaises(EvidenceBudgetExceeded):
                runner.run()
        self.assertEqual(call.call_count, 1)

    def test_cli_forwards_frozen_ceiling_to_actual_dispatch(self):
        from scripts import external_assurance_eval as cli
        from tests import test_preregistered_external as fixtures
        from residual.assurance.preregistered import preregister_from_files, write_preregistration
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            helper = fixtures.PreregisteredExternalTests()
            suite = helper.write_suite(root)
            engines = helper.write_engines(root)
            manifest = preregister_from_files(
                study_id="dispatch-boundary", registered_at="2026-09-16T00:00:00Z",
                suite_path=suite, engines_path=engines, hypotheses=("budget remains bounded",),
                primary_metric="market_success_rate", secondary_metrics=(),
                maximum_budget_usd=0.04, runner_revision="test-only", trials=2)
            frozen = root / "manifest.json"
            write_preregistration(frozen, manifest)
            output = root / "result.json"
            # An adapter loader returning costlier specs must still encounter
            # the frozen ceiling at dispatch, after the genuine preflight.
            with patch.object(cli, "load_engines", return_value=self.engines()):
                with self.assertRaises(EvidenceBudgetExceeded):
                    cli.main(["run", "--suite", str(suite), "--engines", str(engines),
                              "--manifest", str(frozen), "--output", str(output)])
            self.assertEqual(CountingProvider.calls, 3)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
