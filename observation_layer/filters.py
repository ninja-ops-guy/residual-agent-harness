"""
observation_layer.filters
=========================
In-stream processing before events hit sinks. Filters are pure functions:
Observation -> Optional[Observation]. Returning None drops the event.
Redaction runs BEFORE any sink sees the event — once it hits disk it's too late.
"""

from __future__ import annotations

import re
from typing import Callable, Optional, Pattern

from .core import Observation


Filter = Callable[[Observation], Optional[Observation]]


def compose(*filters: Filter) -> Filter:
    def _f(obs: Observation) -> Optional[Observation]:
        for flt in filters:
            obs = flt(obs)
            if obs is None:
                return None
        return obs
    return _f


def allow_kinds(*kinds: str) -> Filter:
    allowed = set(kinds)
    return lambda obs: obs if obs.kind.value in allowed else None


def deny_kinds(*kinds: str) -> Filter:
    denied = set(kinds)
    return lambda obs: None if obs.kind.value in denied else obs


def require_tags(**kv: str) -> Filter:
    return lambda obs: obs if all(obs.tags.get(k) == v for k, v in kv.items()) else None


def sample_every(n: int) -> Filter:
    """Deterministic sampling: keep every n-th event per trace."""
    if type(n) is not int or n < 1:
        raise ValueError("Sampling interval must be a positive integer")
    counters: dict[str, int] = {}
    def _f(obs: Observation) -> Optional[Observation]:
        c = counters.get(obs.trace_id, 0)
        counters[obs.trace_id] = c + 1
        return obs if c % n == 0 else None
    return _f


def _redact_in(obj, patterns: list[Pattern], replacement: str):
    if isinstance(obj, dict):
        return {k: _redact_in(v, patterns, replacement) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_redact_in(v, patterns, replacement) for v in obj]
    if isinstance(obj, str):
        for p in patterns:
            obj = p.sub(replacement, obj)
        return obj
    return obj


def redact_payload(patterns: list[str], replacement: str = "[REDACTED]") -> Filter:
    """
    Regex-based redaction over the entire payload. Use for API keys, tokens,
    PII. Patterns are applied to every string in the payload tree.
    """
    compiled = [re.compile(p) for p in patterns]
    def _f(obs: Observation) -> Observation:
        new_payload = _redact_in(obs.payload, compiled, replacement)
        # Observation is frozen; build a new one preserving chain fields
        return Observation(
            obs_id=obs.obs_id,
            trace_id=obs.trace_id,
            kind=obs.kind,
            timestamp_ns=obs.timestamp_ns,
            schema_version=obs.schema_version,
            prev_hash=obs.prev_hash,
            payload=new_payload,
            tags=obs.tags,
            source=obs.source,
        )
    return _f
