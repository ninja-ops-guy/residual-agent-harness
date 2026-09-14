import unittest

from residual.assurance.evaluation import (
    AdaptiveEvaluation,
    FrozenAssuranceCase,
    FrozenAssuranceWorkload,
    VerifierDefect,
    evaluate_verifier_campaign,
)
from residual.assurance.market import MarketProfile
from residual.assurance.quality import AssuranceClass


class AdaptiveAssuranceEvaluationTests(unittest.TestCase):
    def workload(self):
        return FrozenAssuranceWorkload(
            name="mixed-granularity-v1",
            seed=7,
            cases=(
                FrozenAssuranceCase(
                    case_id="tiny-edit",
                    task_class="small-edit",
                    capability="code",
                    assurance=AssuranceClass.ROUTINE,
                    required_pass_rate=0.90,
                    direct_success=True,
                    swarm_success=True,
                    direct_cost=0.01,
                    swarm_cost=0.20,
                    direct_latency_ms=50,
                    swarm_latency_ms=450,
                    preferred_engine="cheap@1",
                    engine_outcomes={"cheap@1": True, "strong@1": True},
                ),
                FrozenAssuranceCase(
                    case_id="batch-refactor",
                    task_class="batch",
                    capability="code",
                    assurance=AssuranceClass.IMPORTANT,
                    required_pass_rate=0.90,
                    direct_success=False,
                    swarm_success=True,
                    direct_cost=0.04,
                    swarm_cost=0.16,
                    direct_latency_ms=120,
                    swarm_latency_ms=260,
                    preferred_engine="strong@1",
                    engine_outcomes={"cheap@1": False, "strong@1": True},
                ),
                FrozenAssuranceCase(
                    case_id="small-config",
                    task_class="small-edit",
                    capability="code",
                    assurance=AssuranceClass.ROUTINE,
                    required_pass_rate=0.90,
                    direct_success=True,
                    swarm_success=True,
                    direct_cost=0.01,
                    swarm_cost=0.18,
                    direct_latency_ms=40,
                    swarm_latency_ms=400,
                    preferred_engine="cheap@1",
                    engine_outcomes={"cheap@1": True, "strong@1": True},
                ),
                FrozenAssuranceCase(
                    case_id="wide-migration",
                    task_class="batch",
                    capability="code",
                    assurance=AssuranceClass.IMPORTANT,
                    required_pass_rate=0.90,
                    direct_success=False,
                    swarm_success=True,
                    direct_cost=0.05,
                    swarm_cost=0.17,
                    direct_latency_ms=150,
                    swarm_latency_ms=280,
                    preferred_engine="strong@1",
                    engine_outcomes={"cheap@1": False, "strong@1": True},
                ),
            ),
        )

    def engines(self):
        cheap = MarketProfile("cheap@1", frozenset({"code"}), 0.01, 40, alpha=20, beta=2, trials=20)
        strong = MarketProfile("strong@1", frozenset({"code"}), 0.05, 80, alpha=100, beta=1, trials=99)
        return cheap, strong

    def test_workload_hash_is_stable_and_binds_case_content(self):
        workload = self.workload()
        self.assertEqual(workload.sha256, workload.sha256)
        changed = FrozenAssuranceWorkload(
            name=workload.name,
            seed=workload.seed,
            cases=workload.cases[:-1],
        )
        self.assertNotEqual(workload.sha256, changed.sha256)

    def test_adaptive_strategy_beats_fixed_direct_on_mixed_workload(self):
        report = AdaptiveEvaluation(self.workload(), self.engines()).run()
        fixed = {row["policy"]: row for row in report["baselines"]}
        self.assertGreater(report["adaptive"]["success_rate"], fixed["direct"]["success_rate"])
        self.assertLess(report["adaptive"]["total_cost"], fixed["dynamic_swarm"]["total_cost"])

    def test_engine_quality_constraint_prefers_strong_profile(self):
        report = AdaptiveEvaluation(self.workload(), self.engines()).run()
        self.assertGreaterEqual(report["adaptive"]["engine_matches"], 2)

    def test_duplicate_case_ids_are_rejected(self):
        case = self.workload().cases[0]
        with self.assertRaises(ValueError):
            FrozenAssuranceWorkload(name="bad", cases=(case, case))


class VerifierCampaignTests(unittest.TestCase):
    def test_known_defects_measure_recall_and_false_acceptance(self):
        defects = [
            VerifierDefect("good-1", artifact_acceptable=True, verifier_passed=True, confidence=0.99),
            VerifierDefect("good-2", artifact_acceptable=True, verifier_passed=True, confidence=0.99),
            VerifierDefect("defect-detected-1", artifact_acceptable=False, verifier_passed=False, confidence=0.98),
            VerifierDefect("defect-detected-2", artifact_acceptable=False, verifier_passed=False, confidence=0.98),
            VerifierDefect("defect-missed", artifact_acceptable=False, verifier_passed=True, confidence=0.99),
        ]
        result = evaluate_verifier_campaign("host:security", defects)
        self.assertEqual(result.samples, 5)
        self.assertEqual(result.false_accepts, 1)
        self.assertAlmostEqual(result.defect_recall, 2 / 3)
        self.assertAlmostEqual(result.false_accept_rate, 1 / 3)
        self.assertTrue(result.requires_hitl)

    def test_clean_campaign_can_improve_posterior(self):
        defects = [VerifierDefect(f"case-{i}", artifact_acceptable=(i % 2 == 0), verifier_passed=(i % 2 == 0)) for i in range(40)]
        result = evaluate_verifier_campaign("host:clean", defects, assurance=AssuranceClass.ROUTINE)
        self.assertGreater(result.posterior_mean, 0.95)
        self.assertEqual(result.false_accepts, 0)


if __name__ == "__main__":
    unittest.main()
