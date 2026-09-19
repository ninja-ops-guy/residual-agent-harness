"""Arena preview API adapter.

Arena's preview API exposes an OpenAI-compatible chat-completions surface.
This adapter intentionally submits exactly one model per request. Benchmark
runs must keep any higher-level failover in RESIDUAL's Router so every actual
attempt is visible in RESIDUAL receipts instead of being silently relabelled.
"""
from __future__ import annotations

from dataclasses import replace

from ._http import MAX_RESPONSE, decode
from .openai_adapter import OpenAIAdapter
from ..core import ProviderError

ARENA_DEFAULT_BASE_URL = "https://api.preview.arena.ai/v1"


class ArenaAdapter(OpenAIAdapter):
    """OpenAI-compatible transport for the Arena preview API."""

    name = "arena"

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
        # Fail closed for experiment provenance. Arena supports its own gateway
        # fallback chain, but RESIDUAL keeps fallback in Router where every
        # attempt is separately observed and receipted.
        body["allow_fallbacks"] = False
        body.pop("fallbacks", None)
        body.pop("fallback_on", None)
        return body

    @staticmethod
    def _bounded_header(headers, name, limit=500):
        value = headers.get(name)
        if value is None:
            return None
        if not isinstance(value, str) or not value or len(value) > limit or any(ord(ch) < 32 for ch in value):
            raise ProviderError(provider="arena", code="invalid_response")
        return value

    def chat(self, req):
        # Arena's documented response headers carry the actual resolved model,
        # gateway trace ID, and fallback provenance. Preserve only those
        # bounded, non-secret fields in normalized metadata.
        with self._open(self._request_url(req, False), self.wire_bytes(req)) as (response, _start):
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise ProviderError(provider=self.name, code="response_too_large")
            data = decode(raw)
            if data.get("error"):
                raise ProviderError(provider=self.name, code="invalid_response")
            parsed = self._parse(data, req.model)
            resolved = self._bounded_header(response.headers, "X-Arena-Resolved-Model")
            trace_id = self._bounded_header(response.headers, "X-Arena-Trace-ID", 300)
            fallback_index_raw = self._bounded_header(response.headers, "X-Arena-Fallback-Index", 20)
            fallback_reason = self._bounded_header(response.headers, "X-Arena-Fallback-Reason", 100)
            fallback_index = None
            if fallback_index_raw is not None:
                try:
                    fallback_index = int(fallback_index_raw)
                except ValueError:
                    raise ProviderError(provider=self.name, code="invalid_response") from None
                if fallback_index < 1:
                    raise ProviderError(provider=self.name, code="invalid_response")
            fallback_used = fallback_index is not None or fallback_reason is not None
            # Every RESIDUAL Arena request explicitly sends allow_fallbacks=false.
            # Seeing fallback provenance anyway is a trust-boundary violation:
            # do not silently accept or relabel that response.
            if fallback_used:
                raise ProviderError(provider=self.name, code="invalid_response")
            metadata = {
                "arena_resolved_model": resolved,
                "arena_trace_id": trace_id,
                "arena_fallback_used": False,
                "arena_fallback_index": None,
                "arena_fallback_reason": None,
            }
            return replace(parsed, metadata={**parsed.metadata, **metadata})

    def supports_tools(self, model):
        # Arena is a gateway over heterogeneous models. A gateway model ID does
        # not prove the selected backend supports tools, so keep capability
        # discovery conservative. Explicit tool-bearing requests are still
        # serialized using the OpenAI-compatible wire format.
        return False
