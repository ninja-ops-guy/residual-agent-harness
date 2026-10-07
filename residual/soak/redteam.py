"""Red team exercise for the soak test (N9-R12).

A dedicated adversary attempts to bypass quarantine, forge receipts,
trigger unsafe execution, and exfiltrate data. Every attempt MUST
produce a receipt; the report records blocked vs succeeded. The bundled
adversary is a deterministic simulator so the harness is testable
offline; the receipt-producing interface matches what a real Station
integration would call.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import List

ATTACK_KINDS = ("quarantine_bypass", "receipt_forgery", "unsafe_execution", "data_exfiltration")


@dataclass(frozen=True)
class RedTeamAttempt:
    exercise: str
    attack: str
    blocked: bool
    observed: bool
    receipt_id: str
    detail: str

    def to_dict(self):
        return {
            "exercise": self.exercise,
            "attack": self.attack,
            "blocked": self.blocked,
            "observed": self.observed,
            "receipt_id": self.receipt_id,
            "detail": self.detail,
        }


class RedTeamExercise:
    """Runs a deterministic series of adversarial attempts."""

    def __init__(self, seed: int = 20260914, name: str = "redteam-alpha",
                 defense_strength: float = 1.0):
        """defense_strength: probability each attempt is blocked (1.0 = spec)."""
        if not 0.0 <= defense_strength <= 1.0:
            raise ValueError("defense_strength must be in [0, 1]")
        self.seed = seed
        self.name = name
        self.defense_strength = defense_strength

    def run(self, attempts_per_kind: int = 3) -> List[RedTeamAttempt]:
        results: List[RedTeamAttempt] = []
        rng = random.Random(f"{self.seed}:redteam:{self.name}")
        for attack in ATTACK_KINDS:
            for i in range(attempts_per_kind):
                blocked = rng.random() < self.defense_strength
                body = f"{self.seed}:{self.name}:{attack}:{i}:{blocked}"
                results.append(RedTeamAttempt(
                    exercise=self.name,
                    attack=attack,
                    blocked=blocked,
                    observed=True,  # every attempt MUST be observed
                    receipt_id=hashlib.sha256(body.encode()).hexdigest()[:20],
                    detail=f"attempt {i} of {attack}",
                ))
        return results
