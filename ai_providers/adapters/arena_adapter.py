"""Arena preview API adapter.

Arena's preview API exposes an OpenAI-compatible chat-completions surface.
This adapter intentionally submits exactly one model per request. Benchmark
runs must keep any higher-level failover in RESIDUAL's Router so every actual
attempt is visible in RESIDUAL receipts instead of being silently relabelled.
"""
from __future__ import annotations

from .openai_adapter import OpenAIAdapter

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

    def supports_tools(self, model):
        # Arena is a gateway over heterogeneous models. A gateway model ID does
        # not prove the selected backend supports tools, so keep capability
        # discovery conservative. Explicit tool-bearing requests are still
        # serialized using the OpenAI-compatible wire format.
        return False
