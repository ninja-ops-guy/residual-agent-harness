"""StationLM shadow-mode wiring + canary advisory rollout tests.

No network, no real models; FakeDecisionModel only. Invariants under test:
the authoritative router always wins, advisory exceptions are contained,
canary rollout is deterministic, rollback latch demotes and fallbacks are
receipted.
"""
import tempfile
import unittest
from pathlib import Path

from residual.core import ContractError, digest
from residual.station_lm import (
    CanaryRollout, DecisionRequest, FakeDecisionModel, ModelManifest,
    ModelRegistry, RollbackMonitor, ShadowModeHook, StationLMProvider,
    StationShadowIntegration,
)

ROUTES = ("local", "cloud")
HASH = "a" * 64


def make_request(task_id="task1", routes=ROUTES):
    return DecisionRequest(task_id=task_id, packet={"goal": "x"},
                           allowed_routes=routes, deadline_ms=2000)


def make_registry(qualified=True, model_id="fake-decision-v0"):
    manifest = ModelManifest(
        model_id=model_id, model_hash=HASH, tokenizer_hash="b" * 64,
        dataset_manifest_hash="c" * 64, training_config={"lr": 0.1},
        code_commit="d" * 40, seed=1, qualification_receipt="e" * 64,
        model_card={"name": model_id, "version": "1",
                    "intended_use": "advisory routing", "limitations": "stub"})
    reg = ModelRegistry()
    reg.register(manifest)
    reg.transition(model_id, "staged")
    if qualified:
        reg.transition(model_id, "qualified", qualification_receipt="e" * 64)
    return reg


def make_integration(mode="ok", seed=7, steps=(1, 5, 100), qualified=True,
                     monitor=None, sink=None, model_id="fake-decision-v0"):
    monitor = monitor or RollbackMonitor()
    provider = StationLMProvider(FakeDecisionModel(seed=seed, mode=mode,
                                                   model_id=model_id),
                                 default_route="local", monitor=monitor)
    return StationShadowIntegration(
        provider=provider, registry=make_registry(qualified, model_id),
        model_id=model_id, monitor=monitor, canary_steps=steps, sink=sink)


def force_admit(canary):
    """Deterministically admit every request (100% step)."""
    while canary.percent != 100:
        canary.promote()


class CanaryRolloutTests(unittest.TestCase):
    def test_unqualified_model_never_admitted(self):
        integ = make_integration(qualified=False)
        for i in range(20):
            self.assertFalse(integ.canary.admit(make_request(f"t{i}").request_digest))
        self.assertTrue(integ.canary.demoted)
        self.assertEqual(integ.canary.demotion_receipt["reason"], "model_not_qualified")

    def test_percentage_determinism_and_monotonicity(self):
        integ = make_integration(steps=(1, 5, 100))
        digests = [make_request(f"t{i}").request_digest for i in range(2000)]
        at1 = {d for d in digests if integ.canary.admit(d)}
        self.assertGreater(len(at1), 0)
        self.assertLessEqual(len(at1), int(0.05 * len(digests)))
        integ.canary.promote()  # -> 5%
        at5 = {d for d in digests if integ.canary.admit(d)}
        self.assertTrue(at1 <= at5)  # monotone rollout: 1% bucket subset of 5%
        self.assertGreater(len(at5), len(at1))
        self.assertLessEqual(len(at5), int(0.10 * len(digests)))
        # Deterministic: same digest, same verdict, across instances.
        other = make_integration(steps=(1, 5, 100))
        other.canary.promote()
        self.assertEqual({d for d in digests if other.canary.admit(d)}, at5)

    def test_full_rollout_admits_everything(self):
        integ = make_integration(steps=(1, 100))
        integ.canary.promote()
        for i in range(50):
            self.assertTrue(integ.canary.admit(make_request(f"t{i}").request_digest))

    def test_demote_is_latching_and_receipted(self):
        integ = make_integration(steps=(100,))
        d = make_request().request_digest
        self.assertTrue(integ.canary.admit(d))
        receipt = integ.canary.demote("operator halt")
        self.assertEqual(receipt["percent"], 0)
        self.assertEqual(len(receipt["receipt_hash"]), 64)
        self.assertFalse(integ.canary.admit(d))
        with self.assertRaises(ContractError):
            integ.canary.promote()
        self.assertIs(integ.canary.demote("again"), receipt)  # idempotent

    def test_monitor_latch_auto_demotes(self):
        monitor = RollbackMonitor()
        integ = make_integration(mode="authority_violation", monitor=monitor,
                                 steps=(100,))
        d = make_request().request_digest
        self.assertTrue(integ.canary.admit(d))
        integ.provider.decide(make_request())  # latches the monitor
        self.assertTrue(monitor.triggered)
        self.assertFalse(integ.canary.admit(d))
        self.assertTrue(integ.canary.demoted)
        self.assertIn("rollback_triggered",
                      integ.canary.demotion_receipt["reason"])

    def test_step_validation(self):
        for steps in ((), (0,), (101,), (5, 1), (1, 1), ("1",)):
            with self.subTest(steps=steps), self.assertRaises(ContractError):
                make_integration(steps=steps)


