from __future__ import annotations

import unittest
from unittest.mock import patch

from residual.factory import doctor


class DoctorTests(unittest.TestCase):
    def test_model_digest_requires_installed_model(self):
        with patch.object(doctor, '_json_get', return_value={'models': [{'name': 'x:1', 'digest': 'abc'}]}):
            self.assertEqual(doctor._model_digest('http://local', 'x:1'), 'abc')
            with self.assertRaises(doctor.DoctorError):
                doctor._model_digest('http://local', 'missing')

    def test_canary_requires_structured_output_and_usage(self):
        good = {'message': {'content': '{"ok":true}'}, 'prompt_eval_count': 3,
                'eval_count': 2, 'eval_duration': 1000}
        with patch.object(doctor, '_json_post', return_value=good):
            row = doctor._canary('http://local', 'model')
        self.assertTrue(row['ok'])
        self.assertEqual(row['total_tokens'], 5)
        bad = {'message': {'content': '{"ok":true}'}}
        with patch.object(doctor, '_json_post', return_value=bad):
            with self.assertRaises(doctor.DoctorError):
                doctor._canary('http://local', 'model')

    def test_calibration_uses_observed_aggregate_throughput(self):
        def fake_canary(_url, _model, seed=7):
            return {'ok': True, 'elapsed_s': 0.01, 'prompt_tokens': 5,
                    'completion_tokens': 5, 'total_tokens': 10, 'eval_duration_ns': 0}
        times = iter([0.0, 1.0, 2.0, 2.5, 3.0, 5.0])
        with patch.object(doctor, '_canary', side_effect=fake_canary), \
             patch.object(doctor.time, 'monotonic', side_effect=lambda: next(times)):
            result = doctor._calibrate('http://local', 'm', (1, 2, 4))
        self.assertEqual(result['recommended_workers'], 2)
        self.assertEqual([r['width'] for r in result['measurements']], [1, 2, 4])

    def test_collect_profile_fail_closed_on_missing_seccomp(self):
        with patch.object(doctor, '_git_probe', return_value={'version': 'git', 'root': '/x', 'tracked_clean': True, 'worktree': True}), \
             patch.object(doctor.ctypes.util, 'find_library', side_effect=lambda name: None if name == 'seccomp' else 'lib'), \
             patch.object(doctor.os, 'pidfd_open', create=True):
            profile = doctor.collect_profile()
        self.assertEqual(profile['status'], 'not_ready')
        self.assertFalse(profile['checks']['seccomp']['ok'])


if __name__ == '__main__':
    unittest.main()
