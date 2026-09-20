"""StationLM provider adapter: advisory decision pipeline, fail-closed.

Pipeline per decision:

    Station -> StationLMProvider -> DecisionModel backend
             -> schema validation -> policy verification -> receipt

The model proposes; the Station decides. Every model-side failure class
(schema-invalid output, policy violation, missing artifact, timeout,
latched rollback trigger) fails CLOSED to deterministic/default routing and
emits a receipt recording the fallback. No model failure raises through to
the Station caller; only caller-side contract misuse raises.

The adapter structurally implements the repo's ``ai_providers.core.Provider``
protocol surface (chat/stream/achat/astream/list_models/supports_tools) so a
shadow router can treat it like any other provider. ``supports_tools`` is
always False: advisory decisions never execute tools.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Iterator, Optional

from residual.core import ContractError, canonical, digest, strict_json
from ai_providers.core import (
    ChatRequest, ChatResponse, ProviderError, StreamChunk,
)

from .decision_model import (
    DECISION_SCHEMA_VERSION, DecisionModel, DecisionProposal, DecisionRequest,
    default_policy, validate_proposal,
)
from .rollback import RollbackMonitor

RECEIPT_SCHEMA = "residual.station_lm.receipt.v1"


@dataclass(frozen=True)
class DecisionReceipt:
    """Every decision — accepted or fallback — is receipted."""

    task_id: str
    request_digest: str
    model_id: str
    manifest_digest: str
    outcome: str  # "accepted" | "fallback"
    fallback_reason: Optional[str]
    proposal: Optional[dict]
    elapsed_ms: int
    advisory: bool = True

    def payload(self) -> dict:
        return {"schema": RECEIPT_SCHEMA, "task_id": self.task_id,
                "request_digest": self.request_digest, "model_id": self.model_id,
                "manifest_digest": self.manifest_digest, "outcome": self.outcome,
                "fallback_reason": self.fallback_reason, "proposal": self.proposal,
                "elapsed_ms": self.elapsed_ms, "advisory": True}

    @property
    def receipt_hash(self) -> str:
        return hashlib.sha256(
            (RECEIPT_SCHEMA + "\n" + canonical(self.payload())).encode()).hexdigest()

    def to_dict(self) -> dict:
        return {**self.payload(), "receipt_hash": self.receipt_hash}


@dataclass(frozen=True)
class AdvisoryResult:
    """What the Station receives. Never authoritative on its own."""

    proposal: DecisionProposal
    receipt: DecisionReceipt
    fallback: bool

    def to_dict(self) -> dict:
        return {"schema": DECISION_SCHEMA_VERSION, "fallback": self.fallback,
                "proposal": self.proposal.to_dict(), "receipt": self.receipt.to_dict()}


class StationLMProvider:
    """Advisory decision provider. Fail-closed by construction."""

    name = "station_lm"

    def __init__(self, backend: Optional[DecisionModel], *, default_route: str,
                 policy: Optional[Callable[[dict, DecisionProposal], Optional[str]]] = None,
                 monitor: Optional[RollbackMonitor] = None,
                 clock=None):
        if not isinstance(default_route, str) or not default_route:
            raise ContractError("a deterministic default_route is required")
        self.backend = backend
        self.default_route = default_route
        self.policy = policy if policy is not None else default_policy
        self.monitor = monitor
        self._clock = clock or time.monotonic
        self.receipts: list[DecisionReceipt] = []

    # -- internal helpers ----------------------------------------------------

    def _manifest_digest(self) -> str:
        if self.backend is None:
            return "0" * 64
        try:
            return digest(self.backend.manifest())
        except Exception:
            return "0" * 64

    def _model_id(self) -> str:
        if self.backend is None:
            return "station-lm-unavailable"
        try:
            return self.backend.model_id
        except Exception:
            return "station-lm-unavailable"

    def _fallback(self, request: DecisionRequest, reason: str,
                  start: float) -> AdvisoryResult:
        """Deterministic default routing, escalated, receipted."""
        elapsed = int((self._clock() - start) * 1000)
        proposal = DecisionProposal(
            route=(self.default_route if self.default_route in request.allowed_routes
                   else request.allowed_routes[0]),
            confidence=0.0, escalate=True,
            rationale=f"fail-closed fallback: {reason}",
            model_id=self._model_id())
        receipt = DecisionReceipt(
            task_id=request.task_id, request_digest=request.request_digest,
            model_id=self._model_id(), manifest_digest=self._manifest_digest(),
            outcome="fallback", fallback_reason=reason,
            proposal=proposal.to_dict(), elapsed_ms=elapsed)
        self.receipts.append(receipt)
        return AdvisoryResult(proposal=proposal, receipt=receipt, fallback=True)

    # -- primary Station-facing API ------------------------------------------

    def decide(self, request: DecisionRequest) -> AdvisoryResult:
        """Produce an advisory decision. Never raises for model-side failures."""
        if not isinstance(request, DecisionRequest):
            raise ContractError("decide requires a DecisionRequest")
        start = self._clock()
        if self.monitor is not None and self.monitor.triggered:
            return self._fallback(request, "rollback_triggered", start)
        if self.backend is None:
            return self._fallback(request, "missing_model_artifact", start)
        try:
            available = self.backend.available()
        except Exception:
            available = False
        if not available:
            result = self._fallback(request, "missing_model_artifact", start)
        else:
            try:
                raw = self.backend.decide(request)
            except Exception:
                return self._finish(request, self._fallback(request, "backend_error", start))
            elapsed_ms = (self._clock() - start) * 1000
            if elapsed_ms > request.deadline_ms:
                result = self._fallback(request, "timeout", start)
            else:
                try:
                    proposal = validate_proposal(raw, request)
                except ContractError:
                    result = self._fallback(request, "schema_invalid", start)
                else:
                    proposal = DecisionProposal(
                        route=proposal.route, confidence=proposal.confidence,
                        escalate=proposal.escalate, rationale=proposal.rationale,
                        model_id=self._model_id())
                    violation = self.policy(raw, proposal)
                    if violation is not None:
                        result = self._fallback(request, "policy_violation", start)
                    else:
                        receipt = DecisionReceipt(
                            task_id=request.task_id,
                            request_digest=request.request_digest,
                            model_id=self._model_id(),
                            manifest_digest=self._manifest_digest(),
                            outcome="accepted", fallback_reason=None,
                            proposal=proposal.to_dict(),
                            elapsed_ms=int(elapsed_ms))
                        self.receipts.append(receipt)
                        result = AdvisoryResult(proposal=proposal, receipt=receipt,
                                                fallback=False)
        return self._finish(request, result)

    def _finish(self, request: DecisionRequest, result: AdvisoryResult) -> AdvisoryResult:
        if self.monitor is not None:
            self.monitor.record(result.receipt)
        return result

    # -- ai_providers.core.Provider protocol surface --------------------------

    def _request_from_chat(self, req: ChatRequest) -> DecisionRequest:
        if not isinstance(req, ChatRequest):
            raise ProviderError(provider="router", code="invalid_request")
        try:
            packet = strict_json(req.messages[-1].content)
            if not isinstance(packet, dict):
                raise ValueError()
        except (ValueError, TypeError):
            raise ProviderError(provider="router", code="invalid_request") from None
        routes = packet.get("allowed_routes") or [self.default_route]
        task_id = packet.get("task_id", "stationlmchat")
        try:
            return DecisionRequest(
                task_id=task_id if isinstance(task_id, str) else "stationlmchat",
                packet={k: v for k, v in packet.items()
                        if k not in {"task_id", "allowed_routes"}},
                allowed_routes=tuple(routes), context={},
                deadline_ms=req.extra.get("deadline_ms", 2000)
                if isinstance(req.extra, dict) else 2000)
        except ContractError:
            raise ProviderError(provider="router", code="invalid_request") from None

    def chat(self, req: ChatRequest) -> ChatResponse:
        """Advisory decision as a ChatResponse so a Router can shadow it.

        Fail-closed: model-side failures return the fallback decision payload,
        they do not raise. Caller-contract misuse raises ProviderError.
        """
        request = self._request_from_chat(req)
        result = self.decide(request)
        return ChatResponse(model=self._model_id(), content=canonical(result.to_dict()),
                            finish_reason="stop", usage={},
                            metadata={"advisory": True, "fallback": result.fallback,
                                      "receipt_hash": result.receipt.receipt_hash})

    def stream(self, req: ChatRequest) -> Iterator[StreamChunk]:
        resp = self.chat(req)
        yield StreamChunk(content=resp.content, finish_reason="stop", usage={})

    async def achat(self, req: ChatRequest) -> ChatResponse:
        return await asyncio.to_thread(self.chat, req)

    async def astream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]:
        resp = await self.achat(req)
        yield StreamChunk(content=resp.content, finish_reason="stop", usage={})

    def list_models(self) -> list[str]:
        return [self._model_id()] if self.backend is not None else []

    def supports_tools(self, model: str) -> bool:
        # Advisory decisions never execute tools.
        return False
