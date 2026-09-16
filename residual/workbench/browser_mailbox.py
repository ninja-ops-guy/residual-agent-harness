"""Hardened WebVM mailbox provider for the public browser workbench.

This is a transport adapter, not a new trust boundary. Browser responses are
published in two phases: the host writes the response body, then a request-
specific ready marker. The guest does not read the response until that marker
exists, preventing a browser-mediated DataDevice write from being consumed
mid-publication. Raw provider exception text never enters the guest ledger.
"""
from __future__ import annotations

import json
import time
import uuid

from residual.core import ContractError, canonical
from residual.providers import ProviderError, Reply, Usage
from .browser_poll import pause
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


class BrowserRuntimeCorruption(BaseException):
    """Fail-closed browser-runtime corruption signal.

    This deliberately does not inherit from ``Exception``. The core engine
    converts ordinary provider ``Exception`` failures into typed provider
    outcomes; an impossible CPython ``TypeError`` while reading an already-ready
    browser mailbox response must instead cross that boundary and terminate the
    persistent guest worker. No raw exception text is retained or projected.
    """


class BrowserMailboxProvider(MailboxProvider):
    """MailboxProvider with typed browser failures and two-phase publication."""

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
        ready = self.mailbox / f'{self.mission_id}-{rid}.json.ready'
        started = time.monotonic()
        invalid_reads = 0
        while time.monotonic() - started < 90:
            if self.cancelled():
                raise ProviderError('mission_cancelled')
            # DataDevice.writeFile exposes the destination while it is being
            # populated. The browser writes this marker only after the awaited
            # response write resolves, so the guest never races the body write.
            try:
                if not ready.is_file():
                    pause()
                    continue
            except OSError:
                pause()
                continue
            try:
                response = read_json(path, MAX_RESPONSE)
            except FileNotFoundError:
                # Fail closed on publication reordering without manufacturing a
                # candidate. A completed marker with a delayed body may recover.
                pause()
                continue
            except TypeError:
                # The retained production corruption manifested as impossible
                # CPython TypeErrors. This is not a malformed-provider response
                # contract and must not leave a long-lived interpreter reusable.
                raise BrowserRuntimeCorruption() from None
            except (OSError, json.JSONDecodeError, UnicodeDecodeError, ContractError, RecursionError):
                # These are bounded transport/input failures: browser-backed I/O,
                # malformed/duplicate/non-finite JSON, text decoding, or an
                # intentionally bounded deeply-nested provider response.
                invalid_reads += 1
                if invalid_reads >= 5:
                    raise ProviderError('browser_response_invalid')
                pause()
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
