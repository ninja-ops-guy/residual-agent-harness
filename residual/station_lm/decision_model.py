"""StationLM decision-model backends (advisory only, no execution authority).

Core invariant: the model proposes; the Station decides. A ``DecisionModel``
returns a raw advisory proposal. It is ``StationLMProvider`` — never the
backend — that validates schema, verifies policy, and emits a receipt.

Backends are swappable: ``FakeDecisionModel`` implements the ``DecisionModel``
protocol so the integration is testable before real weights exist. Future
PyTorch / llama.cpp / ONNX runtimes implement the same protocol.
"""
from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from residual.core import ContractError, canonical, digest, identifier

DECISION_SCHEMA_VERSION = "residual.station_lm.decision.v1"

# Raw proposal keys the model is allowed to emit. Anything outside this set —
# in particular anything that smells like execution authority — is a policy
# violation and forces a fail-closed fallback.
PROPOSAL_KEYS = {"route", "confidence", "escalate", "rationale"}

# Keys a model output must never contain. Presence alone is an authority
# violation regardless of value.
AUTHORITY_KEYS = {"execute", "authority", "act", "commit", "bypass", "approve_self"}

DEFAULT_DEADLINE_MS = 2000
MAX_RATIONALE_CHARS = 2000


@dataclass(frozen=True)
class DecisionRequest:
    """Station-issued advisory request. The model sees only this."""

    task_id: str
    packet: dict[str, Any]
    allowed_routes: tuple[str, ...]
    context: dict[str, Any] = field(default_factory=dict)
    deadline_ms: int = DEFAULT_DEADLINE_MS

    def __post_init__(self):
        identifier(self.task_id)
        if not isinstance(self.packet, dict) or not isinstance(self.context, dict):
            raise ContractError("decision request packet/context must be objects")
        canonical(self.packet)
        canonical(self.context)
        if (not isinstance(self.allowed_routes, (tuple, list)) or not self.allowed_routes
                or len(set(self.allowed_routes)) != len(self.allowed_routes)
                or any(not isinstance(r, str) or not r for r in self.allowed_routes)):
            raise ContractError("allowed_routes must be distinct nonempty strings")
        if type(self.deadline_ms) is not int or not 1 <= self.deadline_ms <= 60000:
            raise ContractError("deadline_ms must be 1-60000")

    @property
    def request_digest(self) -> str:
        return digest({"schema": DECISION_SCHEMA_VERSION, "task_id": self.task_id,
                       "packet": self.packet, "allowed_routes": list(self.allowed_routes),
                       "context": self.context})


@dataclass(frozen=True)
class DecisionProposal:
    """Validated, policy-clean advisory proposal. Still non-authoritative."""

    route: str
    confidence: float
    escalate: bool
    rationale: str
    model_id: str
    advisory: bool = True  # always True; the model never decides

    def to_dict(self) -> dict:
        return {"route": self.route, "confidence": self.confidence,
                "escalate": self.escalate, "rationale": self.rationale,
                "model_id": self.model_id, "advisory": True}


class DecisionModel(Protocol):
    """Swappable backend contract (fake, PyTorch, llama.cpp, ONNX, ...)."""

    @property
    def model_id(self) -> str: ...

    def manifest(self) -> dict[str, Any]:
        """Manifest fields used for receipt attribution (see model_registry)."""
        ...

    def available(self) -> bool:
        """False when the model artifact is missing/corrupt -> fail closed."""
        ...

    def decide(self, request: DecisionRequest) -> dict[str, Any]:
        """Return a raw JSON-able proposal. May be malformed; the provider
        validates. Must never block past ``request.deadline_ms``."""
        ...


def validate_proposal(raw: Any, request: DecisionRequest) -> DecisionProposal:
    """Strict schema validation. Any deviation raises ContractError."""
    if not isinstance(raw, dict) or set(raw) - PROPOSAL_KEYS:
        raise ContractError("proposal has unknown or non-object keys")
    if set(raw) != PROPOSAL_KEYS:
        raise ContractError("proposal is missing required keys")
    route, confidence, escalate, rationale = (
        raw["route"], raw["confidence"], raw["escalate"], raw["rationale"])
    if route not in request.allowed_routes:
        raise ContractError("proposal route outside allowed routes")
    if (type(confidence) not in (int, float) or not math.isfinite(confidence)
            or not 0.0 <= confidence <= 1.0):
        raise ContractError("proposal confidence must be a finite number in [0,1]")
    if type(escalate) is not bool:
        raise ContractError("proposal escalate must be boolean")
    if not isinstance(rationale, str) or len(rationale) > MAX_RATIONALE_CHARS:
        raise ContractError("proposal rationale must be bounded text")
    return DecisionProposal(route=route, confidence=float(confidence),
                            escalate=escalate, rationale=rationale, model_id="")


