"""Routing decision-context capture for SLM-06 (economic routing).

At each routing/model decision the recorder captures the selected
worker/model, the full alternative set available at decision time, and an
ESTIMATED counterfactual cost per alternative. Counterfactuals are always
labeled ``estimate: true`` and must never be reported as observed savings
(eval-protocol-v1.0.0 §6). Unknown prices stay null (no imputation, §8).
"""
from __future__ import annotations

import uuid
from typing import Optional

from .recorder import SLM_TELEMETRY_SCHEMA_VERSION, Recorder


class DecisionContextRecorder:
    """Fail-open wrapper; shares the Recorder's sink and degradation log."""

    def __init__(self, recorder: Recorder):
        self.recorder = recorder

    def record_decision(self, *, selected_model: str, selected_worker: Optional[str],
                        alternatives: list[dict],
                        assumed_tokens_in: int = 0, assumed_tokens_out: int = 0,
                        escalation_required: Optional[bool] = None,
                        escalation_taken: Optional[bool] = None,
                        escalation_classification: Optional[str] = None,
                        decision_id: Optional[str] = None) -> dict:
        """Record one routing decision.

        ``alternatives``: list of {"model": str, "worker_id": str|None} —
        the candidate set available at decision time (including the selected
        one if desired; it is excluded from counterfactuals automatically).
        """
        r = self.recorder
        if not r.config.enabled:
            return {}
        try:
            decision_id = decision_id or uuid.uuid4().hex
            alt_records = []
            for alt in alternatives:
                model = alt.get("model")
                est = r.price_table.cost_usd(model, assumed_tokens_in, assumed_tokens_out)
                if est is None:
                    r._degrade("unpriced_alternative", str(model))
                alt_records.append({
                    "model": model,
                    "worker_id": alt.get("worker_id"),
                    "available": True,
                    "counterfactual_cost_usd": est,
                    "estimate": True,  # ALWAYS an estimate — never observed
                })
            event = {
                "kind": "routing_decision",
                "schema_version": SLM_TELEMETRY_SCHEMA_VERSION,
                "run_id": r.run_id,
                "decision_id": decision_id,
                "ts": r.wall_clock(),
                "selected": {"model": selected_model, "worker_id": selected_worker},
                "alternatives": alt_records,
                "escalation": {
                    "required": escalation_required,
                    "taken": escalation_taken,
                    "classification": escalation_classification,
                },
                "price_table_version": r.price_table.version,
                "estimate": True,  # decision-level counterfactual block
            }
            r._write(event)
            return event
        except Exception as exc:
            r._degrade("record_decision_failed", repr(exc))
            return {}

    def record_escalation_outcome(self, *, decision_id: str,
                                  required: bool, taken: bool,
                                  classification: str,
                                  correct: Optional[bool] = None) -> dict:
        """Escalation correctness record feeding frozen FNER/UER metrics.

        classification vocabulary matches slm-observation-v0:
        ``false_non_escalation`` | ``unnecessary_escalation`` |
        ``correct_escalation`` | ``correct_non_escalation``.
        """
        r = self.recorder
        if not r.config.enabled:
            return {}
        try:
            if correct is None:
                correct = classification in ("correct_escalation", "correct_non_escalation")
            event = {
                "kind": "escalation_outcome",
                "schema_version": SLM_TELEMETRY_SCHEMA_VERSION,
                "run_id": r.run_id,
                "decision_id": decision_id,
                "ts": r.wall_clock(),
                "escalation": {"required": bool(required), "taken": bool(taken),
                               "classification": classification},
                "escalation_correct": bool(correct),
            }
            r._write(event)
            return event
        except Exception as exc:
            r._degrade("record_escalation_failed", repr(exc))
            return {}
