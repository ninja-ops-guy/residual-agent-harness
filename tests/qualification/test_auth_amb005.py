"""Track C: INV-AUTH-AMB-005 adversarial tests (previously zero coverage).

The only in-code ambiguity fail-closed is ProposedAction construction
validation (residual/quarantine.py): indeterminate proposals are rejected
with AMBIGUOUS_ACCEPTANCE_CONDITION / NO_IMPLICIT_DEFAULT instead of being
defaulted into the approval chain. These tests pin that typed emission.

GAP (honest): the spec's instruction-level ambiguity pipeline
(AMBIGUOUS_INTENT -> SURFACED_AMBIGUITY -> AUTHORIZED_CLARIFICATION ->
VALIDATED_CONTRACT -> HUMAN_APPROVAL -> FROZEN_CONTRACT_ID ->
EXECUTABLE_AUTHORITY) does not exist in the codebase. The last test in
this file documents that gap via xfail rather than pretending the
construction-validation path is the pipeline.
"""
from __future__ import annotations

import importlib.util

import pytest

from residual.authority import AuthorityCoercionRejected
from residual.quarantine import ActionType, ProposedAction


def _assert_ambiguity_rejection(exc_info) -> None:
    err = exc_info.value
    assert isinstance(err, AuthorityCoercionRejected)
    assert err.code == "AMBIGUOUS_ACCEPTANCE_CONDITION"
    assert err.fail_closed_state == "NO_IMPLICIT_DEFAULT"
    assert err.invariant_id == "INV-AUTH-AMB-005"
    assert err.triggered_codes == ("AMBIGUOUS_ACCEPTANCE_CONDITION",)


def test_unknown_action_type_emits_code():
    """AUTH-AMB-005-N01: indeterminate action class is not defaulted."""
    with pytest.raises(AuthorityCoercionRejected) as exc_info:
        ProposedAction("not_a_real_action_type", "x")
    _assert_ambiguity_rejection(exc_info)


def test_missing_name_emits_code():
    """AUTH-AMB-005-N02: a proposal without a name is indeterminate."""
    with pytest.raises(AuthorityCoercionRejected) as exc_info:
        ProposedAction("tool_call", "")
    _assert_ambiguity_rejection(exc_info)


def test_non_canonicalizable_arguments_emit_code():
    """AUTH-AMB-005-N03: arguments that cannot be frozen are indeterminate."""
    with pytest.raises(AuthorityCoercionRejected) as exc_info:
        ProposedAction("tool_call", "x", {"unfreezable": object()})
    _assert_ambiguity_rejection(exc_info)


def test_well_formed_action_constructs():
    """AUTH-AMB-005-P01 (positive): a determinate proposal is accepted.

    Spec positive criterion: executable authority granted for the
    clarified contract. At the construction boundary, the success
    artifact is a validated action with a stable fingerprint.
    """
    action = ProposedAction("tool_call", "my_tool", {"a": 1}, agent_id="agent01")
    assert action.action_type is ActionType.TOOL_CALL
    assert action.name == "my_tool"
    assert action.agent_id == "agent01"
    assert len(action.fingerprint) == 64
    # Deterministic: the same proposal always yields the same fingerprint.
    again = ProposedAction("tool_call", "my_tool", {"a": 1}, agent_id="agent01")
    assert again.fingerprint == action.fingerprint


@pytest.mark.xfail(
    strict=False,
    reason=(
        "TRACK C GAP: the spec's instruction-level ambiguity pipeline "
        "(AMBIGUOUS_INTENT -> SURFACED_AMBIGUITY -> AUTHORIZED_CLARIFICATION "
        "-> VALIDATED_CONTRACT -> HUMAN_APPROVAL -> FROZEN_CONTRACT_ID -> "
        "EXECUTABLE_AUTHORITY) does not exist in the codebase. The only "
        "ambiguity fail-closed is ProposedAction construction validation. "
        "Building the pipeline is a product decision, not Track C. This "
        "test would assert that an ambiguous natural-language instruction "
        "produces a machine-readable SURFACED_AMBIGUITY record (with the "
        "enumerated materially-different interpretations) instead of "
        "executing under any implicit interpretation."
    ),
)
def test_instruction_ambiguity_pipeline_surfaces_record():
    """The pipeline's entry point: surface ambiguity as a typed record."""
    assert importlib.util.find_spec("residual.ambiguity_pipeline") is not None, (
        "no ambiguity-pipeline module: ambiguous instructions have no typed "
        "surface->clarify->validate->approve->freeze path before "
        "ProposedAction construction"
    )
