"""retry_escalate_abort verifier (slm00.verifier.retry_escalate_abort).

Category contract
-----------------
input_state:
  policy:                          frozen policy — executed, not reinterpreted
    max_retries: int
    retry_on: [failure_class]      classes eligible for retry
    escalate_on: [failure_class]   classes that force escalation
    escalate_when_retry_exhausted: bool
    authority_required: [str]      authority needed to retry at all
  state:
    attempts: int                  retries already consumed (0-based count of
                                   prior retries)
    failure_class: str             observed failure (taxonomy label)
    authority_granted: [str]
    capability_ok: bool            whether the failed action's capability
                                   requirements are actually satisfiable

expected_output:
  action: one of "retry" | "escalate" | "abort"
  reason_code: str                 stable policy reason (see below)

Candidate output: {"action": str, "reason_code": str}

Frozen decision procedure (the verifier executes it deterministically):
  1. failure_class in policy.escalate_on            -> escalate (POLICY_ESCALATE_CLASS)
  2. capability_ok is false                         -> abort    (CAPABILITY_MISMATCH)
  3. authority_required not subset of granted       -> escalate (AUTHORITY_INSUFFICIENT)
  4. attempts >= max_retries:
       escalate_when_retry_exhausted                -> escalate (RETRY_BUDGET_EXHAUSTED)
       else                                         -> abort    (RETRY_BUDGET_EXHAUSTED)
  5. failure_class not in retry_on                  -> abort    (CLASS_NOT_RETRYABLE)
  6. otherwise                                      -> retry    (POLICY_RETRY)

Rules are evaluated in order; the first matching rule fires. The frozen
expected action/reason are compared against this derivation — mismatch is a
BENCHMARK_DEFECT.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import BaseVerifier, VerifierResult, _defect, _fail, _pass

ACTIONS = ("retry", "escalate", "abort")


def execute_policy(policy: Mapping[str, Any], state: Mapping[str, Any]) -> tuple[str, str]:
    """Deterministically execute the frozen retry/escalate/abort policy."""
    failure_class = state.get("failure_class")
    if failure_class in (policy.get("escalate_on") or []):
        return "escalate", "POLICY_ESCALATE_CLASS"
    if state.get("capability_ok") is not True:
        return "abort", "CAPABILITY_MISMATCH"
    required = set(policy.get("authority_required") or [])
    granted = set(state.get("authority_granted") or [])
    if not required.issubset(granted):
        return "escalate", "AUTHORITY_INSUFFICIENT"
    attempts = state.get("attempts")
    max_retries = policy.get("max_retries")
    if attempts >= max_retries:
        if policy.get("escalate_when_retry_exhausted") is True:
            return "escalate", "RETRY_BUDGET_EXHAUSTED"
        return "abort", "RETRY_BUDGET_EXHAUSTED"
    if failure_class not in (policy.get("retry_on") or []):
        return "abort", "CLASS_NOT_RETRYABLE"
    return "retry", "POLICY_RETRY"


class RetryEscalateAbortVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.retry_escalate_abort"
    CATEGORY = "retry_escalate_abort"

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        defect = super()._check_item(item)
        if defect is not None:
            return defect
        state = item["input_state"]
        policy = state.get("policy")
        if not isinstance(policy, Mapping):
            return _defect("DEFECT_MISSING_POLICY", "input_state.policy required")
        if not isinstance(policy.get("max_retries"), int) or isinstance(
            policy.get("max_retries"), bool
        ):
            return _defect("DEFECT_BAD_MAX_RETRIES")
        for key in ("retry_on", "escalate_on", "authority_required"):
            if not isinstance(policy.get(key), list):
                return _defect("DEFECT_BAD_POLICY_FIELD", f"policy.{key} must be a list")
        if not isinstance(policy.get("escalate_when_retry_exhausted"), bool):
            return _defect("DEFECT_BAD_POLICY_FIELD", "escalate_when_retry_exhausted: bool")
        st = state.get("state")
        if not isinstance(st, Mapping):
            return _defect("DEFECT_MISSING_STATE", "input_state.state required")
        if not isinstance(st.get("attempts"), int) or isinstance(st.get("attempts"), bool):
            return _defect("DEFECT_BAD_ATTEMPTS")
        if not isinstance(st.get("failure_class"), str):
            return _defect("DEFECT_BAD_FAILURE_CLASS")
        if not isinstance(st.get("authority_granted"), list):
            return _defect("DEFECT_BAD_AUTHORITY_GRANTED")
        if not isinstance(st.get("capability_ok"), bool):
            return _defect("DEFECT_BAD_CAPABILITY_OK")
        if set(policy["retry_on"]) & set(policy["escalate_on"]):
            return _defect(
                "DEFECT_POLICY_OVERLAP",
                "failure class in both retry_on and escalate_on is ambiguous",
            )
        return None

    def _derive_expected(
        self, item: Mapping[str, Any]
    ) -> tuple[Any, Optional[VerifierResult]]:
        state = item["input_state"]
        return execute_policy(state["policy"], state["state"]), None

    def _expected_matches(
        self, expected: Mapping[str, Any], derived: tuple[str, str]
    ) -> Optional[VerifierResult]:
        action = expected.get("action")
        if action not in ACTIONS:
            return _defect("DEFECT_BAD_EXPECTED_ACTION", f"action {action!r}")
        if action != derived[0]:
            return _defect(
                "EXPECTED_ACTION_MISMATCH",
                f"frozen action {action!r} != policy-derived {derived[0]!r}",
            )
        reason = expected.get("reason_code")
        if not isinstance(reason, str) or not reason:
            return _defect("DEFECT_MISSING_REASON_CODE")
        if reason != derived[1]:
            return _defect(
                "EXPECTED_REASON_MISMATCH",
                f"frozen reason {reason!r} != policy-derived {derived[1]!r}",
            )
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        derived_action, derived_reason = execute_policy(
            item["input_state"]["policy"], item["input_state"]["state"]
        )
        action = candidate_output.get("action")
        if action not in ACTIONS:
            return _fail("UNKNOWN_ACTION", f"action {action!r} not in {ACTIONS}")
        if action != derived_action:
            return _fail(
                "WRONG_ACTION",
                f"candidate {action!r} != policy-required {derived_action!r}",
            )
        reason = candidate_output.get("reason_code")
        if not isinstance(reason, str) or not reason:
            return _fail("MISSING_REASON_CODE")
        if reason != derived_reason:
            return _fail(
                "WRONG_REASON_CODE",
                f"candidate reason {reason!r} != {derived_reason!r}",
            )
        return _pass()
