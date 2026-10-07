"""Failure injection for the soak harness (N9-R9, N9-R12).

Injects intentional failures (bad configs, missing dependencies) and
adversarial inputs (injection attempts, contract violations) with
seeded determinism so a resumed soak reproduces the identical mix.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

FAILURE_KINDS = ("bad_config", "missing_dependency")
ADVERSARIAL_KINDS = ("injection_attempt", "contract_violation")


@dataclass(frozen=True)
class InjectionMix:
    bad_config_rate: float = 0.02
    missing_dependency_rate: float = 0.01
    injection_attempt_rate: float = 0.005
    contract_violation_rate: float = 0.005

    def __post_init__(self) -> None:
        total = (self.bad_config_rate + self.missing_dependency_rate
                 + self.injection_attempt_rate + self.contract_violation_rate)
        for name, value in (
            ("bad_config_rate", self.bad_config_rate),
            ("missing_dependency_rate", self.missing_dependency_rate),
            ("injection_attempt_rate", self.injection_attempt_rate),
            ("contract_violation_rate", self.contract_violation_rate),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if total > 1.0:
            raise ValueError("injection rates must sum to <= 1")


@dataclass(frozen=True)
class InjectedFault:
    kind: str  # one of FAILURE_KINDS + ADVERSARIAL_KINDS
    recoverable: bool
    expected_handling: str  # "rejected" for bad inputs, "recover" for missing deps


class FailureInjector:
    """Decides, deterministically, whether a task carries an injected fault."""

    def __init__(self, seed: int = 20260914, mix: Optional[InjectionMix] = None):
        self.seed = seed
        self.mix = mix or InjectionMix()

    def fault_for(self, day: int, index: int) -> Optional[InjectedFault]:
        rng = random.Random(f"{self.seed}:fault:{day}:{index}")
        roll = rng.random()
        m = self.mix
        cumulative = m.bad_config_rate
        if roll < cumulative:
            return InjectedFault("bad_config", recoverable=False, expected_handling="rejected")
        cumulative += m.missing_dependency_rate
        if roll < cumulative:
            return InjectedFault("missing_dependency", recoverable=True, expected_handling="recover")
        cumulative += m.injection_attempt_rate
        if roll < cumulative:
            return InjectedFault("injection_attempt", recoverable=False, expected_handling="rejected")
        cumulative += m.contract_violation_rate
        if roll < cumulative:
            return InjectedFault("contract_violation", recoverable=False, expected_handling="rejected")
        return None
