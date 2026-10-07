"""Deterministic, versioned amendment classifier."""
from __future__ import annotations
from dataclasses import dataclass
from .models import AmendmentClass, AmendmentDelta

DEFAULT_RULES={
 "clarification":AmendmentClass.CLARIFICATION,
 "plan.restructure":AmendmentClass.RESTRUCTURE,
 "scope.workspace_add":AmendmentClass.RESTRUCTURE,
 "budget.increase":AmendmentClass.RESOURCE,
 "budget.decrease":AmendmentClass.RESOURCE,
 "resource.increase":AmendmentClass.RESOURCE,
 "authority.side_effect_add":AmendmentClass.AUTHORITY,
 "authority.capability_add":AmendmentClass.AUTHORITY,
 "authority.scope_expand":AmendmentClass.AUTHORITY,
 "trust_boundary.change":AmendmentClass.TRUST_BOUNDARY,
 "verifier.policy_change":AmendmentClass.TRUST_BOUNDARY,
}
@dataclass(frozen=True)
class AmendmentClassifier:
    revision: str="amendment-classifier-v1"
    def classify_delta(self, delta: AmendmentDelta) -> AmendmentClass:
        if delta.risk_score is not None:
            try: return AmendmentClass(delta.risk_score)
            except ValueError: raise ValueError("risk_score must be 0..4") from None
        if delta.delta_type not in DEFAULT_RULES: raise ValueError(f"unclassified amendment delta: {delta.delta_type}")
        return DEFAULT_RULES[delta.delta_type]
    def classify(self, deltas: tuple[AmendmentDelta,...]) -> AmendmentClass:
        if not deltas: raise ValueError("amendment requires at least one typed delta")
        return max((self.classify_delta(d) for d in deltas), key=int)
