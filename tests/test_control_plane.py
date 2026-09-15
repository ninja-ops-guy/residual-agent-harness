import unittest
from residual.control_plane import *

class ControlPlaneTests(unittest.TestCase):
    def grant(self, subject="w1", action="git.push"):
        return CapabilityGrant(subject, action, "repo", {"branches":["residual/*"]})
    def test_routing_cannot_enlarge_authority(self):
        g=self.grant(); rev=MissionRevision("m","r","goal","p","policy",(g,))
        d=RoutingDecision("d","r","o",("w1",),"w1",{},(),"router1","policy1",g.fingerprint(),g.fingerprint())
        self.assertTrue(RoutingPolicy().validate(d,(g,),rev))
        broader=self.grant(action="git.merge")
        self.assertFalse(RoutingPolicy().validate(d,(broader,),rev))
    def test_authority_amendment_requires_independent_human(self):
        a=PlanAmendment("a","m","r",AmendmentClass.AUTHORITY,"need merge",{},proposer_id="w1",beneficiary_ids=("w1",))
        p=AmendmentPolicy()
        self.assertFalse(p.validate_independence(a,("w1",),human_approvers=("owner",)))
        self.assertFalse(p.validate_independence(a,("v2",)))
        self.assertTrue(p.validate_independence(a,("v2",),human_approvers=("owner",)))
    def test_certified_state_stales_and_invalidates(self):
        s=CertifiedState("k",1,("e",),"d","v",0,10,3,10,20,20,"env")
        self.assertEqual(s.status(now=15,environment_fingerprint="env"),CertifiedStatus.CERTIFIED)
        self.assertEqual(s.status(now=31,environment_fingerprint="env"),CertifiedStatus.STALE)
        self.assertEqual(s.status(now=15,environment_fingerprint="changed"),CertifiedStatus.INVALIDATED)
    def test_transaction_reconciliation_and_partial(self):
        a=AtomicEffect("a","i1")
        b=AtomicEffect("b","i2",("a",))
        tx=SideEffectTransaction("t",{"a":a,"b":b})
        self.assertEqual([x.effect_id for x in tx.ready()],["a"])
        tx.transition("a",IntentState.ATTEMPTED); tx.transition("a",IntentState.APPLIED)
        self.assertEqual([x.effect_id for x in tx.ready()],["b"])
        tx.transition("b",IntentState.ATTEMPTED); tx.transition("b",IntentState.AMBIGUOUS)
        self.assertEqual(tx.state,TransactionState.RECONCILIATION_REQUIRED)
        tx.transition("b",IntentState.RECONCILING); tx.transition("b",IntentState.FAILED)
        self.assertEqual(tx.state,TransactionState.INCOMPLETE)
    def test_transaction_rejects_cycles(self):
        with self.assertRaises(ValueError):
            SideEffectTransaction("t",{"a":AtomicEffect("a","i",("b",)),"b":AtomicEffect("b","j",("a",))})

if