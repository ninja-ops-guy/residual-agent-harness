"""Bridge normalized ai_providers adapters into the ExecutionEngine contract.

Credentials remain environment-owned by ai_providers.registry.  The bridge never
serializes credentials and exposes only normalized response metadata.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ai_providers.core import ChatRequest, Message, Provider, Role
from ai_providers.registry import DEFAULT_REGISTRY, Registry

from .protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec


@dataclass(frozen=True)
class ProviderEngineConfig:
    provider: str
    model: str
    capabilities: tuple[str, ...] = ("text",)
    locality: str = "cloud"
    max_tokens: int = 2048
    temperature: float | None = 0.0
    system_prompt: str = "Return only the requested answer."

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("provider and model are required")
        if not self.capabilities:
            raise ValueError("at least one capability is required")
        if self.locality not in {"local", "cloud"}:
            raise ValueError("locality must be local or cloud")
        if not 1 <= self.max_tokens <= 1_000_000:
            raise ValueError("invalid max_tokens")


class ProviderExecutionEngine:
    """ExecutionEngine backed by a normalized ai_providers Provider."""

    capability_class = "provider_chat"

    def __init__(self, config: ProviderEngineConfig, *, registry: Registry = DEFAULT_REGISTRY):
        self.config = config
        self._registry = registry
        self.name = f"provider:{config.provider}:{config.model}"
        self.version = "provider-bridge-v1"
        self.locality = config.locality
        self._capabilities = frozenset(config.capabilities)

    @property
    def engine_id(self) -> str:
        return f"{self.name}@{self.version}"

    def supports(self, capability: str) -> bool:
        return capability in self._capabilities

    def health(self) -> EngineHealth:
        try:
            self._registry.get(self.config.provider)
            return EngineHealth.HEALTHY
        except Exception:
            return EngineHealth.UNAVAILABLE

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        provider = self._registry.get(self.config.provider)
        prompt = self._prompt(task, context)
        request = ChatRequest(
            model=self.config.model,
            messages=(
                Message(Role.SYSTEM, self.config.system_prompt),
                Message(Role.USER, prompt),
            ),
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        started = time.monotonic()
        response = provider.chat(request)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        usage = response.usage or {}
        token_usage = usage.get("total_tokens")
        if token_usage is None:
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            if prompt_tokens is not None and completion_tokens is not None:
                token_usage = prompt_tokens + completion_tokens
        return EngineResult(
            candidate=response.content,
            token_usage=token_usage,
            wall_clock_ms=elapsed_ms,
            raw_metadata={
                "adapter": "provider_bridge",
                "provider": provider.name,
                "model": response.model,
                "finish_reason": response.finish_reason,
            },
        )

    def normalize(self, raw_output: Any) -> EngineResult:
        if isinstance(raw_output, EngineResult):
            return raw_output
        return EngineResult(candidate=raw_output)

    @staticmethod
    def _prompt(task: TaskSpec, context: ContextAssembly) -> str:
        if isinstance(task.input, str):
            body = task.input
        else:
            import json
            body = json.dumps(task.input, ensure_ascii=False, sort_keys=True)
        if not context.values:
            return body
        import json
        return body + "\n\nContext:\n" + json.dumps(dict(context.values), ensure_ascii=False, sort_keys=True)
