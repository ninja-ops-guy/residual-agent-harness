"""Data-layer tenant isolation with explicit federation.

Implements ENT3-R2: one tenant cannot query, read, or modify another
tenant's receipts, observations, or state — even with administrative
privileges — unless an explicit federation agreement exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError, identifier


@dataclass(frozen=True)
class Principal:
    """A caller identity bound to exactly one tenant. Implements ENT3-R2.

    `admin=True` grants administrative privilege *within* the principal's
    own tenant only; it never authorizes cross-tenant access (ENT3-R2).
    """
    tenant_id: str
    admin: bool = False

    def __post_init__(self):
        identifier(self.tenant_id)
        if type(self.admin) is not bool:
            raise ContractError("principal admin flag must be a bool")


@dataclass(frozen=True)
class FederationAgreement:
    """Explicit cross-tenant access agreement. Implements ENT3-R2.

    Grants `grantee` read access to the named `resources` (store keys)
    owned by `grantor`. Both parties must have opted in (bilateral=True
    enforces that construction records both tenants).
    """
    grantor: str
    grantee: str
    resources: tuple[str, ...]
    bilateral: bool = True

    def __post_init__(self):
        identifier(self.grantor)
        identifier(self.grantee)
        if self.grantor == self.grantee:
            raise ContractError("federation requires two distinct tenants")
        if not self.resources or any(not isinstance(r, str) or not r for r in self.resources):
            raise ContractError("federation resources must be non-empty strings")
        if type(self.bilateral) is not bool or not self.bilateral:
            raise ContractError("federation agreement must be bilateral")

    def covers(self, grantor: str, grantee: str, resource: str) -> bool:
        """True if this agreement authorizes the access (ENT3-R2)."""
        return (self.grantor == grantor and self.grantee == grantee
                and resource in self.resources)


@dataclass
class TenantStore:
    """Hard data-layer isolation boundary. Implements ENT3-R2.

    All reads/writes are checked against the caller's principal. Any
    cross-tenant access raises ContractError — including for admin
    principals — unless a matching FederationAgreement exists.
    """
    _data: dict[str, dict[str, dict]] = field(default_factory=dict)
    _agreements: list[FederationAgreement] = field(default_factory=list)

    def add_federation(self, agreement: FederationAgreement) -> None:
        """Register an explicit federation agreement (ENT3-R2)."""
        if not isinstance(agreement, FederationAgreement):
            raise ContractError("expected a FederationAgreement")
        self._agreements.append(agreement)

    def _authorize(self, principal: Principal, owner: str, key: str, write: bool) -> None:
        if not isinstance(principal, Principal):
            raise ContractError("a typed Principal is required")
        identifier(owner)
        if principal.tenant_id == owner:
            return
        if write:
            raise ContractError(
                "cross-tenant writes are never permitted (ENT3-R2)")
        if not any(a.covers(owner, principal.tenant_id, key) for a in self._agreements):
            raise ContractError(
                "cross-tenant access denied: no federation agreement (ENT3-R2)")

    def put(self, principal: Principal, owner: str, key: str, value: dict) -> None:
        """Write a record; cross-tenant writes always raise (ENT3-R2)."""
        if not isinstance(value, dict):
            raise ContractError("stored value must be a mapping")
        self._authorize(principal, owner, key, write=True)
        self._data.setdefault(owner, {})[key] = dict(value)

    def get(self, principal: Principal, owner: str, key: str) -> dict:
        """Read a record; cross-tenant reads require federation (ENT3-R2)."""
        self._authorize(principal, owner, key, write=False)
        try:
            return dict(self._data[owner][key])
        except KeyError:
            raise ContractError("no such record") from None

    def query(self, principal: Principal, owner: str) -> dict[str, dict]:
        """List an owner's records; cross-tenant listing is denied (ENT3-R2)."""
        if not isinstance(principal, Principal):
            raise ContractError("a typed Principal is required")
        identifier(owner)
        if principal.tenant_id != owner:
            raise ContractError(
                "cross-tenant query denied: no federation agreement (ENT3-R2)")
        return {k: dict(v) for k, v in self._data.get(owner, {}).items()}
