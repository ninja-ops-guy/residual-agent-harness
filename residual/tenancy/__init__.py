"""Multi-tenant architecture for Residual (SPEC-ENT-003).

Implements ENT3-R1 through ENT3-R6: per-tenant isolated state, data-layer
isolation, fair scheduling, cross-tenant delegation, tenant policy layers,
and platform-privileged tenant lifecycle.
"""
from __future__ import annotations

from .tenant import Tenant, TenantState
from .isolation import Principal, FederationAgreement, TenantStore
from .scheduler import FairScheduler, Job
from .delegation import DelegationGrant, DelegationEngine, DelegationReceipt
from .policies import PlatformFloors, TenantPolicy, validate_policy
from .lifecycle import PlatformOperator, TenantLifecycle, DeletionRecord

__all__ = [
    "Tenant", "TenantState",
    "Principal", "FederationAgreement", "TenantStore",
    "FairScheduler", "Job",
    "DelegationGrant", "DelegationEngine", "DelegationReceipt",
    "PlatformFloors", "TenantPolicy", "validate_policy",
    "PlatformOperator", "TenantLifecycle", "DeletionRecord",
]
