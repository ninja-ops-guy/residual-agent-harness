"""budget_decisions verifier (slm00.verifier.budget_decisions).

Category contract
-----------------
input_state:
  budget:
    total_usd: number
    spent_usd: number
    safety_reserve_usd: number   hard reserve; never spendable (0 allowed)
    mission_critical: bool       if false, spending to exactly the reserve
                                 boundary is disallowed unless policy
                                 allows_zero_slack is true
    allows_zero_slack: bool      (optional, default false)
  routes: [{route_id, cost_usd}] candidate routes with frozen costs

expected_output:
  decision: route_id | "abort"
  feasible_routes: [route_id]    EXACT set of routes within hard budget

Candidate output: {"decision": route_id | "abort"}

Derived feasibility (hard constraint):
  spendable = total_usd - spent_usd - safety_reserve_usd
  a route is feasible iff cost_usd > 0 AND cost_usd < spendable, OR
  cost_usd <= spendable when mission_critical is true (mission policy may
  consume down to the reserve) or allows_zero_slack is true.

Negative, zero, or non-numeric route costs in an item are benchmark defects.
Spending beyond the derived feasible set is FAIL (BUDGET_EXCEEDED), never a
judgment call.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import BaseVerifier, VerifierResult, _defect, _fail, _pass


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class BudgetDecisionsVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.budget_decisions"
    CATEGORY = "budget_decisions"

    @staticmethod
    def derive_feasible(budget: Mapping[str, Any], routes: list) -> frozenset:
        spendable = budget["total_usd"] - budget["spent_usd"] - budget["safety_reserve_usd"]
        zero_slack_ok = budget.get("mission_critical") is True or budget.get(
            "allows_zero_slack"
        ) is True
        feasible = set()
        for route in routes:
            cost = route["cost_usd"]
            if cost <= 0:
                continue
            if cost < spendable or (zero_slack_ok and cost <= spendable):
                feasible.add(route["route_id"])
        return frozenset(feasible)

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        defect = super()._check_item(item)
        if defect is not None:
            return defect
        state = item["input_state"]
        budget = state.get("budget")
        if not isinstance(budget, Mapping):
            return _defect("DEFECT_MISSING_BUDGET")
        for key in ("total_usd", "spent_usd", "safety_reserve_usd"):
            if not _is_number(budget.get(key)) or budget[key] < 0:
                return _defect("DEFECT_BAD_BUDGET_FIELD", f"budget.{key}")
        if not isinstance(budget.get("mission_critical"), bool):
            return _defect("DEFECT_BAD_BUDGET_FIELD", "mission_critical: bool")
        if "allows_zero_slack" in budget and not isinstance(
            budget["allows_zero_slack"], bool
        ):
            return _defect("DEFECT_BAD_BUDGET_FIELD", "allows_zero_slack: bool")
        if budget["spent_usd"] > budget["total_usd"]:
            return _defect("DEFECT_OVERSPENT_STATE", "spent_usd > total_usd in input")
        if budget["safety_reserve_usd"] > budget["total_usd"] - budget["spent_usd"]:
            return _defect(
                "DEFECT_RESERVE_EXCEEDS_REMAINING",
                "safety reserve exceeds remaining budget",
            )
        routes = state.get("routes")
        if not isinstance(routes, list) or not routes:
            return _defect("DEFECT_MISSING_ROUTES")
        ids = [r.get("route_id") for r in routes if isinstance(r, Mapping)]
        if len(ids) != len(routes) or None in ids or len(set(ids)) != len(ids):
            return _defect("DEFECT_BAD_ROUTE_IDS")
        for route in routes:
            if not _is_number(route.get("cost_usd")) or route["cost_usd"] <= 0:
                return _defect(
                    "DEFECT_BAD_ROUTE_COST",
                    f"route {route.get('route_id')!r} has non-positive/non-numeric cost",
                )
        return None

    def _derive_expected(
        self, item: Mapping[str, Any]
    ) -> tuple[Any, Optional[VerifierResult]]:
        state = item["input_state"]
        return self.derive_feasible(state["budget"], state["routes"]), None

    def _expected_matches(
        self, expected: Mapping[str, Any], derived: frozenset
    ) -> Optional[VerifierResult]:
        declared = expected.get("feasible_routes")
        if not isinstance(declared, list):
            return _defect("DEFECT_MISSING_FEASIBLE_SET")
        if frozenset(declared) != derived:
            return _defect(
                "EXPECTED_SET_MISMATCH",
                f"expected feasible {sorted(declared)} != derived {sorted(derived)}",
            )
        decision = expected.get("decision")
        if decision == "abort":
            if derived:
                return _defect(
                    "DEFECT_ABORT_WITH_FEASIBLE_ROUTES",
                    "expected decision abort but feasible routes exist",
                )
        elif decision not in derived:
            return _defect(
                "DEFECT_DECISION_INFEASIBLE",
                f"expected decision {decision!r} not in derived feasible set",
            )
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        state = item["input_state"]
        expected = item["expected_output"]
        feasible = self.derive_feasible(state["budget"], state["routes"])
        known_ids = {r["route_id"] for r in state["routes"]}

        decision = candidate_output.get("decision")
        if not isinstance(decision, str) or not decision:
            return _fail("MISSING_DECISION")
        if decision == "abort":
            if expected["decision"] != "abort":
                return _fail(
                    "UNNECESSARY_ABORT",
                    "candidate aborted but expected decision selects a route",
                )
            return _pass()
        if decision not in known_ids:
            return _fail("UNKNOWN_ROUTE", f"route {decision!r} not in input routes")
        if decision not in feasible:
            return _fail(
                "BUDGET_EXCEEDED",
                f"route {decision!r} violates hard budget / safety reserve",
            )
        if decision != expected["decision"]:
            return _fail(
                "SUBOPTIMAL_OR_WRONG_ROUTE",
                f"candidate {decision!r} != expected {expected['decision']!r}",
            )
        return _pass()
