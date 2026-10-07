"""Fail-closed governance for authority, routing and amendments."""
from __future__ import annotations
from dataclasses import dataclass
from .models import AmendmentClass, CapabilityGrant, MissionRevision, PlanAmendment, RoutingDecision

@dataclass(frozen=True)
class AuthorityPolicy:
    """Routing may allocate authority already present in the revision; never enlarge it."""
    def allows(self, required: tuple[CapabilityGrant,...], revision: MissionRevision) -> bool:
        allowed={g.fingerprint() for g in revision.capability_grants}
        return all(g.fingerprint() in allowed for g in required)

@dataclass(frozen=True)
class RoutingPolicy:
    authority: AuthorityPolicy=AuthorityPolicy()
    def validate(self, decision: RoutingDecision, required: tuple[CapabilityGrant,...], revision: MissionRevision) -> bool:
        if decision.selected_worker not in decision.eligible_workers: return False
        if not self.authority.allows(required, revision): return False
        return decision.required_capability_hash == decision.granted_capability_hash

@dataclass(frozen=True)
class AmendmentPolicy:
    """No beneficiary can be sole authority for an authority-expanding amendment."""
    def validate_independence(self, amendment: PlanAmendment, verifier_ids: tuple[str,...], *, human_approvers: tuple[str,...]=()) -> bool:
        if not verifier_ids: return False
        if amendment.amendment_class >= AmendmentClass.AUTHORITY:
            if set(verifier_ids).issubset(set(amendment.beneficiary_ids) | {amendment.proposer_id}): return False
            if not human_approvers: return False
        if amendment.amendment_class >= AmendmentClass.TRUST_BOUNDARY and len(set(verifier_ids)) < 2: return False
        return True
