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

from residual.workbench import browser_mailbox, browser_worker


class BrowserCorruptionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'; self.root.mkdir()
        self.mailbox = self.base / 'mailbox'; self.mailbox.mkdir()
        self.output = self.base / 'runs'; self.output.mkdir()
        self.fifo = self.base / 'worker.fifo'
        self.pid_file = self.base / 'worker.pid'
        (self.root / 'README.md').write_text('corruption boundary source\n', encoding='utf-8')

    def request(self, mission_id: str, mode: str = 'live'):
        value = {
            'id': mission_id,
            'mode': mode,
            'prompt': 'exercise browser corruption boundary',
            'files': ['README.md'],
            'required_text': [],
            'model': 'gpt-5-nano',
            'max_calls': 1,
            'max_output_tokens': 256,
            'cloud_consent': mode == 'live',
        }
        (self.mailbox / f'{mission_id}.json').write_text(json.dumps(value), encoding='utf-8')
        return value

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
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=writer, name='browser-corruption-command-writer')
        thread.start()
        return thread, errors

    def test_corruption_sentinel_is_not_generic_provider_exception(self):
        self.assertTrue(issubclass(browser_mailbox.BrowserRuntimeCorruption, BaseException))
        self.assertFalse(issubclass(browser_mailbox.BrowserRuntimeCorruption, Exception))

    def test_mailbox_typeerror_crosses_engine_and_poison_worker(self):
        first = 'm-' + 'a' * 32
        second = 'm-' + 'b' * 32
        rid = 'c' * 32
        self.request(first, 'live')
        self.request(second, 'audit')

        # Make publication look complete so the live provider reaches read_json.
        response = self.mailbox / f'{first}-{rid}.json'
        response.write_text('{}', encoding='utf-8')
        (self.mailbox / f'{first}-{rid}.json.ready').write_text('1', encoding='ascii')

        writer, errors = self.start_writer([
            f'{first} live',
            f'{second} audit',
        ])
        stdout = io.StringIO()
        with (
            mock.patch.object(browser_mailbox.uuid, 'uuid4', return_value=SimpleNamespace(hex=rid)),
            mock.patch.object(
                browser_mailbox,
                'read_json',
                side_effect=TypeError('impossible constructor return'),
            ),
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
        self.assertFalse((self.output / second).exists())
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.fifo.exists())
        # execute() must still unwind its cooperative workspace lock when the
        # corruption sentinel propagates normally through Python.
        self.assertFalse((self.output / '.active').exists())


if __name__ == '__main__':
    unittest.main()
