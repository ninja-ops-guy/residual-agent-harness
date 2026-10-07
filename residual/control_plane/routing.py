"""Execution-start binding for routing decisions."""
from __future__ import annotations
import time
from dataclasses import dataclass
from .models import CertifiedState, CertifiedStatus, MissionRevision, RoutingDecision

@dataclass(frozen=True)
class RoutingPreconditionResult:
    allowed: bool; reason: str="ok"

def validate_execution_start(decision: RoutingDecision, revision: MissionRevision, certified_states: dict[str,CertifiedState], *, current_policy_revision: str, now=None, environment_fingerprints: dict[str,str]|None=None):
    now=time.time() if now is None else now; environment_fingerprints=environment_fingerprints or {}
    if decision.mission_revision != revision.revision_id: return RoutingPreconditionResult(False,"mission revision changed")
    if decision.expires_at is not None and now > decision.expires_at: return RoutingPreconditionResult(False,"routing decision expired")
    if decision.policy_revision != current_policy_revision: return RoutingPreconditionResult(False,"policy revision changed")
    for ref in decision.certified_state_refs:
        state=certified_states.get(ref)
        if state is None: return RoutingPreconditionResult(False,f"missing certified state: {ref}")
        if state.status(now=now,environment_fingerprint=environment_fingerprints.get(ref)) is not CertifiedStatus.CERTIFIED:
            return RoutingPreconditionResult(False,f"certified state not valid: {ref}")
    if decision.required_capability_hash != decision.granted_capability_hash: return RoutingPreconditionResult(False,"capability grant changed")
    return RoutingPreconditionResult(True)
