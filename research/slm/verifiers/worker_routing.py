"""worker_routing verifier (VERIFIER_ID: slm00.verifier.worker_routing).

Category contract
-----------------
input_state:
  task: {required_capabilities: [str], required_authority: [str]}  (lists may
        be empty)
  workers: [{worker_id, capabilities: [str], authority: [str],
             available: bool}]
  allowed_actions: [str]  (e.g. ["route", "hold", "escalate"]; optional,
        defaults to ["route","hold","escalate"])

expected_output:
  action: str                       (one of allowed_actions)
  allowed_routes: [worker_id]       (EXACT set of legal route targets; empty
                                     list means no worker may be routed)
  selected_route: worker_id | null  (only meaningful when action == "route";
                                     must be in allowed_routes or null when
                                     the item permits any legal route)

Candidate output: {"action": str, "route": worker_id | null}

Checks: capability constraint satisfaction, authority compatibility, route
legality (known worker, in allowed set), worker availability, action legality.
The exact allowed route set is derived independently from input_state; a
mismatch with the frozen expected allowed_routes is a BENCHMARK_DEFECT, never
silently repaired.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import BaseVerifier, VerifierResult, _defect, _fail, _pass

DEFAULT_ACTIONS = ("route", "hold", "escalate")


class WorkerRoutingVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.worker_routing"
    CATEGORY = "worker_routing"

    @staticmethod
    def derive_legal_routes(input_state: Mapping[str, Any]) -> frozenset:
        """Exact legal route set: capability + authority + availability."""
        task = input_state.get("task") or {}
        req_caps = set(task.get("required_capabilities") or [])
        req_auth = set(task.get("required_authority") or [])
        legal = set()
        for worker in input_state.get("workers") or []:
            if not isinstance(worker, Mapping):
                continue
            if worker.get("available") is not True:
                continue
            if not req_caps.issubset(set(worker.get("capabilities") or [])):
                continue
            if not req_auth.issubset(set(worker.get("authority") or [])):
                continue
            legal.add(worker.get("worker_id"))
        return frozenset(legal)

    def _derive_expected(
        self, item: Mapping[str, Any]
    ) -> tuple[Any, Optional[VerifierResult]]:
        state = item["input_state"]
        workers = state.get("workers")
        if not isinstance(workers, list):
            return None, _defect("DEFECT_MISSING_WORKERS", "input_state.workers must be a list")
        ids = [w.get("worker_id") for w in workers if isinstance(w, Mapping)]
        if len(ids) != len(set(ids)):
            return None, _defect("DEFECT_DUPLICATE_WORKER_ID")
        task = state.get("task")
        if not isinstance(task, Mapping):
            return None, _defect("DEFECT_MISSING_TASK", "input_state.task must be an object")
        return self.derive_legal_routes(state), None

    def _expected_matches(
        self, expected: Mapping[str, Any], derived: Any
    ) -> Optional[VerifierResult]:
        declared = expected.get("allowed_routes")
        if not isinstance(declared, list):
            return _defect(
                "DEFECT_MISSING_ALLOWED_ROUTES",
                "expected_output.allowed_routes must be an exact list",
            )
        if len(declared) != len(set(declared)):
            return _defect("DEFECT_DUPLICATE_ALLOWED_ROUTE")
        if frozenset(declared) != derived:
            return _defect(
                "EXPECTED_SET_MISMATCH",
                f"expected allowed_routes {sorted(declared)} != derived "
                f"legal set {sorted(derived)}",
            )
        action = expected.get("action")
        if action not in DEFAULT_ACTIONS:
            return _defect(
                "DEFECT_ILLEGAL_EXPECTED_ACTION",
                f"expected action {action!r} not in allowed actions",
            )
        if action == "route" and not derived:
            return _defect(
                "DEFECT_ROUTE_WITHOUT_LEGAL_TARGET",
                "expected action 'route' but no legal route exists",
            )
        selected = expected.get("selected_route", None)
        if action == "route" and selected is not None and selected not in derived:
            return _defect(
                "DEFECT_SELECTED_ROUTE_ILLEGAL",
                f"expected selected_route {selected!r} not in legal set",
            )
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        state = item["input_state"]
        expected = item["expected_output"]
        workers = {w["worker_id"]: w for w in state["workers"]}

        action = candidate_output.get("action")
        if action not in DEFAULT_ACTIONS:
            return _fail("UNKNOWN_ACTION", f"action {action!r} not in {DEFAULT_ACTIONS}")
        route = candidate_output.get("route")

        if action == "route":
            if not isinstance(route, str) or not route:
                return _fail("MISSING_ROUTE", "action 'route' requires a worker_id")
            if route not in workers:
                return _fail("ROUTE_UNKNOWN_WORKER", f"unknown worker {route!r}")
            worker = workers[route]
            if worker.get("available") is not True:
                return _fail("WORKER_UNAVAILABLE", f"worker {route!r} unavailable")
            task = state["task"]
            req_caps = set(task.get("required_capabilities") or [])
            if not req_caps.issubset(set(worker.get("capabilities") or [])):
                return _fail(
                    "CAPABILITY_MISMATCH",
                    f"worker {route!r} lacks capabilities "
                    f"{sorted(req_caps - set(worker.get('capabilities') or []))}",
                )
            req_auth = set(task.get("required_authority") or [])
            if not req_auth.issubset(set(worker.get("authority") or [])):
                return _fail(
                    "AUTHORITY_MISMATCH",
                    f"worker {route!r} lacks authority "
                    f"{sorted(req_auth - set(worker.get('authority') or []))}",
                )
            if route not in set(expected["allowed_routes"]):
                return _fail(
                    "ROUTE_NOT_IN_ALLOWED_SET",
                    f"route {route!r} outside frozen allowed set",
                )
            selected = expected.get("selected_route")
            if selected is not None and route != selected:
                return _fail(
                    "WRONG_ROUTE",
                    f"route {route!r} != required selected_route {selected!r}",
                )
            return _pass()
        # hold / escalate
        if route is not None:
            return _fail(
                "UNEXPECTED_ROUTE",
                f"action {action!r} must not carry a route target",
            )
        if action != expected.get("action"):
            return _fail(
                "WRONG_ACTION",
                f"action {action!r} != expected {expected.get('action')!r}",
            )
        return _pass()
