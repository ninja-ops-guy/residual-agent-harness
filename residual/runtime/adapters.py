"""RUN-R1: ExecutionEngine adapters for supported engines.

Builds on the existing ``residual.engines`` protocol/adapters instead of
duplicating them:

- :class:`SDKFunctionEngine` wraps the existing SDK adapter
  (``ClaudeSDKEngine``/``OpenAIAssistantsEngine``) around a callable so
  SDK-style engines can be exercised without live credentials.
- :class:`LocalDeterministicEngine` is a local, fully deterministic engine
  used as the local-preferred candidate and as a fixture-grade adapter.

Both satisfy the ``residual.engines.protocol.ExecutionEngine`` protocol.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Iterable

from ..engines.protocol import ContextAssembly, EngineHealth, EngineResult, ExecutionEngine, TaskSpec
from ..engines.sdk_adapter import ClaudeSDKEngine, OpenAIAssistantsEngine


class SDKFunctionEngine:
    """Conformance-friendly wrapper over an existing SDK adapter class."""

    def __init__(self, execute_fn: Callable, *, name: str = "claude-sdk",
                 version: str = "unknown", capabilities: Iterable[str] = ("agent",),
                 timeout_s: float = 30.0):
        adapter_cls = {"claude-sdk": ClaudeSDKEngine,
                       "openai-assistants": OpenAIAssistantsEngine}.get(name)
        if adapter_cls is None:
            raise ValueError(f"unsupported sdk adapter: {name}")
        self._inner: ClaudeSDKEngine = adapter_cls(
            execute_fn, version=version, capabilities=tuple(capabilities), timeout_s=timeout_s)

    # Delegate the full ExecutionEngine surface to the wrapped adapter.
    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def version(self) -> str:
        return self._inner.version

    @property
    def capability_class(self) -> str:
        return self._inner.capability_class

    @property
    def locality(self) -> str:
        return self._inner.locality

    def supports(self, capability: str) -> bool:
        return self._inner.supports(capability)

    def health(self) -> EngineHealth:
        return self._inner.health()

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        return self._inner.execute(task, context)

    def normalize(self, raw_output: Any) -> EngineResult:
        return self._inner.normalize(raw_output)


class LocalDeterministicEngine:
    """Local engine whose output is a pure function of (task, context).

    Determinism: identical inputs always produce identical candidates and
    traces; ``wall_clock_ms`` is reported as measured but never enters the
    candidate. Used as the local-preferred routing candidate (RUN-R3) and as
    a fixture adapter for the conformance suite (RUN-R9).
    """

    name = "local-deterministic"
    capability_class = "deterministic_local"
    locality = "local"

    def __init__(self, *, version: str = "1.0.0", capabilities: Iterable[str] = ("agent", "text")):
        caps = tuple(capabilities)
        if not caps:
            raise ValueError("at least one capability is required")
        self.version = version
        self._capabilities = frozenset(caps)

    def supports(self, capability: str) -> bool:
        return capability in self._capabilities

    def health(self) -> EngineHealth:
        return EngineHealth.HEALTHY

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        t0 = time.monotonic()
        candidate = {
            "task_id": task.task_id,
            "capability": task.capability,
            "input": task.input,
            "context": dict(context.values),
            "engine": self.name,
            "engine_version": self.version,
        }
        return EngineResult(
            candidate=candidate,
            wall_clock_ms=int((time.monotonic() - t0) * 1000),
            raw_metadata={
                "adapter": self.name,
                "deterministic": True,
                "residual_policy_authoritative": True,
            },
        )

    def normalize(self, raw_output: Any) -> EngineResult:
        if isinstance(raw_output, EngineResult):
            return raw_output
        return EngineResult(candidate=raw_output)


def sdk_echo(task_input: Any, context: dict) -> dict:
    """Module-level echo callable (picklable for the SDK adapter's isolated
    spawn-process execution)."""
    return {"output": {"echo": task_input, "context": context}}


def build_default_adapters() -> tuple[ExecutionEngine, ExecutionEngine]:
    """Return the two default adapters used by the conformance suite."""
    return (
        LocalDeterministicEngine(),
        SDKFunctionEngine(sdk_echo, name="claude-sdk", version="fixture-1",
                          capabilities=("agent",)),
    )
