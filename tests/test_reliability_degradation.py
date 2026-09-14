from __future__ import annotations

import unittest

from residual.engines.protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec
from residual.experiments.degradation import DegradationProfile, DegradingExecutionEngine


class StubEngine:
    name = "stub"
    version = "v1"
    capability_class = "text"
    locality = "local"

    def execute(self, task, context):
        return EngineResult(candidate={"a": 1, "b": 2}, token_usage=7, wall_clock_ms=11,
                            raw_metadata={"source": "stub"})

    def supports(self, capability):
        return capability == "text"

    def health(self):
        return EngineHealth.HEALTHY

    def normalize(self, raw_output):
        return EngineResult(candidate=raw_output)


class DegradationProfileTests(unittest.TestCase):
    def test_profile_validation(self):
        with self.assertRaises(ValueError):
            DegradationProfile("", 0.5, 1)
        with self.assertRaises(ValueError):
            DegradationProfile("x", 1.1, 1)
        with self.assertRaises(ValueError):
            DegradationProfile("x", 0.5, -1)
        with self.assertRaises(ValueError):
            DegradationProfile("x", 0.5, 1, "unknown")

    def test_zero_rate_preserves_candidate(self):
        engine = DegradingExecutionEngine(StubEngine(), DegradationProfile("nominal", 0.0, 42))
        result = engine.execute(TaskSpec("task-1", "text", "hello"), ContextAssembly())
        self.assertEqual(result.candidate, {"a": 1, "b": 2})
        self.assertFalse(result.raw_metadata["degradation"]["mutated"])
        self.assertEqual(result.token_usage, 7)
        self.assertEqual(result.wall_clock_ms, 11)

    def test_full_rate_mutates_candidate(self):
        engine = DegradingExecutionEngine(StubEngine(), DegradationProfile("severe", 1.0, 42))
        result = engine.execute(TaskSpec("task-1", "text", "hello"), ContextAssembly())
        self.assertEqual(result.candidate, {"b": 2})
        self.assertTrue(result.raw_metadata["degradation"]["mutated"])
        self.assertNotEqual(
            result.raw_metadata["degradation"]["original_candidate_sha256"],
            result.raw_metadata["degradation"]["candidate_sha256"],
        )

    def test_decision_is_reproducible(self):
        profile = DegradationProfile("medium", 0.5, 123)
        engine = DegradingExecutionEngine(StubEngine(), profile)
        task = TaskSpec("task-9", "text", "hello")
        first = engine.execute(task, ContextAssembly())
        second = engine.execute(task, ContextAssembly())
        self.assertEqual(first.candidate, second.candidate)
        self.assertEqual(first.raw_metadata["degradation"], second.raw_metadata["degradation"])

    def test_seed_changes_profile_binding(self):
        one = DegradationProfile("medium", 0.5, 1)
        two = DegradationProfile("medium", 0.5, 2)
        self.assertNotEqual(one.sha256, two.sha256)

    def test_identity_and_capabilities_are_preserved(self):
        engine = DegradingExecutionEngine(StubEngine(), DegradationProfile("medium", 0.5, 1))
        self.assertEqual(engine.name, "stub")
        self.assertEqual(engine.version, "v1")
        self.assertEqual(engine.health(), EngineHealth.HEALTHY)
        self.assertTrue(engine.supports("text"))
        self.assertFalse(engine.supports("code"))


if __name__ == "__main__":
    unittest.main()
