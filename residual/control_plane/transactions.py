"""Compound side effects are DAGs of atomic, individually reconcilable intents."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from .models import AtomicEffect, IntentState, TransactionState

@dataclass
class SideEffectTransaction:
    transaction_id: str
    effects: dict[str, AtomicEffect]
    def __post_init__(self):
        unknown={d for e in self.effects.values() for d in e.depends_on if d not in self.effects}
        if unknown: raise ValueError(f"unknown dependencies: {sorted(unknown)}")
        self._assert_acyclic()
    def _assert_acyclic(self):
        visiting=set(); done=set()
        def visit(k):
            if k in visiting: raise ValueError("side-effect dependency cycle")
            if k in done: return
            visiting.add(k)
            for d in self.effects[k].depends_on: visit(d)
            visiting.remove(k); done.add(k)
        for k in self.effects: visit(k)
    def ready(self):
        return tuple(e for e in self.effects.values() if e.state is IntentState.PREPARED and all(self.effects[d].state is IntentState.APPLIED for d in e.depends_on))
    def transition(self, effect_id, state, *, result_ref=None):
        e=self.effects[effect_id]
        allowed={IntentState.PREPARED:{IntentState.ATTEMPTED}, IntentState.ATTEMPTED:{IntentState.APPLIED,IntentState.FAILED,IntentState.AMBIGUOUS}, IntentState.AMBIGUOUS:{IntentState.RECONCILING}, IntentState.RECONCILING:{IntentState.APPLIED,IntentState.FAILED}}
        if state not in allowed.get(e.state,set()): raise ValueError(f"illegal transition {e.state}->{state}")
        self.effects[effect_id]=replace(e,state=state,result_ref=result_ref)
    @property
    def state(self):
        states={e.state for e in self.effects.values()}
        if states=={IntentState.APPLIED}: return TransactionState.COMPLETE
        if IntentState.AMBIGUOUS in states or IntentState.RECONCILING in states: return TransactionState.RECONCILIATION_REQUIRED
        if IntentState.FAILED in states and IntentState.APPLIED in states: return TransactionState.INCOMPLETE
        if states=={IntentState.FAILED}: return TransactionState.FAILED
        if states=={IntentState.PREPARED}: return TransactionState.PREPARED
        return TransactionState.IN_PROGRESS