class ShadowIntegrationTests(unittest.TestCase):
    def authoritative(self, request):
        return "local"

    def test_authoritative_always_wins(self):
        integ = make_integration(seed=9, steps=(100,))
        for i in range(10):
            route = integ.decide_route(make_request(f"t{i}"), self.authoritative)
            self.assertEqual(route, "local")
        self.assertEqual(len(integ.pairs), 10)
        self.assertTrue(all(p.authoritative_route == "local" for p in integ.pairs))

    def test_advisory_exception_contained(self):
        class Exploding(StationLMProvider):
            def decide(self, request):
                raise RuntimeError("kaboom")
        integ = make_integration(steps=(100,))
        integ.provider = Exploding(FakeDecisionModel(), default_route="local")
        route = integ.decide_route(make_request(), self.authoritative)
        self.assertEqual(route, "local")
        pair = integ.pairs[0]
        self.assertIsNone(pair.agreement)
        self.assertTrue(pair.advisory_fallback)

    def test_pairs_logged_to_sink(self):
        events = []
        integ = make_integration(seed=9, steps=(100,),
                                 sink=lambda e, p: events.append((e, p)))
        integ.decide_route(make_request(), self.authoritative)
        self.assertEqual([e for e, _ in events], ["station_lm.shadow_pair"])
        pair = events[0][1]
        self.assertEqual(pair["authoritative_route"], "local")
        self.assertIsNotNone(pair["advisory_receipt_hash"])

    def test_canary_gate_skips_advisory(self):
        integ = make_integration(steps=(1,))
        # Find a digest outside the 1% bucket.
        skipped = None
        for i in range(500):
            req = make_request(f"t{i}")
            if not integ.canary.admit(req.request_digest):
                skipped = req
                break
        self.assertIsNotNone(skipped)
        route = integ.decide_route(skipped, self.authoritative)
        self.assertEqual(route, "local")
        self.assertEqual(len(integ.pairs), 0)  # no advisory observation logged

    def test_rollback_latch_falls_back_with_receipt(self):
        monitor = RollbackMonitor()
        events = []
        integ = make_integration(mode="authority_violation", monitor=monitor,
                                 steps=(100,),
                                 sink=lambda e, p: events.append((e, p)))
        # First decision latches the monitor via the provider receipt.
        integ.decide_route(make_request(), self.authoritative)
        self.assertTrue(monitor.triggered)
        # Next decision: immediate deterministic fallback, receipted.
        route = integ.decide_route(make_request("t2"), self.authoritative)
        self.assertEqual(route, "local")
        self.assertEqual(len(integ.fallback_receipts), 1)
        receipt = integ.fallback_receipts[0]
        self.assertEqual(receipt["route"], "local")
        self.assertIn("rollback_triggered", receipt["reason"])
        self.assertEqual(len(receipt["receipt_hash"]), 64)
        self.assertIn(("station_lm.fallback", receipt), events)
        self.assertTrue(integ.canary.demoted)
        self.assertEqual(integ.report()["canary_percent"], 0)

    def test_invalid_authoritative_route_rejected(self):
        integ = make_integration(steps=(100,))
        with self.assertRaises(ContractError):
            integ.decide_route(make_request(), lambda req: "elsewhere")


class StationServiceWiringTests(unittest.TestCase):
    def setUp(self):
        from residual.station.service import Station
        self.tmp = tempfile.TemporaryDirectory()
        self.station = Station(Path(self.tmp.name) / "store")

    def tearDown(self):
        self.tmp.cleanup()

    def _demo_project(self):
        from residual.station.service import demo_spec
        pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(pid)
        return pid

    def test_shadow_off_by_default(self):
        pid = self._demo_project()
        result = self.station.run_one(pid, "OPS-101")
        self.assertNotEqual(result["state"], "repair_required")
        events = [e for e in self.station.store.events(pid, 0, 100000)
                  if e["event_type"].startswith("station_lm.")]
        self.assertEqual(events, [])

    def test_shadow_wiring_logs_pairs_and_authoritative_wins(self):
        pid = self._demo_project()
        events = []
        integ = make_integration(seed=9, steps=(100,),
                                 sink=lambda e, p: events.append((e, p)))
        self.station.attach_station_lm(integ)
        self.station.store.settings({"station_lm": {"enabled": True}})
        result = self.station.run_one(pid, "OPS-101")
        self.assertEqual(result["state"], "review_ready")
        self.assertEqual(len(integ.pairs), 1)
        pair = integ.pairs[0]
        self.assertEqual(pair.authoritative_route, "local")  # OPS-101 spec route
        self.assertEqual(pair.task_id, "OPS-101")
        logged = [e for e in self.station.store.events(pid, 0, 100000)
                  if e["event_type"] == "station_lm.shadow_pair"]
        self.assertEqual(len(logged), 1)
        self.assertEqual(logged[0]["data"]["authoritative_route"], "local")

    def test_attach_validates_type(self):
        with self.assertRaises(ContractError):
            self.station.attach_station_lm(object())

    def test_attached_but_disabled_stays_silent(self):
        pid = self._demo_project()
        integ = make_integration(steps=(100,))
        self.station.attach_station_lm(integ)
        result = self.station.run_one(pid, "OPS-101")
        self.assertEqual(result["state"], "review_ready")
        self.assertEqual(len(integ.pairs), 0)


if __name__ == "__main__":
    unittest.main()
