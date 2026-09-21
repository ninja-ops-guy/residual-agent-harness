"""Canary advisory rollout for qualified StationLM models.

A model may serve a small, deterministic fraction of advisory traffic ONLY
when it is ``qualified`` in the registry with a valid qualification receipt.
Exposure is keyed on the request digest, so rollout percentages are
reproducible and monotone (the 1% bucket is a subset of the 5% bucket).
Any RollbackMonitor latch demotes the canary to 0% immediately; demotion is
latching and receipted. Advisory traffic never gains execution authority:
the canary only decides whether the shadow/advisory path OBSERVES a request.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from residual.core import ContractError, digest

from .model_registry import ModelRegistry
from .rollback import RollbackMonitor

CANARY_SCHEMA = "residual.station_lm.canary.v1"
DEFAULT_STEPS = (1, 5)


class CanaryRollout:
    """Deterministic percentage rollout of advisory traffic for one model."""

    def __init__(self, registry: ModelRegistry, model_id: str,
                 monitor: RollbackMonitor, *, steps=DEFAULT_STEPS):
        if not isinstance(registry, ModelRegistry):
            raise ContractError("canary requires a ModelRegistry")
        from residual.core import identifier
        identifier(model_id)
        if not isinstance(monitor, RollbackMonitor):
            raise ContractError("canary requires a RollbackMonitor")
        if (not isinstance(steps, (tuple, list)) or not steps
                or any(type(s) is not int or not 0 < s <= 100 for s in steps)
                or list(steps) != sorted(set(steps))):
            raise ContractError("steps must be distinct increasing integers in 1-100")
        self.registry = registry
        self.model_id = model_id
        self.monitor = monitor
        self.steps = tuple(steps)
        self._step = 0
        self._demotion: Optional[dict] = None
        self.receipts: list[dict] = []

    # -- receipts -------------------------------------------------------------

    def _receipt(self, action: str, reason: str, percent: int) -> dict:
        payload = {"schema": CANARY_SCHEMA, "model_id": self.model_id,
                   "action": action, "reason": reason, "percent": percent,
                   "seq": len(self.receipts),
                   "previous": self.receipts[-1]["receipt_hash"] if self.receipts else "0" * 64}
        receipt = {**payload, "receipt_hash": digest(payload)}
        self.receipts.append(receipt)
        return receipt

    # -- state -----------------------------------------------------------------

    @property
    def percent(self) -> int:
        return 0 if self._demotion is not None else self.steps[self._step]

    @property
    def demoted(self) -> bool:
        return self._demotion is not None

    @property
    def demotion_receipt(self) -> Optional[dict]:
        return self._demotion

    def _bucket(self, request_digest: str) -> int:
        material = f"{self.model_id}:{request_digest}".encode()
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % 100

    def admit(self, request_digest: str) -> bool:
        """True iff this request's advisory path may observe the model."""
        if not isinstance(request_digest, str) or len(request_digest) != 64:
            raise ContractError("admit requires a request digest")
        if self._demotion is not None:
            return False
        if self.monitor.triggered:
            self.demote(f"rollback_triggered:{self.monitor.trigger.condition}")
            return False
        try:
            manifest = self.registry.qualified_manifest(self.model_id)
        except ContractError:
            self.demote("model_not_qualified")
            return False
        if not manifest.qualification_receipt:
            self.demote("missing_qualification_receipt")
            return False
        return self._bucket(request_digest) < self.percent

    def promote(self) -> int:
        """Advance to the next rollout step (e.g. 1% -> 5%). Returns percent."""
        if self._demotion is not None:
            raise ContractError("demoted canary cannot be promoted")
        if self._step < len(self.steps) - 1:
            self._step += 1
        self._receipt("promote", "operator step-up", self.percent)
        return self.percent

    def demote(self, reason: str) -> dict:
        """Latching demotion to 0%. Idempotent; the first demotion is receipted."""
        if not isinstance(reason, str) or not reason:
            raise ContractError("demotion requires a reason")
        if self._demotion is None:
            self._demotion = self._receipt("demote", reason, 0)
        return self._demotion
