"""SPEC-003: Independent brake state machines subscribing to the observation bus.

Four brakes: MaxIteration, Budget, NoProgress, Completion.
Brakes never terminate the run directly (R9). They trip and the
LoopController decides.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from .core import ContractError, canonical, positive_int
from .goalspec import GoalSpec


class BrakeAction(str, Enum):
    CONTINUE = "continue"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass(frozen=True)
class BrakeTrip:
    """SPEC-003-R3: structured trip record."""
    brake_name: str
    trip_reason: str
    triggering_obs_hash: str
    recommended_action: BrakeAction


class Brake(Protocol):
    """SPEC-003-R1: the brake contract."""
    name: str

    def update(self, event: dict) -> Optional[BrakeTrip]: ...
    def reset(self) -> None: ...


def _obs_hash(event: dict) -> str:
    return hashlib.sha256(canonical(event).encode()).hexdigest()


class MaxIterationBrake:
    """SPEC-003-R4: trips when pass count reaches spec.max_passes."""

    def __init__(self, spec: GoalSpec):
        self.name = "max_iteration"
        self._spec = spec
        self._pass_count = 0

    def update(self, event: dict) -> Optional[BrakeTrip]:
        if event.get("kind") == "state.transition" and event.get("to_state") == "pass_complete":
            self._pass_count += 1
            if self._pass_count >= self._spec.max_passes and event.get("overall_pass") is not True:
                return BrakeTrip(
                    brake_name=self.name,
                    trip_reason=f"pass_count {self._pass_count} >= max_passes {self._spec.max_passes}",
                    triggering_obs_hash=_obs_hash(event),
                    recommended_action=BrakeAction.ESCALATE,
                )
        return None

    def reset(self) -> None:
        self._pass_count = 0


class BudgetBrake:
    """SPEC-003-R5: trips on token or wall-clock budget exhaustion."""

    def __init__(self, spec: GoalSpec):
        self.name = "budget"
        self._spec = spec
        self._tokens_used = 0
        self._start_ns: Optional[int] = None

    def update(self, event: dict) -> Optional[BrakeTrip]:
        if self._start_ns is None:
            self._start_ns = time.monotonic_ns()
        usage = event.get("usage") or {}
        if event.get("kind") == "llm.response":
            tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
            if type(tokens) is not int or tokens < 0:
                return BrakeTrip(self.name, "usage_unknown_or_invalid", _obs_hash(event), BrakeAction.ABORT)
            self._tokens_used += tokens
            if self._tokens_used >= self._spec.token_budget:
                return BrakeTrip(
                    brake_name=self.name,
                    trip_reason=f"tokens {self._tokens_used} >= budget {self._spec.token_budget}",
                    triggering_obs_hash=_obs_hash(event),
                    recommended_action=BrakeAction.ABORT,
                )
        elapsed_s = (time.monotonic_ns() - self._start_ns) / 1e9
        if elapsed_s >= self._spec.wall_clock_budget_s:
            return BrakeTrip(
                brake_name=self.name,
                trip_reason=f"elapsed {elapsed_s:.1f}s >= budget {self._spec.wall_clock_budget_s}s",
                triggering_obs_hash=_obs_hash(event),
                recommended_action=BrakeAction.ABORT,
            )
        return None

    def reset(self) -> None:
        self._tokens_used = 0
        self._start_ns = None


class NoProgressBrake:
    """SPEC-003-R6: trips on consecutive identical tool call fingerprints."""

    def __init__(self, threshold: int = 3):
        positive_int(threshold, "no-progress threshold")
        if threshold < 2:
            raise ContractError("no-progress threshold must be >= 2")
        self.name = "no_progress"
        self._threshold = threshold
        self._last_fingerprint: Optional[str] = None
        self._streak = 0

    def update(self, event: dict) -> Optional[BrakeTrip]:
        if event.get("kind") != "tool.invoked":
            return None
        payload = event.get("payload") or {}
        # Prefer a host-computed digest so argument bodies need not enter telemetry.
        fp = payload.get("fingerprint") or hashlib.sha256(canonical({
            "tool": payload.get("tool"),
            "args": payload.get("args"),
            "kwargs": payload.get("kwargs"),
        }).encode()).hexdigest()
        if fp == self._last_fingerprint:
            self._streak += 1
        else:
            self._last_fingerprint = fp
            self._streak = 1
        if self._streak >= self._threshold:
            return BrakeTrip(
                brake_name=self.name,
                trip_reason=f"identical tool call repeated {self._streak} consecutive times",
                triggering_obs_hash=_obs_hash(event),
                recommended_action=BrakeAction.ESCALATE,
            )
        return None

    def reset(self) -> None:
        self._last_fingerprint = None
        self._streak = 0


class CompletionBrake:
    """SPEC-003-R7: trips when all GoalSpec checks pass."""

    def __init__(self):
        self.name = "completion"
        self._tripped = False

    def update(self, event: dict) -> Optional[BrakeTrip]:
        if self._tripped:
            return None
        if (event.get("kind") == "custom" and event.get("payload", {}).get("event") == "verification_report"
                and event.get("payload", {}).get("overall_pass") is True):
            self._tripped = True
            return BrakeTrip(
                brake_name=self.name,
                trip_reason="all goal spec checks passed",
                triggering_obs_hash=_obs_hash(event),
                recommended_action=BrakeAction.CONTINUE,
            )
        return None

    def reset(self) -> None:
        self._tripped = False


def build_brakes(spec: GoalSpec, no_progress_threshold: int = 3) -> tuple[Brake, ...]:
    """Construct the standard brake set for a GoalSpec."""
    return (
        MaxIterationBrake(spec),
        BudgetBrake(spec),
        NoProgressBrake(threshold=no_progress_threshold),
        CompletionBrake(),
    )
