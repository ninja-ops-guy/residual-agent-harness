"""Exact-head HITL approvals for consequential Copilot Studio actions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...core import ContractError, canonical, digest, identifier
from ...goalspec import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
from ...hitl.gateway import HITLEscalationGateway, HITLStatus


@dataclass(frozen=True)
class ExternalWriteIntent:
    mission_id: str
    binding_hash: str
    plan_hash: str
    evidence_hash: str
    action: str
    target: str

    def __post_init__(self):
        for name in ("mission_id","binding_hash","plan_hash","evidence_hash","action","target"):
            value=getattr(self,name)
            if not isinstance(value,str) or not value.strip():
                raise ContractError(f"{name} is required")
        identifier(self.action)

    @property
    def content_hash(self) -> str:
        return digest({
            "mission_id":self.mission_id,
            "binding_hash":self.binding_hash,
            "plan_hash":self.plan_hash,
            "evidence_hash":self.evidence_hash,
            "action":self.action,
            "target":self.target,
        })


@dataclass(frozen=True)
class ExternalWriteApproval:
    challenge_id: str
    approver_role: str
    intent_hash: str
    decision: str

    @property
    def approved(self) -> bool:
        return self.decision=="approved"


class CopilotExternalWriteGate:
    """Issue/consume human approvals bound to the exact mission evidence head."""

    def __init__(self,gateway:HITLEscalationGateway,authorized_roles:tuple[str,...]):
        if not isinstance(gateway,HITLEscalationGateway):
            raise ContractError("gateway must be HITLEscalationGateway")
        if not isinstance(authorized_roles,tuple) or not authorized_roles:
            raise ContractError("authorized_roles must be non-empty")
        for role in authorized_roles: identifier(role)
        self.gateway=gateway
        self.authorized_roles=authorized_roles

    def _goal(self,intent:ExternalWriteIntent)->GoalSpec:
        return GoalSpec(
            goal_id="copilot_external_write",
            objective=f"Authorize exact consequential action {intent.action}",
            success_criteria=(SuccessCriterion(
                "exact_head","mechanical",
                "Approval is bound to the exact mission, plan, evidence and target.",
                "host_exact_head",
                {"intent_hash":intent.content_hash},
            ),),
            max_passes=1,
            token_budget=1,
            wall_clock_budget_s=3600,
            amendment_rule=AmendmentRule(self.authorized_roles,1),
        )

    def request(self,intent:ExternalWriteIntent):
        if not isinstance(intent,ExternalWriteIntent):
            raise ContractError("ExternalWriteIntent required")
        return self.gateway.generate_challenge(
            "copilot.external_write",
            {
                "action":"copilot-external-write",
                "intent_hash":intent.content_hash,
                "mission_id":intent.mission_id,
                "binding_hash":intent.binding_hash,
                "plan_hash":intent.plan_hash,
                "evidence_hash":intent.evidence_hash,
                "write_action":intent.action,
                "target":intent.target,
            },
            "Consequential external write requires exact-head human approval.",
            self._goal(intent),
        )

    def confirm(self,intent:ExternalWriteIntent,challenge_id:str,operator_response:str,operator_role:str)->ExternalWriteApproval:
        record=self.gateway.get_challenge(challenge_id)
        if record is None: raise ContractError("unknown or tampered approval challenge")
        try: action=record["payload"]["action"]
        except (KeyError,TypeError): raise ContractError("malformed approval challenge") from None
        expected={
            "action":"copilot-external-write",
            "intent_hash":intent.content_hash,
            "mission_id":intent.mission_id,
            "binding_hash":intent.binding_hash,
            "plan_hash":intent.plan_hash,
            "evidence_hash":intent.evidence_hash,
            "write_action":intent.action,
            "target":intent.target,
        }
        if canonical(action)!=canonical(expected):
            raise ContractError("approval challenge is stale or bound to different evidence")
        status=self.gateway.verify_approval(challenge_id,operator_response,operator_role,self.authorized_roles)
        decision="approved" if status is HITLStatus.APPROVED else status.value
        return ExternalWriteApproval(challenge_id,operator_role,intent.content_hash,decision)
