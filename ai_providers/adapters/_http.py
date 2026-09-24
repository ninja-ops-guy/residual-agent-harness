"""Bounded stdlib HTTP. No ambient proxies, redirects, raw upstream errors or hidden retries."""
from __future__ import annotations
import asyncio
import email.utils
import functools
import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from ..core import AuthenticationError, ModelNotFoundError, ProviderError, RateLimitError

MAX_RESPONSE = 2_000_000
MAX_STREAM = 16_000_000


def encode(body):
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def decode(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d: raise ValueError('Duplicate JSON key')
            d[k] = v
        return d
    def invalid(_): raise ValueError('Non-finite JSON number')
    data = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    if not isinstance(data, dict): raise ValueError('Expected JSON object')
    return data


def validate_url(url, provider, local=False):
    try:
        u = urllib.parse.urlsplit(url)
        port = u.port
        loopback = u.hostname in {'localhost', '127.0.0.1', '::1'}
        if u.scheme not in {'http', 'https'} or not u.hostname or u.username or u.password or u.query or u.fragment or any(ord(c) < 33 for c in url): raise ValueError()
        if local and not loopback: raise ValueError()
        if u.scheme == 'http' and not loopback: raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ProviderError(provider=provider, code='config') from None
    return url.rstrip('/')


def map_http_error(provider, status, body='', headers=None):
    # Body may be JSON, HTML, a string error, or contain secrets. Never echo it.
    # Only structured JSON error codes can classify quota exhaustion. Arbitrary
    # text is not authority to widen routing.
    if status == 401:
        return AuthenticationError(provider=provider, code='auth_rejected', status=status,
                                   failover_allowed=True)
    if status == 403:
        # Preserve the public authentication-error type expected by existing
        # adapters while keeping policy denial fail-closed for continuity.
        return AuthenticationError(provider=provider, code='policy_denied', status=status,
                                   retryable=False, failover_allowed=False)
    if status == 404:
        return ModelNotFoundError(provider=provider, code='model_not_found', status=status)
    if status == 429:
        structured = None
        try:
            raw = body.decode('utf-8') if isinstance(body, (bytes, bytearray)) else str(body or '')
            parsed = decode(raw)
            err = parsed.get('error')
            if isinstance(err, dict):
                structured = err.get('code') or err.get('type')
            elif isinstance(parsed.get('code'), str):
                structured = parsed.get('code')
        except (ValueError, TypeError, UnicodeError):
            structured = None
        if structured in {'insufficient_quota', 'quota_exhausted'}:
            return ProviderError(provider=provider, code='quota_exhausted', status=status,
                                 retryable=False, failover_allowed=True)
        retry = None
        hint = (headers or {}).get('Retry-After')
        if hint is not None:
            try: retry = float(hint)
            except (ValueError, TypeError):
                try: retry = (email.utils.parsedate_to_datetime(hint) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError): pass
        if retry is not None and (not math.isfinite(retry) or retry < 0): retry = None
        return RateLimitError('Rate limited', provider=provider, retry_after=retry)
    return ProviderError(provider=provider, code='server_error' if 500 <= status < 600 else 'http_error',
                         status=status, retryable=500 <= status < 600)


def usage_values(inp=None, out=None, total=None, cached=None, cache_write=None):
    result = {k: v for k, v in [('prompt_tokens', inp), ('completion_tokens', out), ('total_tokens', total), ('cached_prompt_tokens', cached), ('cache_write_prompt_tokens', cache_write)] if v is not None}
    if any(type(v) is not int or v < 0 for v in result.values()): raise ValueError('Invalid usage')
    if inp is not None and cached is not None and cached > inp: raise ValueError('Invalid cache usage')
    if total is None and inp is not None and out is not None: result['total_tokens'] = inp + out
    return result


def cached_usage(u, input_key, output_key, read_key, write_key):
    if not isinstance(u, dict): raise ValueError("Invalid usage")
    inp, out, cached, written = (u.get(k) for k in (input_key, output_key, read_key, write_key))
    for value in (inp, out, cached, written):
        if value is not None and (type(value) is not int or value < 0): raise ValueError("Invalid usage")
    if inp is not None: inp += (cached or 0) + (written or 0)
    return usage_values(inp, out, cached=cached, cache_write=written)


def extract_usage(d):
    u = d.get('usage') or {}
    if not isinstance(u, dict): raise ValueError('Invalid usage')
    return usage_values(u.get('prompt_tokens', u.get('input_tokens')), u.get('completion_tokens', u.get('output_tokens')),
                        u.get('total_tokens'), (u.get('prompt_tokens_details') or {}).get('cached_tokens'))


def finish(value):
    return {'end_turn':'stop', 'stop_sequence':'stop', 'STOP':'stop', 'max_tokens':'length', 'MAX_TOKENS':'length',
            'tool_use':'tool_calls', 'function_call':'tool_calls', 'FUNCTION_CALL':'tool_calls', 'SAFETY':'content_filter',
            'guardrail_intervened':'content_filter', 'refusal':'content_filter', 'RECITATION':'content_filter'}.get(value, value if value in {'stop','length','tool_calls','content_filter','error'} else 'unknown')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError(provider='router', code='redirect_refused', status=code)


class HTTPAdapter:
    supports_streaming = True
    allowed_extra = set()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in ("chat", "list_models", "supports_tools"):
            fn = cls.__dict__.get(name)
            if fn is None: continue
            def guard(fn):
                @functools.wraps(fn)
                def wrapped(self, *a, **kw):
                    try: return fn(self, *a, **kw)
                    except ProviderError: raise
                    except Exception:
                        raise ProviderError(provider=self.name, code="invalid_response") from None
                return wrapped
            setattr(cls, name, guard(fn))

    def _options(self, req, body):
        if set(req.extra) - self.allowed_extra:
            raise ProviderError(provider=self.name, code='invalid_request')
        body.update(req.extra)
        return body

    def _headers(self): return {'Content-Type': 'application/json'}

    def wire_bytes(self, req, stream=False):
        if not req.model: raise ProviderError(provider=self.name, code="invalid_request")
        return encode(self._build_body(req, stream))

    @contextmanager
    def _open(self, url, body=None, headers=None):
        start = time.monotonic()
        try:
            if not 0 < self.timeout <= 600: raise ProviderError(provider=self.name, code='config')
            hdrs = headers or self._headers()
            if any(not isinstance(v, str) or '\r' in v or '\n' in v for v in hdrs.values()):
                raise ProviderError(provider=self.name, code='config')
            request = urllib.request.Request(url, data=body, headers=hdrs)
            opener = getattr(self, 'opener', None) or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with opener.open(request, timeout=self.timeout) as response:
                yield response, start
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read(MAX_RESPONSE + 1)
                if len(body) > MAX_RESPONSE:
                    body = b''
            except Exception:
                body = b''
            finally:
                exc.close()
            raise map_http_error(self.name, exc.code, body=body, headers=exc.headers) from None
        except ProviderError: raise
        except (TimeoutError, socket.timeout):
            raise ProviderError(provider=self.name, code='timeout', retryable=True) from None
        except (urllib.error.URLError, OSError):
            raise ProviderError(provider=self.name, code='connection', retryable=True) from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, RecursionError):
            raise ProviderError(provider=self.name, code='invalid_response') from None

    def _json(self, url, body=None, headers=None):
        with self._open(url, body, headers) as (response, start):
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE: raise ProviderError(provider=self.name, code='response_too_large')
            data = decode(raw)
            if data.get('error'): raise ProviderError(provider=self.name, code='invalid_response')
            return data

    def chat(self, req):
        try:
            data = self._json(self._request_url(req, False), self.wire_bytes(req))
            return self._parse(data, req.model)
        except ProviderError: raise
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise ProviderError(provider=self.name, code='invalid_response') from None

    def _events(self, url, body, *, ndjson=False):
        with self._open(url, body) as (response, start):
            total, parts, frame = 0, [], 0
            while True:
                if time.monotonic() - start > self.timeout: raise ProviderError(provider=self.name, code='timeout', retryable=True)
                raw = response.readline(MAX_RESPONSE + 1)
                if not raw: break
                total += len(raw); frame += len(raw)
                if total > MAX_STREAM or frame > MAX_RESPONSE: raise ProviderError(provider=self.name, code='response_too_large')
                line = raw.decode('utf-8').rstrip('\r\n')
                if ndjson:
                    frame = 0
                    if line: yield decode(line)
                elif not line:
                    if parts:
                        payload = '\n'.join(parts); parts = []; frame = 0
                        if payload == '[DONE]': yield {'_done': True}; return
                        yield decode(payload)
                elif line.startswith('data:'):
                    parts.append(line[5:].lstrip(' '))
            if parts: raise ProviderError(provider=self.name, code='stream_incomplete')

    def stream(self, req):
        if not self.supports_streaming: raise ProviderError(provider=self.name, code='not_implemented')
        completed = False
        try:
            events = self._events(self._request_url(req, True), self.wire_bytes(req, True), ndjson=self.name == 'ollama')
            state = {}
            for event in events:
                if event.get('error') or event.get('type') == 'error': raise ProviderError(provider=self.name, code='server_error', retryable=True)
                for chunk in self._chunks(event, state):
                    if chunk.finish_reason is not None: completed = True
                    yield chunk
            if not completed: raise ProviderError(provider=self.name, code='stream_incomplete', retryable=True)
        except ProviderError: raise
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise ProviderError(provider=self.name, code='invalid_response') from None

    async def achat(self, req):
        return await asyncio.to_thread(self.chat, req)

    async def astream(self, req):
        iterator = self.stream(req)
        sentinel = object()
        def advance(): return next(iterator, sentinel)
        try:
            while True:
                task = asyncio.create_task(asyncio.to_thread(advance))
                try: item = await asyncio.shield(task)
                except asyncio.CancelledError:
                    # Let the bounded outstanding read finish before closing its generator.
                    try: await task
                    except Exception: pass
                    raise
                if item is sentinel: break
                yield item
        finally:
            iterator.close()
