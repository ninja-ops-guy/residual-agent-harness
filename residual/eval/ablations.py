"""Ablation definitions for the FrozenWorkload evaluation.

Each ablation names the harness features that are disabled so the
contribution of each subsystem can be measured against the full
configuration (matched-controller ablations, T10-R1/T10-R3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Tuple


@dataclass(frozen=True)
class Ablation:
    name: str
    description: str
    disabled_features: FrozenSet[str] = field(default_factory=frozenset)

    def disables(self, feature: str) -> bool:
        return feature in self.disabled_features


_FULL = Ablation(
    name="full",
    description="Full harness: cache, brakes, escalation, swarm memory all enabled.",
    disabled_features=frozenset(),
)
_NO_CACHE = Ablation(
    name="no_cache",
    description="Solution cache disabled; every task pays full token cost.",
    disabled_features=frozenset({"cache"}),
)
_NO_BRAKES = Ablation(
    name="no_brakes",
    description="Safety brakes disabled; unsafe actions are not intercepted.",
    disabled_features=frozenset({"brakes"}),
)
_NO_ESCALATION = Ablation(
    name="no_escalation",
    description="HITL escalation disabled; hard tasks are forced local.",
    disabled_features=frozenset({"escalation"}),
)
_NO_MEMORY = Ablation(
    name="no_swarm_memory",
    description="Shared swarm memory disabled; agents cannot reuse prior runs.",
    disabled_features=frozenset({"cache", "memory"}),
)

ABLATIONS: Dict[str, Ablation] = {a.name: a for a in (_FULL, _NO_CACHE, _NO_BRAKES, _NO_ESCALATION, _NO_MEMORY)}

DEFAULT_ABLATION_ORDER: Tuple[str, ...] = tuple(ABLATIONS.keys())
