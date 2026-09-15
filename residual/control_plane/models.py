"""Versioned mission, authority, evidence and governance models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional
import time, uuid
from ..core import digest

class Verification(str, Enum): PASS="pass"; FAIL="fail"; UNKNOWN="unknown"
class IntentState(str, Enum): PREPARED="prepared"; ATTEMPTED="attempted"; APPLIED="applied"; FAILED="failed"; AMBIGUOUS="ambiguous"; RECONCILING="reconciling"
class TransactionState(str, Enum): PREPARED="prepared"; IN_PROGRESS="in_progress"; COMPLETE="complete"; INCOMPLETE="incomplete"; FAILED="failed"; RECONCILIATION_REQUIRED="reconciliation_required"
class CertifiedStatus(str, Enum): CERTIFIED="certified"; STALE="stale"; INVALIDATED="invalidated"
class AmendmentClass(int, Enum): CLARIFICATION=0; RESTRUCTURE=1; RESOURCE=2; AUTHORITY=3; TRUST_BOUNDARY=4

@dataclass(frozen=True)
class Mission:
    mission_id: str
    principal_id: str
    tenant_id: str = "default"
    created_at: float = field(default_factory=time.time)

@dataclass(frozen=True)
class CapabilityGrant:
    subject: str; action: str; resource: str
    scope: Mapping[str, Any] = field(default_factory=dict)
    constraints: Mapping[str, Any] = field(default_factory=dict)
    conditions: Mapping[str, Any] = field(default_factory=dict)
    approval_policy: Mapping[str, Any] = field(default_factory=dict)
    expires_at: Optional[float] = None
    def fingerprint(self): return digest(self.__dict__)

@dataclass(frozen=True)
class MissionRevision:
    mission_id: str; revision_id: str; objective: str; plan_hash: str; policy_hash: str
    capability_grants: tuple[CapabilityGrant, ...] = ()
    parent_revision: Optional[str] = None; amendment_id: Optional[str] = None
    workspaces: tuple[str, ...] = (); budget: Mapping[str, Any] = field(default_factory=dict)
    def authority_hash(self): return digest([g.fingerprint() for g in self.capability_grants])

@dataclass(frozen=True)
class PlanAmendment:
    amendment_id: str; mission_id: str; from_revision: str; amendment_class: AmendmentClass
    reason: str; proposed_delta: Mapping[str, Any]; counterexample_refs: tuple[str, ...] = ()
    proposer_id: str = "unknown"; beneficiary_ids: tuple[str, ...] = ()

@dataclass(frozen=True)
class RoutingDecision:
    decision_id: str; mission_revision: str; obligation_id: str
    eligible_workers: tuple[str, ...]; selected_worker: str
    scoring_inputs: Mapping[str, Any]; certified_state_refs: tuple[str, ...]
    router_revision: str; policy_revision: str
    required_capability_hash: str; granted_capability_hash: str
    excluded_workers: Mapping[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class CertifiedState:
    key: str; value: Any; evidence_refs: tuple[str, ...]; derivation: str; verifier_revision: str
    measurement_start: float; measurement_end: float; sample_size: int; certified_at: float
    valid_until: float; staleness_budget: float; environment_fingerprint: str
    drift_detector: Optional[str] = None; drift_status: str = "stable"
    def status(self, *, now=None, environment_fingerprint=None):
        now=time.time() if now is None else now
        if environment_fingerprint is not None and environment_fingerprint != self.environment_fingerprint: return CertifiedStatus.INVALIDATED
        if self.drift_status != "stable": return CertifiedStatus.INVALIDATED
        if now > self.valid_until or now-self.certified_at > self.staleness_budget: return CertifiedStatus.STALE
        return CertifiedStatus.CERTIFIED

@dataclass(frozen=True)
class ApprovalDecision:
    principal_id: str; role: str; mission_id: str; revision_id: str; intent_id: str
    decision: str; challenge_nonce: str; policy_revision: str; timestamp: float=field(default_factory=time.time)

@dataclass(frozen=True)
class AtomicEffect:
    effect_id: str; intent_id: str; depends_on: tuple[str, ...]=(); state: IntentState=IntentState.PREPARED
    reversibility: str="unknown"; result_ref: Optional[str]=None
