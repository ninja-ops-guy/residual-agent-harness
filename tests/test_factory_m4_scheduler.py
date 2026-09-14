from __future__ import annotations

import unittest

from residual.assurance.market import MarketProfile, VerifiedComputeMarket
from residual.factory.m4_evidence import ReadyDagSnapshot
from residual.factory.m4_scheduler import (
    M4AdaptiveScheduler,
    SchedulerCapacity,
    SchedulerNode,
    SchedulerPolicy,
)
from residual.factory.models import ExecutionPlan, FactoryTask, Requirement


class M4SchedulerTests(unittest.TestCase):
    def setUp(self):
        requirements = tuple(
            Requirement(f"R{i}", f"requirement {i}", ("unit",)) for i in range(1, 14)
        )
        tasks = [FactoryTask("root", "high fanout blocker", ("R1",))]
        for i in range(2, 13):
            tasks.append(FactoryTask(f"child{i}", f"child {i}", (f"R{i}",), depends_on=("root",)))
        tasks.append(FactoryTask("free", "independent", ("R13",)))
        self.plan = ExecutionPlan("scheduler", requirements, tuple(tasks))
        self.market = VerifiedComputeMarket()
        self.market.register(MarketProfile(
            "local@1", frozenset({"python", "reasoning"}), 0.01, 20.0,
            location="local",
        ))
        self.market.register(MarketProfile(
            "cloud@1", frozenset({"python", "reasoning", "vision"}), 0.10, 40.0,
            location="cloud",
        ))
        self.events: list[dict] = []

    def scheduler(self, *, local_active=0, policy=None):
        return M4AdaptiveScheduler(
            self.plan,
            self.market,
            (
                SchedulerNode("local-node", "local@1", "local", frozenset({"python", "reasoning"}),
                              capacity=2, active_slots=local_active),
                SchedulerNode("cloud-node", "cloud@1", "cloud", frozenset({"python", "reasoning", "vision"}),
                              capacity=8),
            ),
            policy=policy,
            observe=self.events.append,
        )

    def snapshot(self, *, ready=("free",), blocked=tuple(f"child{i}" for i in range(2, 13)) + ("root",)):
        return ReadyDagSnapshot(
            plan_hash=self.plan.graph_hash,
            completed_tasks=(),
            ready_tasks=tuple(ready),
            blocked_tasks=tuple(blocked),
            independence_fraction=len(ready) / (len(ready) + len(blocked)),
            receipt_hashes=(),
        )

    def test_local_engine_preferred_when_capability_equal(self):
        placement = self.scheduler().select_engine("free", "python")
        self.assertEqual((placement.engine_id, placement.node_id, placement.locality),
                         ("local@1", "local-node", "local"))
        self.assertEqual(placement.reason, "local_capability_equal_preferred")
        self.assertEqual(self.events[-1]["event"], "M4EngineSelected")

    def test_cloud_used_for_capability_gap_or_local_exhaustion(self):
        scheduler = self.scheduler()
        vision = scheduler.select_engine("free", "vision")
        self.assertEqual(vision.engine_id, "cloud@1")
        self.assertEqual(vision.reason, "cloud_selected_for_capability_gap")

        exhausted = self.scheduler(local_active=2).select_engine("free", "python")
        self.assertEqual(exhausted.engine_id, "cloud@1")
        self.assertEqual(exhausted.reason, "cloud_selected_local_capacity_exhausted")

    def test_measurements_cover_all_required_bottlenecks(self):
        result = self.scheduler().measure(
            self.snapshot(),
            total_workers=4,
            active_workers=3,
            verification_queue_depth=5,
            integration_conflicts=1,
            integration_attempts=4,
        )
        self.assertEqual(result.worker_utilization, 0.75)
        self.assertEqual(result.verification_queue_depth, 5)
        self.assertEqual(result.integration_conflict_rate, 0.25)
        self.assertEqual(result.independent_tasks, 1)
        self.assertEqual(result.blocked_tasks, 12)
        self.assertGreater(result.blocked_task_ratio, 0.9)
        self.assertEqual(self.events[-1]["event"], "M4SchedulerMeasurements")

    def test_resize_adds_workers_and_verifiers_when_pressure_demands(self):
        scheduler = self.scheduler(policy=SchedulerPolicy(imbalance_ratio=2, verification_queue_threshold=2))
        snapshot = self.snapshot(ready=("root", "free", "child2", "child3", "child4", "child5"), blocked=("child6",))
        measurements = scheduler.measure(
            snapshot,
            total_workers=2,
            active_workers=2,
            verification_queue_depth=5,
            integration_conflicts=0,
            integration_attempts=3,
        )
        capacity, actions = scheduler.resize(measurements, SchedulerCapacity(2, 1, max_workers=8, max_verifiers=4))
        self.assertEqual((capacity.workers, capacity.verifiers), (3, 2))
        self.assertEqual({action.resource for action in actions}, {"workers", "verifiers"})
        self.assertTrue(all(action.action == "resize" for action in actions))

    def test_resize_releases_workers_when_blocked_dominates(self):
        scheduler = self.scheduler()
        measurements = scheduler.measure(
            self.snapshot(),
            total_workers=6,
            active_workers=1,
            verification_queue_depth=0,
            integration_conflicts=0,
            integration_attempts=1,
        )
        capacity, actions = scheduler.resize(measurements, SchedulerCapacity(6, 1, min_workers=1, max_workers=8))
        self.assertEqual(capacity.workers, 5)
        self.assertEqual(actions[-1].reason, "blocked_tasks_dominate_independent_tasks")

    def test_conflict_pressure_pauses_before_resize(self):
        policy = SchedulerPolicy(integration_conflict_threshold=1)
        scheduler = self.scheduler(policy=policy)
        measurements = scheduler.measure(
            self.snapshot(ready=("root", "free", "child2", "child3", "child4"), blocked=("child5",)),
            total_workers=2,
            active_workers=2,
            verification_queue_depth=10,
            integration_conflicts=2,
            integration_attempts=2,
        )
        initial = SchedulerCapacity(2, 1, max_workers=8, max_verifiers=8)
        capacity, actions = scheduler.resize(measurements, initial)
        self.assertEqual(capacity, initial)
        self.assertEqual(len(actions), 1)
        self.assertEqual((actions[0].action, actions[0].resource), ("pause", "integration"))
        self.assertEqual(self.events[-1]["event"], "M4SchedulerPaused")

    def test_structural_bottleneck_generates_new_plan_proposal(self):
        scheduler = self.scheduler()
        proposals = scheduler.structural_replan({"root": 3})
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.blocking_task_id, "root")
        self.assertGreaterEqual(len(proposal.downstream_tasks), 10)
        self.assertEqual(len(proposal.replacement_task_ids), 2)
        self.assertNotEqual(proposal.source_plan_hash, proposal.replacement_plan_hash)
        self.assertNotIn("root", {task.id for task in proposal.replacement_plan.tasks})
        replacement_ids = set(proposal.replacement_task_ids)
        for task in proposal.replacement_plan.tasks:
            if task.id.startswith("child"):
                self.assertTrue(replacement_ids <= set(task.depends_on))
        self.assertEqual(self.events[-1]["event"], "M4StructuralReplan")

    def test_structural_replan_does_not_trigger_below_threshold(self):
        scheduler = self.scheduler()
        self.assertEqual(scheduler.structural_replan({"root": 2}), ())
        self.assertEqual(scheduler.structural_replan({"free": 9}), ())


if __name__ == "__main__":
    unittest.main()
