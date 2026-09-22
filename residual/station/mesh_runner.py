"""Bounded mesh runner joining Station authority to a qualified claw adapter."""
from __future__ import annotations

import hashlib
import uuid

from residual.core import ContractError, canonical, strict_json


def _placement_for_route(route):
    if route == "local":
        return "local"
    if route == "cloud":
        return "remote"
    raise ContractError("Unknown task route")


def provider_plan(work, routes, request_bytes):
    policy = work["packet"].get("execution_policy") or {}
    placements = policy.get("placements") or [_placement_for_route(work["route"])]
    models = policy.get("models") or []
    maximum = policy.get("max_provider_attempts", 1)
    cross = policy.get("cross_placement", False)
    wanted = _placement_for_route(work["route"])
    eligible = []
    for route in routes:
        if not isinstance(route, dict) or set(route) != {"placement", "model"}:
            raise ContractError("Configured claw provider route is invalid")
        if route["placement"] not in {"local", "remote"}:
            raise ContractError("Configured claw provider placement is invalid")
        if not isinstance(route["model"], str) or not route["model"]:
            raise ContractError("Configured claw model is invalid")
        if route["placement"] not in placements:
            continue
        if models and route["model"] not in models:
            continue
        eligible.append(route)
    same = [x for x in eligible if x["placement"] == wanted]
    other = [x for x in eligible if x["placement"] != wanted] if cross else []
    ordered = (same + other)[:maximum]
    if not ordered:
        raise ContractError("No configured claw provider route satisfies the task execution policy")
    return [{"placement": x["placement"], "model": x["model"], "request_bytes": request_bytes}
            for x in ordered]


def normalized_openclaw_usage(value, model, placement, request_bytes):
    if not isinstance(value, dict):
        value = {}
    inp = value.get("input", value.get("prompt_tokens"))
    out = value.get("output", value.get("completion_tokens"))
    cached = value.get("cacheRead", value.get("cached_prompt_tokens", 0))
    written = value.get("cacheWrite", value.get("cache_write_prompt_tokens", 0))
    counters = [inp, out, cached, written]
    known = inp is not None and out is not None and all(
        v is None or (type(v) is int and v >= 0) for v in counters)
    return {
        "input_tokens": inp if known else None,
        "output_tokens": out if known else None,
        "cached_input_tokens": cached if known else None,
        "cache_write_input_tokens": written if known else None,
        "source": "worker_reported",
        "placement": placement,
        "role": "mesh_runner",
        "model": model,
        "request_bytes": request_bytes,
    }


class MeshClawRunner:
    def __init__(self, client, adapter, *, project_id, provider_routes, max_request_bytes=500_000):
        if not isinstance(provider_routes, list) or not provider_routes:
            raise ContractError("Mesh claw runner requires explicit provider routes")
        if type(max_request_bytes) is not int or not 1 <= max_request_bytes <= 5_000_000:
            raise ContractError("Invalid mesh runner request-byte bound")
        self.client = client
        self.adapter = adapter
        self.project_id = project_id
        self.provider_routes = provider_routes
        self.max_request_bytes = max_request_bytes
        self.current = None
        self.current_assignment_id = None

    def synchronize(self):
        self.client.recover_outbox()
        return self.client.sync(self.project_id)

    def run_once(self):
        snapshot = self.client.snapshots.get(self.project_id) or self.synchronize()
        work = self.client.claim(self.project_id)
        if not work:
            return False
        self.current = work
        packet_bytes = len(canonical(work["packet"]).encode("utf-8"))
        # Bound includes wrapper/system text and implementation variance; admission
        # is intentionally conservative rather than using an optimistic estimate.
        request_bound = min(self.max_request_bytes, packet_bytes + 64_000)
        plan = provider_plan(work, self.provider_routes, request_bound)
        self.client.execution_admit(work, plan)
        assignment_id = (
            f"{work['project_id']}:{work['task_id']}:{work['attempt']}:"
            f"{work['fencing_token']}:{uuid.uuid4().hex[:12]}"
        )
        self.current_assignment_id = assignment_id
        try:
            execution = self.adapter.execute({
                "assignment_id": assignment_id,
                "packet": work["packet"],
                "provider_plan": plan,
            })
            response = strict_json(execution.text)
            if not isinstance(response, dict) or set(response) != {"files"}:
                raise ContractError("Claw response must contain exactly the files object")
            winner = next((x for x in plan
                           if x["model"] in {execution.model, f"{execution.provider}/{execution.model}"}),
                          plan[-1])
            usage = normalized_openclaw_usage(
                execution.usage, winner["model"], winner["placement"], winner["request_bytes"])
            attempts = list(execution.provider_attempts) if execution.provider_attempts else None
            return self.client.submit_result(
                work,
                submission_id=hashlib.sha256(assignment_id.encode()).hexdigest(),
                response=response,
                usage=usage,
                provider_attempts=attempts,
            )
        except Exception:
            # No blind replay after execution begins. Authority expires naturally or
            # an operator/Station stop path cancels and reconciles the attempt.
            try:
                self.adapter.cancel(assignment_id)
            except Exception:
                pass
            raise
        finally:
            self.current = None
            self.current_assignment_id = None

    def cancel_current(self):
        if not self.current_assignment_id:
            return {"requested": False, "observed_stopped": True}
        return self.adapter.cancel(self.current_assignment_id)

    def shutdown(self):
        return self.adapter.shutdown()