def default_policy(raw: dict[str, Any], proposal: DecisionProposal) -> Optional[str]:
    """Authoritative-side policy verification. Returns a violation reason or None.

    This check runs in RESIDUAL, not in the model; it is the policy gate the
    model cannot bypass.
    """
    lowered = {str(k).lower() for k in raw}
    if lowered & AUTHORITY_KEYS:
        return "authority_violation"
    if proposal.escalate and not proposal.rationale.strip():
        return "escalation_without_rationale"
    return None


class FakeDecisionModel:
    """Deterministic, seeded, rule-based backend for pre-weights integration tests.

    Decisions are a pure function of (seed, request digest), so repeated runs
    are reproducible regardless of call order. ``mode`` injects failure classes
    so the fail-closed pipeline can be exercised without a real model:

    - ``"ok"``                  deterministic valid proposals
    - ``"invalid_schema"``      emits structurally invalid output
    - ``"authority_violation"`` emits an output claiming execution authority
    - ``"non_escalation"``      valid schema but never escalates (risk probe)
    - ``"timeout"``             exceeds the request deadline
    - ``"missing_artifact"``    ``available()`` is False
    """

    MODES = {"ok", "invalid_schema", "authority_violation", "non_escalation",
             "timeout", "missing_artifact"}

    def __init__(self, seed: int = 0, model_id: str = "fake-decision-v0",
                 mode: str = "ok", canned: Optional[dict[str, dict]] = None,
                 latency_ms: int = 0):
        if type(seed) is not int or seed < 0:
            raise ContractError("seed must be a nonnegative integer")
        identifier(model_id)
        if mode not in self.MODES:
            raise ContractError("unknown fake decision mode")
        if canned is not None and (not isinstance(canned, dict)
                                   or any(not isinstance(k, str) for k in canned)):
            raise ContractError("canned decisions must be keyed by request digest")
        if type(latency_ms) is not int or latency_ms < 0:
            raise ContractError("latency_ms must be a nonnegative integer")
        self._seed, self._model_id, self.mode = seed, model_id, mode
        self.canned = dict(canned or {})
        self.latency_ms = latency_ms

    @property
    def model_id(self) -> str:
        return self._model_id

    def manifest(self) -> dict[str, Any]:
        # Hashes are deterministic stand-ins for artifact digests.
        def h(label: str) -> str:
            return hashlib.sha256(f"{self._model_id}:{self._seed}:{label}".encode()).hexdigest()
        return {"model_id": self._model_id, "model_hash": h("weights"),
                "tokenizer_hash": h("tokenizer"), "dataset_manifest_hash": h("dataset"),
                "training_config": {"seed": self._seed, "backend": "fake", "rules": "canned"},
                "code_commit": "0" * 40, "seed": self._seed, "qualification_receipt": None,
                "model_card": {"name": self._model_id, "version": "0",
                               "intended_use": "integration testing only",
                               "limitations": "rule-based canned decisions; not a learned model"}}

    def available(self) -> bool:
        return self.mode != "missing_artifact"

    def _draw(self, request: DecisionRequest, label: str) -> int:
        material = f"{self._seed}:{request.request_digest}:{label}".encode()
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    def decide(self, request: DecisionRequest) -> dict[str, Any]:
        if not isinstance(request, DecisionRequest):
            raise ContractError("decide requires a DecisionRequest")
        if self.mode == "timeout":
            time.sleep((request.deadline_ms + 50) / 1000.0)
        elif self.latency_ms:
            time.sleep(self.latency_ms / 1000.0)
        canned = self.canned.get(request.request_digest)
        if canned is not None:
            return dict(canned)
        if self.mode == "invalid_schema":
            return {"route": request.allowed_routes[0], "confidence": "high"}  # wrong type/keys
        if self.mode == "authority_violation":
            return {"route": request.allowed_routes[0], "confidence": 1.0,
                    "escalate": False, "rationale": "acting directly",
                    "execute": True}
        draw = self._draw(request, "route")
        route = request.allowed_routes[draw % len(request.allowed_routes)]
        confidence = (self._draw(request, "confidence") % 1000) / 1000.0
        escalate = confidence < 0.5 and self.mode != "non_escalation"
        return {"route": route, "confidence": confidence, "escalate": escalate,
                "rationale": f"seeded-rule:{self._seed}"}
