"""Per-tenant namespaces and isolated state containers.

Implements ENT3-R1: every tenant owns an independent GoalSpec registry,
module registry, receipt chain, observation log, HITL queue, quarantine
policy set, and brake configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core import ContractError, digest, identifier


@dataclass
class TenantState:
    """Independent state container for one tenant. Implements ENT3-R1.

    Each attribute is private to the owning tenant and never shared:
    goalspec_registry, module_registry, receipt_chain, observation_log,
    hitl_queue, quarantine_policies, and brake_config.
    """
    goalspec_registry: dict[str, Any] = field(default_factory=dict)
    module_registry: dict[str, Any] = field(default_factory=dict)
    receipt_chain: list[dict] = field(default_factory=list)
    observation_log: list[dict] = field(default_factory=list)
    hitl_queue: list[dict] = field(default_factory=list)
    quarantine_policies: set[str] = field(default_factory=set)
    brake_config: dict[str, float] = field(default_factory=dict)

    def append_receipt(self, receipt: dict) -> str:
        """Append a receipt to this tenant's chain (ENT3-R1)."""
        if not isinstance(receipt, dict):
            raise ContractError("receipt must be a mapping")
        entry = dict(receipt)
        entry["sequence"] = len(self.receipt_chain)
        entry["chain_digest"] = digest(
            [r.get("receipt_hash") for r in self.receipt_chain] + [receipt]
        )
        self.receipt_chain.append(entry)
        return entry["chain_digest"]

    def append_observation(self, observation: dict) -> None:
        """Append to this tenant's observation log (ENT3-R1)."""
        if not isinstance(observation, dict):
            raise ContractError("observation must be a mapping")
        self.observation_log.append(dict(observation))

    def enqueue_hitl(self, request: dict) -> None:
        """Enqueue a HITL approval request for this tenant (ENT3-R1)."""
        if not isinstance(request, dict):
            raise ContractError("HITL request must be a mapping")
        self.hitl_queue.append(dict(request))


@dataclass(frozen=True)
class Tenant:
    """A tenant namespace. Implements ENT3-R1.

    `quota` is the scheduling weight used by the fair scheduler (ENT3-R3).
    `state` holds the tenant's fully independent runtime state.
    """
    id: str
    quota: int = 1
    state: TenantState = field(default_factory=TenantState, compare=False)

    def __post_init__(self):
        identifier(self.id)
        if type(self.quota) is not int or self.quota < 1:
            raise ContractError("tenant quota must be a positive integer")
        if not isinstance(self.state, TenantState):
            raise ContractError("tenant state must be a TenantState")

    def register_goalspec(self, spec_id: str, spec: Any) -> None:
        """Register a GoalSpec in this tenant's own registry (ENT3-R1)."""
        identifier(spec_id)
        if spec_id in self.state.goalspec_registry:
            raise ContractError("duplicate goalspec id")
        self.state.goalspec_registry[spec_id] = spec

    def register_module(self, module_id: str, module: Any) -> None:
        """Register a module in this tenant's own registry (ENT3-R1)."""
        identifier(module_id)
        if module_id in self.state.module_registry:
            raise ContractError("duplicate module id")
        self.state.module_registry[module_id] = module
