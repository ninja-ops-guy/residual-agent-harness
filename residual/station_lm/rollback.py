"""Rollback triggers for StationLM advisory routing.

Automatic, latching fallback conditions. Once triggered, the provider must
fail closed to deterministic/default routing until a human clears the trigger
(``reset``) and the model is re-qualified.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from residual.core import ContractError

# Immediate (single-event) triggers: no rate window needed.
IMMEDIATE_REASONS = {"authority_violation", "missing_model_artifact"}


@dataclass(frozen=True)
class RollbackTrigger:
    condition: str
    detail: str
    receipts_considered: int


class RollbackMonitor:
    """Sliding-window monitor over decision receipts.

    Rate triggers:
      - schema-invalid rate spike
      - false non-escalation spike (model said no-escalate where the
        authoritative outcome required escalation)
      - latency regression vs baseline
    Immediate triggers: authority violation, missing model artifact.
    """

    def __init__(self, *, window: int = 50, schema_invalid_rate: float = 0.2,
                 false_non_escalation_rate: float = 0.1,
                 latency_regression_factor: float = 2.0,
                 baseline_latency_ms: Optional[float] = None):
        if type(window) is not int or not 1 <= window <= 100000:
            raise ContractError("window must be 1-100000")
        for name, value in (("schema_invalid_rate", schema_invalid_rate),
                            ("false_non_escalation_rate", false_non_escalation_rate)):
            if type(value) not in (int, float) or not 0 < value <= 1:
                raise ContractError(f"{name} must be in (0,1]")
        if type(latency_regression_factor) not in (int, float) or latency_regression_factor < 1:
            raise ContractError("latency_regression_factor must be >= 1")
        if baseline_latency_ms is not None and (
                type(baseline_latency_ms) not in (int, float) or baseline_latency_ms <= 0):
            raise ContractError("baseline_latency_ms must be positive")
        self.window = window
        self.schema_invalid_rate = float(schema_invalid_rate)
        self.false_non_escalation_rate = float(false_non_escalation_rate)
        self.latency_regression_factor = float(latency_regression_factor)
        self.baseline_latency_ms = baseline_latency_ms
        self._records: list[dict[str, Any]] = []
        self._trigger: Optional[RollbackTrigger] = None

    @property
    def triggered(self) -> bool:
        return self._trigger is not None

    @property
    def trigger(self) -> Optional[RollbackTrigger]:
        return self._trigger

    def record(self, receipt, *, expected_escalation: Optional[bool] = None) -> Optional[RollbackTrigger]:
        """Record one decision receipt; returns the trigger if one latched."""
        entry = {"outcome": receipt.outcome,
                 "fallback_reason": receipt.fallback_reason,
                 "elapsed_ms": receipt.elapsed_ms,
                 "escalate": (receipt.proposal.get("escalate")
                              if isinstance(receipt.proposal, dict) else None),
                 "expected_escalation": expected_escalation}
        self._records.append(entry)
        del self._records[:-self.window]
        if self._trigger is None:
            self._trigger = self._evaluate()
        return self._trigger

    def _evaluate(self) -> Optional[RollbackTrigger]:
        records = self._records
        n = len(records)
        if n == 0:
            return None
        for r in records:
            if r["fallback_reason"] in IMMEDIATE_REASONS:
                return RollbackTrigger(r["fallback_reason"],
                                       "immediate fail-closed condition observed", n)
        invalid = sum(1 for r in records if r["fallback_reason"] == "schema_invalid")
        if invalid / n >= self.schema_invalid_rate and invalid > 0:
            return RollbackTrigger("schema_invalid_rate_spike",
                                   f"{invalid}/{n} schema-invalid proposals", n)
        escalations = [r for r in records if r["expected_escalation"] is not None]
        if escalations:
            false_ne = sum(1 for r in escalations
                           if r["expected_escalation"] is True and r["escalate"] is False)
            if false_ne and false_ne / len(escalations) >= self.false_non_escalation_rate:
                return RollbackTrigger("false_non_escalation_spike",
                                       f"{false_ne}/{len(escalations)} missed escalations", n)
        if self.baseline_latency_ms is not None:
            accepted = [r["elapsed_ms"] for r in records if r["outcome"] == "accepted"]
            if accepted:
                mean = sum(accepted) / len(accepted)
                if mean > self.latency_regression_factor * self.baseline_latency_ms:
                    return RollbackTrigger("latency_regression",
                                           f"mean {mean:.1f}ms vs baseline "
                                           f"{self.baseline_latency_ms}ms", n)
        return None

    def reset(self) -> None:
        """Human/operator reset after re-qualification. Clears history."""
        self._records.clear()
        self._trigger = None
