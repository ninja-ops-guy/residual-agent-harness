from __future__ import annotations

import contextlib
import io
import json
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
        self.fifo = self.base / 'worker.fifo'
        self.pid_file = self.base / 'worker.pid'
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
                deadline = time.monotonic() + 5.0
                while not self.fifo.exists():
                    if time.monotonic() >= deadline:
                        raise TimeoutError('worker FIFO was not created')
                    time.sleep(0.01)
                with self.fifo.open('w', encoding='ascii') as stream:
                    stream.write('\n'.join(commands) + '\n')
                    stream.flush()
            except BaseException as exc:  # surfaced in the test thread below
                errors.append(exc)

        thread = threading.Thread(target=writer, name='persistent-worker-command-writer')
        thread.start()
        return thread, errors

    def test_bounded_live_failure_then_valid_live_mission_is_isolated(self):
        failed = 'm-' + 'a' * 32
        good = 'm-' + 'b' * 32
        rid = 'c' * 32

        # The first mission is admitted but fails its user contract before provider
        # dispatch. The worker must report a bounded nonzero result and remain reusable.
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
            status = browser_worker.serve(
                fifo=self.fifo,
                pid_file=self.pid_file,
                mailbox=self.mailbox,
                root=self.root,
                output_root=self.output,
            )
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

        # The bounded failure never created accepted run state or provider traffic.
        self.assertFalse((self.output / failed).exists())
        self.assertFalse(any(path.name.startswith(f'{failed}-') for path in self.mailbox.iterdir()))

        # The second mission owns its provider response and all retained evidence.
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
        self.assertFalse(self.fifo.exists())

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
            status = browser_worker.serve(
                fifo=self.fifo,
                pid_file=self.pid_file,
                mailbox=self.mailbox,
                root=self.root,
                output_root=self.output,
            )
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
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.fifo.exists())

    def test_mailbox_typeerror_crosses_engine_boundary_and_kills_worker(self):
        first = 'm-' + 'f' * 32
        second = 'm-' + '1' * 32
        rid = '2' * 32
        self.write_request(first, mode='live', files=['README.md'])
        self.write_request(second, mode='audit', files=['README.md'])
        # Make the browser response visible so the real BrowserMailboxProvider
        # reaches read_json(), then inject the retained impossible TypeError there.
        (self.mailbox / f'{first}-{rid}.json.ready').write_text('1', encoding='ascii')

        writer, errors = self.start_writer([f'{first} live', f'{second} audit'])
        stdout = io.StringIO()
        with (
            mock.patch.object(browser_mailbox.uuid, 'uuid4', return_value=SimpleNamespace(hex=rid)),
            mock.patch.object(browser_mailbox, 'read_json', side_effect=TypeError('impossible constructor return')),
            contextlib.redirect_stdout(stdout),
        ):
            status = browser_worker.serve(
                fifo=self.fifo,
                pid_file=self.pid_file,
                mailbox=self.mailbox,
                root=self.root,
                output_root=self.output,
            )
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
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.fifo.exists())


class PersistentWorkerHostTimeoutTests(unittest.TestCase):
    def test_startup_and_mission_timeouts_terminate_only_verified_worker(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')
        self.assertIn('function terminateResidualWorker()', source)
        self.assertGreaterEqual(source.count('terminateResidualWorker();'), 2)
        self.assertIn('kill -KILL "$residual_worker_pid"', source)
        self.assertIn('[ ! -L /tmp/residual-workbench.pid ]', source)
        self.assertIn('[ -O /tmp/residual-workbench.pid ]', source)
        self.assertIn("mapfile -d '' residual_worker_argv", source)
        self.assertIn(r'\${residual_worker_argv[2]-}', source)
        self.assertIn('residual.workbench.browser_worker', source)


if __name__ == '__main__':
    unittest.main()
