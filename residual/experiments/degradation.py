"""Deterministic worker-output degradation for reliability experiments.

This module changes candidate quality without changing the underlying model, prompt,
tool surface, or verifier. It is an experimental control, not a production feature.
Every mutation decision is derived from frozen identifiers and recorded in result
metadata so degradation can be reproduced and audited.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..core import canonical, digest
from ..engines.protocol import ContextAssembly, EngineHealth, EngineResult, ExecutionEngine, TaskSpec


_ALLOWED_STRATEGIES = {"type_aware_corruption", "replace_null", "truncate_text"}


def _unit_interval(payload: Mapping[str, Any]) -> float:
    value = int(digest(payload)[:16], 16)
    return value / float(0xFFFFFFFFFFFFFFFF)


def _corrupt(candidate: Any, strategy: str) -> Any:
    if strategy == "replace_null":
        return None
    if strategy == "truncate_text":
        if isinstance(candidate, str):
            return candidate[: max(0, len(candidate) // 2)]
        return None
    if strategy != "type_aware_corruption":
        raise ValueError("unsupported degradation strategy")
    if isinstance(candidate, str):
        if not candidate:
            return "<degraded>"
        return candidate[: max(1, len(candidate) // 2)]
    if isinstance(candidate, dict):
        if not candidate:
            return {"__degraded__": True}
        key = sorted(candidate, key=lambda value: canonical(value))[0]
        return {k: v for k, v in candidate.items() if k != key}
    if isinstance(candidate, list):
        return candidate[:-1] if candidate else [None]
    if isinstance(candidate, tuple):
        return candidate[:-1] if candidate else (None,)
    if isinstance(candidate, bool):
        return not candidate
    if isinstance(candidate, (int, float)):
        return candidate + 1
    return None


@dataclass(frozen=True)
class DegradationProfile:
    level: str
    rate: float
    seed: int
    strategy: str = "type_aware_corruption"

    def __post_init__(self) -> None:
        if not isinstance(self.level, str) or not self.level.strip():
            raise ValueError("degradation level is required")
        if type(self.rate) not in (int, float) or not 0.0 <= float(self.rate) <= 1.0:
            raise ValueError("degradation rate must be in [0,1]")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("degradation seed must be a non-negative integer")
        if self.strategy not in _ALLOWED_STRATEGIES:
            raise ValueError("unsupported degradation strategy")

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.degradation-profile.v1",
            "level": self.level,
            "rate": float(self.rate),
            "seed": self.seed,
            "strategy": self.strategy,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


@dataclass
class DegradingExecutionEngine:
    """ExecutionEngine wrapper that deterministically corrupts a fraction of outputs.

    The wrapped engine's identity is preserved. Experimental provenance is added to
    `raw_metadata`; callers should freeze the profile hash in the study manifest.
    """

    engine: ExecutionEngine
    profile: DegradationProfile

    @property
    def name(self) -> str:
        return self.engine.name

    @property
    def version(self) -> str:
        return self.engine.version

    @property
    def capability_class(self) -> str:
        return self.engine.capability_class

    @property
    def locality(self) -> str:
        return self.engine.locality

    def supports(self, capability: str) -> bool:
        return self.engine.supports(capability)

    def health(self) -> EngineHealth:
        return self.engine.health()

    def normalize(self, raw_output: Any) -> EngineResult:
        return self.engine.normalize(raw_output)

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        original = self.engine.execute(task, context)
        decision_payload = {
            "profile_sha256": self.profile.sha256,
            "task_id": task.task_id,
            "capability": task.capability,
            "engine_name": self.engine.name,
            "engine_version": self.engine.version,
        }
        score = _unit_interval(decision_payload)
        mutated = score < float(self.profile.rate)
        candidate = _corrupt(original.candidate, self.profile.strategy) if mutated else original.candidate
        metadata = dict(original.raw_metadata)
        metadata["degradation"] = {
            "profile_sha256": self.profile.sha256,
            "level": self.profile.level,
            "rate": float(self.profile.rate),
            "seed": self.profile.seed,
            "strategy": self.profile.strategy,
            "decision_score": score,
            "mutated": mutated,
            "original_candidate_sha256": digest({"candidate": original.candidate}),
            "candidate_sha256": digest({"candidate": candidate}),
        }
        return EngineResult(
            candidate=candidate,
            tool_calls=original.tool_calls,
            token_usage=original.token_usage,
            wall_clock_ms=original.wall_clock_ms,
            engine_trace=original.engine_trace,
            raw_metadata=metadata,
        )
