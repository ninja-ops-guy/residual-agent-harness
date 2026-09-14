"""Platform-privileged tenant lifecycle operations.

Implements ENT3-R6: tenant creation and deletion are administrative
operations requiring platform-level privileges. Deletion archives all
receipts and observations, destroys all tenant state, and emits a
final deletion receipt into the archive.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError, digest, identifier
from .tenant import Tenant


@dataclass(frozen=True)
class PlatformOperator:
    """A platform-level operator. Implements ENT3-R6.

    Only operators with `platform_admin=True` may create or delete
    tenants; tenant-scoped admins are not sufficient.
    """
    id: str
    platform_admin: bool = False

    def __post_init__(self):
        identifier(self.id)
        if type(self.platform_admin) is not bool:
            raise ContractError("platform_admin must be a bool")


@dataclass(frozen=True)
class DeletionRecord:
    """Archive produced by tenant deletion. Implements ENT3-R6."""
    tenant_id: str
    archived_receipts: tuple[dict, ...]
    archived_observations: tuple[dict, ...]
    deletion_receipt: dict

    def __post_init__(self):
        identifier(self.tenant_id)
        if not isinstance(self.deletion_receipt, dict):
            raise ContractError("deletion receipt must be a mapping")


@dataclass
class TenantLifecycle:
    """Creates and deletes tenants under platform privilege. Implements ENT3-R6."""
    tenants: dict[str, Tenant] = field(default_factory=dict)
    archives: dict[str, DeletionRecord] = field(default_factory=dict)

    @staticmethod
    def _require_platform_admin(operator: PlatformOperator) -> None:
        if not isinstance(operator, PlatformOperator):
            raise ContractError("a typed PlatformOperator is required")
        if not operator.platform_admin:
            raise ContractError(
                "platform-level privileges required for tenant lifecycle (ENT3-R6)")

    def create_tenant(self, operator: PlatformOperator, tenant_id: str,
                      quota: int = 1) -> Tenant:
        """Create a tenant; platform-admin only (ENT3-R6)."""
        self._require_platform_admin(operator)
        identifier(tenant_id)
        if tenant_id in self.tenants:
            raise ContractError("tenant already exists")
        if tenant_id in self.archives:
            raise ContractError("tenant id was previously deleted and archived")
        tenant = Tenant(id=tenant_id, quota=quota)
        self.tenants[tenant_id] = tenant
        return tenant

    def delete_tenant(self, operator: PlatformOperator, tenant_id: str) -> DeletionRecord:
        """Delete a tenant. Implements ENT3-R6.

        Archives all receipts and observations, destroys all state, and
        produces a final deletion receipt stored in the archive.
        """
        self._require_platform_admin(operator)
        identifier(tenant_id)
        try:
            tenant = self.tenants.pop(tenant_id)
        except KeyError:
            raise ContractError("unknown tenant") from None
        receipts = tuple(dict(r) for r in tenant.state.receipt_chain)
        observations = tuple(dict(o) for o in tenant.state.observation_log)
        deletion_receipt = {
            "kind": "tenant-deletion",
            "tenant_id": tenant_id,
            "receipt_count": len(receipts),
            "observation_count": len(observations),
            "receipts_digest": digest([r.get("receipt_hash") for r in receipts]),
            "observations_digest": digest(observations),
        }
        deletion_receipt["receipt_hash"] = digest(deletion_receipt)
        # Destroy all tenant state.
        tenant.state.goalspec_registry.clear()
        tenant.state.module_registry.clear()
        tenant.state.receipt_chain.clear()
        tenant.state.observation_log.clear()
        tenant.state.hitl_queue.clear()
        tenant.state.quarantine_policies.clear()
        tenant.state.brake_config.clear()
        record = DeletionRecord(
            tenant_id=tenant_id,
            archived_receipts=receipts,
            archived_observations=observations,
            deletion_receipt=deletion_receipt)
        self.archives[tenant_id] = record
        return record
