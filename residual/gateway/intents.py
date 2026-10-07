"""Track D: SideEffectIntent schema — the only currency of mutation.

Requirement IDs (RFC 2119):
- D-R1: Every mutating action MUST be expressed as a validated
  ``SideEffectIntent`` before it reaches any executor.
- D-R2: An intent MUST declare its action kind, target, reversibility, and
  blast radius; unknown values MUST be rejected at construction.
- D-R3: Intents MUST be immutable and content-addressed so the gateway audit
  log binds to exactly what was proposed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from observation_layer.core import freeze

from ..core import ContractError, digest, identifier


class ActionKind(str, Enum):
    """The universe of mutating action kinds the gateway understands."""

    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    PROCESS_SPAWN = "process_spawn"
    NETWORK_EGRESS = "network_egress"
    CONFIG_CHANGE = "config_change"
    PROVIDER_CALL = "provider_call"
    TOOL_CALL = "tool_call"
    STATE_MUTATION = "state_mutation"


class Reversibility(str, Enum):
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class BlastRadius(str, Enum):
    """Ordered scope of potential damage. Order matters for policy."""

    LOCAL = "local"        # one artifact in the workspace
    MODULE = "module"      # one module/package
    RUN = "run"            # the whole run's state
    SYSTEM = "system"      # host system beyond the run


_RADIUS_ORDER = tuple(BlastRadius)


def radius_at_least(radius: BlastRadius, floor: BlastRadius) -> bool:
    """True when ``radius`` is at least as broad as ``floor``."""
    return _RADIUS_ORDER.index(radius) >= _RADIUS_ORDER.index(floor)


@dataclass(frozen=True)
class SideEffectIntent:
    """D-R1..D-R3: a validated, immutable, content-addressed mutation request."""

    action_kind: ActionKind
    target: str                      # path, host, tool name, state key
    reversibility: Reversibility
    blast_radius: BlastRadius
    parameters: dict[str, Any] = field(default_factory=dict)
    agent_id: str = "unknown"
    intent_id: str = field(default_factory=lambda: f"i-{uuid.uuid4().hex}")

    def __post_init__(self):
        try:
            object.__setattr__(self, "action_kind", ActionKind(self.action_kind))
        except (ValueError, TypeError):
            raise ContractError("unknown action kind") from None
        try:
            object.__setattr__(self, "reversibility", Reversibility(self.reversibility))
        except (ValueError, TypeError):
            raise ContractError("unknown reversibility") from None
        try:
            object.__setattr__(self, "blast_radius", BlastRadius(self.blast_radius))
        except (ValueError, TypeError):
            raise ContractError("unknown blast radius") from None
        if not isinstance(self.target, str) or not self.target.strip() or "\x00" in self.target:
            raise ContractError("intent requires a non-empty target")
        identifier(self.agent_id)
        identifier(self.intent_id)
        try:
            if not isinstance(self.parameters, dict):
                raise ValueError()
            object.__setattr__(self, "parameters", freeze(self.parameters))
        except Exception:
            raise ContractError("intent parameters must be canonicalizable")

    def content(self) -> dict:
        """Canonical content used for hashing (excludes the random id)."""
        return {
            "action_kind": self.action_kind.value,
            "target": self.target,
            "reversibility": self.reversibility.value,
            "blast_radius": self.blast_radius.value,
            "parameters": self.parameters,
            "agent_id": self.agent_id,
        }

    @property
    def content_hash(self) -> str:
        """D-R3: content address — identical proposals hash identically."""
        return digest(self.content())
