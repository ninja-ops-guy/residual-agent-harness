"""Track C: INV-AUTH-CTR-004 harder case — the authorized actor.

Spec (AUTH_INVARIANTS.md, CTR-004): "if an authorized amendment creates
contract B and the new semantics should apply to the work, the pending
transition is cancelled and reissued under B — never quietly rebound."
Authority to amend a contract does not include authority to rebind an
in-flight transition to the amended version.

GAP (documented): the codebase has no first-class pending-transition
type. The test models the pending transition as a frozen record bound to
a GoalSpec content_hash — the same contract-identity boundary that
GoalSpec.amend() governs (new identity + parent_hash lineage, original
preserved). The rebind rule enforced here is the spec's rule, stated at
that boundary. A future first-class transition type should carry the
rule natively; until then, this test pins the normative behavior and
names what it stands in for.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from residual.authority import AuthorityCoercionRejected
from residual.goalspec import AmendmentRule, CheckType, GoalSpec, SuccessCriterion


def _criterion() -> SuccessCriterion:
    return SuccessCriterion(
        name="mechanical-gate",
        check_type=CheckType.MECHANICAL,
        description="mechanical gate",
        evaluator="mechanical",
        parameters={},
    )


def _contract_a() -> GoalSpec:
    """Contract A: amendable by the owner role, up to three amendments."""
    return GoalSpec(
        goal_id="ctr004-harder",
        objective="do the thing under contract A",
        success_criteria=(_criterion(),),
        max_passes=3,
        token_budget=1000,
        wall_clock_budget_s=60.0,
        amendment_rule=AmendmentRule(authorized_roles=("owner",), max_amendments=3),
    )


@dataclass(frozen=True)
class PendingTransition:
    """In-flight work bound to a frozen contract identity.

    Stand-in for a first-class pending-transition type (see module
    docstring). request_rebind enforces CTR-004's fail-closed behavior:
    in-flight work is never quietly rebound to an amended contract.
    """

    transition_id: str
    contract_hash: str
    state: str = "in_flight"  # in_flight | cancelled

    def request_rebind(self, new_contract_hash: str) -> "PendingTransition":
        """Attempt to move this in-flight transition onto another contract.

        Always fails closed while in flight: the only legal path is
        cancel() + reissue under the new contract identity.
        """
        if self.state == "in_flight" and new_contract_hash != self.contract_hash:
            raise AuthorityCoercionRejected(
                code="UNAUTHORIZED_CONTRACT_REINTERPRETATION",
                fail_closed_state="NO_AUTHORITY_CHANGE",
                reason=(
                    "pending transition cannot be rebound to an amended "
                    "contract; cancel and reissue under the new identity"
                ),
            )
        return self

    def cancel(self) -> "PendingTransition":
        return PendingTransition(
            transition_id=self.transition_id,
            contract_hash=self.contract_hash,
            state="cancelled",
        )


def test_authorized_amendment_creates_contract_b():
    """Positive: the permitted conversion — legitimate amendment authority
    produces a NEW frozen identity with parent_hash lineage; the original
    is preserved."""
    a = _contract_a()
    b = a.amend(
        objective="do the thing under contract B",
        amendment_reason="owner refines scope",
        amended_by="owner",
    )
    assert b.parent_hash == a.content_hash
    assert b.content_hash != a.content_hash
    assert b.amendment_count == 1
    assert b.amended_by == "owner"
    # The original is untouched: amendment never mutates in place.
    assert a.amendment_count == 0
    assert a.parent_hash is None


def test_authorized_actor_cannot_rebind_pending_transition():
    """AUTH-CTR-004-N02 (harder case): the well-intentioned owner amends
    mid-flight, then tries to move the pending transition onto B."""
    a = _contract_a()
    b = a.amend(
        objective="do the thing under contract B",
        amendment_reason="owner refines scope",
        amended_by="owner",
    )
    pending = PendingTransition(transition_id="t-1", contract_hash=a.content_hash)

    with pytest.raises(AuthorityCoercionRejected) as exc_info:
        pending.request_rebind(b.content_hash)

    err = exc_info.value
    assert err.code == "UNAUTHORIZED_CONTRACT_REINTERPRETATION"
    assert err.fail_closed_state == "NO_AUTHORITY_CHANGE"
    assert err.invariant_id == "INV-AUTH-CTR-004"
    assert err.triggered_codes == ("UNAUTHORIZED_CONTRACT_REINTERPRETATION",)
    # Nothing was rebound: the transition is still bound to A, still in flight.
    assert pending.contract_hash == a.content_hash
    assert pending.state == "in_flight"


def test_cancel_and_reissue_under_b_succeeds():
    """Positive: the spec's prescribed path — the pending transition dies
    under A and is reissued under B."""
    a = _contract_a()
    b = a.amend(
        objective="do the thing under contract B",
        amendment_reason="owner refines scope",
        amended_by="owner",
    )
    pending = PendingTransition(transition_id="t-1", contract_hash=a.content_hash)
    cancelled = pending.cancel()
    assert cancelled.state == "cancelled"

    reissued = PendingTransition(transition_id="t-2", contract_hash=b.content_hash)
    assert reissued.contract_hash == b.content_hash
    assert reissued.state == "in_flight"
    # Rebinding the cancelled transition is a no-op, not a violation:
    # there is nothing in flight to rebind.
    assert cancelled.request_rebind(b.content_hash).state == "cancelled"
