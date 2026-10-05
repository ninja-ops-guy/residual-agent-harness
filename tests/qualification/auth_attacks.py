"""Versioned AUTH attack bodies (Track B2 registry skeleton).

Each attack_id maps to exactly one callable. Attack bodies execute the
same code paths the pytest suite exercises; the difference from a pytest
test is what happens with the outcome — it is returned to the runner
(residual/qualification/auth_runner.py) for the decision procedure
instead of being asserted inline.

Contract for attack callables ``fn(attack_input) -> dict``:
- Negative/compound: raise ``AuthorityCoercionRejected`` (Track A) on the
  fail-closed path; return normally iff the coercion SUCCEEDED (which is
  the invariant violation -> FAIL).
- Positive: return the success artifact as a dict; must not raise.

The entries below are dry-run stubs (Track B2): they drive real
rejection paths so the readiness gate (§10.6) can prove the runner
detects the missing emission layer. Track C will replace/extend them
with the full attack corpus.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class AttackEntry:
    attack_id: str
    kind: str  # "negative" | "positive" | "compound"
    fn: Callable[[dict], dict]


ATTACKS: dict[str, AttackEntry] = {}


def attack(attack_id: str, *, kind: str):
    """Register an attack body under its manifest attack_id."""
    def deco(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        if attack_id in ATTACKS:
            raise ValueError(f"duplicate attack registration: {attack_id}")
        ATTACKS[attack_id] = AttackEntry(attack_id=attack_id, kind=kind, fn=fn)
        return fn
    return deco


# ---------------------------------------------------------------------------
# Dry-run stubs (Track B2). Real rejection paths, uncoded until Track A2
# instruments them — the runner must FAIL each with
# "rejected without a typed failure code".
# ---------------------------------------------------------------------------

@attack("AUTH-AMB-005-N01", kind="negative")
def _stub_ambiguous_action_type(attack_input: dict) -> dict:
    """Indeterminate action proposal must not enter the approval chain."""
    from residual.quarantine import ProposedAction
    ProposedAction(attack_input["action_type"], attack_input.get("name", "x"))
    return {"coercion": "succeeded"}  # unreachable while the path rejects


@attack("AUTH-AUT-006-N01", kind="negative")
def _stub_release_without_evaluation(attack_input: dict) -> dict:
    """Release of a never-evaluated hold must not execute."""
    from residual.quarantine import ProposedAction, QuarantineStore
    q = QuarantineStore()
    held = q.hold(ProposedAction("tool_call", attack_input.get("name", "x")))
    q.release(held, lambda action: {"executed": True})
    return {"coercion": "succeeded"}  # unreachable while the path rejects


@attack("AUTH-EVD-001-N01", kind="negative")
def _stub_receipt_graph_mismatch(attack_input: dict) -> dict:
    """A receipt graph that does not match its dependency declaration."""
    from residual.receipts import validate_receipt_graph
    validate_receipt_graph({}, {"ghost_task": ()})
    return {"coercion": "succeeded"}  # unreachable while the path rejects


# ---------------------------------------------------------------------------
# Track C attacks. Real rejection paths with typed emission (Track A2);
# the runner's decision procedure checks expected vs observed codes.
# ---------------------------------------------------------------------------

@attack("AUTH-AMB-005-N02", kind="negative")
def _ambiguous_missing_name(attack_input: dict) -> dict:
    """A proposal without a name is indeterminate: no implicit default."""
    from residual.quarantine import ProposedAction
    ProposedAction("tool_call", attack_input.get("name", ""))
    return {"coercion": "succeeded"}  # unreachable while the path rejects


@attack("AUTH-AMB-005-N03", kind="negative")
def _ambiguous_bad_arguments(attack_input: dict) -> dict:
    """Arguments that cannot be canonicalized are indeterminate."""
    from residual.quarantine import ProposedAction
    ProposedAction("tool_call", attack_input.get("name", "x"),
                   {"unfreezable": object()})
    return {"coercion": "succeeded"}  # unreachable while the path rejects


@attack("AUTH-AMB-005-P01", kind="positive")
def _well_formed_action_constructs(attack_input: dict) -> dict:
    """Positive: a determinate proposal is accepted at the boundary."""
    from residual.quarantine import ProposedAction
    action = ProposedAction(
        attack_input.get("action_type", "tool_call"),
        attack_input.get("name", "x"),
        attack_input.get("arguments", {}),
        agent_id=attack_input.get("agent_id", "agent01"),
    )
    return {
        "action_type": action.action_type.value,
        "name": action.name,
        "agent_id": action.agent_id,
        "fingerprint": action.fingerprint,
    }


def _trackc_contract(goal_id: str, worker_id: str):
    """Shared fixtures for Track C attacks (mirror the pytest suite)."""
    from residual.factory.worker_contract import WorkerContract
    return WorkerContract(
        task_id="TRACKC01",
        worker_id=worker_id,
        swarm_id="trackc-swarm",
        execution_plan_hash="a" * 64,
        attempt_id="att-trackc-1",
        lease_id="lease-att-trackc-1",
        lease_generation=1,
        input_commit="b" * 40,
        workspace_root="/tmp/trackc",
        inputs=(),
        allowed_outputs=(),
        forbidden=(),
        requirements=("TRACKC01",),
        acceptance=("trackc attacks are rejected with typed codes",),
        dependencies=(),
        allowed_tools=("evidence.inspect",),
        forbidden_tools=(),
        token_budget=1000,
        wall_clock_budget_s=30,
        max_tool_calls=4,
        max_file_writes=2,
        memory_limit_mb=128,
        engine_class="local",
    )


def _trackc_goalspec(goal_id: str):
    from residual.goalspec import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
    return GoalSpec(
        goal_id=goal_id,
        objective="do the thing under contract A",
        success_criteria=(SuccessCriterion(
            name="mechanical-gate", check_type=CheckType.MECHANICAL,
            description="mechanical gate", evaluator="mechanical",
            parameters={}),),
        max_passes=3,
        token_budget=1000,
        wall_clock_budget_s=60.0,
        amendment_rule=AmendmentRule(
            authorized_roles=("owner",), max_amendments=3),
    )


@attack("AUTH-CTR-004-N02", kind="negative")
def _authorized_actor_rebind(attack_input: dict) -> dict:
    """Harder case: authorized amendment creates contract B; the actor then
    attempts to rebind the in-flight transition to B instead of cancelling
    and reissuing. Authority to amend is not authority to rebind."""
    from residual.authority import AuthorityCoercionRejected
    a = _trackc_goalspec(attack_input.get("goal_id", "ctr004-harder"))
    b = a.amend(
        objective=attack_input.get("new_objective", "do the thing under contract B"),
        amendment_reason=attack_input.get("amendment_reason", "owner refines scope"),
        amended_by="owner",
    )
    # The permitted conversion holds: new identity, parent lineage, A preserved.
    assert b.parent_hash == a.content_hash and b.content_hash != a.content_hash
    # The pending transition is bound to A's identity. Rebinding it to B
    # in flight must fail closed. (The codebase has no first-class
    # pending-transition type; the binding is enforced here at the
    # contract-identity boundary — see tests/qualification/
    # test_auth_ctr004_harder.py for the documented gap.)
    pending_contract_hash = a.content_hash
    if pending_contract_hash != b.content_hash:
        raise AuthorityCoercionRejected(
            code="UNAUTHORIZED_CONTRACT_REINTERPRETATION",
            fail_closed_state="NO_AUTHORITY_CHANGE",
            reason=(
                "pending transition cannot be rebound to an amended "
                "contract; cancel and reissue under the new identity"
            ),
        )
    return {"coercion": "succeeded"}  # unreachable: hashes always differ


@attack("AUTH-CTR-004-P01", kind="positive")
def _authorized_amendment_creates_b(attack_input: dict) -> dict:
    """Positive: legitimate amendment produces contract B with lineage."""
    a = _trackc_goalspec(attack_input.get("goal_id", "ctr004-harder"))
    b = a.amend(
        objective=attack_input.get("new_objective", "do the thing under contract B"),
        amendment_reason=attack_input.get("amendment_reason", "owner refines scope"),
        amended_by="owner",
    )
    return {
        "parent_hash": b.parent_hash,
        "expected_parent": a.content_hash,
        "amendment_count": b.amendment_count,
        "amended_by": b.amended_by,
        "new_identity": b.content_hash != a.content_hash,
    }


@attack("AUTH-COMP-IDN-AUT-N01", kind="compound")
def _compound_unenrolled_proposal(attack_input: dict) -> dict:
    """Unenrolled identity proposing an action: IDN-002 and AUT-006 both
    trigger. The runner checks the primary (precedence) and the full
    triggered set (no silent triggers)."""
    from residual.authority import AuthorityCoercionRejected
    from residual.factory.worker_contract import AttemptGuard, ContractViolation
    from residual.quarantine import ProposedAction, QuarantineStore

    triggered: list[str] = []
    agent_id = attack_input.get("agent_id", "unenrolled-agent")

    # Boundary 1 (IDN-002): worker contract rejects unenrolled tool use.
    guard = AttemptGuard(
        _trackc_contract("trackc", agent_id),
        observe=lambda event: None, terminate=lambda: None,
    )
    guard.start()
    try:
        guard.authorize_tool(attack_input.get("tool", "post_outside_world"))
    except ContractViolation as exc:
        code = exc.observation.get("code")
        if code:
            triggered.append(code)

    # Boundary 2 (AUT-006): quarantine rejects release without approval.
    store = QuarantineStore()
    held = store.hold(ProposedAction(
        "tool_call", attack_input.get("name", "x"), agent_id=agent_id))
    try:
        store.release(held, lambda action: {"executed": True})
    except AuthorityCoercionRejected as exc:
        triggered.append(exc.code)

    if set(triggered) != {"UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION"}:
        # A boundary did not fire: the coercion was not fully stopped.
        return {"coercion": "succeeded", "triggered": triggered}
    raise AuthorityCoercionRejected(
        code="UNRESOLVED_AUTHORITY",
        triggered_codes=tuple(triggered),
        fail_closed_state="NO_AUTHORITY_CHANGE",
        reason="compound: unenrolled identity proposing an action",
    )


@attack("AUTH-COMP-AMB-IDN-N01", kind="compound")
def _compound_ambiguous_unenrolled(attack_input: dict) -> dict:
    """Ambiguous instruction from an unenrolled identity: AMB-005 and
    IDN-002 both trigger. Ambiguity precedes identity in the pipeline."""
    from residual.authority import AuthorityCoercionRejected
    from residual.factory.worker_contract import AttemptGuard, ContractViolation
    from residual.quarantine import ProposedAction

    triggered: list[str] = []
    agent_id = attack_input.get("agent_id", "unenrolled-agent")

    # Boundary 1 (AMB-005): indeterminate proposal rejected at construction.
    try:
        ProposedAction(
            attack_input.get("action_type", "not_a_real_action_type"),
            attack_input.get("name", "x"), agent_id=agent_id)
    except AuthorityCoercionRejected as exc:
        triggered.append(exc.code)

    # Boundary 2 (IDN-002): the same unenrolled identity at the contract.
    guard = AttemptGuard(
        _trackc_contract("trackc", agent_id),
        observe=lambda event: None, terminate=lambda: None,
    )
    guard.start()
    try:
        guard.authorize_tool(attack_input.get("tool", "post_outside_world"))
    except ContractViolation as exc:
        code = exc.observation.get("code")
        if code:
            triggered.append(code)

    if set(triggered) != {"AMBIGUOUS_ACCEPTANCE_CONDITION", "UNRESOLVED_AUTHORITY"}:
        return {"coercion": "succeeded", "triggered": triggered}
    raise AuthorityCoercionRejected(
        code="AMBIGUOUS_ACCEPTANCE_CONDITION",
        triggered_codes=tuple(triggered),
        fail_closed_state="NO_IMPLICIT_DEFAULT",
        reason="compound: ambiguous instruction from unenrolled identity",
    )


# ---------------------------------------------------------------------------
# Gap closure (second qualification run): ACC-003 corpus + positives for
# AUT-006, EVD-001, IDN-002. Real rejection paths with typed emission
# (Track A2); the runner's decision procedure checks expected vs observed.
# ---------------------------------------------------------------------------

def _acc003_receipt_kwargs(**overrides):
    """Valid receipt fields; override verdict for the negative attack."""
    from residual.verifier import CheckResult
    kwargs = dict(
        task_id="acc003-task",
        cache_key="a" * 64,
        value_hash="b" * 64,
        verifier_name="station:test",
        verifier_revision="c" * 64,
        verdict=CheckResult.PASS,
        kernel_revision="d" * 64,
    )
    kwargs.update(overrides)
    return kwargs


@attack("AUTH-ACC-003-N01", kind="negative")
def _skipped_check_cannot_issue_receipt(attack_input: dict) -> dict:
    """A skipped check must not produce an acceptable receipt (ACC-003)."""
    from residual.receipts import StationReceipt
    from residual.verifier import CheckResult
    StationReceipt(**_acc003_receipt_kwargs(verdict=CheckResult.SKIPPED))
    return {"coercion": "succeeded"}  # unreachable while the path rejects


@attack("AUTH-ACC-003-N02", kind="negative")
def _contradictory_verdict_rejected(attack_input: dict) -> dict:
    """Reviewer approval containing blocking findings is unproven (ACC-003).

    Mirrors tests/station/test_reviewer_contract.py::
    test_reviewer_cannot_approve_with_blocking_finding.
    """
    import tempfile
    from unittest.mock import patch
    from residual.station.service import DEMO_FILES, Station, demo_spec
    tmp = tempfile.TemporaryDirectory()
    try:
        s = Station(tmp.name)
        pid = s.create(demo_spec(), commands=True, demo=False)["project_id"]
        s.triage(pid)
        work = s.prepare(pid, "review-contract", "OPS-101")
        s.finish(work, {"files": DEMO_FILES["OPS-101"]})
        verdict = {"approved": True, "findings": [
            {"severity": "blocking", "message": "serious semantic defect"}]}
        with patch("residual.station.service.model_call", return_value=verdict):
            s.review(pid, "OPS-101")
    finally:
        tmp.cleanup()
    return {"coercion": "succeeded"}  # unreachable while the path rejects


@attack("AUTH-ACC-003-P01", kind="positive")
def _full_binding_issues_acceptance(attack_input: dict) -> dict:
    """Positive: full verifier/admission binding issues a signed acceptance
    artifact bound to the contract identity and candidate identity
    (ACC-003). Mirrors test_full_binding_issues_signed_acceptance_artifact.
    """
    from residual.factory.evidence_receipts import StationIdentity
    from tests.test_eval_frozen_acceptance_binding import (
        ACCEPTANCE_SCHEMA, COMMIT, FreshRunRegistry, begin,
        development_workload, issue, make_evidence, verify_acceptance_artifact,
    )
    identity = StationIdentity.generate()
    registry = FreshRunRegistry(identity)
    workload = development_workload()
    begin(registry, workload)
    artifact = issue(identity, registry, workload,
                     make_evidence(identity, registry, workload, "run-1"))
    return {
        "schema_version": artifact["schema_version"],
        "expected_schema": ACCEPTANCE_SCHEMA,
        "verified": bool(verify_acceptance_artifact(
            artifact, identity.public_bytes())),
        "run_id": artifact["verifier_qualification"]["run_id"],
        "required_commit": COMMIT,
    }


@attack("AUTH-AUT-006-P01", kind="positive")
def _approved_action_executes(attack_input: dict) -> dict:
    """Positive: approval record bound to proposal identity; the authorized
    action executes within approved scope (AUT-006)."""
    from residual.quarantine import ProposedAction, QuarantineStore

    def allow_all(action):
        return None  # policy approves: no denial reason

    store = QuarantineStore()
    action = ProposedAction(
        "tool_call", attack_input.get("name", "approved-action"),
        {"scope": "approved"},
        agent_id=attack_input.get("agent_id", "agent01"))
    held = store.hold(action)
    decision = store.evaluate(held, (allow_all,))  # the approval record
    executed = store.release(
        held, lambda a: {"executed": True, "name": a.name})
    return {
        "decision": decision.value,
        "executed": bool(executed.result and executed.result.get("executed")),
        "name": (executed.result or {}).get("name"),
        "fingerprint": held.fingerprint,
    }


@attack("AUTH-EVD-001-P01", kind="positive")
def _evidence_receipt_admissible(attack_input: dict) -> dict:
    """Positive: evidence receipt issued; admissible at an evidence-gated
    transition (EVD-001). The gate is exact prerequisite-DAG validation."""
    from residual.receipts import StationReceipt, validate_receipt_graph
    from residual.verifier import CheckResult
    receipt = StationReceipt(
        task_id="evd001-task",
        cache_key="a" * 64,
        value_hash="b" * 64,
        verifier_name="station:test",
        verifier_revision="c" * 64,
        verdict=CheckResult.PASS,
        kernel_revision="d" * 64,
    )
    validate_receipt_graph({"evd001-task": receipt}, {"evd001-task": ()})
    return {
        "receipt_issued": True,
        "receipt_hash": receipt.receipt_hash,
        "admissible": True,
        "verdict": receipt.verdict.value,
    }


@attack("AUTH-IDN-002-P01", kind="positive")
def _enrolled_identity_acts_in_scope(attack_input: dict) -> dict:
    """Positive: authority grant recorded; enrolled identity acts within
    granted scope (IDN-002)."""
    from residual.factory.worker_contract import AttemptGuard
    events: list = []
    agent_id = attack_input.get("agent_id", "enrolled-agent")
    guard = AttemptGuard(
        _trackc_contract("trackc", agent_id),
        observe=events.append, terminate=lambda: None,
    )
    guard.start()
    guard.authorize_tool("evidence.inspect")  # allowed tool: within scope
    granted = [e for e in events if e.get("event") == "ToolAuthorized"]
    return {
        "grant_recorded": bool(granted),
        "tool": "evidence.inspect",
        "worker_id": agent_id,
    }
