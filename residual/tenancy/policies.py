"""Per-tenant policy layers validated against platform floors.

Implements ENT3-R5: each tenant may define its own quarantine policies,
brake thresholds, verification requirements, and module allow/deny
lists — but only by *tightening* platform defaults, never loosening
them below platform floors.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError, identifier


@dataclass(frozen=True)
class PlatformFloors:
    """Platform-level safety minimums. Implements ENT3-R5.

    - `brake_floor`: maximum allowed brake threshold (lower is safer;
      tenants may only set thresholds at or below this).
    - `verification_minimum`: minimum required verification level
      (higher is stricter; tenants may only set levels at or above this).
    - `default_quarantine`: quarantine policies every tenant must keep.
    """
    brake_floor: float = 1.0
    verification_minimum: int = 1
    default_quarantine: frozenset[str] = frozenset({"unverified-receipt"})

    def __post_init__(self):
        if not isinstance(self.brake_floor, (int, float)) or isinstance(self.brake_floor, bool):
            raise ContractError("brake floor must be numeric")
        if self.brake_floor <= 0:
            raise ContractError("brake floor must be positive")
        if type(self.verification_minimum) is not int or self.verification_minimum < 1:
            raise ContractError("verification minimum must be a positive integer")
        if any(not isinstance(p, str) or not p for p in self.default_quarantine):
            raise ContractError("default quarantine policies must be non-empty strings")


@dataclass(frozen=True)
class TenantPolicy:
    """A tenant's own policy layer. Implements ENT3-R5.

    `brake_threshold` trips braking earlier (safer) when lower;
    `verification_level` is stricter when higher; `quarantine_policies`
    add to platform defaults; modules may be allowlisted or denylisted
    but not both.
    """
    tenant_id: str
    brake_threshold: float
    verification_level: int
    quarantine_policies: frozenset[str] = frozenset()
    module_allowlist: frozenset[str] = frozenset()
    module_denylist: frozenset[str] = frozenset()

    def __post_init__(self):
        identifier(self.tenant_id)
        if (not isinstance(self.brake_threshold, (int, float))
                or isinstance(self.brake_threshold, bool) or self.brake_threshold <= 0):
            raise ContractError("brake threshold must be a positive number")
        if type(self.verification_level) is not int or self.verification_level < 1:
            raise ContractError("verification level must be a positive integer")
        for name in ("quarantine_policies", "module_allowlist", "module_denylist"):
            value = getattr(self, name)
            if any(not isinstance(p, str) or not p for p in value):
                raise ContractError(f"{name} entries must be non-empty strings")
        if self.module_allowlist and self.module_denylist:
            overlap = self.module_allowlist & self.module_denylist
            if overlap:
                raise ContractError("module cannot be both allowed and denied")


def validate_policy(policy: TenantPolicy, floors: PlatformFloors) -> TenantPolicy:
    """Validate a tenant policy against platform floors. Implements ENT3-R5.

    Tenants may only tighten: brake thresholds must be at or below the
    floor, verification levels at or above the minimum, and all default
    quarantine policies must be retained. Any loosening raises.
    """
    if not isinstance(policy, TenantPolicy) or not isinstance(floors, PlatformFloors):
        raise ContractError("expected TenantPolicy and PlatformFloors")
    if policy.brake_threshold > floors.brake_floor:
        raise ContractError(
            "brake threshold loosens the platform floor (ENT3-R5)")
    if policy.verification_level < floors.verification_minimum:
        raise ContractError(
            "verification level below the platform minimum (ENT3-R5)")
    missing = floors.default_quarantine - policy.quarantine_policies
    if missing:
        raise ContractError(
            f"tenant dropped platform quarantine policies: {sorted(missing)} (ENT3-R5)")
    return policy
