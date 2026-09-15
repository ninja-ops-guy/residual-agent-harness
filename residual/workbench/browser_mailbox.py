"""Hardened WebVM mailbox provider for the public browser workbench.

This is a transport adapter, not a new trust boundary. It preserves a bounded
safe error vocabulary from the browser helper and tolerates a small number of
transient/partial mailbox reads. Raw provider exception text never enters the
guest ledger.
"""
from __future__ import annotations

import time
import uuid

from residual.core import canonical
from residual.providers import ProviderError, Reply, Usage
from .runner import MailboxProvider, MAX_REQUEST, MAX_RESPONSE, read_json

SAFE_BROWSER_ERRORS = {
    'provider_disconnected',
    'provider_timeout',
    'provider_error',
    'provider_request_failed',
    'provider_model_unavailable',
    'provider_authorization_failed',
    'provider_protocol_invalid',
    'mission_cancelled',
    'provider_budget_exhausted',
    'provider_response_too_large',
    'browser_response_invalid',
}


class BrowserMailboxProvider(MailboxProvider):
    """MailboxProvider with typed browser failures and bounded torn-read recovery."""

    def generate(self, packet, max_output_tokens):
        if self.cancelled():
            raise ProviderError('mission_cancelled')
        rid = uuid.uuid4().hex
        request = {
            'request_id': rid,
            'model': self.model,
            'messages': self.payload(packet, max_output_tokens)['messages'],
            'max_output_tokens': max_output_tokens,
        }
        if len(canonical(request).encode()) > MAX_REQUEST:
            raise ProviderError('browser_request_too_large')
        self.emit('inference_requested', request)
        path = self.mailbox / f'{self.mission_id}-{rid}.json'
        started = time.monotonic()
        invalid_reads = 0
        while time.monotonic() - started < 90:
            if self.cancelled():
                raise ProviderError('mission_cancelled')
            try:
                response = read_json(path, MAX_RESPONSE)
            except FileNotFoundError:
                time.sleep(0.05)
                continue
            except (ValueError, TypeError, UnicodeDecodeError, RecursionError):
                # DataDevice writes are browser-mediated. A reader may observe a
                # transient partial file; retry a small fixed number rather than
                # converting that race into an opaque provider_exception.
                invalid_reads += 1
                if invalid_reads >= 5:
                    raise ProviderError('browser_response_invalid')
                time.sleep(0.05)
                continue
            if not isinstance(response, dict) or response.get('request_id') != rid:
                raise ProviderError('browser_response_identity_mismatch')
            if response.get('ok') is not True:
                code = response.get('error')
                raise ProviderError(code if code in SAFE_BROWSER_ERRORS else 'provider_error')
            text = response.get('text')
            if not isinstance(text, str) or len(text.encode()) > 48000:
                raise ProviderError('browser_response_invalid')
            usage = response.get('usage') if isinstance(response.get('usage'), dict) else {}
            inp, out = usage.get('input_tokens'), usage.get('output_tokens')
            inp = inp if type(inp) is int and inp >= 0 else None
            out = out if type(out) is int and out >= 0 else None
            return Reply(
                text,
                Usage(inp, out, source='reported' if inp is not None and out is not None else 'unavailable'),
                (time.monotonic() - started) * 1000,
            )
        raise ProviderError('provider_timeout')
