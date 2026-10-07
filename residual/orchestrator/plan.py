"""Orchestration plan, deterministic plan hash, and HITL plan approval.

ORCH-I-R16: The plan hash MUST be SHA-256 over the canonical JSON of the
            plan content (intent, requirements, packets, risk); identical
            intents MUST yield identical hashes. The hash input MUST NOT
            contain clocks, random values, or object identities.
ORCH-I-R17: Plan approval MUST be gated by an ApprovalGate; a plan MUST
            NOT be treated as executable before `is_approved(plan_hash)`
            returns True.
ORCH-I-R18: An approval record MUST bind approver, timestamp, and the
            exact plan hash.

`ApprovalGate` is the local protocol. `InMemoryApprovalGate` is a stub for
tests/development; `HITLApprovalGate` adapts the existing
residual.hitl.gateway.HITLEscalationGateway, which fails closed without a
host authenticator.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..core import ContractError, digest
from ..hitl.gateway import HITLEscalationGateway, HITLStatus
from ..goalspec import GoalSpec
from .ambiguity import AmbiguityReport
from .intent import Intent
from .partition import WorkPacket
from .risk import RiskReport

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
DECISION_APPROVED = "approved"
DECISION_DENIED = "denied"
_DECISIONS = (DECISION_APPROVED, DECISION_DENIED)


@dataclass(frozen=True)
class Plan:
    """Executable-ready orchestration plan (pre-approval)."""

    intent: Intent
    requirements: tuple[Any, ...]
    packets: tuple[WorkPacket, ...]
    risk_reports: tuple[RiskReport, ...]
    ambiguity: AmbiguityReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.orchestrator.plan.v1",
            "intent": self.intent.to_dict(),
            "requirements": [r.to_dict() for r in self.requirements],
            "packets": [p.to_dict() for p in self.packets],
            "risk_reports": [r.to_dict() for r in self.risk_reports],
            "ambiguity": self.ambiguity.to_dict(),
        }

    @property
    def plan_hash(self) -> str:
        """Deterministic content hash of the full plan."""
        return digest(self.to_dict())


@dataclass(frozen=True)
class PlanApproval:
    """HITL-gated approval record bound to an exact plan hash."""

    approver: str
    timestamp_ns: int
    plan_hash: str
    decision: str = DECISION_APPROVED
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.approver, str) or not self.approver.strip():
            raise ContractError("approver must be a non-empty string")
        if type(self.timestamp_ns) is not int or self.timestamp_ns < 0:
            raise ContractError("timestamp_ns must be a nonnegative integer")
        if not isinstance(self.plan_hash, str) or not _HASH_RE.fullmatch(self.plan_hash):
            raise ContractError("plan_hash must be a lowercase sha256 hex digest")
        if self.decision not in _DECISIONS:
            raise ContractError(f"decision must be one of {_DECISIONS}")
        if not isinstance(self.reason, str):
            raise ContractError("reason must be a string")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.orchestrator.approval.v1",
            "approver": self.approver,
            "timestamp_ns": self.timestamp_ns,
            "plan_hash": self.plan_hash,
            "decision": self.decision,
            "reason": self.reason,
        }


@runtime_checkable
class ApprovalGate(Protocol):
    """Local protocol for plan-approval backends."""

    def record(self, approval: PlanApproval) -> None: ...

    def is_approved(self, plan_hash: str) -> bool: ...


class InMemoryApprovalGate:
    """Stub approval backend for tests and local development."""

    def __init__(self):
        self._records: dict[str, PlanApproval] = {}

    def record(self, approval: PlanApproval) -> None:
        if not isinstance(approval, PlanApproval):
            raise ContractError("record requires a PlanApproval")
        self._records[approval.plan_hash] = approval

    def is_approved(self, plan_hash: str) -> bool:
        record = self._records.get(plan_hash)
        return record is not None and record.decision == DECISION_APPROVED

    def approvals(self) -> tuple[PlanApproval, ...]:
        return tuple(self._records[k] for k in sorted(self._records))


class HITLApprovalGate:
    """Adapter over residual.hitl.gateway.HITLEscalationGateway.

    Each approval request issues a signed challenge whose proposed action
    carries the plan hash; the challenge is consumed exactly once by the
    host-authenticated operator. Denials, expiries, and replays all fail
    closed (plan stays unapproved).
    """

    def __init__(self, gateway: HITLEscalationGateway, goal_spec: GoalSpec,
                 authorized_roles: tuple[str, ...], *, task_id: str = "orchestrator.plan"):
        if not isinstance(gateway, HITLEscalationGateway):
            raise ContractError("gateway must be a HITLEscalationGateway")
        if not isinstance(goal_spec, GoalSpec):
            raise ContractError("goal_spec must be a GoalSpec")
        if not isinstance(authorized_roles, (tuple, list)) or not authorized_roles:
            raise ContractError("authorized_roles must be a non-empty sequence")
        self._gateway = gateway
        self._goal_spec = goal_spec
        self._roles = tuple(authorized_roles)
        self._task_id = task_id

    def request_approval(self, plan: Plan, reason: str = "plan approval required"):
        """Issue a durable challenge for this plan. Returns the challenge."""
        if not isinstance(plan, Plan):
            raise ContractError("request_approval requires a Plan")
        return self._gateway.generate_challenge(
            self._task_id,
            {"action": "approve-plan", "plan_hash": plan.plan_hash},
            reason,
            self._goal_spec,
        )

    def confirm(self, plan_hash: str, challenge_id: str, operator_response: str,
                operator_role: str) -> PlanApproval:
        """Consume a challenge; returns a PlanApproval binding the plan hash."""
        if not isinstance(plan_hash, str) or not _HASH_RE.fullmatch(plan_hash):
            raise ContractError("plan_hash must be a lowercase sha256 hex digest")
        record = self._gateway.get_challenge(challenge_id)
        if record is None:
            raise ContractError("unknown or tampered challenge")
        try:
            action = record["payload"]["action"]
        except (KeyError, TypeError):
            raise ContractError("challenge payload is malformed") from None
        if action.get("action") != "approve-plan" or action.get("plan_hash") != plan_hash:
            raise ContractError("challenge is not bound to this plan hash")
        status = self._gateway.verify_approval(
            challenge_id, operator_response, operator_role, self._roles)
        return PlanApproval(
            approver=operator_role,
            timestamp_ns=time.time_ns(),
            plan_hash=plan_hash,
            decision=(DECISION_APPROVED if status is HITLStatus.APPROVED
                      else DECISION_DENIED),
            reason=f"hitl challenge {challenge_id} -> {status.value}",
        )

    def is_approved(self, plan_hash: str) -> bool:
        raise ContractError(
            "HITLApprovalGate is stateless across challenges; carry the "
            "PlanApproval returned by confirm() as the approval token")
