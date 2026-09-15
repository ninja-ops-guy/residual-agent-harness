"""Compound side effects and deterministic saga coordination."""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Callable, Any
from .models import AtomicEffect, IntentState, TransactionState

@dataclass
class SideEffectTransaction:
    transaction_id: str; effects: dict[str,AtomicEffect]
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
    def ready(self): return tuple(e for e in self.effects.values() if e.state is IntentState.PREPARED and all(self.effects[d].state is IntentState.APPLIED for d in e.depends_on))
    def transition(self,effect_id,state,*,result_ref=None):
        e=self.effects[effect_id]
        allowed={IntentState.PREPARED:{IntentState.ATTEMPTED},IntentState.ATTEMPTED:{IntentState.APPLIED,IntentState.FAILED,IntentState.AMBIGUOUS},IntentState.AMBIGUOUS:{IntentState.RECONCILING},IntentState.RECONCILING:{IntentState.APPLIED,IntentState.FAILED},IntentState.APPLIED:{IntentState.COMPENSATING},IntentState.COMPENSATING:{IntentState.COMPENSATED,IntentState.FAILED}}
        if state not in allowed.get(e.state,set()): raise ValueError(f"illegal transition {e.state}->{state}")
        self.effects[effect_id]=replace(e,state=state,result_ref=result_ref)
    @property
    def state(self):
        s={e.state for e in self.effects.values()}
        if s=={IntentState.APPLIED}: return TransactionState.COMPLETE
        if IntentState.AMBIGUOUS in s or IntentState.RECONCILING in s: return TransactionState.RECONCILIATION_REQUIRED
        if IntentState.COMPENSATING in s: return TransactionState.COMPENSATING
        if IntentState.COMPENSATED in s and s.issubset({IntentState.COMPENSATED,IntentState.FAILED,IntentState.PREPARED}): return TransactionState.COMPENSATED
        if IntentState.FAILED in s and IntentState.APPLIED in s: return TransactionState.INCOMPLETE
        if s=={IntentState.FAILED}: return TransactionState.FAILED
        if s=={IntentState.PREPARED}: return TransactionState.PREPARED
        return TransactionState.IN_PROGRESS

@dataclass(frozen=True)
class TransactionReceipt:
    transaction_id: str; final_state: TransactionState; effect_states: tuple[tuple[str,str],...]; evidence_refs: tuple[str,...]

class TransactionCoordinator:
    """Trusted deterministic saga coordinator. Gateway remains single-intent executor."""
    def __init__(self, dispatch: Callable[[AtomicEffect],Any], reconcile: Callable[[AtomicEffect],str], compensate: Callable[[AtomicEffect],Any]|None=None, emit: Callable[[str,dict],None]|None=None):
        self.dispatch=dispatch; self.reconcile=reconcile; self.compensate=compensate; self.emit=emit or (lambda *_:None); self.evidence=[]
    def _event(self,name,effect,**extra):
        ref=f"{name}:{effect.effect_id}:{len(self.evidence)}"; self.evidence.append(ref); self.emit(name,{"effect_id":effect.effect_id,"evidence_ref":ref,**extra}); return ref
    def run(self,tx: SideEffectTransaction):
        while tx.ready():
            effect=tx.ready()[0]; tx.transition(effect.effect_id,IntentState.ATTEMPTED); self._event("attempted",effect)
            try: outcome=self.dispatch(effect)
            except Exception: outcome="ambiguous"
            if outcome in (True,"applied","executed"):
                tx.transition(effect.effect_id,IntentState.APPLIED); self._event("applied",effect); continue
            if outcome in (False,"failed","denied"):
                tx.transition(effect.effect_id,IntentState.FAILED); self._event("failed",effect); break
            tx.transition(effect.effect_id,IntentState.AMBIGUOUS); self._event("ambiguous",effect)
            tx.transition(effect.effect_id,IntentState.RECONCILING); self._event("reconciling",effect)
            resolved=self.reconcile(effect)
            tx.transition(effect.effect_id,IntentState.APPLIED if resolved=="applied" else IntentState.FAILED); self._event(f"reconciled_{resolved}",effect)
            if resolved!="applied": break
        if any(e.state is IntentState.FAILED for e in tx.effects.values()) and self.compensate:
            applied=[e for e in tx.effects.values() if e.state is IntentState.APPLIED and e.compensation_intent_id]
            for e in reversed(applied):
                tx.transition(e.effect_id,IntentState.COMPENSATING); self._event("compensating",e)
                try: ok=self.compensate(e)
                except Exception: ok=False
                tx.transition(e.effect_id,IntentState.COMPENSATED if ok else IntentState.FAILED); self._event("compensated" if ok else "compensation_failed",e)
        return TransactionReceipt(tx.transaction_id,tx.state,tuple(sorted((k,v.state.value) for k,v in tx.effects.items())),tuple(self.evidence))
