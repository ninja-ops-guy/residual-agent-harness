import unittest
from decimal import Decimal

from residual.core import Obligation
from residual.factory.loop_runtime import (
    AbortCondition, CapabilityFloor, DeduplicationMaterial, FactoryResultSet,
    GoalContract, GoalEvaluator, LoopController, MissionStatus, ObligationState,
    VerificationResultRef, VerificationStatus,
)


def obligation(oid):
    return Obligation(oid, "fix it", "test")


def verified(run_id, tree, root, residuals=(), states=None, status=VerificationStatus.PASS, cost="0"):
    return FactoryResultSet(
        factory_run_id=run_id,
        accepted_tree_hash=tree,
        accepted_evidence_root=root,
        rejected_evidence_root=None,
        verification_results=(VerificationResultRef("required", status, tree, root, "receipt-v"),),
        residual_obligations=tuple(residuals),
        obligation_states=states or {},
        receipt_refs=(f"receipt-{run_id}",),
        cost=Decimal(cost),
    )


class FakeFactory:
    def __init__(self, results):
        self.results=list(results); self.calls=[]; self.cancelled=False
    def run(self, obligations, intent):
        self.calls.append((tuple(o.id for o in obligations), intent))
        return self.results.pop(0)
    def deduplication_material(self, obligation):
        return DeduplicationMaterial(("inputhash",), f"contract-{obligation.id}")
    def cancel_inflight(self, timeout_s):
        self.cancelled=True


