"""Licensing model: open-core plus commercial tiers with metering (ENT8-R7)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..core import ContractError, identifier


class Tier(str, Enum):
    OPEN = "open"            # open source core platform (ENT8-R7)
    COMMERCIAL = "commercial"  # enterprise features
    EDUCATIONAL = "educational"  # discounted commercial
    NONPROFIT = "nonprofit"     # discounted commercial


class MeteringModel(str, Enum):
    PER_NODE = "per_node"
    PER_TASK = "per_task"
    FLAT = "flat"


# Enterprise features gated behind a commercial license (ENT8-R7).
COMMERCIAL_FEATURES = frozenset({
    "multi_tenancy",
    "ha_dr",
    "compliance_reporting",
    "premium_support",
    "sso_scim",
    "audit_export",
})

OPEN_FEATURES = frozenset({
    "task_execution",
    "hitl",
    "brakes",
    "receipts",
    "modules",
})

# Discount applied to list price for discounted tiers (ENT8-R7).
DISCOUNT_RATES = {
    Tier.OPEN: 1.0,
    Tier.COMMERCIAL: 0.0,
    Tier.EDUCATIONAL: 0.5,
    Tier.NONPROFIT: 0.4,
}

# List prices in USD.
LIST_PRICES = {
    MeteringModel.PER_NODE: 1200.0,   # per node per month
    MeteringModel.PER_TASK: 0.05,     # per executed task
    MeteringModel.FLAT: 60000.0,      # per year
}


@dataclass(frozen=True)
class License:
    """A commercial license grant (ENT8-R7)."""
    licensee: str
    tier: Tier
    metering: MeteringModel
    node_limit: int = 0       # 0 = unlimited
    task_limit: int = 0       # 0 = unlimited
    features: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        identifier(self.licensee)
        if self.node_limit < 0 or self.task_limit < 0:
            raise ContractError("limits must be non-negative")
        if self.tier is Tier.OPEN:
            object.__setattr__(self, "features", frozenset(OPEN_FEATURES))
        elif not self.features:
            object.__setattr__(
                self, "features", frozenset(OPEN_FEATURES | COMMERCIAL_FEATURES))
        unknown = self.features - (OPEN_FEATURES | COMMERCIAL_FEATURES)
        if unknown:
            raise ContractError(f"unknown licensed features: {sorted(unknown)}")

    def allows(self, feature: str) -> bool:
        """Enforcement hook: True when the feature is licensed (ENT8-R7)."""
        return feature in self.features

    def require(self, feature: str) -> None:
        """Enforcement hook raising ContractError on unlicensed use."""
        if not self.allows(feature):
            raise ContractError(
                f"feature '{feature}' requires a commercial license (ENT8-R7)")

    def price(self) -> float:
        """List price after tier discount; open tier is free."""
        if self.tier is Tier.OPEN:
            return 0.0
        base = LIST_PRICES[self.metering]
        return round(base * (1.0 - DISCOUNT_RATES[self.tier]), 2)


@dataclass
class UsageMeter:
    """Tracks node and task usage against a license (ENT8-R7)."""
    license: License
    active_nodes: int = 0
    tasks_executed: int = 0

    def register_node(self, count: int = 1) -> None:
        if count < 1:
            raise ContractError("node count must be positive")
        if self.license.metering is MeteringModel.PER_NODE:
            limit = self.license.node_limit
            if limit and self.active_nodes + count > limit:
                raise ContractError(
                    f"node limit {limit} exceeded (ENT8-R7 per-node metering)")
        self.active_nodes += count

    def deregister_node(self, count: int = 1) -> None:
        if count < 1 or count > self.active_nodes:
            raise ContractError("cannot deregister more nodes than active")
        self.active_nodes -= count

    def record_task(self, count: int = 1) -> None:
        if count < 1:
            raise ContractError("task count must be positive")
        if self.license.metering is MeteringModel.PER_TASK:
            limit = self.license.task_limit
            if limit and self.tasks_executed + count > limit:
                raise ContractError(
                    f"task limit {limit} exceeded (ENT8-R7 per-task metering)")
        self.tasks_executed += count

    def overage(self) -> dict:
        """Report current usage vs. limits for billing reconciliation."""
        return {
            "metering": self.license.metering.value,
            "active_nodes": self.active_nodes,
            "node_limit": self.license.node_limit,
            "tasks_executed": self.tasks_executed,
            "task_limit": self.license.task_limit,
        }
