"""
ai_providers.registry
======================
Provider discovery, construction, and routing. One entry point; the caller
never imports adapter modules directly.
"""

from __future__ import annotations

import os
from typing import Optional

from .core import Provider, ProviderError, ProviderName
import threading


class Registry:
    """
    Lazily loads adapters. Adapters register themselves via entry points
    (production) or explicit registration (below). Keeps import graph clean:
    importing ai_providers does not import every SDK.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._factories: dict[str, callable] = {}
        self._instances: dict[str, Provider] = {}

    def register(self, name: str, factory: callable) -> None:
        """factory: () -> Provider. Called lazily on first use."""
        name = ProviderName(name).value
        with self._lock:
            self._factories[name] = factory
            self._instances.pop(name, None)

    def get(self, name: str) -> Provider:
        with self._lock:
            if name not in self._factories:
                raise ProviderError(provider="router", code="unknown_provider")
            if name not in self._instances:
                try:
                    instance = self._factories[name]()
                    if instance.name != name: raise ValueError("Factory name mismatch")
                    self._instances[name] = instance
                except ProviderError: raise
                except Exception: raise ProviderError(provider=name, code="config") from None
            return self._instances[name]

    def names(self) -> list[str]:
        return sorted(self._factories)


# --- Built-in registrations (lazy) -------------------------------------------

def _default_registry() -> Registry:
    reg = Registry()

    def _openai():
        from .adapters.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=os.environ.get("OPENAI_API_KEY"))

    def _anthropic():
        from .adapters.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def _google():
        from .adapters.google_adapter import GoogleAdapter
        return GoogleAdapter(api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))

    def _azure():
        from .adapters.azure_adapter import AzureAdapter
        return AzureAdapter(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )

    def _bedrock():
        from .adapters.bedrock_adapter import BedrockAdapter
        return BedrockAdapter(
            access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            session_token=os.environ.get("AWS_SESSION_TOKEN"),
        )

    def _ollama():
        from .adapters.ollama_adapter import OllamaAdapter
        return OllamaAdapter(base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))

    def _arena():
        from .adapters.arena_adapter import ArenaAdapter
        return ArenaAdapter(
            api_key=os.environ.get("ARENA_API_KEY"),
            base_url=os.environ.get("ARENA_BASE_URL", "https://api.preview.arena.ai/v1"),
        )

    def _compatible():
        from .adapters.openai_adapter import OpenAICompatibleAdapter
        return OpenAICompatibleAdapter(api_key=os.environ.get("LLM_API_KEY"), base_url=os.environ.get("LLM_BASE_URL", "http://localhost:8080/v1"))

    reg.register("openai_compatible", _compatible)
    reg.register("arena", _arena)
    reg.register("openai", _openai)
    reg.register("anthropic", _anthropic)
    reg.register("google", _google)
    reg.register("azure", _azure)
    reg.register("bedrock", _bedrock)
    reg.register("ollama", _ollama)
    return reg


DEFAULT_REGISTRY = _default_registry()
