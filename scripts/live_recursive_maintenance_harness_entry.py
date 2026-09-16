#!/usr/bin/env python3
"""Run the live maintenance study through RESIDUAL's provider abstraction.

The benchmark orchestration remains in live_recursive_maintenance_study.py. This
entrypoint replaces only its transport function so every generator/critic call
flows through RESIDUAL's OpenAICompatibleAdapter rather than calling FreeLLMAPI
directly. The adapter is instrumented solely to retain non-secret response route
metadata such as X-Routed-Via.
"""
from __future__ import annotations

from ai_providers.adapters._http import MAX_RESPONSE, decode
from ai_providers.adapters.openai_adapter import OpenAICompatibleAdapter
from ai_providers.core import ChatRequest, Message, ProviderError, Role
import live_recursive_maintenance_study as study


class InstrumentedCompatibleAdapter(OpenAICompatibleAdapter):
    """RESIDUAL adapter with response-header observation for the experiment."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_headers: dict[str, str] = {}

    def _json(self, url, body=None, headers=None):
        with self._open(url, body, headers) as (response, _start):
            self.last_headers = dict(response.headers.items())
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise ProviderError(provider=self.name, code="response_too_large")
            data = decode(raw)
            if data.get("error"):
                raise ProviderError(provider=self.name, code="invalid_response")
            return data


def harness_chat(unified: str, route: str, messages: list[dict[str, str]], *, max_tokens: int, temperature: float):
    adapter = InstrumentedCompatibleAdapter(
        api_key=unified,
        base_url=study.FREELLM_BASE + "/v1",
        timeout=300.0,
        output_token_field="max_tokens",
    )
    req = ChatRequest(
        model=route,
        messages=tuple(Message(Role(message["role"]), message["content"]) for message in messages),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = adapter.chat(req)
    routed = adapter.last_headers.get("X-Routed-Via") or adapter.last_headers.get("x-routed-via")
    return response.content, {
        "http_status": 200,
        "requested_route": route,
        "response_model": response.model,
        "routed_via": routed,
        "usage": dict(response.usage),
        "residual_adapter": adapter.name,
    }


study.chat = harness_chat

if __name__ == "__main__":
    raise SystemExit(study.main())
