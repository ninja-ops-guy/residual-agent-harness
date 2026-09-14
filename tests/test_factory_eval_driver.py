from __future__ import annotations

import threading
import time
import unittest

from residual.engines.protocol import EngineHealth, EngineResult
from residual.factory.eval_driver import CostRates, EngineBackedEvaluationDriver, FinalizedRun
from residual.factory.eval_framework import EvaluationError, FrozenEvalTask, FrozenWorkload


def workload():
    return FrozenWorkload(
        "measured",
        ("R1", "R2", "R3"),
        (
            FrozenEvalTask("root", ("R1",), (), ("root-pass",)),
            FrozenEvalTask("left", ("R2",), ("root",), ("left-pass",)),
            FrozenEvalTask("right", ("R3",), ("root",), ("right-pass",)),
        ),
        "a" * 40,
        "b" * 40,
        "fake-engine",
        "1.0",
        0.0,
        7,
    )


class FakeEngine:
    name = "fake-engine"
    version = "1.0"
    capability_class = "agent"
    locality = "local"

    def __init__(self, provenance="measured", delay=0.01):
        self.provenance = provenance
        self.delay = delay
        self.active = 0
        self.peak = 0
        self.lock = threading.Lock()

    def supports(self, capability):
        return capability == "agent"

    def health(self):
        return EngineHealth.HEALTHY

    def normalize(self, raw):
        return raw

    def execute(self, task, context):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(self.delay)
            return EngineResult(
                candidate={"task": task.task_id, "deps": sorted(context.values.get("dependencies", {}))},
                token_usage=10,
                wall_clock_ms=int(self.delay * 1000),
                raw_metadata={"provenance": self.provenance, "gpu_time_ms": 60.0, "api_cost_usd": 0.01},
            )
        finally:
            with self.lock:
                self.active -= 1


class EvalDriverTests(unittest.TestCase):
    def finalizer(self, w, outputs, config, run_index):
        self.assertEqual(set(outputs), {"root", "left", "right"})
        return FinalizedRun(w.expected_output_commit, 3, 3, 0)

    def test_single_is_serial_and_measured(self):
        engine = FakeEngine()
        driver = EngineBackedEvaluationDriver(engine, finalizer=self.finalizer)
        events = []
        result = driver.run(workload(), "single", 1, events.append)
        self.assertFalse(result.simulation)
        self.assertEqual(result.accepted_tasks, 3)
        self.assertEqual(result.token_cost_total, 30)
        self.assertEqual(result.output_commit, workload().expected_output_commit)
        self.assertEqual(engine.peak, 1)
        self.assertTrue(any(e["event"] == "MeasuredFactoryRunCompleted" for e in events))

    def test_dynamic_uses_ready_frontier_concurrently(self):
        engine = FakeEngine(delay=0.05)
        driver = EngineBackedEvaluationDriver(engine, finalizer=self.finalizer, max_workers=8)
        result = driver.run(workload(), "dynamic", 1, lambda e: None)
        self.assertEqual(result.accepted_tasks, 3)
        self.assertGreaterEqual(engine.peak, 2)

    def test_fixed_worker_bound(self):
        engine = FakeEngine(delay=0.03)
        driver = EngineBackedEvaluationDriver(engine, finalizer=self.finalizer, fixed_workers=1, max_workers=8)
        driver.run(workload(), "fixed", 1, lambda e: None)
        self.assertEqual(engine.peak, 1)

    def test_requires_measured_provenance(self):
        driver = EngineBackedEvaluationDriver(FakeEngine("fixture"), finalizer=self.finalizer)
        with self.assertRaises(EvaluationError):
            driver.run(workload(), "single", 1, lambda e: None)

    def test_requires_reported_tokens(self):
        class Missing(FakeEngine):
            def execute(self, task, context):
                r = super().execute(task, context)
                return EngineResult(candidate=r.candidate, token_usage=None, raw_metadata=r.raw_metadata)
        with self.assertRaises(EvaluationError):
            EngineBackedEvaluationDriver(Missing(), finalizer=self.finalizer).run(workload(), "single", 1, lambda e: None)

    def test_engine_identity_is_frozen(self):
        engine = FakeEngine()
        engine.version = "2.0"
        with self.assertRaises(EvaluationError):
            EngineBackedEvaluationDriver(engine, finalizer=self.finalizer).run(workload(), "single", 1, lambda e: None)

    def test_cost_accounting_prefers_provider_cost(self):
        driver = EngineBackedEvaluationDriver(
            FakeEngine(), finalizer=self.finalizer,
            rates=CostRates(api_per_1k_tokens_usd=99, gpu_per_minute_usd=2,
                            infrastructure_per_minute_usd=1),
        )
        result = driver.run(workload(), "single", 1, lambda e: None)
        self.assertAlmostEqual(result.api_cost_usd, 0.03, places=6)
        self.assertGreater(result.gpu_cost_usd, 0)
        self.assertGreater(result.infrastructure_cost_usd, 0)


if __name__ == "__main__":
    unittest.main()
