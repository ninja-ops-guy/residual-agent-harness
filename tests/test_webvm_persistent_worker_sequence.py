from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from residual.workbench import browser_mailbox, browser_run, browser_worker
from residual.workbench.runner import verify_run


class PersistentWorkerSequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'; self.root.mkdir()
        self.mailbox = self.base / 'mailbox'; self.mailbox.mkdir()
        self.output = self.base / 'runs'; self.output.mkdir()
        self.control = self.mailbox / browser_worker.CONTROL_NAME
        self.pid_file = self.base / 'worker.pid'
        self.busy_file = self.base / 'worker.busy'
        self.poison_file = self.base / 'worker.poison'
        (self.root / 'README.md').write_text('fresh second source\nsecond line\n', encoding='utf-8')

    def write_request(self, mission_id: str, *, mode: str, files: list[str], required: list[str] | None = None):
        request = {
            'id': mission_id,
            'mode': mode,
            'prompt': 'persistent worker isolation test',
            'files': files,
            'required_text': required or [],
            'model': 'gpt-5-nano',
            'max_calls': 1,
            'max_output_tokens': 256,
            'cloud_consent': mode in {'live', 'build'},
        }
        (self.mailbox / f'{mission_id}.json').write_text(json.dumps(request), encoding='utf-8')
        return request

    def start_writer(self, commands: list[str]):
        errors: list[BaseException] = []

        def writer():
            try:
                for index, command in enumerate(commands):
                    deadline = time.monotonic() + 5.0
                    while self.control.exists():
                        if time.monotonic() >= deadline:
                            raise TimeoutError('worker control record was not consumed')
                        time.sleep(0.01)
                    # DataDevice publishes a complete record at the path. Use an
                    # atomic regular-file publication here so the test does not
                    # add a local truncate/write race absent from that contract.
                    publish = self.mailbox / (
                        f'.{browser_worker.CONTROL_NAME}.{threading.get_ident()}.{index}'
                    )
                    publish.write_text(command + '\n', encoding='ascii')
                    os.replace(publish, self.control)
                    # Wait for consumption only when another command still needs
                    # to be published. The final command may deliberately remain
                    # unconsumed when the worker exits fail-closed; requiring its
                    # consumption would turn that intended negative path into a
                    # test-thread timeout rather than proving no later dispatch.
                    if index + 1 < len(commands):
                        while self.control.exists():
                            if time.monotonic() >= deadline:
                                raise TimeoutError('worker control record was not consumed')
                            time.sleep(0.01)
            except BaseException as exc:  # surfaced in the test thread below
                errors.append(exc)

        thread = threading.Thread(target=writer, name='persistent-worker-command-writer')
        thread.start()
        return thread, errors

    def serve(self):
        return browser_worker.serve(
            control_file=self.control,
            pid_file=self.pid_file,
            busy_file=self.busy_file,
            poison_file=self.poison_file,
            mailbox=self.mailbox,
            root=self.root,
            output_root=self.output,
        )

    def test_bounded_live_failure_then_valid_live_mission_is_isolated(self):
        failed = 'm-' + 'a' * 32
        good = 'm-' + 'b' * 32
        rid = 'c' * 32

        self.write_request(failed, mode='live', files=['../escape.py'], required=['FIRST_ONLY'])
        self.write_request(good, mode='live', files=['README.md'], required=['SECOND_ONLY'])

        provider_value = {
            'updates': {
                'answer': {
                    'text': 'SECOND_ONLY answer from the second mission only.',
                    'citations': [{
                        'artifact_id': 'source-0',
                        'start_line': 1,
                        'end_line': 1,
                        'quote': 'fresh second source',
                    }],
                },
            },
            'requests': [],
        }
        response = {
            'request_id': rid,
            'ok': True,
            'text': json.dumps(provider_value, separators=(',', ':')),
            'usage': {'input_tokens': 10, 'output_tokens': 10},
        }
        response_path = self.mailbox / f'{good}-{rid}.json'
        response_path.write_text(json.dumps(response), encoding='utf-8')
        (self.mailbox / f'{good}-{rid}.json.ready').write_text('1', encoding='ascii')

        writer, errors = self.start_writer([
            f'{failed} live',
            f'{good} live',
            browser_worker.SHUTDOWN,
        ])
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(browser_mailbox.uuid, 'uuid4', return_value=SimpleNamespace(hex=rid)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = self.serve()
        writer.join(timeout=5)
        self.assertFalse(writer.is_alive(), 'command writer did not finish')
        self.assertEqual(errors, [])
        self.assertEqual(status, 0)

        transcript = stdout.getvalue()
        failed_marker = f'{browser_worker.RUN_PREFIX}{failed}:1'
        good_marker = f'{browser_worker.RUN_PREFIX}{good}:0'
        self.assertIn(failed_marker, transcript)
        self.assertIn(good_marker, transcript)
        self.assertLess(transcript.index(failed_marker), transcript.index(good_marker))
        self.assertIn(browser_worker.STOPPED, transcript)
        self.assertNotIn(browser_worker.FATAL_PREFIX, transcript)

        self.assertFalse((self.output / failed).exists())
        self.assertFalse(any(path.name.startswith(f'{failed}-') for path in self.mailbox.iterdir()))

        good_dir = self.output / good
        self.assertTrue((good_dir / 'answer.md').is_file())
        self.assertIn('SECOND_ONLY', (good_dir / 'answer.md').read_text(encoding='utf-8'))
        self.assertNotIn('FIRST_ONLY', (good_dir / 'answer.md').read_text(encoding='utf-8'))
        result, proof = verify_run(good_dir)
        self.assertTrue(proof['result_bound'])
        self.assertEqual(result['task_id'], good)
        summary = json.loads((good_dir / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['result']['task_id'], good)
        retained = (good_dir / 'trace.jsonl').read_text(encoding='utf-8') + (good_dir / 'summary.json').read_text(encoding='utf-8')
        self.assertNotIn(failed, retained)
        self.assertNotIn('FIRST_ONLY', retained)
        self.assertTrue(response_path.is_file())
        self.assertEqual(json.loads(response_path.read_text(encoding='utf-8'))['request_id'], rid)
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.busy_file.exists())
        self.assertFalse(self.control.exists())
        self.assertFalse(self.poison_file.exists())

    def test_runtime_typeerror_exits_before_queued_next_mission(self):
        first = 'm-' + 'd' * 32
        second = 'm-' + 'e' * 32
        self.write_request(first, mode='audit', files=['README.md'])
        self.write_request(second, mode='audit', files=['README.md'])

        writer, errors = self.start_writer([f'{first} audit', f'{second} audit'])
        stdout = io.StringIO()
        with (
            mock.patch.object(
                browser_run,
                'persistent_run',
                side_effect=[TypeError('impossible constructor return'), 0],
            ) as persistent_run,
            contextlib.redirect_stdout(stdout),
        ):
            status = self.serve()
        writer.join(timeout=5)
        self.assertFalse(writer.is_alive(), 'command writer did not finish')
        self.assertEqual(errors, [])
        self.assertEqual(status, 70)
        self.assertEqual(persistent_run.call_count, 1, 'fatal worker processed a later queued mission')

        transcript = stdout.getvalue()
        self.assertIn(f'{browser_worker.FATAL_PREFIX}{first}:70', transcript)
        self.assertNotIn(f'{browser_worker.RUN_PREFIX}{first}:', transcript)
        self.assertNotIn(f'{browser_worker.RUN_PREFIX}{second}:', transcript)
        self.assertFalse((self.output / second).exists())
        self.assertTrue(self.poison_file.is_file(), 'fatal worker did not durably poison generation')
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.busy_file.exists())
        if self.control.exists():
            self.assertEqual(self.control.read_text(encoding='ascii'), f'{second} audit\n')
        restart_stdout = io.StringIO()
        with contextlib.redirect_stdout(restart_stdout):
            self.assertEqual(self.serve(), 75)
        self.assertIn(browser_worker.POISONED, restart_stdout.getvalue())

    def test_mailbox_typeerror_crosses_engine_boundary_and_kills_worker(self):
        first = 'm-' + 'f' * 32
        second = 'm-' + '1' * 32
        rid = '2' * 32
        self.write_request(first, mode='live', files=['README.md'])
        self.write_request(second, mode='audit', files=['README.md'])
        (self.mailbox / f'{first}-{rid}.json.ready').write_text('1', encoding='ascii')

        writer, errors = self.start_writer([f'{first} live', f'{second} audit'])
        stdout = io.StringIO()
        with (
            mock.patch.object(browser_mailbox.uuid, 'uuid4', return_value=SimpleNamespace(hex=rid)),
            mock.patch.object(browser_mailbox, 'read_json', side_effect=TypeError('impossible constructor return')),
            contextlib.redirect_stdout(stdout),
        ):
            status = self.serve()
        writer.join(timeout=5)
        self.assertFalse(writer.is_alive(), 'command writer did not finish')
        self.assertEqual(errors, [])
        self.assertEqual(status, 70)

        transcript = stdout.getvalue()
        self.assertIn(f'{browser_worker.FATAL_PREFIX}{first}:70', transcript)
        self.assertNotIn(f'{browser_worker.RUN_PREFIX}{first}:', transcript)
        self.assertNotIn(f'{browser_worker.RUN_PREFIX}{second}:', transcript)
        self.assertTrue((self.output / first).is_dir(), 'incomplete failed mission evidence was discarded')
        self.assertFalse((self.output / first / 'result.json').exists())
        self.assertFalse((self.output / second).exists())
        self.assertFalse((self.output / '.active').exists(), 'Python finally did not release mission lock')
        self.assertTrue(self.poison_file.is_file())
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.busy_file.exists())
        if self.control.exists():
            self.assertEqual(self.control.read_text(encoding='ascii'), f'{second} audit\n')
        restart_stdout = io.StringIO()
        with contextlib.redirect_stdout(restart_stdout):
            self.assertEqual(self.serve(), 75)
        self.assertIn(browser_worker.POISONED, restart_stdout.getvalue())


class PersistentWorkerHostTimeoutTests(unittest.TestCase):
    def test_host_wiring_uses_durable_bound_recovery(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')
        self.assertIn('build_recovery_command', source)
        self.assertIn('async function terminateResidualWorker(missionId)', source)
        self.assertIn('residualWorkerRecovery', source)
        self.assertIn('await terminateResidualWorker(request.id)', source)
        self.assertIn('await terminateResidualWorker(null)', source)
        self.assertIn('/tmp/residual-workbench.poison', source)
        self.assertIn('/tmp/residual-workbench.busy', source)
        self.assertIn('/data/residual-worker.control', source)
        self.assertIn('RESIDUAL_WORKER_POISONED', source)
        self.assertIn('--poison-file /tmp/residual-workbench.poison', source)
        self.assertIn('reset guest before retry', source)


if __name__ == '__main__':
    unittest.main()
