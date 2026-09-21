"""Shadow-mode wiring between the Station service and StationLM advisory.

This module is the single integration point: the Station service hands the
route-selection decision to ``StationShadowIntegration.decide_route`` when
(and only when) shadow mode is config-gated on. The authoritative,
deterministic decider always runs first and its result is what the Station
acts on. The StationLM advisory path observes the request only when the
canary admits it; its output is paired with the authoritative outcome and
logged, never returned. A RollbackMonitor latch short-circuits to
deterministic/default routing and the fallback is receipted.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from residual.core import ContractError, digest

from .canary import CanaryRollout, DEFAULT_STEPS
from .decision_model import DecisionRequest
from .model_registry import ModelRegistry
from .provider import StationLMProvider
from .rollback import RollbackMonitor
from .shadow import ShadowModeHook

FALLBACK_SCHEMA = "residual.station_lm.shadow_fallback.v1"


class StationShadowIntegration:
    """Owns the shadow hook, canary rollout, and rollback wiring."""

    def __init__(self, *, provider: StationLMProvider, registry: ModelRegistry,
                 model_id: str, monitor: RollbackMonitor,
                 canary_steps=DEFAULT_STEPS,
                 sink: Optional[Callable[[str, dict], None]] = None):
        if not isinstance(provider, StationLMProvider):
            raise ContractError("provider must be a StationLMProvider")
        self.provider = provider
        self.monitor = monitor
        self.canary = CanaryRollout(registry, model_id, monitor, steps=canary_steps)
        self.sink = sink
        self.pairs: list = []
        self.fallback_receipts: list[dict] = []

    def _emit(self, event: str, payload: dict) -> None:
        if self.sink is not None:
            self.sink(event, payload)

    def _fallback_receipt(self, request: DecisionRequest, route: str, reason: str) -> dict:
        payload = {"schema": FALLBACK_SCHEMA, "task_id": request.task_id,
                   "request_digest": request.request_digest,
                   "route": route, "reason": reason,
                   "seq": len(self.fallback_receipts),
                   "previous": (self.fallback_receipts[-1]["receipt_hash"]
                                if self.fallback_receipts else "0" * 64)}
        receipt = {**payload, "receipt_hash": digest(payload)}
        self.fallback_receipts.append(receipt)
        self._emit("station_lm.fallback", receipt)
        return receipt

    def decide_route(self, request: DecisionRequest,
                     authoritative: Callable[[DecisionRequest], str]) -> str:
        """Return the AUTHORITATIVE route. Advisory output is never returned.

        Fail-closed order:
          1. RollbackMonitor latch -> deterministic fallback, receipted.
          2. Canary gate -> advisory path skipped; authoritative stands.
          3. ShadowModeHook -> paired advisory decision logged; any advisory
             exception is contained inside the hook.
        """
        if not isinstance(request, DecisionRequest):
            raise ContractError("decide_route requires a DecisionRequest")
        if not callable(authoritative):
            raise ContractError("authoritative decider must be callable")
        if self.monitor.triggered:
            route = authoritative(request)
            if not isinstance(route, str) or route not in request.allowed_routes:
                raise ContractError("authoritative decider returned an invalid route")
            self.canary.demote(f"rollback_triggered:{self.monitor.trigger.condition}")
            self._fallback_receipt(request, route,
                                   f"rollback_triggered:{self.monitor.trigger.condition}")
            return route
        if not self.canary.admit(request.request_digest):
            route = authoritative(request)
            if not isinstance(route, str) or route not in request.allowed_routes:
                raise ContractError("authoritative decider returned an invalid route")
            return route
        hook = ShadowModeHook(
            authoritative, self.provider,
            sink=lambda pair: self._emit("station_lm.shadow_pair", pair))
        route = hook.decide(request)
        self.pairs.extend(hook.pairs)
        return route

    def report(self) -> dict:
        scored = [p for p in self.pairs if p.agreement is not None]
        return {"pairs": len(self.pairs), "scored": len(scored),
                "agreements": sum(1 for p in scored if p.agreement),
                "canary_percent": self.canary.percent,
                "canary_demoted": self.canary.demoted,
                "monitor_triggered": self.monitor.triggered,
                "fallback_receipts": len(self.fallback_receipts),
                "pairs_digest": digest([p.to_dict() for p in self.pairs])}