class LoopRuntimeTests(unittest.TestCase):
    def contract(self, **kw):
        base=dict(goal_id="g1", objective="finish", required_verification_ids=("required",), max_iterations=3)
        base.update(kw); return GoalContract(**base)

    def test_completion_requires_tree_and_accepted_evidence_binding(self):
        evaluator=GoalEvaluator(); c=self.contract()
        ok=verified("r1","tree1","root1")
        self.assertTrue(evaluator.evaluate(c,ok).complete)
        bad=FactoryResultSet("r2","tree1","root1",None,(VerificationResultRef("required",VerificationStatus.PASS,"tree1","other"),),(),{})
        self.assertFalse(evaluator.evaluate(c,bad).complete)

    def test_unknown_never_completes(self):
        f=FakeFactory([verified("r1","tree","root",status=VerificationStatus.UNKNOWN)])
        result=LoopController(f).run(self.contract(max_iterations=1),(obligation("a"),))
        self.assertNotEqual(result.status,MissionStatus.COMPLETE)

    def test_resubmits_only_factory_residuals(self):
        a,b=obligation("a"),obligation("b")
        first=verified("r1","t1","e1",(b,),{"a":ObligationState.ACCEPTED,"b":ObligationState.REJECTED},status=VerificationStatus.FAIL)
        second=verified("r2","t2","e2",(),{"a":ObligationState.ACCEPTED,"b":ObligationState.ACCEPTED})
        f=FakeFactory([first,second])
        result=LoopController(f).run(self.contract(),(a,b))
        self.assertEqual(result.status,MissionStatus.COMPLETE)
        self.assertEqual(f.calls[0][0],("a","b"))
        self.assertEqual(f.calls[1][0],("b",))

    def test_deduplication_key_is_stable_across_equivalent_resubmission(self):
        b=obligation("b")
        first=verified("r1","t1","e1",(b,),{"b":ObligationState.REJECTED},status=VerificationStatus.FAIL)
        second=verified("r2","t1","e1",(b,),{"b":ObligationState.REJECTED},status=VerificationStatus.FAIL)
        f=FakeFactory([first,second])
        result=LoopController(f).run(self.contract(max_iterations=2,no_progress_limit=3),(b,))
        self.assertEqual(result.status,MissionStatus.EXHAUSTED)
        self.assertEqual(f.calls[0][1].deduplication_keys["b"],f.calls[1][1].deduplication_keys["b"])

    def test_escalation_respects_cooldown(self):
        b=obligation("b")
        fail=lambda rid: verified(rid,"t1","e1",(b,),{"b":ObligationState.REJECTED},status=VerificationStatus.FAIL)
        f=FakeFactory([fail("r1"),fail("r2"),fail("r3")])
        LoopController(f).run(self.contract(max_iterations=3,no_progress_limit=5,escalation_cooldown_period=2),(b,))
        self.assertNotEqual(f.calls[1][1].capability_floor,CapabilityFloor.HIGHER)
        self.assertEqual(f.calls[2][1].capability_floor,CapabilityFloor.HIGHER)

    def test_abort_cancels_inflight_and_returns_aborted(self):
        f=FakeFactory([])
        result=LoopController(f,abort_requested=lambda: True).run(self.contract(),(obligation("a"),))
        self.assertEqual(result.status,MissionStatus.ABORTED)
        self.assertTrue(f.cancelled)
        self.assertEqual(len(f.calls),0)

    def test_budget_abort_after_no_progress(self):
        b=obligation("b")
        fail=verified("r1","t1","e1",(b,),{"b":ObligationState.REJECTED},status=VerificationStatus.FAIL,cost="5")
        f=FakeFactory([fail])
        c=self.contract(abort_conditions=(AbortCondition(budget_threshold=Decimal("5"),require_no_progress=False),))
        result=LoopController(f).run(c,(b,))
        self.assertEqual(result.status,MissionStatus.ABORTED)
        self.assertTrue(f.cancelled)

    def test_prefix_consistency_first_iteration_record_is_stable(self):
        b=obligation("b")
        first_a=verified("r1","t1","e1",(b,),{"b":ObligationState.REJECTED},status=VerificationStatus.FAIL)
        first_b=verified("r1","t1","e1",(b,),{"b":ObligationState.REJECTED},status=VerificationStatus.FAIL)
        second=verified("r2","t2","e2",(),{"b":ObligationState.ACCEPTED})
        short=LoopController(FakeFactory([first_a])).run(self.contract(max_iterations=1),(b,))
        long=LoopController(FakeFactory([first_b,second])).run(self.contract(max_iterations=2),(b,))
        self.assertEqual(short.iterations[0].record_hash,long.iterations[0].record_hash)

    def test_worker_text_has_no_stop_channel(self):
        params=GoalEvaluator.evaluate.__annotations__
        self.assertNotIn("worker_output",params)

    def test_unrecognized_verifier_states_are_rejected(self):
        for status in ("error", "skipped", None, "PASS", 1):
            with self.subTest(status=status), self.assertRaises(ValueError):
                VerificationResultRef("required", status, "tree", "root")

    def test_serialized_status_is_normalized(self):
        ref = VerificationResultRef("required", "unknown", "tree", "root")
        self.assertIs(ref.status, VerificationStatus.UNKNOWN)

    def test_duplicate_result_cannot_hide_failed_verification(self):
        fail = VerificationResultRef("required", VerificationStatus.FAIL, "tree", "root")
        passed = VerificationResultRef("required", VerificationStatus.PASS, "tree", "root")
        for results in ((fail, passed), (passed, fail), (passed, passed)):
            with self.subTest(results=results), self.assertRaisesRegex(ValueError, "duplicate verification"):
                FactoryResultSet("r", "tree", "root", None, results, (), {})

    def test_abort_during_factory_call_overrides_late_pass(self):
        factory = FakeFactory([verified("r1", "tree", "root")])
        result = LoopController(factory, abort_requested=lambda: bool(factory.calls)).run(
            self.contract(), (obligation("a"),)
        )
        self.assertEqual(result.status, MissionStatus.ABORTED)
        self.assertTrue(factory.cancelled)
        self.assertEqual(len(result.iterations), 1)
        self.assertEqual(result.state.accepted_evidence_root, "root")

    def test_wall_deadline_during_factory_call_overrides_late_pass(self):
        factory = FakeFactory([verified("r1", "tree", "root")])
        ticks = iter((0, 0, 11))
        result = LoopController(factory, monotonic=lambda: next(ticks)).run(
            self.contract(max_wall_time_s=10), (obligation("a"),)
        )
        self.assertEqual(result.status, MissionStatus.ABORTED)
        self.assertEqual(result.reason, "wall_time_exhausted")
        self.assertTrue(factory.cancelled)

if __name__ == "__main__": unittest.main()
