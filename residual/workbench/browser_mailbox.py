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
    'browser_mailbox_io',
}

_MAX_TRANSIENT_MAILBOX_FAULTS = 40
_MAX_RUNTIME_VISIBILITY_FAULTS = 3
_CANCEL_PROBE_ATTEMPTS = 3
_RETRY_SLEEP_SECONDS = 0.05


class BrowserRuntimeCorruption(BaseException):
    """Fail-closed browser-runtime corruption signal.

    This deliberately does not inherit from ``Exception``. The core engine
    converts ordinary provider ``Exception`` failures into typed provider
    outcomes; impossible CPython/runtime failures while observing the browser
    mailbox must instead cross that boundary and terminate the persistent guest
    worker. No raw exception text is retained or projected.
    """


class BrowserMailboxProvider(MailboxProvider):
    """MailboxProvider with typed browser failures and two-phase publication."""

    def _is_cancelled(self):
        runtime_faults = 0
        for attempt in range(_CANCEL_PROBE_ATTEMPTS):
            try:
                return bool(self.cancelled())
            except OSError:
                if attempt + 1 == _CANCEL_PROBE_ATTEMPTS:
                    raise ProviderError('browser_mailbox_io') from None
                time.sleep(0.01)
            except RecursionError:
                raise BrowserRuntimeCorruption() from None
            except RuntimeError:
                runtime_faults += 1
                if runtime_faults >= _MAX_RUNTIME_VISIBILITY_FAULTS or attempt + 1 == _CANCEL_PROBE_ATTEMPTS:
                    raise BrowserRuntimeCorruption() from None
                time.sleep(0.01)
            except (TypeError, ValueError, OverflowError):
                raise BrowserRuntimeCorruption() from None
        raise ProviderError('browser_mailbox_io')

    def generate(self, packet, max_output_tokens):
        if self._is_cancelled():
            raise ProviderError('mission_cancelled')
        rid = uuid.uuid4().hex
        request = {
            'request_id': rid,
            'model': self.model,
            'messages': self.payload(packet, max_output_tokens)['messages'],
            'max_output_tokens': max_output_tokens,
        }
        if len(canonical(request).encode('utf-8')) > MAX_REQUEST:
            raise ProviderError('browser_request_too_large')
        self.emit('inference_requested', request)
        path = self.mailbox / f'{self.mission_id}-{rid}.json'
        ready = self.mailbox / f'{self.mission_id}-{rid}.json.ready'
        started = time.monotonic()
        invalid_reads = 0
        transport_faults = 0
        runtime_faults = 0
        while time.monotonic() - started < 90:
            if self._is_cancelled():
                raise ProviderError('mission_cancelled')
            # DataDevice.writeFile exposes the destination while it is being
            # populated. The browser writes this marker only after the awaited
            # response write resolves. Some browser engines can still lag on
            # guest-side visibility, so tolerate bounded transport faults while
            # preserving fail-closed handling for corruption-class failures.
            try:
                if not ready.is_file():
                    time.sleep(_RETRY_SLEEP_SECONDS)
                    continue
            except OSError:
                transport_faults += 1
                if transport_faults >= _MAX_TRANSIENT_MAILBOX_FAULTS:
                    raise ProviderError('browser_mailbox_io') from None
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            except RecursionError:
                raise BrowserRuntimeCorruption() from None
            except RuntimeError:
                runtime_faults += 1
                if runtime_faults >= _MAX_RUNTIME_VISIBILITY_FAULTS:
                    raise BrowserRuntimeCorruption() from None
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            except (TypeError, ValueError, OverflowError):
                raise BrowserRuntimeCorruption() from None

            try:
                response = read_json(path, MAX_RESPONSE)
            except OSError:
                # Fail closed on publication reordering without manufacturing a
                # candidate. A completed marker with a delayed body may recover.
                transport_faults += 1
                if transport_faults >= _MAX_TRANSIENT_MAILBOX_FAULTS:
                    raise ProviderError('browser_mailbox_io') from None
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            except (json.JSONDecodeError, UnicodeDecodeError, ContractError, RecursionError):
                # These are bounded input failures: malformed/duplicate/non-finite
                # JSON, text decoding, or intentionally bounded deeply nested JSON.
                invalid_reads += 1
                if invalid_reads >= _MAX_TRANSIENT_MAILBOX_FAULTS:
                    raise ProviderError('browser_response_invalid') from None
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            except RuntimeError:
                # A small number of browser-runtime visibility faults may be
                # transient. Repeated occurrences poison the long-lived worker
                # instead of converting a suspect interpreter into a reusable
                # provider failure.
                runtime_faults += 1
                if runtime_faults >= _MAX_RUNTIME_VISIBILITY_FAULTS:
                    raise BrowserRuntimeCorruption() from None
                time.sleep(_RETRY_SLEEP_SECONDS)
                continue
            except (TypeError, ValueError, OverflowError):
                # The retained production corruption manifested as impossible
                # CPython TypeErrors. Other impossible runtime/value conversion
                # failures at this fixed read boundary are treated equivalently.
                raise BrowserRuntimeCorruption() from None

            transport_faults = 0
            runtime_faults = 0
            invalid_reads = 0
            if not isinstance(response, dict) or response.get('request_id') != rid:
                raise ProviderError('browser_response_identity_mismatch')
            if response.get('ok') is not True:
                code = response.get('error')
                raise ProviderError(code if code in SAFE_BROWSER_ERRORS else 'provider_error')
            text = response.get('text')
            if not isinstance(text, str):
                raise ProviderError('browser_response_invalid')
            try:
                encoded = text.encode('utf-8')
            except UnicodeEncodeError:
                raise ProviderError('browser_response_invalid') from None
            if len(encoded) > 48000:
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
