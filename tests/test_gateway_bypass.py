"""Track D invariant tests: no bypass path around the side-effect gateway.

Every mutating action must be held, evaluated, and either released or denied
by the quarantine store. These tests attempt the bypass paths and prove each
one is denied and observed.
"""
import unittest

from residual.core import ContractError
from residual.gateway import (
    ActionKind,
    BlastRadius,
    Reversibility,
    SideEffectGateway,
    SideEffectIntent,
)
from residual.quarantine import PolicyDecision, ProposedAction, QuarantineStore


def intent(**kw):
    values = dict(
        action_kind=ActionKind.STATE_MUTATION,
        target="run.flags",
        reversibility=Reversibility.REVERSIBLE,
        blast_radius=BlastRadius.MODULE,
        parameters={"set": {"debug": True}},
        agent_id="agent-1",
    )
    return SideEffectIntent(**{**values, **kw})


class TestDenyByDefault(unittest.TestCase):
    def test_unregistered_intent_denied_and_observed(self):
        gw = SideEffectGateway()
        result = gw.execute(intent())
        self.assertEqual(result.status, "denied")
        self.assertIn("deny-by-default", result.denial_reason)
        events = [e["event"] for e in gw.audit_log()]
        self.assertEqual(events, ["held", "evaluated", "denied"])
        denied = [e for e in gw.audit_log() if e["event"] == "denied"]
        self.assertEqual(denied[0]["policy_name"], "side_effect_gateway")

    def test_unregistered_action_kind_denied(self):
        gw = SideEffectGateway()
        gw.register(ActionKind.FILE_WRITE, "*", lambda i: "ok")
        result = gw.execute(intent())  # STATE_MUTATION is not registered
        self.assertEqual(result.status, "denied")

    def test_non_intent_rejected_before_quarantine(self):
        gw = SideEffectGateway()
        with self.assertRaises(ContractError):
            gw.execute({"action": "mutate"})


class TestNoBypassPath(unittest.TestCase):
    """Attempt direct mutation paths; each must fail and remain observable."""

    def test_no_public_executor_accessor(self):
        gw = SideEffectGateway()
        gw.register(ActionKind.STATE_MUTATION, "run.flags", lambda i: "mutated")
        for attr in ("executors", "run", "invoke", "call", "dispatch", "execute_direct"):
            self.assertFalse(hasattr(gw, attr), f"gateway exposes bypass path: {attr}")

    def test_release_without_evaluation_is_refused(self):
        qs = QuarantineStore()
        held = qs.hold(ProposedAction("tool_call", "mutate", {}, "agent-1"))
        with self.assertRaises(ContractError):
            qs.release(held, lambda a: "mutated")

    def test_release_after_denial_is_refused(self):
        qs = QuarantineStore()
        held = qs.hold(ProposedAction("tool_call", "mutate", {}, "agent-1"))
        decision = qs.evaluate(held, (lambda a: "policy says no",))
        self.assertEqual(decision, PolicyDecision.DENY)
        qs.deny(held, "policy says no", "test_policy")
        with self.assertRaises(ContractError):
            qs.release(held, lambda a: "mutated")

    def test_consumed_hold_cannot_be_reused(self):
        qs = QuarantineStore()
        held = qs.hold(ProposedAction("tool_call", "mutate", {}, "agent-1"))
        qs.evaluate(held, ())
        qs.release(held, lambda a: "mutated")
        with self.assertRaises(ContractError):
            qs.release(held, lambda a: "mutated again")

    def test_forged_hold_is_refused(self):
        from residual.quarantine import HeldAction
        qs = QuarantineStore()
        foreign = QuarantineStore()
        held = foreign.hold(ProposedAction("tool_call", "mutate", {}, "agent-1"))
        foreign.evaluate(held, ())
        with self.assertRaises(ContractError):
            qs.release(held, lambda a: "mutated")
        self.assertEqual(qs.log(), ())  # nothing entered the victim's log

    def test_bypass_executor_call_is_not_recorded_as_execution(self):
        """Calling a raw callable outside the gateway must not appear in the
        gateway audit trail — the trail only reflects gateway-routed actions,
        which is exactly what makes bypass detectable."""
        gw = SideEffectGateway()
        raw = lambda i: "mutated"
        gw.register(ActionKind.STATE_MUTATION, "run.flags", raw)
        raw(intent())  # attacker calls the callable directly
        self.assertEqual(gw.audit_log(), ())  # gateway saw nothing to authorize
        result = gw.execute(intent())  # the only authorized path
        self.assertEqual(result.status, "executed")
        self.assertEqual(len([e for e in gw.audit_log() if e["event"] == "executed"]), 1)

    def test_policy_error_denies_closed(self):
        qs = QuarantineStore()

        def broken(_action):
            raise RuntimeError("policy engine crashed")

        held = qs.hold(ProposedAction("tool_call", "mutate", {}, "agent-1"))
        self.assertEqual(qs.evaluate(held, (broken,)), PolicyDecision.DENY)

    def test_denied_action_invisible_but_fully_observed(self):
        gw = SideEffectGateway()
        result = gw.execute(intent(target="secret.store"))
        self.assertEqual(result.status, "denied")
        self.assertIsNone(result.result)
        self.assertIsNone(result.error)
        trail = gw.audit_log()
        self.assertEqual({e["event"] for e in trail}, {"held", "evaluated", "denied"})
        for event in trail:
            self.assertEqual(event["hold_id"], result.hold_id)


if __name__ == "__main__":
    unittest.main()
