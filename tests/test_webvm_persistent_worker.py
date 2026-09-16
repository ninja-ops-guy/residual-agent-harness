from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from residual.core import ContractError
from residual.workbench import browser_worker, conversation_build, runner
from residual.workbench.browser_mailbox import BrowserMailboxProvider


class PersistentBrowserWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mailbox = self.root / 'mailbox'; self.mailbox.mkdir()
        self.output = self.root / 'runs'; self.output.mkdir()
        self.control = self.mailbox / browser_worker.CONTROL_NAME
        self.mid = 'm-' + 'a' * 32

    def write_request(self, mode):
        request = {'id': self.mid, 'mode': mode}
        path = self.mailbox / f'{self.mid}.json'
        path.write_text(json.dumps(request))
        return path, request

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

    def test_regular_control_record_requires_complete_newline(self):
        self.control.write_text(f'{self.mid} audit', encoding='ascii')
        self.assertIsNone(browser_worker._consume_control(self.control))
        self.assertTrue(self.control.is_file())
        self.control.write_text(f'{self.mid} audit\n', encoding='ascii')
        self.assertEqual(browser_worker._consume_control(self.control), (self.mid, 'audit'))
        self.assertFalse(self.control.exists())

    @unittest.skipUnless(os.name == 'posix', 'control-path symlink safety is POSIX-specific')
    def test_control_record_never_follows_symlink(self):
        target = self.root / 'sentinel'
        target.write_text(f'{self.mid} audit\n', encoding='ascii')
        self.control.symlink_to(target)
        with self.assertRaises(RuntimeError):
            browser_worker._consume_control(self.control)
        self.assertEqual(target.read_text(encoding='ascii'), f'{self.mid} audit\n')

    def test_browser_entrypoints_do_not_mutate_core_provider_defaults(self):
        self.assertIsNot(runner.MailboxProvider, BrowserMailboxProvider)
        self.assertIs(conversation_build.MailboxProvider, runner.MailboxProvider)
        self.assertTrue(issubclass(BrowserMailboxProvider, runner.MailboxProvider))

    def test_build_dispatch_reuses_fail_closed_in_process_entrypoint(self):
        _path, request = self.write_request('build')
        with mock.patch.object(browser_worker.browser_build, 'persistent_build', return_value=2) as entry:
            status = browser_worker.dispatch(
                self.mid, 'build', mailbox=self.mailbox,
                root=self.root, output_root=self.output,
            )
        self.assertEqual(status, 2)
        entry.assert_called_once_with(
            request=request,
            mailbox=self.mailbox,
            root=self.root,
            output_root=self.output,
        )

    def test_audit_and_live_dispatch_share_fail_closed_persistent_entrypoint(self):
        for mode in ('audit', 'live'):
            with self.subTest(mode=mode):
                _path, request = self.write_request(mode)
                with mock.patch.object(browser_worker.browser_run, 'persistent_run', return_value=0) as entry:
                    status = browser_worker.dispatch(
                        self.mid, mode, mailbox=self.mailbox,
                        root=self.root, output_root=self.output,
                    )
                self.assertEqual(status, 0)
                entry.assert_called_once_with(
                    request=request,
                    mailbox=self.mailbox,
                    root=self.root,
                    output_root=self.output,
                )

    def test_admission_returns_exact_validated_request_object(self):
        _path, expected = self.write_request('audit')
        self.assertEqual(browser_worker._request(self.mailbox, self.mid, 'audit'), expected)

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

    def test_persistent_run_does_not_mask_runtime_typeerror(self):
        _path, request = self.write_request('audit')
        with mock.patch.object(
            browser_worker.browser_run.implementation,
            'execute',
            side_effect=TypeError('impossible constructor return'),
        ) as execute:
            with self.assertRaisesRegex(TypeError, 'impossible constructor return'):
                browser_worker.browser_run.persistent_run(
                    request=request,
                    mailbox=self.mailbox,
                    root=self.root,
                    output_root=self.output,
                )
        self.assertIs(execute.call_args.kwargs['mailbox_provider_type'], BrowserMailboxProvider)

    def test_persistent_build_does_not_mask_runtime_typeerror(self):
        _path, request = self.write_request('build')
        with mock.patch.object(
            browser_worker.browser_build.implementation,
            'execute',
            side_effect=TypeError('impossible constructor return'),
        ) as execute:
            with self.assertRaisesRegex(TypeError, 'impossible constructor return'):
                browser_worker.browser_build.persistent_build(
                    request=request,
                    mailbox=self.mailbox,
                    root=self.root,
                    output_root=self.output,
                )
        self.assertIs(execute.call_args.kwargs['mailbox_provider_type'], BrowserMailboxProvider)

    def test_typed_contract_failure_stays_bounded_in_persistent_entrypoint(self):
        _path, request = self.write_request('audit')
        with mock.patch.object(
            browser_worker.browser_run.implementation,
            'execute',
            side_effect=ContractError('bad user contract'),
        ):
            self.assertEqual(
                browser_worker.browser_run.persistent_run(
                    request=request,
                    mailbox=self.mailbox,
                    root=self.root,
                    output_root=self.output,
                ),
                1,
            )

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

    def test_worker_module_does_not_require_fifo_or_spawn_subprocesses(self):
        source = Path(browser_worker.__file__).read_text(encoding='utf-8')
        self.assertNotIn('subprocess', source)
        self.assertNotIn('os.system', source)
        self.assertNotIn('os.mkfifo', source)
        self.assertIn('browser_build.persistent_build(', source)
        self.assertIn('browser_run.persistent_run(', source)
        self.assertNotIn('browser_build.main(common)', source)
        self.assertNotIn('browser_run.main(["run", *common])', source)
        self.assertIn("command == SHUTDOWN", source)


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
        self.assertIn('--control-file /data/residual-worker.control', source)
        self.assertNotIn('/tmp/residual-workbench.fifo', source)

    def test_reused_worker_requires_idle_process_identity(self):
        source = self.source()
        self.assertIn('[ -e /tmp/residual-workbench.busy ]', source)
        self.assertIn('[ -e /data/residual-worker.control ]', source)
        self.assertIn('[ ! -L /tmp/residual-workbench.pid ]', source)
        self.assertIn("mapfile -d '' residual_worker_argv", source)
        self.assertIn('/proc/$residual_worker_pid/cmdline', source)
        self.assertIn(r'\${residual_worker_argv[1]-}', source)
        self.assertIn(r'\${residual_worker_argv[2]-}', source)
        self.assertIn('residual.workbench.browser_worker', source)

    def test_reuse_shell_input_cannot_echo_the_ready_marker(self):
        source = self.source()
        self.assertNotIn('echo RESIDUAL_WORKER_READY', source)
        self.assertIn("printf 'RESIDUAL_WORKER_%s", source)
        self.assertIn("READY; else python3 -m residual.workbench.browser_worker", source)

    def test_per_mission_dispatch_uses_regular_datadevice_control_record(self):
        source = self.source()
        self.assertIn('"/residual-worker.control"', source)
        self.assertIn('request.id + " " + request.mode + "\\\\n"', source)
        self.assertIn('Invalid mission ID', source)
        self.assertIn('Invalid mission mode', source)
        self.assertNotIn('request.prompt}', source)
        self.assertNotIn('mkfifo', source)

    def test_poisoned_worker_requires_restart(self):
        source = self.source()
        self.assertIn('residualWorkerPoisoned = true;', source)
        self.assertIn('Guest worker requires restart', source)
        self.assertIn('!residualWorkerPoisoned', source)
        self.assertIn('RESIDUAL_WORKER_FATAL_', source)


if __name__ == '__main__':
    unittest.main()
