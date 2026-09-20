"""contract_compilation verifier (slm00.verifier.contract_compilation).

Category contract
-----------------
input_state:
  contract_spec:
    required_fields: [dotted.path, ...]     schema: required keys present
    invariants: [                           declarative invariant checks
      {"kind": "equals",       "path": p, "value": v},
      {"kind": "subset_of",    "path": p, "value": [..]},   # list at path
      {"kind": "not_empty",    "path": p},
      {"kind": "max_value",    "path": p, "value": n},
      {"kind": "min_value",    "path": p, "value": n},
      {"kind": "enum",         "path": p, "value": [..]}    # scalar at path
    ]
    capability_boundary: [str]    compiled contract capabilities MUST be a
                                  subset of this boundary (checked at path
                                  "capabilities" unless overridden by
                                  capability_path)
    authority_scope: [str]        compiled authority grants MUST be a subset
    evidence_requirements: [str]  each required evidence id MUST appear in the
                                  compiled contract's "evidence" list
    budget: {"max_cost_usd": n}   compiled "budget_usd" MUST be <= max and > 0

expected_output:
  contract: {...}    reference compiled contract

Candidate output: {"contract": {...}}

Semantic equivalence is allowed: candidate contract is compared against the
reference via canonical JSON equality (key order and 1 vs 1.0 normalized),
NOT byte-exact serialization. When allowed_alternatives on the item lists
alternative reference contracts, any canonical match passes. Independently of
the reference, the candidate MUST satisfy every declarative invariant above;
a reference contract that violates its own spec invariants is a
BENCHMARK_DEFECT.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import (
    BaseVerifier,
    MISSING,
    VerifierResult,
    _defect,
    _fail,
    _pass,
    get_path,
    semantically_equal,
)

_ALLOWED_INVARIANT_KINDS = {
    "equals",
    "subset_of",
    "not_empty",
    "max_value",
    "min_value",
    "enum",
}


class ContractCompilationVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.contract_compilation"
    CATEGORY = "contract_compilation"

    # -- item/spec validation --------------------------------------------

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        defect = super()._check_item(item)
        if defect is not None:
            return defect
        spec = item["input_state"].get("contract_spec")
        if not isinstance(spec, Mapping):
            return _defect("DEFECT_MISSING_SPEC", "input_state.contract_spec required")
        required_fields = spec.get("required_fields")
        if not isinstance(required_fields, list) or not all(
            isinstance(f, str) for f in required_fields
        ):
            return _defect("DEFECT_BAD_REQUIRED_FIELDS")
        invariants = spec.get("invariants") or []
        if not isinstance(invariants, list):
            return _defect("DEFECT_BAD_INVARIANTS")
        for inv in invariants:
            if not isinstance(inv, Mapping) or inv.get("kind") not in _ALLOWED_INVARIANT_KINDS:
                return _defect(
                    "DEFECT_UNKNOWN_INVARIANT_KIND",
                    f"invariant {inv!r} has unknown/missing kind",
                )
            if not isinstance(inv.get("path"), str):
                return _defect("DEFECT_INVARIANT_MISSING_PATH")
        reference = item["expected_output"].get("contract")
        if not isinstance(reference, Mapping):
            return _defect(
                "DEFECT_MISSING_REFERENCE_CONTRACT",
                "expected_output.contract must be an object",
            )
        # Adversarial: the frozen reference must itself satisfy the spec.
        violation = self._check_contract(reference, spec, defect_mode=True)
        if violation is not None:
            return violation
        for alt in item.get("allowed_alternatives") or []:
            if not isinstance(alt, Mapping) or not isinstance(alt.get("contract"), Mapping):
                return _defect(
                    "DEFECT_BAD_ALTERNATIVE",
                    "allowed_alternatives entries must be objects with a contract",
                )
        return None

    # -- core contract checks --------------------------------------------

    def _check_contract(
        self, contract: Mapping[str, Any], spec: Mapping[str, Any], defect_mode: bool
    ) -> Optional[VerifierResult]:
        mark = _defect if defect_mode else _fail
        prefix = "DEFECT_REFERENCE_" if defect_mode else ""
        for field_path in spec.get("required_fields") or []:
            if get_path(contract, field_path) is MISSING:
                return mark(
                    prefix + "MISSING_REQUIRED_FIELD",
                    f"contract missing required field {field_path!r}",
                )
        for inv in spec.get("invariants") or []:
            result = self._check_invariant(contract, inv, defect_mode)
            if result is not None:
                return result
        boundary = spec.get("capability_boundary")
        if boundary is not None:
            cap_path = spec.get("capability_path", "capabilities")
            caps = get_path(contract, cap_path)
            if caps is MISSING or not isinstance(caps, list):
                return mark(prefix + "MISSING_CAPABILITIES", "capability list absent")
            extra = set(caps) - set(boundary)
            if extra:
                return mark(
                    prefix + "CAPABILITY_BOUNDARY_VIOLATION",
                    f"capabilities outside boundary: {sorted(extra)}",
                )
        scope = spec.get("authority_scope")
        if scope is not None:
            grants = get_path(contract, spec.get("authority_path", "authority"))
            if grants is MISSING or not isinstance(grants, list):
                return mark(prefix + "MISSING_AUTHORITY", "authority grant list absent")
            extra = set(grants) - set(scope)
            if extra:
                return mark(
                    prefix + "AUTHORITY_SCOPE_VIOLATION",
                    f"authority grants outside scope: {sorted(extra)}",
                )
        evidence_reqs = spec.get("evidence_requirements")
        if evidence_reqs is not None:
            present = get_path(contract, spec.get("evidence_path", "evidence"))
            if present is MISSING or not isinstance(present, list):
                return mark(prefix + "MISSING_EVIDENCE", "evidence list absent")
            missing = sorted(set(evidence_reqs) - set(present))
            if missing:
                return mark(
                    prefix + "EVIDENCE_REQUIREMENT_UNMET",
                    f"missing evidence entries: {missing}",
                )
        budget = spec.get("budget")
        if budget is not None:
            max_cost = budget.get("max_cost_usd")
            value = get_path(contract, spec.get("budget_path", "budget_usd"))
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return mark(prefix + "MISSING_BUDGET", "budget_usd not numeric")
            if value <= 0:
                return mark(prefix + "BUDGET_NONPOSITIVE", "budget_usd must be > 0")
            if isinstance(max_cost, (int, float)) and value > max_cost:
                return mark(
                    prefix + "BUDGET_EXCEEDED",
                    f"budget_usd {value} > max {max_cost}",
                )
        return None

    def _check_invariant(
        self, contract: Mapping[str, Any], inv: Mapping[str, Any], defect_mode: bool
    ) -> Optional[VerifierResult]:
        mark = _defect if defect_mode else _fail
        prefix = "DEFECT_REFERENCE_" if defect_mode else "INVARIANT_"
        kind = inv["kind"]
        value = get_path(contract, inv["path"])
        name = f"{inv['kind']}@{inv['path']}"
        if value is MISSING:
            return mark(prefix + "VIOLATED", f"{name}: path absent")
        if kind == "equals" and not semantically_equal(value, inv.get("value")):
            return mark(prefix + "VIOLATED", f"{name}: {value!r} != {inv.get('value')!r}")
        if kind == "subset_of":
            if not isinstance(value, list) or not set(value).issubset(set(inv.get("value") or [])):
                return mark(prefix + "VIOLATED", f"{name}: {value!r} not subset")
        if kind == "not_empty" and not value:
            return mark(prefix + "VIOLATED", f"{name}: empty")
        if kind == "max_value" and not (
            isinstance(value, (int, float)) and value <= inv.get("value")
        ):
            return mark(prefix + "VIOLATED", f"{name}: {value!r} > {inv.get('value')!r}")
        if kind == "min_value" and not (
            isinstance(value, (int, float)) and value >= inv.get("value")
        ):
            return mark(prefix + "VIOLATED", f"{name}: {value!r} < {inv.get('value')!r}")
        if kind == "enum" and value not in (inv.get("value") or []):
            return mark(prefix + "VIOLATED", f"{name}: {value!r} not in enum")
        return None

    # -- candidate grading ------------------------------------------------

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        spec = item["input_state"]["contract_spec"]
        contract = candidate_output.get("contract")
        if not isinstance(contract, Mapping):
            return _fail("MISSING_CONTRACT", "candidate output lacks 'contract' object")
        violation = self._check_contract(contract, spec, defect_mode=False)
        if violation is not None:
            return violation
        reference = item["expected_output"]["contract"]
        candidates = [reference] + [
            alt["contract"] for alt in item.get("allowed_alternatives") or []
        ]
        if any(semantically_equal(contract, ref) for ref in candidates):
            return _pass()
        return _fail(
            "CONTRACT_MISMATCH",
            "candidate contract not semantically equal to any reference contract",
        )
