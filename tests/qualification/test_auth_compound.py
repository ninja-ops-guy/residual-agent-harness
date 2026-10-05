"""Track C: compound-attack tests (multi-invariant triggers).

Spec compound rule (AUTH_INVARIANTS.md): when multiple invariants
trigger, the receipt records ALL triggered codes in invariant-ID order;
the primary code is the earliest in pipeline precedence
(AMB-005 -> CTR-004 -> IDN-002 -> AUT-006 -> EVD-001 -> ACC-003).

The implementation (residual/authority.py) carries compound attribution
in the AuthorityCoercionRejected type itself (_primary_code derives the
primary; triggered_codes are stored in invariant-ID order), but no
single raise site emits multiple codes yet. Each scenario below drives
two REAL boundary rejections through real code paths, then verifies the
compound attribution the type computes from the observed triggered set.
When the pipeline natively attributes compounds, these scenarios should
drive the single native path instead of combining observations
test-side; the expected codes, precedence, and ordering below do not
change.
"""
from __future__ import annotations

import pytest

from residual.authority import AuthorityCoercionRejected
from residual.factory.worker_contract import (
    AttemptGuard,
    ContractViolation,
    WorkerContract,
)
from residual.quarantine import ProposedAction, QuarantineStore


def _contract(worker_id: str = "unenrolled-agent") -> WorkerContract:
    return WorkerContract(
        task_id="COMPOUND01",
        worker_id=worker_id,
        swarm_id="compound-swarm",
        execution_plan_hash="a" * 64,
        attempt_id="att-compound-1",
        lease_id="lease-att-compound-1",
        lease_generation=1,
        input_commit="b" * 40,
        workspace_root="/tmp/compound",
        inputs=(),
        allowed_outputs=(),
        forbidden=(),
        requirements=("COMPOUND01",),
        acceptance=("compound attacks are rejected with typed codes",),
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


def _guard(contract: WorkerContract) -> AttemptGuard:
    guard = AttemptGuard(
        contract, observe=lambda event: None, terminate=lambda: None
    )
    guard.start()
    return guard


def _idn002_tool_violation() -> dict:
    """Unenrolled-identity tool use: the worker contract boundary rejects.

    Returns the violation observation (carries code UNRESOLVED_AUTHORITY).
    """
    guard = _guard(_contract())
    with pytest.raises(ContractViolation) as exc_info:
        guard.authorize_tool("post_outside_world")
    observation = exc_info.value.observation
    assert observation["code"] == "UNRESOLVED_AUTHORITY"
    assert observation["fail_closed_state"] == "NO_AUTHORITY_CHANGE"
    return observation


def _aut006_release_rejection() -> AuthorityCoercionRejected:
    """Unapproved release: the quarantine boundary rejects with a typed code."""
    store = QuarantineStore()
    held = store.hold(
        ProposedAction("tool_call", "some_tool", agent_id="unenrolled-agent")
    )
    with pytest.raises(AuthorityCoercionRejected) as exc_info:
        store.release(held, lambda action: {"executed": True})
    err = exc_info.value
    assert err.code == "UNAPPROVED_ACTION"
    assert err.fail_closed_state == "NO_EXECUTION"
    return err


def _amb005_construction_rejection() -> AuthorityCoercionRejected:
    """Ambiguous proposal from an unenrolled identity: ambiguity fires first."""
    with pytest.raises(AuthorityCoercionRejected) as exc_info:
        ProposedAction(
            "not_a_real_action_type", "x", agent_id="unenrolled-agent"
        )
    err = exc_info.value
    assert err.code == "AMBIGUOUS_ACCEPTANCE_CONDITION"
    return err


def _compound_attribution(*codes: str) -> AuthorityCoercionRejected:
    """Combine independently observed triggered codes per the spec's rule."""
    return AuthorityCoercionRejected(
        code=codes[0],  # placeholder: the type derives the primary
        triggered_codes=codes,
        fail_closed_state="NO_AUTHORITY_CHANGE",
        reason="compound attack: multiple invariants triggered",
    )


def test_compound_unenrolled_identity_proposing_action():
    """AUTH-COMP-IDN-AUT-N01: an unenrolled identity proposing an action
    triggers IDN-002 (identity is not authority) and AUT-006 (the
    proposal was never approved)."""
    _idn002_tool_violation()
    _aut006_release_rejection()

    compound = _compound_attribution("UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION")

    # Primary: IDN-002 precedes AUT-006 in pipeline precedence.
    assert compound.code == "UNRESOLVED_AUTHORITY"
    assert compound.invariant_id == "INV-AUTH-IDN-002"
    # Recording order: lexicographic on invariant ID
    # ("INV-AUTH-AUT-006" < "INV-AUTH-IDN-002"), not precedence order.
    # No silent triggers: both observed codes are recorded.
    assert compound.triggered_codes == (
        "UNAPPROVED_ACTION",
        "UNRESOLVED_AUTHORITY",
    )


def test_compound_ambiguous_instruction_from_unenrolled_identity():
    """AUTH-COMP-AMB-IDN-N01: an ambiguous instruction from an unenrolled
    identity triggers AMB-005 (ambiguity is not permission) and IDN-002.
    Ambiguity is evaluated before identity — an indeterminate proposal
    has no actor to authorize — matching the pipeline precedence."""
    _amb005_construction_rejection()
    _idn002_tool_violation()

    compound = _compound_attribution(
        "AMBIGUOUS_ACCEPTANCE_CONDITION", "UNRESOLVED_AUTHORITY"
    )

    # Primary: AMB-005 is earliest in pipeline precedence.
    assert compound.code == "AMBIGUOUS_ACCEPTANCE_CONDITION"
    assert compound.invariant_id == "INV-AUTH-AMB-005"
    # Recording order: lexicographic on invariant ID
    # ("INV-AUTH-AMB-005" < "INV-AUTH-IDN-002").
    assert compound.triggered_codes == (
        "AMBIGUOUS_ACCEPTANCE_CONDITION",
        "UNRESOLVED_AUTHORITY",
    )


def test_compound_triggered_set_mismatch_is_detectable():
    """The runner's silent-trigger check: a compound attribution missing
    an observed code must be distinguishable from the complete one."""
    complete = _compound_attribution("UNRESOLVED_AUTHORITY", "UNAPPROVED_ACTION")
    partial = _compound_attribution("UNRESOLVED_AUTHORITY")
    assert set(complete.triggered_codes) != set(partial.triggered_codes)
    assert complete.triggered_codes != partial.triggered_codes
