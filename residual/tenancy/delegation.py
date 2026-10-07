"""Cross-tenant task delegation with per-execution HITL approval.

Implements ENT3-R4: tenant A may grant tenant B permission to execute
scoped tasks affecting A's infrastructure. Delegations are scoped
(task types and resources), time-limited, require HITL approval from
the granting tenant for each execution, and produce receipts visible
to both tenants.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError, digest, identifier
from .tenant import Tenant


@dataclass(frozen=True)
class DelegationGrant:
    """A scoped, time-limited cross-tenant grant. Implements ENT3-R4."""
    id: str
    grantor: str
    grantee: str
    task_types: tuple[str, ...]
    resources: tuple[str, ...]
    expires_at: int

    def __post_init__(self):
        identifier(self.id)
        identifier(self.grantor)
        identifier(self.grantee)
        if self.grantor == self.grantee:
            raise ContractError("delegation requires two distinct tenants")
        if not self.task_types or any(not isinstance(t, str) or not t for t in self.task_types):
            raise ContractError("delegation task_types must be non-empty")
        if not self.resources or any(not isinstance(r, str) or not r for r in self.resources):
            raise ContractError("delegation resources must be non-empty")
        if type(self.expires_at) is not int or self.expires_at < 0:
            raise ContractError("delegation expires_at must be a nonnegative integer")

    def permits(self, task_type: str, resource: str, now: int) -> bool:
        """True if the grant covers this execution at time `now` (ENT3-R4)."""
        if type(now) is not int:
            raise ContractError("now must be an integer timestamp")
        return (now <= self.expires_at
                and task_type in self.task_types
                and resource in self.resources)


@dataclass(frozen=True)
class DelegationReceipt:
    """A dual-visibility delegation execution receipt. Implements ENT3-R4."""
    grant_id: str
    task_type: str
    resource: str
    executed_at: int
    approval_id: str
    result_digest: str

    @property
    def receipt_hash(self) -> str:
        """Deterministic digest of the delegation receipt (ENT3-R4)."""
        return digest({
            "grant_id": self.grant_id,
            "task_type": self.task_type,
            "resource": self.resource,
            "executed_at": self.executed_at,
            "approval_id": self.approval_id,
            "result_digest": self.result_digest,
        })

    def to_dict(self) -> dict:
        """Serialize the receipt for both tenants' chains (ENT3-R4)."""
        return {"receipt_hash": self.receipt_hash,
                "grant_id": self.grant_id,
                "task_type": self.task_type,
                "resource": self.resource,
                "executed_at": self.executed_at,
                "approval_id": self.approval_id,
                "result_digest": self.result_digest}


@dataclass
class DelegationEngine:
    """Executes delegated tasks under grant constraints. Implements ENT3-R4.

    Every execution requires a fresh HITL approval recorded in the
    granting tenant's HITL queue; the resulting receipt is appended to
    both the grantor's and the grantee's receipt chains.
    """
    tenants: dict[str, Tenant]
    grants: dict[str, DelegationGrant] = field(default_factory=dict)

    def add_grant(self, grant: DelegationGrant) -> None:
        """Register a delegation grant (ENT3-R4)."""
        if not isinstance(grant, DelegationGrant):
            raise ContractError("expected a DelegationGrant")
        if grant.id in self.grants:
            raise ContractError("duplicate delegation grant id")
        for tenant in (grant.grantor, grant.grantee):
            if tenant not in self.tenants:
                raise ContractError("delegation tenant is unknown")
        self.grants[grant.id] = grant

    def request_approval(self, grant_id: str, task_type: str,
                         resource: str, now: int) -> str:
        """Enqueue a HITL approval request on the grantor (ENT3-R4)."""
        grant = self._scoped_grant(grant_id, task_type, resource, now)
        approval_id = digest({"grant": grant.id, "task": task_type,
                              "resource": resource, "at": now,
                              "pending": len(self.tenants[grant.grantor].state.hitl_queue)})
        self.tenants[grant.grantor].state.enqueue_hitl({
            "kind": "delegation-approval",
            "approval_id": approval_id,
            "grant_id": grant.id,
            "grantee": grant.grantee,
            "task_type": task_type,
            "resource": resource,
            "approved": False,
        })
        return approval_id

    def _scoped_grant(self, grant_id: str, task_type: str,
                      resource: str, now: int) -> DelegationGrant:
        try:
            grant = self.grants[grant_id]
        except KeyError:
            raise ContractError("unknown delegation grant") from None
        if now > grant.expires_at:
            raise ContractError("delegation grant has expired (ENT3-R4)")
        if task_type not in grant.task_types or resource not in grant.resources:
            raise ContractError("delegation scope violation (ENT3-R4)")
        return grant

    def _approved(self, grant: DelegationGrant, approval_id: str,
                  task_type: str, resource: str) -> dict:
        queue = self.tenants[grant.grantor].state.hitl_queue
        for request in queue:
            if (request.get("approval_id") == approval_id
                    and request.get("grant_id") == grant.id
                    and request.get("task_type") == task_type
                    and request.get("resource") == resource):
                if not request.get("approved"):
                    raise ContractError(
                        "grantor HITL approval is still pending (ENT3-R4)")
                return request
        raise ContractError("no HITL approval recorded for this execution (ENT3-R4)")

    def execute(self, grant_id: str, task_type: str, resource: str,
                now: int, approval_id: str, result: dict) -> DelegationReceipt:
        """Execute a delegated task with verified approval. Implements ENT3-R4.

        The receipt is appended to both tenants' receipt chains so it is
        visible to the grantor and the grantee.
        """
        grant = self._scoped_grant(grant_id, task_type, resource, now)
        approval = self._approved(grant, approval_id, task_type, resource)
        if not isinstance(result, dict):
            raise ContractError("delegation result must be a mapping")
        receipt = DelegationReceipt(
            grant_id=grant.id, task_type=task_type, resource=resource,
            executed_at=now, approval_id=approval["approval_id"],
            result_digest=digest(result))
        for tenant_id in (grant.grantor, grant.grantee):
            self.tenants[tenant_id].state.append_receipt(receipt.to_dict())
        return receipt
