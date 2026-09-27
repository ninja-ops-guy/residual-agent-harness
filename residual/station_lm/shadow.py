"""Shadow-mode advisory routing hook.

Both the authoritative router and StationLM produce decisions; ONLY the
authoritative decision is acted on. StationLM output is logged, paired with
the authoritative outcome, for later SLM-08 disagreement analysis. Any
StationLM failure inside the hook is contained: it degrades to a logged
fallback pair, never to an exception crossing into the authoritative path.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from residual.core import ContractError, canonical, digest

from .decision_model import DecisionRequest
from .provider import StationLMProvider


@dataclass(frozen=True)
class PairedDecision:
    """One shadow observation: authoritative vs advisory, side by side."""

    request_digest: str
    task_id: str
    authoritative_route: str
    advisory_route: Optional[str]
    advisory_escalate: Optional[bool]
    advisory_fallback: bool
    advisory_receipt_hash: Optional[str]
    agreement: Optional[bool]
    elapsed_ms: int

    def to_dict(self) -> dict:
        return {"request_digest": self.request_digest, "task_id": self.task_id,
                "authoritative_route": self.authoritative_route,
                "advisory_route": self.advisory_route,
                "advisory_escalate": self.advisory_escalate,
                "advisory_fallback": self.advisory_fallback,
                "advisory_receipt_hash": self.advisory_receipt_hash,
                "agreement": self.agreement, "elapsed_ms": self.elapsed_ms}


class ShadowModeHook:
    """Wrap the authoritative decider with an advisory shadow path."""

    def __init__(self, authoritative: Callable[[DecisionRequest], str],
                 station_lm: StationLMProvider,
                 sink: Optional[Callable[[dict], None]] = None):
        if not callable(authoritative):
            raise ContractError("authoritative decider must be callable")
        if not isinstance(station_lm, StationLMProvider):
            raise ContractError("station_lm must be a StationLMProvider")
        self.authoritative = authoritative
        self.station_lm = station_lm
        self.sink = sink
        self.pairs: list[PairedDecision] = []

    def decide(self, request: DecisionRequest) -> str:
        """Return the AUTHORITATIVE route. Advisory output is never returned."""
        if not isinstance(request, DecisionRequest):
            raise ContractError("decide requires a DecisionRequest")
        start = time.monotonic()
        # Authoritative path first and unconditioned on the model.
        route = self.authoritative(request)
        if not isinstance(route, str) or route not in request.allowed_routes:
            raise ContractError("authoritative decider returned an invalid route")
        advisory_route = advisory_escalate = receipt_hash = agreement = None
        advisory_fallback = True
        try:
            result = self.station_lm.decide(request)
            advisory_route = result.proposal.route
            advisory_escalate = result.proposal.escalate
            advisory_fallback = result.fallback
            receipt_hash = result.receipt.receipt_hash
            agreement = (not result.fallback) and advisory_route == route
        except Exception:
            # Contain any advisory-path failure; the authoritative result stands.
            advisory_route, advisory_escalate, receipt_hash, agreement = None, None, None, None
        pair = PairedDecision(
            request_digest=request.request_digest, task_id=request.task_id,
            authoritative_route=route, advisory_route=advisory_route,
            advisory_escalate=advisory_escalate, advisory_fallback=advisory_fallback,
            advisory_receipt_hash=receipt_hash, agreement=agreement,
            elapsed_ms=int((time.monotonic() - start) * 1000))
        self.pairs.append(pair)
        if self.sink is not None:
            self.sink(pair.to_dict())
        return route

    def disagreement_report(self) -> dict:
        """Aggregate for SLM-08 analysis."""
        scored = [p for p in self.pairs if p.agreement is not None]
        return {"pairs": len(self.pairs), "scored": len(scored),
                "agreements": sum(1 for p in scored if p.agreement),
                "advisory_fallbacks": sum(1 for p in self.pairs if p.advisory_fallback),
                "pairs_digest": digest([p.to_dict() for p in self.pairs])}
