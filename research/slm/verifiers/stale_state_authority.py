"""stale_state_authority verifier (slm00.verifier.stale_state_authority).

Category contract
-----------------
input_state:
  current_generation: int          authoritative state generation
  receipt:
    generation: int                generation stamped on the receipt being
                                   acted upon
    authority_scope: [str]         authority carried by the receipt
  state_machine:
    current_state: str
    legal_transitions: [str]       states reachable from current_state
  protected_boundaries: [str]      state fields that receipts may never touch
  proposed_action:
    transition_to: str             requested next state
    required_authority: [str]      authority the action needs
    touches: [str]                 state fields the action would modify

expected_output:
  legal: bool
  violation: null | one of
    "STALE_RECEIPT" | "AUTHORITY_SCOPE_EXCEEDED" | "ILLEGAL_TRANSITION" |
    "PROTECTED_BOUNDARY_TOUCHED"

Candidate output: {"legal": bool, "violation": str | null}

Violation precedence (deterministic, first match fires):
  1. receipt.generation != current_generation     -> STALE_RECEIPT
  2. required_authority not subset of scope       -> AUTHORITY_SCOPE_EXCEEDED
  3. transition_to not in legal_transitions       -> ILLEGAL_TRANSITION
     (a self-transition transition_to == current_state counts as legal only
      if listed in legal_transitions)
  4. touches intersects protected_boundaries      -> PROTECTED_BOUNDARY_TOUCHED
  otherwise legal. The frozen expected legal/violation pair must equal the
  derived pair exactly; mismatch is a BENCHMARK_DEFECT.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import BaseVerifier, VerifierResult, _defect, _fail, _pass

VIOLATIONS = (
    "STALE_RECEIPT",
    "AUTHORITY_SCOPE_EXCEEDED",
    "ILLEGAL_TRANSITION",
    "PROTECTED_BOUNDARY_TOUCHED",
)


def derive_legality(input_state: Mapping[str, Any]) -> Optional[str]:
    """Return the violation code, or None if the proposed action is legal."""
    receipt = input_state["receipt"]
    machine = input_state["state_machine"]
    action = input_state["proposed_action"]
    if receipt["generation"] != input_state["current_generation"]:
        return "STALE_RECEIPT"
    required = set(action["required_authority"])
    if not required.issubset(set(receipt["authority_scope"])):
        return "AUTHORITY_SCOPE_EXCEEDED"
    if action["transition_to"] not in set(machine["legal_transitions"]):
        return "ILLEGAL_TRANSITION"
    if set(action["touches"]) & set(input_state["protected_boundaries"]):
        return "PROTECTED_BOUNDARY_TOUCHED"
    return None


class StaleStateAuthorityVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.stale_state_authority"
    CATEGORY = "stale_state_authority"

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        defect = super()._check_item(item)
        if defect is not None:
            return defect
        state = item["input_state"]
        if not isinstance(state.get("current_generation"), int) or isinstance(
            state.get("current_generation"), bool
        ):
            return _defect("DEFECT_BAD_GENERATION", "current_generation: int")
        receipt = state.get("receipt")
        if not isinstance(receipt, Mapping):
            return _defect("DEFECT_MISSING_RECEIPT")
        if not isinstance(receipt.get("generation"), int) or isinstance(
            receipt.get("generation"), bool
        ):
            return _defect("DEFECT_BAD_GENERATION", "receipt.generation: int")
        if not isinstance(receipt.get("authority_scope"), list):
            return _defect("DEFECT_BAD_AUTHORITY_SCOPE")
        machine = state.get("state_machine")
        if not isinstance(machine, Mapping):
            return _defect("DEFECT_MISSING_STATE_MACHINE")
        if not isinstance(machine.get("current_state"), str):
            return _defect("DEFECT_BAD_CURRENT_STATE")
        if not isinstance(machine.get("legal_transitions"), list):
            return _defect("DEFECT_BAD_LEGAL_TRANSITIONS")
        if not isinstance(state.get("protected_boundaries"), list):
            return _defect("DEFECT_BAD_PROTECTED_BOUNDARIES")
        action = state.get("proposed_action")
        if not isinstance(action, Mapping):
            return _defect("DEFECT_MISSING_PROPOSED_ACTION")
        if not isinstance(action.get("transition_to"), str):
            return _defect("DEFECT_BAD_TRANSITION")
        for key in ("required_authority", "touches"):
            if not isinstance(action.get(key), list):
                return _defect("DEFECT_BAD_ACTION_FIELD", f"proposed_action.{key}")
        return None

    def _derive_expected(
        self, item: Mapping[str, Any]
    ) -> tuple[Any, Optional[VerifierResult]]:
        return derive_legality(item["input_state"]), None

    def _expected_matches(
        self, expected: Mapping[str, Any], derived: Optional[str]
    ) -> Optional[VerifierResult]:
        legal = expected.get("legal")
        if not isinstance(legal, bool):
            return _defect("DEFECT_MISSING_LEGAL", "expected legal: bool")
        violation = expected.get("violation")
        if violation is not None and violation not in VIOLATIONS:
            return _defect(
                "DEFECT_UNKNOWN_VIOLATION", f"violation {violation!r} not frozen taxonomy"
            )
        if legal != (derived is None):
            return _defect(
                "EXPECTED_LEGAL_MISMATCH",
                f"frozen legal={legal} != derived legal={derived is None}",
            )
        if violation != derived:
            return _defect(
                "EXPECTED_VIOLATION_MISMATCH",
                f"frozen violation {violation!r} != derived {derived!r}",
            )
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        derived = derive_legality(item["input_state"])
        legal = candidate_output.get("legal")
        if not isinstance(legal, bool):
            return _fail("MISSING_FIELD", "legal must be a bool")
        violation = candidate_output.get("violation")
        if violation is not None and violation not in VIOLATIONS:
            return _fail("UNKNOWN_VIOLATION", f"violation {violation!r} not in taxonomy")
        if legal != (derived is None):
            return _fail(
                "WRONG_LEGALITY",
                f"candidate legal={legal} != actual legal={derived is None}",
            )
        if violation != derived:
            return _fail(
                "WRONG_VIOLATION",
                f"candidate violation {violation!r} != actual {derived!r}",
            )
        return _pass()
