import unittest
from residual.loop.state import MissionStatus, ProgressVector
from residual.observability.metrics import MetricsRegistry
from residual.observability.loop_metrics import LoopMetrics

class LoopMetricsTests(unittest.TestCase):
    def test_loop_metrics_use_bounded_mode_labels(self):
        registry=MetricsRegistry(); metrics=LoopMetrics(registry)
        p=ProgressVector(2.0,1.0,1,1,True,False,True)
        metrics.iteration(mode="host-owned",progress=p,escalated=True)
        metrics.terminal(mode="host-owned",status=MissionStatus.COMPLETE)
        self.assertEqual(registry["residual_loop_iterations_total"].samples()[("host-owned",)],1.0)
        self.assertEqual(registry.label_names("residual_loop_completion_total"),("mode","status"))
        self.assertNotIn("goal_id",registry.label_names("residual_loop_iterations_total"))

if __name__ == "__main__": unittest.main()
