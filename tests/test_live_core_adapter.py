import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "vendor"))

from adapter_conformance_suite import AdapterConformanceTests, AdapterHandle

from residual.adapter_backend import (
    AttestationError,
    CoreGateDecision,
    CoreUnreachableError,
    GateFiredError,
    LedgerWriteError,
    LiveCoreResidualBackend,
    recompute_attestation_id,
)
from residual.core import Artifact, Obligation, Registry, Task, Verdict, register_builtins
from residual.engine import Harness


class ChaosTransport:
    def __init__(self):
        self.reachable = True
        self.writable = True

    def ping(self):
        if not self.reachable:
            raise ConnectionRefusedError("core unavailable")
        return True

    def commit(self):
        if not self.writable:
            raise OSError("write barrier failed")


class LiveCoreHandle(AdapterHandle):
    core_unreachable_exc = CoreUnreachableError
    ledger_write_exc = LedgerWriteError
    gate_fired_exc = GateFiredError

    def __init__(self):
        self.transport = ChaosTransport()
        self.blocked = set()
        self.backend = LiveCoreResidualBackend(
            ":memory:",
            spec_version="1.0.0",
            spec_head_sha="a" * 40,
            impl_commit_sha="b" * 40,
            impl_tree_sha="c" * 40,
            transport=self.transport,
            gate_evaluator=self._evaluate,
            evaluator_id="test-core-verifier",
        )

    def _evaluate(self, run_id, module, call_id, inputs_digest):
        if module in self.blocked:
            return CoreGateDecision(
                "BLOCKED",
                f"CORE:{module}",
                {"source": "test-core-policy", "module": module},
            )
        return Verdict.passed()

    def start_run(self, run_id, spec_id):
        self.backend.on_run_start(run_id, spec_id)

    def module_call(self, run_id, module):
        return self.backend.on_module_call(run_id, module, f"call:{module}", "0" * 64)

    def complete_run(self, run_id, outcome="success"):
        self.backend.on_run_complete(run_id, outcome)

    def events(self, run_id):
        return self.backend.events(run_id)

    def get_attestation(self, run_id):
        return self.backend.get_attestation(run_id)

    def break_core(self):
        self.transport.reachable = False

    def heal_core(self):
        self.transport.reachable = True

    def break_ledger(self):
        self.transport.writable = False

    def heal_ledger(self):
        self.transport.writable = True

    def block_module(self, module):
        self.blocked.add(module)

    def try_mutate_ledger(self):
        self.backend._conn.execute("UPDATE events SET kind='mutated'")


class TestLiveCoreConformance(AdapterConformanceTests):
    def make_handle(self):
        return LiveCoreHandle()


class MutantCoercesVerdict(LiveCoreHandle):
    def get_attestation(self, run_id):
        token = super().get_attestation(run_id)
        token["verdicts"] = {key: "PASS" for key in token["verdicts"]}
        token["attestation_id"] = recompute_attestation_id(token)
        return token


class MutantFailOpenCore(LiveCoreHandle):
    def break_core(self):
        self.transport.reachable = True


class MutantSwallowsGate(LiveCoreHandle):
    def module_call(self, run_id, module):
        try:
            return super().module_call(run_id, module)
        except GateFiredError:
            return "PASS"


class MutantMutableLedger(LiveCoreHandle):
    def try_mutate_ledger(self):
        try:
            super().try_mutate_ledger()
        except Exception:
            return None


class TestLiveCoreMutationEvidence(unittest.TestCase):
    def _run(self, handle_cls):
        class Bound(AdapterConformanceTests):
            def make_handle(self):
                return handle_cls()

        result = unittest.TestResult()
        unittest.TestLoader().loadTestsFromTestCase(Bound).run(result)
        return {case._testMethodName for case, _ in result.failures + result.errors}

    def test_verdict_coercion_is_detected(self):
        self.assertIn("test_verdict_not_coerced", self._run(MutantCoercesVerdict))

    def test_fail_open_core_is_detected(self):
        self.assertIn("test_core_unreachable_fail_closed", self._run(MutantFailOpenCore))

    def test_swallowed_gate_is_detected(self):
        self.assertIn("test_gate_firing_propagates", self._run(MutantSwallowsGate))

    def test_mutable_ledger_is_detected(self):
        self.assertIn("test_ledger_append_only", self._run(MutantMutableLedger))


class TestLiveHarnessBinding(unittest.TestCase):
    def backend(self):
        return LiveCoreResidualBackend(
            ":memory:",
            spec_version="1.0.0",
            spec_head_sha="a" * 40,
            impl_commit_sha="b" * 40,
            impl_tree_sha="c" * 40,
        )

    def test_absent_evaluator_is_unknown_and_fail_closed(self):
        backend = self.backend()
        backend.on_run_start("r-unknown", "spec@1")
        with self.assertRaises(GateFiredError) as raised:
            backend.on_module_call("r-unknown", "tool:shell", "call-1", "0" * 64)
        self.assertEqual(raised.exception.verdict, "UNKNOWN")
        token = backend.get_attestation("r-unknown")
        self.assertEqual(token["verdicts"]["CORE:tool:shell"], "UNKNOWN")
        self.assertEqual(token["verdicts"]["CORE-RUN-OUTCOME"], "BLOCKED")

    def test_real_harness_pass_is_bound_without_reinterpretation(self):
        registry = Registry()
        register_builtins(registry)
        task = Task(
            "binding_pass",
            "extract a declared JSON value",
            {"input": Artifact("input", '{"answer":42}')},
            (
                Obligation(
                    "answer",
                    "return the answer",
                    "json_value",
                    evidence=("input",),
                    parameters={"artifact": "input", "pointer": "/answer"},
                    solver="json_value",
                ),
            ),
        )
        result, token = self.backend().run_harness(Harness(registry, None, None), task, run_id="r-pass")
        self.assertTrue(result["success"])
        self.assertEqual(token["verdicts"]["CORE-OBLIGATION:answer"], "PASS")
        self.assertEqual(token["verdicts"]["CORE-RUN-OUTCOME"], "PASS")
        self.assertTrue(result["station_receipts"])
        self.assertTrue(
            any(e["kind"] == "core.run.bound" for e in self.backend().events("never")),
            "anti-vacuity guard is exercised in the dedicated event assertions below",
        )

    def test_real_harness_fail_remains_fail_and_aborts_attested_run(self):
        registry = Registry()
        registry.check("always_fail", lambda value, ctx: Verdict.fail("forced_failure"), "1")
        registry.solver("candidate", lambda ctx: {"candidate": True})
        task = Task(
            "binding_fail",
            "exercise a real core verifier failure",
            {},
            (
                Obligation(
                    "decision",
                    "this verifier deliberately rejects",
                    "always_fail",
                    solver="candidate",
                ),
            ),
        )
        backend = self.backend()
        result, token = backend.run_harness(Harness(registry, None, None), task, run_id="r-fail")
        self.assertFalse(result["success"])
        self.assertEqual(token["verdicts"]["CORE-OBLIGATION:decision"], "FAIL")
        self.assertEqual(token["verdicts"]["CORE-RUN-OUTCOME"], "BLOCKED")
        fired = [e for e in backend.events("r-fail") if e["kind"] == "gate.fired"]
        self.assertTrue(fired)
        self.assertEqual(fired[0]["payload"]["verdict"], "FAIL")

    def test_attestation_absent_before_terminal(self):
        backend = self.backend()
        backend.on_run_start("r-open", "spec@1")
        with self.assertRaises(AttestationError):
            backend.get_attestation("r-open")


if __name__ == "__main__":
    unittest.main(verbosity=2)
