"""Experimental FreeLLMAPI lane; gateway reports are not execution proofs.

No SDK dependency, credential discovery, implicit auto-routing, tool execution,
or client retries. A response allowlist is NOT a pre-dispatch egress control:
operators must independently restrict the gateway's enabled providers.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
import uuid
from dataclasses import replace
from urllib.parse import unquote

from ._http import MAX_RESPONSE, decode, encode
from .openai_adapter import OpenAIAdapter
from ..core import ProviderError, RateLimitError, Role

# Upper bound in the inspected upstream fallback loop. Reserve conservatively
# and never refund from response headers. Not a guarantee about an unpinned or
# malicious gateway, nor about nested providers' internal inference calls.
REVIEWED_UPSTREAM = '496ec4ef1bd1da48fa7c83fd1094a34c2b204e7d'
UPSTREAM_ATTEMPT_RESERVATION = 20
_ROUTE = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,220}\Z')
_lock = threading.Lock()
_inflight = {}


def validate_gateway_config(routes, allow_auto=False):
    if (not isinstance(routes, (list, tuple)) or not 1 <= len(routes) <= 64
            or any(not isinstance(r, str) or not _ROUTE.fullmatch(r) for r in routes)
            or len(set(routes)) != len(routes) or type(allow_auto) is not bool):
        raise ProviderError(provider='freellmapi', code='config')
    return tuple(sorted(routes))


class FreeLLMAPIAdapter(OpenAIAdapter):
    name = 'freellmapi'
    supports_streaming = False
    allowed_extra = set()
    attempt_reservation = UPSTREAM_ATTEMPT_RESERVATION

    def __init__(self, api_key=None, base_url='http://127.0.0.1:3001/v1',
                 allowed_routes=(), allow_auto=False, timeout=45.0):
        super().__init__(api_key, base_url, timeout=timeout, output_token_field='max_tokens')
        self.allowed_routes = validate_gateway_config(allowed_routes, allow_auto)
        self.allow_auto = allow_auto
        if (not isinstance(api_key, str) or not api_key or len(api_key) > 10000
                or any(ord(c) < 33 or ord(c) == 127 for c in api_key)
                or type(timeout) not in (int, float) or not 0 < timeout <= 600):
            raise ProviderError(provider=self.name, code='config')

    def _headers(self):
        return {**super()._headers(), 'X-FreeLLM-Compress': 'off',
                'X-FreeLLM-Cache': 'off', 'Cache-Control': 'no-store',
                # Prevent unrelated batch tasks sharing sticky/handoff memory.
                'X-Session-ID': uuid.uuid4().hex}

    def _build_body(self, req, stream=False):
        model = req.model
        auto = model == 'auto' or model.startswith('auto:')
        if (stream or req.tools or any(m.role == Role.TOOL or m.tool_calls for m in req.messages)
                or req.max_tokens is None or req.max_tokens > 16000 or req.extra
                or not model or model == 'fusion' or model.startswith('fusion:')
                or (auto and not self.allow_auto)
                or (auto and not re.fullmatch(r'auto(?::[A-Za-z0-9_.-]{1,80})?',model))
                or (not auto and model not in {r.split('/', 1)[1] for r in self.allowed_routes})):
            raise ProviderError(provider=self.name, code='invalid_request')
        return super()._build_body(req, False)

    def chat(self, req):
        body = self.wire_bytes(req)
        # Shared across adapter instances and all credentials for one gateway.
        # Refuse immediately: no hidden queue or thread-per-request expansion.
        with _lock:
            if _inflight.get(self.base_url, 0) >= 2:
                raise RateLimitError('', provider=self.name, retry_after=1)
            _inflight[self.base_url] = _inflight.get(self.base_url, 0) + 1
        try:
            with self._open(self._request_url(req, False), body) as (response, start):
                raw = response.read(MAX_RESPONSE + 1)
                if time.monotonic() - start > self.timeout:
                    raise ProviderError(provider=self.name, code='timeout', retryable=True)
                if len(raw) > MAX_RESPONSE:
                    raise ProviderError(provider=self.name, code='response_too_large')
                data = decode(raw)
                if data.get('error'):
                    raise ProviderError(provider=self.name, code='invalid_response')
                headers = response.headers
                # Conflicting duplicate provenance headers cannot be interpreted.
                for key in ('X-Routed-Via', 'X-Fallback-Attempts', 'X-FreeLLM-Compress', 'X-FreeLLM-Cache'):
                    if len(headers.get_all(key, [])) > 1:
                        raise ProviderError(provider=self.name, code='invalid_response')
                route = unquote(headers.get('X-Routed-Via', ''), errors='strict')
                if route not in self.allowed_routes:
                    raise ProviderError(provider=self.name, code='invalid_response')
                if headers.get('X-FreeLLM-Compress', '').split(';', 1)[0].strip() != 'off':
                    raise ProviderError(provider=self.name, code='invalid_response')
                if headers.get('X-FreeLLM-Cache', '').upper() in {'HIT', 'ON'}:
                    raise ProviderError(provider=self.name, code='invalid_response')
                # Upstream omits this header when there were no failed hops.
                failed = headers.get('X-Fallback-Attempts', '0')
                if not re.fullmatch(r'0|[1-9][0-9]?', failed) or int(failed) >= UPSTREAM_ATTEMPT_RESERVATION:
                    raise ProviderError(provider=self.name, code='invalid_response')
                result = self._parse(data, req.model)
                if result.tool_calls or result.finish_reason == 'tool_calls':
                    raise ProviderError(provider=self.name, code='invalid_response')
                provider, model = route.split('/', 1)
                if not (req.model == 'auto' or req.model.startswith('auto:')) and model != req.model:
                    raise ProviderError(provider=self.name, code='invalid_response')
                receipt = {
                    'schema': 'residual.gateway-report.v1', 'trust_class': 'opportunistic',
                    'requested_model': req.model, 'actual_provider': provider, 'actual_model': model,
                    'identity_source': 'gateway_reported', 'upstream_attempts_reported': int(failed) + 1,
                    'reserved_attempts': UPSTREAM_ATTEMPT_RESERVATION,
                    'accounting_complete': False, 'transformations_verified': False,
                    'catalog_digest': None, 'reported_usage': dict(result.usage),
                    'usage_estimated': (data.get('usage') or {}).get('estimated') is True,
                    'request_sha256': hashlib.sha256(body).hexdigest(),
                    'response_sha256': hashlib.sha256(raw).hexdigest(),
                }
                receipt['receipt_sha256'] = hashlib.sha256(b'residual.gateway-report.v1\n' + encode(receipt)).hexdigest()
                # Gateway usage may cover only the successful hop. Missing full
                # accounting must trip existing unknown-usage brakes, not become $0.
                return replace(result, model=model, usage={}, raw=None, metadata={'gateway': receipt})
        finally:
            with _lock:
                _inflight[self.base_url] -= 1
                if not _inflight[self.base_url]: del _inflight[self.base_url]

    def stream(self, req):
        raise ProviderError(provider=self.name, code='not_implemented')
        yield  # retain the iterator contract; emit no partial output

    def supports_tools(self, model):
        return False

    def list_models(self):
        # Discovery is not permission to dispatch a new model.
        permitted = {r.split('/', 1)[1] for r in self.allowed_routes}
        return sorted(set(super().list_models()) & permitted)
