"""Fail-closed historical inspection proof, allowing only background observations."""
import unittest
from demo.vm.mission_smoke import verify_inspection_history


class TimeTravelProofTests(unittest.TestCase):
    def setUp(self):
        self.before = [{'event_id': 'a', 'event_type': 'mission.finished', 'context': {'status': 'passed'}}]

    def test_unchanged(self):
        self.assertEqual(verify_inspection_history(self.before, self.before), [])

    def test_background_observation_can_append(self):
        after = self.before + [{'event_id': 'b', 'event_type': 'runtime.health_changed', 'context': {'health': 'ready'}}]
        self.assertEqual(verify_inspection_history(self.before, after), ['runtime.health_changed'])

    def test_existing_record_mutation_rejected(self):
        after = [{'event_id': 'a', 'event_type': 'mission.finished', 'context': {'status': 'failed'}}]
        with self.assertRaisesRegex(AssertionError, 'changed or deleted'):
            verify_inspection_history(self.before, after)

    def test_existing_record_deletion_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'changed or deleted'):
            verify_inspection_history(self.before, [])

    def test_execution_side_effect_rejected(self):
        for kind in ['mission.submitted', 'provider.mailbox_write_started', 'evidence.projected', 'recovery.guest_restart_requested']:
            with self.subTest(kind=kind), self.assertRaisesRegex(AssertionError, 'execution or unexpected'):
                verify_inspection_history(self.before, self.before + [{'event_id': 'b', 'event_type': kind}])

    def test_duplicate_identity_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'duplicate'):
            verify_inspection_history(self.before, self.before * 2)
