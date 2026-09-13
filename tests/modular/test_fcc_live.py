"""Explicit opt-in smoke: one synthetic FCC inference, no project data."""
import os
import unittest

from ai_providers import ChatRequest, Message, ProviderError, Role, Router
from ai_providers.registry import _default_registry


@unittest.skipUnless(os.environ.get('RESIDUAL_FCC_LIVE_TEST') == '1', 'FCC live smoke is opt-in and consumes quota')
class FCCLiveTests(unittest.TestCase):
    def test_synthetic_primary_outage_uses_configured_standby(self):
        class Unavailable:
            name = 'openai'
            def chat(self, req):
                raise ProviderError(provider=self.name, code='server_error', retryable=True, status=503)
        registry = _default_registry()
        registry.register('openai', Unavailable)
        standby = registry.get('free_claude_code')
        model = standby.list_models()[0]
        req = ChatRequest('synthetic-outage', (Message(Role.USER, 'Reply with the single word READY.'),), max_tokens=64)
        receipts = []
        response = Router(registry=registry, after_attempt=receipts.append).chat(
            'openai:synthetic-outage', req, ['free_claude_code:' + model])
        self.assertIn('READY', response.content.upper())
        self.assertEqual(len(receipts), 2)
        self.assertEqual(receipts[0]['request_id'], receipts[1]['request_id'])
        self.assertEqual(receipts[1]['provider'], 'free_claude_code')
        self.assertFalse(receipts[1]['gateway']['accounting_complete'])
