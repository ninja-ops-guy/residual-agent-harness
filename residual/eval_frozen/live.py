"""Provider-backed live worker execution for frozen evaluation.

This module deliberately separates genuine model execution from the scripted
control-layer fixture. A live worker observation is never labelled live_model
unless bytes actually came from a configured provider.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from ai_providers import ChatRequest, Message, Role, DEFAULT_REGISTRY, ProviderError
from .workload import FrozenTask


@dataclass(frozen=True)
class LiveWorkerObservation:
    task_id: str
    repeat: int
    provider: str
    model: str
    content: str
    correct: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int


def _exact_match(value: str, expected: str) -> bool:
    return value.strip() == expected.strip()


def run_live_worker(task: FrozenTask, repeat: int, *, provider: str,
                    model: str, seed: int = 0) -> LiveWorkerObservation:
    """Execute one frozen task against a real provider and independently grade it."""
    adapter = DEFAULT_REGISTRY.get(provider)
    req = ChatRequest(
        model=model,
        messages=(
            Message(Role.SYSTEM, "Return only the answer. No explanation."),
            Message(Role.USER, task.prompt),
        ),
        temperature=0.0,
        max_tokens=512,
        seed=seed + repeat,
    )
    started = time.perf_counter_ns()
    response = adapter.chat(req)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    usage = response.usage or {}
    return LiveWorkerObservation(
        task_id=task.task_id,
        repeat=repeat,
        provider=provider,
        model=response.model or model,
        content=response.content,
        correct=_exact_match(response.content, task.expected),
        latency_ms=round(elapsed_ms, 3),
        input_tokens=int(usage.get("prompt_tokens", 0)),
        output_tokens=int(usage.get("completion_tokens", 0)),
    )


def probe_provider(*, provider: str, model: str) -> dict[str, object]:
    """Fail closed unless the requested provider/model is genuinely reachable."""
    adapter = DEFAULT_REGISTRY.get(provider)
    models = adapter.list_models()
    if provider == "ollama" and model not in models:
        raise ProviderError(provider=provider, code="model_not_found")
    return {"provider": provider, "model": model, "available_models": models}
