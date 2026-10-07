"""Track D: SideEffectIntent schema and SideEffectGateway behavior tests."""
import unittest

from residual.core import ContractError
from residual.gateway import (
    ActionKind,
    BlastRadius,
    GatewayResult,
    Reversibility,
    SideEffectGateway,
    SideEffectIntent,
)
from residual.gateway.intents import radius_at_least


def intent(**kw):
    values = dict(
        action_kind=ActionKind.FILE_WRITE,
        target="out/report.txt",
        reversibility=Reversibility.REVERSIBLE,
        blast_radius=BlastRadius.LOCAL,
        parameters={"content": "hello"},
        agent_id="agent-1",
    )
    return SideEffectIntent(**{**values, **kw})


class TestSideEffectIntent(unittest.TestCase):
    def test_valid_intent_constructs_and_hashes(self):
        a, b = intent(), intent()
        self.assertEqual(a.content_hash, b.content_hash)  # content-addressed
        self.assertNotEqual(a.intent_id, b.intent_id)
        self.assertEqual(len(a.content_hash), 64)

    def test_hash_changes_with_content(self):
        self.assertNotEqual(intent().content_hash, intent(target="other.txt").content_hash)
        self.assertNotEqual(intent().content_hash,
                            intent(blast_radius=BlastRadius.SYSTEM).content_hash)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ContractError):
            intent(action_kind="rm -rf /")

    def test_unknown_reversibility_rejected(self):
        with self.assertRaises(ContractError):
            intent(reversibility="maybe")

    def test_unknown_blast_radius_rejected(self):
        with self.assertRaises(ContractError):
            intent(blast_radius="galaxy")

    def test_empty_target_rejected(self):
        for bad in ("", "   ", "a\x00b"):
            with self.assertRaises(ContractError):
                intent(target=bad)

    def test_noncanonical_parameters_rejected(self):
        with self.assertRaises(ContractError):
            intent(parameters={"x": object()})

    def test_intent_is_immutable(self):
        i = intent()
        with self.assertRaises(Exception):
            i.target = "elsewhere"

    def test_radius_ordering(self):
        self.assertTrue(radius_at_least(BlastRadius.SYSTEM, BlastRadius.LOCAL))
        self.assertFalse(radius_at_least(BlastRadius.LOCAL, BlastRadius.RUN))


class TestGatewayExecution(unittest.TestCase):
    def test_registered_intent_executes_through_quarantine(self):
        gw = SideEffectGateway()
        calls = []
        gw.register(ActionKind.FILE_WRITE, "out/*", lambda i: calls.append(i.target) or "ok")
        result = gw.execute(intent())
        self.assertIsInstance(result, GatewayResult)
        self.assertEqual(result.status, "executed")
        self.assertEqual(result.result, "ok")
        self.assertEqual(calls, ["out/report.txt"])
        events = [e["event"] for e in gw.audit_log()]
        self.assertEqual(events, ["held", "evaluated", "executed"])

    def test_executor_exception_is_observed_not_hidden(self):
        gw = SideEffectGateway()

        def boom(_intent):
            raise RuntimeError("disk full")

        gw.register(ActionKind.FILE_WRITE, "out/*", boom)
        result = gw.execute(intent())
        self.assertEqual(result.status, "executed")
        self.assertEqual(result.error, "RuntimeError")
        executed = [e for e in gw.audit_log() if e["event"] == "executed"]
        self.assertEqual(executed[0]["error"], "RuntimeError")

    def test_executor_exception_reraises_when_requested(self):
        gw = SideEffectGateway()

        def boom(_intent):
            raise RuntimeError("disk full")

        gw.register(ActionKind.FILE_WRITE, "out/*", boom)
        with self.assertRaises(RuntimeError):
            gw.execute(intent(), raise_errors=True)

    def test_glob_patterns_scope_registration(self):
        gw = SideEffectGateway()
        gw.register(ActionKind.NETWORK_EGRESS, "api.internal/*", lambda i: "sent")
        self.assertEqual(gw.execute(intent(
            action_kind=ActionKind.NETWORK_EGRESS, target="api.internal/hosts")).status, "executed")
        denied = gw.execute(intent(action_kind=ActionKind.NETWORK_EGRESS,
                                   target="evil.example/exfil"))
        self.assertEqual(denied.status, "denied")

    def test_executor_receives_exact_intent(self):
        gw = SideEffectGateway()
        seen = []
        gw.register(ActionKind.TOOL_CALL, "search", lambda i: seen.append(i))
        i = intent(action_kind=ActionKind.TOOL_CALL, target="search",
                   parameters={"q": "residual"})
        gw.execute(i)
        self.assertEqual(seen, [i])


class TestApprovalPolicy(unittest.TestCase):
    def dangerous(self, **kw):
        return intent(action_kind=ActionKind.PROCESS_SPAWN, target="cleanup-daemon",
                      reversibility=Reversibility.IRREVERSIBLE,
                      blast_radius=BlastRadius.SYSTEM, **kw)

    def test_irreversible_system_intent_fails_closed_without_verifier(self):
        gw = SideEffectGateway()
        calls = []
        gw.register(ActionKind.PROCESS_SPAWN, "*", lambda i: calls.append(i))
        result = gw.execute(self.dangerous())
        self.assertEqual(result.status, "denied")
        self.assertEqual(calls, [])

    def test_irreversible_intent_executes_with_host_approval(self):
        gw = SideEffectGateway(approval_verifier=lambda i: True)
        calls = []
        gw.register(ActionKind.PROCESS_SPAWN, "*", lambda i: calls.append(i) or "done")
        self.assertEqual(gw.execute(self.dangerous()).status, "executed")
        self.assertEqual(len(calls), 1)

    def test_verifier_rejection_denies(self):
        gw = SideEffectGateway(approval_verifier=lambda i: False)
        gw.register(ActionKind.PROCESS_SPAWN, "*", lambda i: "never")
        self.assertEqual(gw.execute(self.dangerous()).status, "denied")

    def test_verifier_exception_denies(self):
        def bad(_intent):
            raise RuntimeError("verifier down")

        gw = SideEffectGateway(approval_verifier=bad)
        gw.register(ActionKind.PROCESS_SPAWN, "*", lambda i: "never")
        self.assertEqual(gw.execute(self.dangerous()).status, "denied")

    def test_reversible_local_intent_needs_no_approval(self):
        gw = SideEffectGateway()  # no verifier at all
        gw.register(ActionKind.FILE_WRITE, "out/*", lambda i: "ok")
        self.assertEqual(gw.execute(intent()).status, "executed")


if __name__ == "__main__":
    unittest.main()
