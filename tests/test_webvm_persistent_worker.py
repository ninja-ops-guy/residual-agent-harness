from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from residual.workbench import browser_worker


class PersistentBrowserWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mailbox = self.root / 'mailbox'; self.mailbox.mkdir()
        self.output = self.root / 'runs'; self.output.mkdir()
        self.mid = 'm-' + 'a' * 32

    def write_request(self, mode):
        path = self.mailbox / f'{self.mid}.json'
        path.write_text(json.dumps({'id': self.mid, 'mode': mode}))
        return path

    def test_command_contract_is_exact_and_bounded(self):
        self.assertEqual(browser_worker.parse_command(f'{self.mid} build\n'), (self.mid, 'build'))
        for value in [
            '', 'bad build', f'{self.mid} shell', f'{self.mid} build extra',
            '../escape build', 'm-' + 'a' * 32 + ';rm build', 'x' * 97,
            browser_worker.SHUTDOWN,
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                browser_worker.parse_command(value)

    def test_shutdown_is_separate_from_mission_command_contract(self):
        self.assertEqual(browser_worker.SHUTDOWN, 'shutdown')
        self.assertEqual(browser_worker.STOPPED, 'RESIDUAL_WORKER_STOPPED')

    def test_build_dispatch_reuses_in_process_entrypoint(self):
        request = self.write_request('build')
        with mock.patch.object(browser_worker.browser_build, 'main', return_value=2) as entry:
            status = browser_worker.dispatch(
                self.mid, 'build', mailbox=self.mailbox,
                root=self.root, output_root=self.output,
            )
        self.assertEqual(status, 2)
        argv = entry.call_args.args[0]
        self.assertEqual(argv[0:2], ['--request', str(request)])
        self.assertIn('--stream', argv)
        self.assertNotIn('run', argv)

    def test_audit_and_live_dispatch_share_persistent_run_entrypoint(self):
        for mode in ('audit', 'live'):
            with self.subTest(mode=mode):
                self.write_request(mode)
                with mock.patch.object(browser_worker.browser_run, 'main', return_value=0) as entry:
                    status = browser_worker.dispatch(
                        self.mid, mode, mailbox=self.mailbox,
                        root=self.root, output_root=self.output,
                    )
                self.assertEqual(status, 0)
                argv = entry.call_args.args[0]
                self.assertEqual(argv[0], 'run')
                self.assertIn('--stream', argv)

    def test_request_identity_and_mode_cannot_be_swapped(self):
        self.write_request('audit')
        with self.assertRaises(browser_worker.RequestAdmissionError):
            browser_worker.dispatch(
                self.mid, 'build', mailbox=self.mailbox,
                root=self.root, output_root=self.output,
            )

    def test_only_typed_admission_failure_is_reusable(self):
        kwargs = {'mailbox': self.mailbox, 'root': self.root, 'output_root': self.output}
        with mock.patch.object(
            browser_worker, 'dispatch',
            side_effect=browser_worker.RequestAdmissionError('bad request'),
        ):
            self.assertEqual(browser_worker._dispatch_admitted(self.mid, 'audit', **kwargs), 64)
        with mock.patch.object(browser_worker, 'dispatch', side_effect=TypeError('runtime corruption')):
            with self.assertRaises(TypeError):
                browser_worker._dispatch_admitted(self.mid, 'audit', **kwargs)

    def test_request_parse_typeerror_is_never_downgraded_to_admission(self):
        # Both retained production corruptions surfaced as impossible TypeErrors
        # from CPython internals. If one appears while read_json is executing, it
        # must escape so serve() emits a fatal marker and terminates the worker.
        with mock.patch.object(
            browser_worker, 'read_json', side_effect=TypeError('impossible constructor return')
        ):
            with self.assertRaisesRegex(TypeError, 'impossible constructor return'):
                browser_worker._request(self.mailbox, self.mid, 'audit')

    def test_json_decode_failure_remains_typed_admission(self):
        error = json.JSONDecodeError('partial request', '{', 1)
        with (
            mock.patch.object(browser_worker, 'read_json', side_effect=error),
            mock.patch.object(browser_worker.time, 'monotonic', side_effect=[0.0, 3.0]),
            mock.patch.object(browser_worker.time, 'sleep'),
        ):
            with self.assertRaises(browser_worker.RequestAdmissionError):
                browser_worker._request(self.mailbox, self.mid, 'audit')

    @unittest.skipUnless(os.name == 'posix', 'PID-file safety uses POSIX no-follow/link semantics')
    def test_pid_file_never_follows_symlink_or_truncates_hardlink(self):
        sentinel = self.root / 'sentinel'
        sentinel.write_text('do-not-touch', encoding='ascii')
        pid_file = self.root / 'worker.pid'

        pid_file.symlink_to(sentinel)
        with self.assertRaises(RuntimeError):
            browser_worker._write_pid_file(pid_file)
        self.assertEqual(sentinel.read_text(encoding='ascii'), 'do-not-touch')
        pid_file.unlink()

        os.link(sentinel, pid_file)
        with self.assertRaises(RuntimeError):
            browser_worker._write_pid_file(pid_file)
        self.assertEqual(sentinel.read_text(encoding='ascii'), 'do-not-touch')

    def test_worker_module_does_not_spawn_subprocesses(self):
        source = Path(browser_worker.__file__).read_text(encoding='utf-8')
        self.assertNotIn('subprocess', source)
        self.assertNotIn('os.system', source)
        self.assertIn('browser_build.main(common)', source)
        self.assertIn('browser_run.main(["run", *common])', source)
        self.assertIn('line.strip() == SHUTDOWN', source)


class PersistentWorkerHostWiringTests(unittest.TestCase):
    def source(self):
        root = Path(__file__).resolve().parents[1]
        return (root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')

    def test_mission_control_starts_one_persistent_python_worker(self):
        source = self.source()
        self.assertIn('python3 -m residual.workbench.browser_worker', source)
        self.assertNotIn('python3 -m ${entry}', source)
        self.assertNotIn('cx.run("/usr/bin/python3"', source)
        self.assertIn('RESIDUAL_WORKER_READY', source)
        self.assertIn('RESIDUAL_WORKER_RUN_', source)
        self.assertIn('/tmp/residual-workbench.pid', source)

    def test_reused_worker_requires_fifo_and_process_identity(self):
        source = self.source()
        self.assertIn('[ -p /tmp/residual-workbench.fifo ]', source)
        self.assertIn('[ ! -L /tmp/residual-workbench.pid ]', source)
        self.assertIn("mapfile -d '' residual_worker_argv", source)
        self.assertIn('/proc/$residual_worker_pid/cmdline', source)
        self.assertIn('${residual_worker_argv[2]-}', source)
        self.assertIn('residual.workbench.browser_worker', source)

    def test_per_mission_dispatch_contains_only_validated_identity_and_mode(self):
        source = self.source()
        self.assertIn("const command = `printf '%s\\\\n' '${request.id} ${request.mode}' > /tmp/residual-workbench.fifo`;", source)
        self.assertIn('Invalid mission ID', source)
        self.assertIn('Invalid mission mode', source)
        self.assertNotIn('request.prompt}', source)

    def test_poisoned_worker_requires_restart(self):
        source = self.source()
        self.assertIn('residualWorkerPoisoned = true;', source)
        self.assertIn('Guest worker requires restart', source)
        self.assertIn('!residualWorkerPoisoned', source)
        self.assertIn('RESIDUAL_WORKER_FATAL_', source)


if __name__ == '__main__':
    unittest.main()
