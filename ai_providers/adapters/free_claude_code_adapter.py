"""Opt-in FCC Messages standby. No agent runtime or subscription login reuse.

The operator must pin and restrict the separate server. Its model field echoes
the request, not the actual provider; neither routing nor costs are attested.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from dataclasses import replace
from urllib.parse import urlsplit

from ._http import MAX_RESPONSE, decode, encode
from .anthropic_adapter import AnthropicAdapter
from ..core import ProviderError, RateLimitError, Role

REVIEWED_UPSTREAM = 'bf59598ccc04b02befa1d649dfbcc569534c365c'
# The reviewed shared Chat transport uses one five-attempt admission budget.
# Conditional on the dedicated-server contract: no MODEL_FALLBACKS or web tools.
# This reservation is NOT a verified upstream count or a remote enforcement cap.
UPSTREAM_ATTEMPT_RESERVATION = 5
SUPPORTED_PROVIDERS = frozenset({'groq', 'nvidia_nim', 'lmstudio', 'llamacpp'})
_ROUTE = re.compile(r'([a-z_]+)/[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,220}\Z')
_lock = threading.Lock()
_inflight = {}


def validate_fcc_config(routes, standby_confirmed=False):
    if (standby_confirmed is not True or not isinstance(routes, (list, tuple))
            or not 1 <= len(routes) <= 16
            or any(not isinstance(r, str) or not (m := _ROUTE.fullmatch(r))
                   or m.group(1) not in SUPPORTED_PROVIDERS for r in routes)
            or len(set(routes)) != len(routes)):
        raise ProviderError(provider='free_claude_code', code='config')
    return tuple(sorted(routes))


class FreeClaudeCodeAdapter(AnthropicAdapter):
    name = 'free_claude_code'
    supports_streaming = False
    supports_approval_review = False
    fallback_only = True
    allowed_extra = set()
    attempt_reservation = UPSTREAM_ATTEMPT_RESERVATION

    def __init__(self, api_key=None, base_url='http://127.0.0.1:8082',
                 allowed_routes=(), standby_confirmed=False, timeout=30.0):
        super().__init__(api_key, base_url, timeout)
        self.allowed_routes = validate_fcc_config(allowed_routes, standby_confirmed)
        if (not isinstance(api_key, str) or not api_key or api_key == 'freecc'
                or len(api_key) > 10000 or any(ord(c) < 33 or ord(c) > 126 for c in api_key)
                or type(timeout) not in (int, float) or not 0 < timeout <= 60
                or urlsplit(self.base_url).path):
            raise ProviderError(provider=self.name, code='config')

    def _headers(self):
        # Only the proxy credential crosses this boundary, never an upstream key.
        return {'Content-Type': 'application/json', 'anthropic-version': self.API_VERSION,
                'Authorization': 'Bearer ' + self.api_key, 'Cache-Control': 'no-store'}

    def _build_body(self, req, stream=False):
        if (stream or req.model not in self.allowed_routes or req.tools or req.extra
                or any(m.role == Role.TOOL or m.tool_calls for m in req.messages)
                or req.max_tokens is None or req.max_tokens > 16000 or req.seed is not None):
            raise ProviderError(provider=self.name, code='invalid_request')
        return super()._build_body(req, False)

    def chat(self, req):
        body = self.wire_bytes(req)
        with _lock:
            if _inflight.get(self.base_url, 0) >= 2:
                raise RateLimitError('', provider=self.name, retry_after=1)
            _inflight[self.base_url] = _inflight.get(self.base_url, 0) + 1
        try:
            with self._open(self._request_url(req, False), body) as (response, start):
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise ProviderError(provider=self.name, code='response_too_large')
                if time.monotonic() - start > self.timeout:
                    raise ProviderError(provider=self.name, code='timeout', retryable=True)
                data = decode(raw)
                # Inspect every block: unknown/server-tool blocks cannot silently
                # disappear in the generic Messages parser. Thinking stays private.
                blocks = data.get('content')
                if (data.get('error') or data.get('type') != 'message'
                        or data.get('role') != 'assistant' or data.get('model') != req.model
                        or not isinstance(blocks, list) or not blocks
                        or any(not isinstance(b, dict) or b.get('type') not in
                               {'text', 'thinking', 'redacted_thinking'} for b in blocks)
                        or any(b.get('type') == 'text' and not isinstance(b.get('text'), str) for b in blocks)
                        or data.get('stop_reason') not in {'end_turn', 'stop_sequence', 'max_tokens'}):
                    raise ProviderError(provider=self.name, code='invalid_response')
                result = self._parse(data, req.model)
                if not result.content.strip():
                    raise ProviderError(provider=self.name, code='invalid_response')
                report = {
                    'schema': 'residual.gateway-report.v1', 'trust_class': 'continuity_standby',
                    'requested_model': req.model, 'actual_provider': None, 'actual_model': None,
                    'identity_source': 'unverified_request_echo',
                    'upstream_attempts_reported': None, 'reserved_attempts': self.attempt_reservation,
                    'reservation_basis': 'operator_confirmed_pinned_standby_contract',
                    'accounting_complete': False, 'transformations_verified': False,
                    'catalog_digest': None, 'reported_usage': dict(result.usage),
                    'usage_estimated': None,
                    'request_sha256': hashlib.sha256(body).hexdigest(),
                    'response_sha256': hashlib.sha256(raw).hexdigest(),
                }
                report['receipt_sha256'] = hashlib.sha256(b'residual.gateway-report.v1\n' + encode(report)).hexdigest()
                return replace(result, usage={}, raw=None, metadata={'gateway': report})
        finally:
            with _lock:
                _inflight[self.base_url] -= 1
                if not _inflight[self.base_url]: del _inflight[self.base_url]

    def stream(self, req):
        raise ProviderError(provider=self.name, code='not_implemented')
        yield

    def supports_tools(self, model):
        return False

    def list_models(self):
        # Static permitted routes, not a probe that can spend provider quota.
        return list(self.allowed_routes)
