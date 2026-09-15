from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest

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

    def test_safe_provider_error_survives_as_typed_provider_error(self):
        def respond(request):
            self.response_path(request).write_text(json.dumps({
                'request_id': request['request_id'],
                'ok': False,
                'error': 'provider_authorization_failed',
            }))
        provider = self.provider(respond)
        with self.assertRaisesRegex(ProviderError, 'provider_authorization_failed'):
            provider.generate({'goal': 'build'}, 256)

    def test_unknown_provider_body_is_not_propagated(self):
        def respond(request):
            self.response_path(request).write_text(json.dumps({
                'request_id': request['request_id'],
                'ok': False,
                'error': 'secret-upstream-body-with-token',
            }))
        provider = self.provider(respond)
        with self.assertRaisesRegex(ProviderError, '^provider_error$'):
            provider.generate({'goal': 'build'}, 256)

    def test_transient_partial_mailbox_write_is_retried(self):
        timers = []
        def respond(request):
            path = self.response_path(request)
            path.write_text('{"request_id":')
            good = json.dumps({
                'request_id': request['request_id'],
                'ok': True,
                'text': '{"updates":{},"requests":[]}',
                'usage': {'input_tokens': 2, 'output_tokens': 3},
            })
            timer = threading.Timer(0.08, lambda: path.write_text(good))
            timers.append(timer)
            timer.start()
        provider = self.provider(respond)
        reply = provider.generate({'goal': 'build'}, 256)
        for timer in timers:
            timer.join()
        self.assertEqual(reply.text, '{"updates":{},"requests":[]}')
        self.assertEqual(reply.usage.input_tokens, 2)
        self.assertEqual(reply.usage.output_tokens, 3)


if __name__ == '__main__':
    unittest.main()
