from __future__ import annotations

import unittest

from residual.factory.scheduler import EngineOption, Scheduler, SchedulerMetrics, SchedulerTask
from residual.factory.worker_contract import WorkerContractError


class M4SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.scheduler = Scheduler(observe=self.events.append)

    def test_independence_fraction_tracks_ready_dag(self):
        tasks = (
            SchedulerTask('a'),
            SchedulerTask('b'),
            SchedulerTask('c', ('a',)),
            SchedulerTask('d', ('c',)),
        )
        self.assertEqual(self.scheduler.independence_fraction(tasks, set()), 0.5)
        self.assertEqual(self.scheduler.independence_fraction(tasks, {'a'}), 2 / 3)

    def test_local_engine_preferred_when_capability_equal(self):
        task = SchedulerTask('a', required_capabilities=('python',))
        local = EngineOption('local', ('python',), 2.0, 'local', 1)
        cloud = EngineOption('cloud', ('python',), 0.5, 'cloud', 10)
        selected = self.scheduler.select_engine(task, (cloud, local))
        self.assertEqual(selected.name, 'local')
        self.assertEqual(self.events[-1]['event'], 'SchedulerEngineSelected')

    def test_capability_gap_can_select_cloud(self):
        task = SchedulerTask('a', required_capabilities=('gpu',))
        local = EngineOption('local', ('python',), 0.1, 'local', 10)
        cloud = EngineOption('cloud', ('python', 'gpu'), 2.0, 'cloud', 2)
        self.assertEqual(self.scheduler.select_engine(task, (local, cloud)).name, 'cloud')

    def test_no_capable_engine_fails_closed(self):
        task = SchedulerTask('a', required_capabilities=('gpu',))
        with self.assertRaises(WorkerContractError):
            self.scheduler.select_engine(task, (EngineOption('local', ('python',), 1, 'local', 1),))

    def test_resize_adds_workers_for_independent_capacity_gap(self):
        metrics = SchedulerMetrics(active_workers=2, total_workers=2, blocked_tasks=1,
                                   total_tasks=12, verification_queue_depth=0, integration_conflicts=0)
        decision = self.scheduler.decide_resize(independent_tasks=10, metrics=metrics,
                                                current_workers=2, current_verifiers=1)
        self.assertGreater(decision['workers'], 2)
        self.assertFalse(decision['paused'])

    def test_resize_releases_workers_when_blocked(self):
        metrics = SchedulerMetrics(active_workers=1, total_workers=8, blocked_tasks=9,
                                   total_tasks=10, verification_queue_depth=0, integration_conflicts=0)
        decision = self.scheduler.decide_resize(independent_tasks=1, metrics=metrics,
                                                current_workers=8, current_verifiers=1)
        self.assertLess(decision['workers'], 8)

    def test_verification_queue_adds_verifiers(self):
        metrics = SchedulerMetrics(active_workers=2, total_workers=2, blocked_tasks=0,
                                   total_tasks=4, verification_queue_depth=9, integration_conflicts=0)
        decision = self.scheduler.decide_resize(independent_tasks=2, metrics=metrics,
                                                current_workers=2, current_verifiers=1)
        self.assertGreater(decision['verifiers'], 1)

    def test_conflict_threshold_pauses_scheduler(self):
        metrics = SchedulerMetrics(active_workers=2, total_workers=4, blocked_tasks=1,
                                   total_tasks=4, verification_queue_depth=0, integration_conflicts=3)
        decision = self.scheduler.decide_resize(independent_tasks=3, metrics=metrics,
                                                current_workers=4, current_verifiers=1)
        self.assertTrue(decision['paused'])
        self.assertIn('integration_conflict_threshold', decision['reasoning'])

    def test_structural_bottleneck_requests_replan(self):
        tasks = [SchedulerTask('root', failures=3)]
        previous = 'root'
        for i in range(10):
            task_id = f't{i}'
            tasks.append(SchedulerTask(task_id, dependencies=(previous,)))
            previous = task_id
        candidates = self.scheduler.structural_replan_candidates(tuple(tasks), set())
        self.assertEqual(candidates, ('root',))
        self.assertTrue(any(event['event'] == 'SchedulerReplanRequested' for event in self.events))


if __name__ == '__main__':
    unittest.main()
