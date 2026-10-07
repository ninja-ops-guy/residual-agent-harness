import unittest

from residual.assurance import (
    AssuranceClass,
    ExecutionStrategy,
    MarketProfile,
    MarketRequest,
    OrchestrationTaxController,
    VerifiedComputeMarket,
    VerifierQualityProfile,
)


class VerifierQualityTests(unittest.TestCase):
    def test_false_accepts_reduce_quality_and_trigger_hitl(self):
        p = VerifierQualityProfile("security-policy")
        for _ in range(30):
            p.record_outcome(verifier_passed=True, artifact_acceptable=True, confidence=0.99)
        for _ in range(4):
            p.record_outcome(verifier_passed=True, artifact_acceptable=False, confidence=0.99)
        self.assertGreater(p.false_accept_rate, 0)
        self.assertTrue(p.requires_hitl(AssuranceClass.SECURITY_CRITICAL))

    def test_low_sample_high_stakes_is_not_trusted(self):
        p = VerifierQualityProfile("new-verifier")
        self.assertTrue(p.requires_hitl(AssuranceClass.SAFETY_CRITICAL))


class OrchestrationTests(unittest.TestCase):
    def test_controller_learns_not_to_swarm(self):
        c = OrchestrationTaxController()
        task = {"task_class": "small-edit"}
        for _ in range(25):
            c.observe(task, ExecutionStrategy.DIRECT, success=True, cost=0.01, latency_ms=100)
            c.observe(task, ExecutionStrategy.DYNAMIC_SWARM, success=True, cost=0.20, latency_ms=500)
        chosen = c.choose(task, [ExecutionStrategy.DIRECT, ExecutionStrategy.DYNAMIC_SWARM])
        self.assertEqual(chosen, ExecutionStrategy.DIRECT)
        self.assertGreater(c.orchestration_tax(task), 0)


class MarketTests(unittest.TestCase):
    def test_market_prefers_lowest_cost_engine_meeting_quality(self):
        m = VerifiedComputeMarket(exploration_strength=0.0)
        a = MarketProfile("cheap", frozenset({"code"}), 0.1, 100)
        b = MarketProfile("expensive", frozenset({"code"}), 1.0, 100)
        a.alpha, a.beta, a.trials = 100, 1, 99
        b.alpha, b.beta, b.trials = 100, 1, 99
        m.register(a)
        m.register(b)
        decision = m.select(MarketRequest("code", required_pass_rate=0.95, allow_exploration=False))
        self.assertEqual(decision.engine_id, "cheap")

    def test_verifier_reliability_weights_engine_update(self):
        m = VerifiedComputeMarket()
        p = MarketProfile("e", frozenset({"code"}), 0.1, 100)
        m.register(p)
        before = p.pass_rate
        m.update("e", verifier_passed=True, verifier_reliability=0.55)
        self.assertLess(p.pass_rate, before + 0.2)


if __name__ == "__main__":
    unittest.main()
