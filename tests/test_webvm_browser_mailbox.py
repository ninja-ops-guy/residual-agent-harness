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
        good = {
            'request_id': None,
            'ok': True,
            'text': '{"updates":{},"requests":[]}',
            'usage': {'input_tokens': 5, 'output_tokens': 7},
        }
        original = __import__('residual.workbench.browser_mailbox', fromlist=['read_json']).read_json
        calls = {'count': 0}
        def flaky_read(path, limit):
            calls['count'] += 1
            if calls['count'] == 1:
                raise OSError('transient browser-backed read fault')
            value = original(path, limit)
            good['request_id'] = observed['request_id']
            return value
        with mock.patch('residual.workbench.browser_mailbox.read_json', side_effect=flaky_read):
            reply = provider.generate({'goal': 'build'}, 256)
        self.assertGreaterEqual(calls['count'], 2)
        self.assertEqual(reply.text, '{"updates":{},"requests":[]}')
        self.assertEqual(reply.usage.input_tokens, 5)
        self.assertEqual(reply.usage.output_tokens, 7)


class BrowserMailboxPublicationSourceTests(unittest.TestCase):
    def test_host_publishes_body_before_ready_marker(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'demo/vm/install_workbench.py').read_text(encoding='utf-8')
        body_write = 'await residualDataDevice.writeFile(path, text);'
        ready_write = 'await residualDataDevice.writeFile(path + ".ready", "1");'
        self.assertIn(body_write, source)
        self.assertIn(ready_write, source)
        self.assertLess(source.index(body_write), source.index(ready_write))
        self.assertIn('Invalid mailbox response path', source)


if __name__ == '__main__':
    unittest.main()
