"""Arena preview API adapter.

Arena's preview API exposes an OpenAI-compatible chat-completions surface.
RESIDUAL submits exactly one Arena model per request and disables Arena-side
fallback. Any higher-level failover stays in RESIDUAL's Router so every actual
attempt is independently observed and receipted.
"""
from __future__ import annotations

import time
from dataclasses import replace

from ._http import MAX_RESPONSE, MAX_STREAM, decode
from .openai_adapter import OpenAIAdapter
from ..core import ProviderError

ARENA_DEFAULT_BASE_URL = "https://api.preview.arena.ai/v1"


class ArenaAdapter(OpenAIAdapter):
    """OpenAI-compatible transport for the Arena preview API."""

    name = "arena"
    allowed_extra = set()

    def __init__(
        self,
        api_key=None,
        base_url=ARENA_DEFAULT_BASE_URL,
        organization=None,
        timeout=120.0,
        output_token_field="max_completion_tokens",
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            organization=organization,
            timeout=timeout,
            output_token_field=output_token_field,
        )

    def _build_body(self, req, stream=False):
        body = super()._build_body(req, stream)
        # Arena documents model fallback as an optional gateway feature.
        # Scientific attribution requires one requested model per transport
        # attempt, so disable gateway fallback at the request boundary.
        body["allow_fallbacks"] = False
        body.pop("fallbacks", None)
        body.pop("fallback_on", None)
        # Arena's published chat schema does not currently document the
        # OpenAI response_format or stream_options extensions. The parent
        # adapter still injects the requested JSON schema into a system message;
        # RESIDUAL then validates the returned JSON locally.
        body.pop("response_format", None)
        body.pop("stream_options", None)
        return body

    @staticmethod
    def _bounded_header(headers, name, limit=500):
        value = headers.get(name)
        if value is None:
            return None
        if (
            not isinstance(value, str)
            or not value
            or len(value) > limit
            or any(ord(ch) < 32 for ch in value)
        ):
            raise ProviderError(provider="arena", code="invalid_response")
        return value

    def _response_metadata(self, headers):
        """Normalize only Arena's documented, non-secret provenance headers."""
        resolved = self._bounded_header(headers, "X-Arena-Resolved-Model")
        trace_id = self._bounded_header(headers, "X-Arena-Trace-ID", 300)
        fallback_index_raw = self._bounded_header(headers, "X-Arena-Fallback-Index", 20)
        fallback_reason = self._bounded_header(headers, "X-Arena-Fallback-Reason", 100)
        fallback_index = None
        if fallback_index_raw is not None:
            try:
                fallback_index = int(fallback_index_raw)
            except ValueError:
                raise ProviderError(provider=self.name, code="invalid_response") from None
            if fallback_index < 1:
                raise ProviderError(provider=self.name, code="invalid_response")
        fallback_used = fallback_index is not None or fallback_reason is not None
        # Every Arena request emitted by this adapter says allow_fallbacks=false.
        # A fallback response would invalidate model attribution, so reject it.
        if fallback_used:
            raise ProviderError(provider=self.name, code="invalid_response")
        return {
            "arena_resolved_model": resolved,
            "arena_trace_id": trace_id,
            "arena_fallback_used": False,
            "arena_fallback_index": None,
            "arena_fallback_reason": None,
        }

    def chat(self, req):
        # Capture response headers before the generic JSON helper releases the
        # response object. Raw response bodies and headers are never retained.
        with self._open(self._request_url(req, False), self.wire_bytes(req)) as (response, _start):
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise ProviderError(provider=self.name, code="response_too_large")
            data = decode(raw)
            if data.get("error"):
                raise ProviderError(provider=self.name, code="invalid_response")
            parsed = self._parse(data, req.model)
            metadata = self._response_metadata(response.headers)
            return replace(parsed, metadata={**parsed.metadata, **metadata})

    def _events(self, url, body, *, ndjson=False):
        # Arena streams use the same documented response provenance headers.
        # Validate them before emitting the first SSE chunk so a forbidden
        # gateway fallback can never be partially consumed as the requested model.
        with self._open(url, body) as (response, start):
            self._response_metadata(response.headers)
            total, parts, frame = 0, [], 0
            while True:
                if time.monotonic() - start > self.timeout:
                    raise ProviderError(provider=self.name, code="timeout", retryable=True)
                raw = response.readline(MAX_RESPONSE + 1)
                if not raw:
                    break
                total += len(raw)
                frame += len(raw)
                if total > MAX_STREAM or frame > MAX_RESPONSE:
                    raise ProviderError(provider=self.name, code="response_too_large")
                line = raw.decode("utf-8").rstrip("\r\n")
                if ndjson:
                    frame = 0
                    if line:
                        yield decode(line)
                elif not line:
                    if parts:
                        payload = "\n".join(parts)
                        parts = []
                        frame = 0
                        if payload == "[DONE]":
                            yield {"_done": True}
                            return
                        yield decode(payload)
                elif line.startswith("data:"):
                    parts.append(line[5:].lstrip(" "))
            if parts:
                raise ProviderError(provider=self.name, code="stream_incomplete")

    def supports_tools(self, model):
        # Arena is a gateway over heterogeneous models. A gateway model ID does
        # not prove the selected backend supports tools, so keep capability
        # discovery conservative. Explicit tool-bearing requests are serialized
        # using the documented OpenAI-compatible wire format.
        return False
