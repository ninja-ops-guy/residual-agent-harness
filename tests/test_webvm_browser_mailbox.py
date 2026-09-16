from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from residual.providers import ProviderError
from residual.workbench.browser_mailbox import BrowserMailboxProvider


class BrowserMailboxProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mailbox = Path(self.tmp.name)
        self.mid = 'm-' + 'a' * 32

    def provider(self, responder):
        def emit(kind, data):
            if kind == 'inference_requested':
                responder(data)
        return BrowserMailboxProvider('openai/gpt-5-nano', self.mid, self.mailbox, emit, lambda: False)

    def response_path(self, request):
        return self.mailbox / f"{self.mid}-{request['request_id']}.json"

    def ready_path(self, request):
        path = self.response_path(request)
        return path.with_name(path.name + '.ready')

    def publish(self, request, payload):
        self.response_path(request).write_text(json.dumps(payload))
        self.ready_path(request).write_text('1')

    def test_safe_provider_error_survives_as_typed_provider_error(self):
        def respond(request):
            self.publish(request, {
                'request_id': request['request_id'],
                'ok': False,
                'error': 'provider_authorization_failed',
            })
        provider = self.provider(respond)
        with self.assertRaisesRegex(ProviderError, 'provider_authorization_failed'):
            provider.generate({'goal': 'build'}, 256)

    def test_unknown_provider_body_is_not_propagated(self):
        def respond(request):
            self.publish(request, {
                'request_id': request['request_id'],
                'ok': False,
                'error': 'secret-upstream-body-with-token',
            })
        provider = self.provider(respond)
        with self.assertRaisesRegex(ProviderError, '^provider_error$'):
            provider.generate({'goal': 'build'}, 256)

    def test_response_is_not_consumed_until_ready_marker_exists(self):
        timers = []
        def respond(request):
            path = self.response_path(request)
            ready = self.ready_path(request)
            path.write_text('{"request_id":')
            good = json.dumps({
                'request_id': request['request_id'],
                'ok': True,
                'text': '{"updates":{},"requests":[]}',
                'usage': {'input_tokens': 2, 'output_tokens': 3},
            })
            def finish_publication():
                path.write_text(good)
                ready.write_text('1')
            timer = threading.Timer(0.08, finish_publication)
            timers.append(timer)
            timer.start()
        provider = self.provider(respond)
        reply = provider.generate({'goal': 'build'}, 256)
        for timer in timers:
            timer.join()
        self.assertEqual(reply.text, '{"updates":{},"requests":[]}')
        self.assertEqual(reply.usage.input_tokens, 2)
        self.assertEqual(reply.usage.output_tokens, 3)

    def test_transient_browser_filesystem_oserror_after_ready_is_retried(self):
        observed = {}
        def respond(request):
            observed.update(request)
            self.publish(request, {
                'request_id': request['request_id'],
                'ok': True,
                'text': '{"updates":{},"requests":[]}',
                'usage': {'input_tokens': 5, 'output_tokens': 7},
            })
        provider = self.provider(respond)
        original = __import__('residual.workbench.browser_mailbox', fromlist=['read_json']).read_json
        calls = {'count': 0}
        def flaky_read(path, limit):
            calls['count'] += 1
            if calls['count'] == 1:
                raise OSError('transient browser-backed read fault')
            return original(path, limit)
        with mock.patch('residual.workbench.browser_mailbox.read_json', side_effect=flaky_read):
            reply = provider.generate({'goal': 'build'}, 256)
        self.assertGreaterEqual(calls['count'], 2)
        self.assertEqual(reply.text, '{"updates":{},"requests":[]}')
        self.assertEqual(reply.usage.input_tokens, 5)
        self.assertEqual(reply.usage.output_tokens, 7)


class BrowserMailboxPublicationSourceTests(unittest.TestCase):
    def source(self):
        root = Path(__file__).resolve().parents[1]
        return (root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')

    def test_host_publishes_body_before_ready_marker(self):
        source = self.source()
        body_write = 'await residualDataDevice.writeFile(path, text);'
        ready_write = 'await residualDataDevice.writeFile(path + ".ready", "1");'
        self.assertIn(body_write, source)
        self.assertIn(ready_write, source)
        self.assertLess(source.index(body_write), source.index(ready_write))
        self.assertIn('Invalid mailbox path', source)
        self.assertIn('-cancel\\\\.json', source)

    def test_workbench_uses_persistent_guest_worker_not_per_mission_python(self):
        source = self.source()
        self.assertNotIn('cx.run("/usr/bin/python3"', source)
        self.assertNotIn('python3 -m ${entry}', source)
        self.assertIn('python3 -m residual.workbench.browser_worker', source)
        self.assertIn('RESIDUAL_WORKER_RUN_', source)
        self.assertIn('/data/residual-worker.control', source)
        self.assertIn('/tmp/residual-workbench.busy', source)
        self.assertNotIn('/tmp/residual-workbench.fifo', source)
        self.assertNotIn('mkfifo', source)
        self.assertIn('Guest command already active', source)

    def test_worker_control_is_published_after_request_body(self):
        source = self.source()
        request_write = 'await residualDataDevice.writeFile(name, JSON.stringify(request));'
        control_write = 'residualDataDevice.writeFile(\n                        "/residual-worker.control"'
        self.assertIn(request_write, source)
        self.assertIn(control_write, source)
        self.assertLess(source.index(request_write), source.index(control_write))
        self.assertIn('request.id + " " + request.mode + "\\\\n"', source)

    def test_terminal_input_is_queued_not_dropped_while_worker_is_active(self):
        source = self.source()
        self.assertIn('var residualShellInputBuffer = "";', source)
        self.assertIn('residualShellInputBuffer += data;', source)
        self.assertIn('const queuedInput = residualShellInputBuffer;', source)
        self.assertIn('if (queuedInput) readData(queuedInput);', source)
        self.assertIn('residualShellCommandBusy = true;', source)

    def test_completion_frames_are_projected_before_worker_marker_resolution(self):
        source = self.source()
        projection = 'residualWorkbench?.onOutput(out);'
        marker = 'const normal = new RegExp('
        self.assertIn(projection, source)
        self.assertIn(marker, source)
        self.assertLess(source.index(projection), source.index(marker))

    def test_worker_fatal_marker_poisoning_is_fail_closed(self):
        source = self.source()
        self.assertIn('RESIDUAL_WORKER_FATAL_', source)
        self.assertIn('residualWorkerPoisoned = true;', source)
        self.assertIn('!residualWorkerPoisoned', source)
        self.assertIn('await terminateResidualWorker(current.missionId)', source)


if __name__ == '__main__':
    unittest.main()
