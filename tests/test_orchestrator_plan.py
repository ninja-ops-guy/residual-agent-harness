import os

import pytest

from residual.core import ContractError
from residual.goalspec import AmendmentRule, GoalSpec, SuccessCriterion
from residual.hitl.gateway import HITLEscalationGateway
from residual.orchestrator import (
    ApprovalGate,
    DECISION_APPROVED,
    DECISION_DENIED,
    HITLApprovalGate,
    InMemoryApprovalGate,
    Intent,
    Orchestrator,
    Plan,
    PlanApproval,
)


def make_plan(**intent_kw):
    intent_kw.setdefault("goal", "orchestrate build")
    return Orchestrator().plan(Intent(**intent_kw))


def test_pipeline_produces_plan():
    plan = make_plan(constraints=("c",), context_refs=("r",))
    assert isinstance(plan, Plan)
    assert plan.packets
    assert len(plan.risk_reports) == len(plan.packets)
    assert plan.ambiguity.has_ambiguity  # default decomposition is unowned


def test_pipeline_rejects_non_intent():
    with pytest.raises(ContractError):
        Orchestrator().plan("nope")


def test_plan_hash_deterministic_for_identical_intent():
    p1 = make_plan(constraints=("b", "a"), context_refs=("r2", "r1"))
    p2 = make_plan(constraints=("a", "b"), context_refs=("r1", "r2"))
    assert p1.plan_hash == p2.plan_hash
    assert len(p1.plan_hash) == 64
    int(p1.plan_hash, 16)


def test_plan_hash_changes_with_intent():
    assert make_plan(goal="one").plan_hash != make_plan(goal="two").plan_hash


def test_plan_hash_stable_across_processes():
    # canonical JSON -> sha256 must match an independently computed value
    import hashlib
    from residual.core import canonical
    plan = make_plan()
    expected = hashlib.sha256(canonical(plan.to_dict()).encode("utf-8")).hexdigest()
    assert plan.plan_hash == expected


def test_plan_approval_validation():
    h = make_plan().plan_hash
    approval = PlanApproval(approver="ops", timestamp_ns=1, plan_hash=h)
    assert approval.decision == DECISION_APPROVED
    with pytest.raises(ContractError):
        PlanApproval(approver=" ", timestamp_ns=1, plan_hash=h)
    with pytest.raises(ContractError):
        PlanApproval(approver="ops", timestamp_ns=-1, plan_hash=h)
    with pytest.raises(ContractError):
        PlanApproval(approver="ops", timestamp_ns=1, plan_hash="not-a-hash")
    with pytest.raises(ContractError):
        PlanApproval(approver="ops", timestamp_ns=1, plan_hash=h, decision="maybe")


def test_in_memory_gate_roundtrip():
    gate = InMemoryApprovalGate()
    assert isinstance(gate, ApprovalGate)
    plan = make_plan()
    assert not gate.is_approved(plan.plan_hash)
    gate.record(PlanApproval(approver="ops", timestamp_ns=5, plan_hash=plan.plan_hash))
    assert gate.is_approved(plan.plan_hash)


def test_in_memory_gate_denial_not_approved():
    gate = InMemoryApprovalGate()
    plan = make_plan()
    gate.record(PlanApproval(approver="ops", timestamp_ns=5, plan_hash=plan.plan_hash,
                             decision=DECISION_DENIED, reason="too risky"))
    assert not gate.is_approved(plan.plan_hash)


def _goal_spec():
    return GoalSpec(
        goal_id="orch-goal",
        objective="approve orchestration plans",
        success_criteria=(SuccessCriterion(
            name="signed", check_type="mechanical",
            description="challenge signed", evaluator="none"),),
        max_passes=1,
        token_budget=1000,
        wall_clock_budget_s=60.0,
        amendment_rule=AmendmentRule(authorized_roles=("ops",)),
    )


def test_hitl_gate_approval_flow(tmp_path):
    gateway = HITLEscalationGateway(
        signing_key=os.urandom(32), challenge_dir=str(tmp_path),
        authenticate=lambda record, response, role: response == "yes" and role == "ops")
    hitl = HITLApprovalGate(gateway, _goal_spec(), ("ops",))
    plan = make_plan()
    challenge = hitl.request_approval(plan)
    approval = hitl.confirm(plan.plan_hash, challenge.challenge_id, "yes", "ops")
    assert approval.decision == DECISION_APPROVED
    assert approval.plan_hash == plan.plan_hash
    assert approval.approver == "ops"


def test_hitl_gate_denies_wrong_plan_hash(tmp_path):
    gateway = HITLEscalationGateway(
        signing_key=os.urandom(32), challenge_dir=str(tmp_path),
        authenticate=lambda record, response, role: True)
    hitl = HITLApprovalGate(gateway, _goal_spec(), ("ops",))
    plan = make_plan()
    challenge = hitl.request_approval(plan)
    other = make_plan(goal="different").plan_hash
    with pytest.raises(ContractError, match="not bound"):
        hitl.confirm(other, challenge.challenge_id, "yes", "ops")


def test_hitl_gate_replay_denied(tmp_path):
    gateway = HITLEscalationGateway(
        signing_key=os.urandom(32), challenge_dir=str(tmp_path),
        authenticate=lambda record, response, role: True)
    hitl = HITLApprovalGate(gateway, _goal_spec(), ("ops",))
    plan = make_plan()
    challenge = hitl.request_approval(plan)
    first = hitl.confirm(plan.plan_hash, challenge.challenge_id, "yes", "ops")
    assert first.decision == DECISION_APPROVED
    second = hitl.confirm(plan.plan_hash, challenge.challenge_id, "yes", "ops")
    assert second.decision == DECISION_DENIED


def test_hitl_gate_fails_closed_without_authenticator(tmp_path):
    gateway = HITLEscalationGateway(signing_key=os.urandom(32), challenge_dir=str(tmp_path))
    hitl = HITLApprovalGate(gateway, _goal_spec(), ("ops",))
    plan = make_plan()
    challenge = hitl.request_approval(plan)
    approval = hitl.confirm(plan.plan_hash, challenge.challenge_id, "yes", "ops")
    assert approval.decision == DECISION_DENIED
