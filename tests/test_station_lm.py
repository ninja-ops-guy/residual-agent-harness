"""StationLM provider stub tests. Fake backend only; no network, no real models."""
import asyncio
import json
import unittest

from residual.core import ContractError, digest
from ai_providers.core import ChatRequest, Message, ProviderError, Role
from residual.station_lm import (
    DecisionRequest, FakeDecisionModel, ModelManifest, ModelRegistry,
    RollbackMonitor, ShadowModeHook, StationLMProvider, validate_proposal,
)

ROUTES = ("local:qwen2.5-coder:7b", "cloud:fallback", "defer")
HASH = "a" * 64


def make_request(task_id="task1", routes=ROUTES, deadline_ms=2000, packet=None):
    return DecisionRequest(task_id=task_id, packet=packet or {"goal": "x"},
                           allowed_routes=routes, deadline_ms=deadline_ms)


def make_provider(mode="ok", seed=7, **kwargs):
    backend = FakeDecisionModel(seed=seed, mode=mode,
                                model_id=kwargs.pop("model_id", "fake-decision-v0"),
                                **kwargs)
    return StationLMProvider(backend, default_route="defer")


class FakeDecisionModelTests(unittest.TestCase):
    def test_deterministic_across_instances(self):
        req = make_request()
        a = FakeDecisionModel(seed=42).decide(req)
        b = FakeDecisionModel(seed=42).decide(req)
        self.assertEqual(a, b)
        self.assertIn(a["route"], ROUTES)
        self.assertTrue(0.0 <= a["confidence"] <= 1.0)

    def test_seed_changes_output_surface(self):
        outs = {json.dumps(FakeDecisionModel(seed=s).decide(make_request(f"t{i}")), sort_keys=True)
                for s in (1, 2) for i in range(3)}
        self.assertGreater(len(outs), 1)

    def test_canned_decision_overrides_rules(self):
        req = make_request()
        canned = {req.request_digest: {"route": "defer", "confidence": 0.9,
                                       "escalate": False, "rationale": "pinned"}}
        model = FakeDecisionModel(seed=1, canned=canned)
        self.assertEqual(model.decide(req)["route"], "defer")

    def test_manifest_is_complete_and_deterministic(self):
        m = FakeDecisionModel(seed=3).manifest()
        for key in ("model_id", "model_hash", "tokenizer_hash",
                    "dataset_manifest_hash", "training_config", "code_commit",
                    "seed", "qualification_receipt", "model_card"):
            self.assertIn(key, m)
        self.assertEqual(m, FakeDecisionModel(seed=3).manifest())

    def test_invalid_constructor_args_fail_closed(self):
        for kwargs in ({"seed": -1}, {"seed": "x"}, {"mode": "nope"},
                       {"model_id": "bad id!"}):
            with self.assertRaises(ContractError):
                FakeDecisionModel(**kwargs)


class SchemaValidationTests(unittest.TestCase):
    def test_valid_proposal_passes(self):
        req = make_request()
        p = validate_proposal({"route": "defer", "confidence": 0.5,
                               "escalate": True, "rationale": "why"}, req)
        self.assertEqual(p.route, "defer")
        self.assertTrue(p.advisory)

    def test_rejects_bad_schema(self):
        req = make_request()
        bad = [
            "not a dict",
            {"route": "defer"},  # missing keys
            {"route": "defer", "confidence": 0.5, "escalate": True,
             "rationale": "", "execute": True},  # extra key
            {"route": "nope", "confidence": 0.5, "escalate": True, "rationale": ""},
            {"route": "defer", "confidence": 1.5, "escalate": True, "rationale": ""},
            {"route": "defer", "confidence": float("nan"), "escalate": True, "rationale": ""},
            {"route": "defer", "confidence": 0.5, "escalate": "yes", "rationale": ""},
            {"route": "defer", "confidence": 0.5, "escalate": True, "rationale": 3},
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                validate_proposal(raw, req)


class ProviderPipelineTests(unittest.TestCase):
    def test_accepted_decision_is_receipted_and_advisory(self):
        provider = make_provider()
        result = provider.decide(make_request())
        self.assertFalse(result.fallback)
        self.assertEqual(result.receipt.outcome, "accepted")
        self.assertTrue(result.proposal.advisory)
        self.assertEqual(len(result.receipt.receipt_hash), 64)
        self.assertEqual(result.receipt, provider.receipts[-1])

    def test_fail_closed_on_invalid_schema(self):
        result = make_provider(mode="invalid_schema").decide(make_request())
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "schema_invalid")
        self.assertEqual(result.proposal.route, "defer")
        self.assertTrue(result.proposal.escalate)
        self.assertEqual(result.proposal.confidence, 0.0)

    def test_fail_closed_on_authority_violation(self):
        result = make_provider(mode="authority_violation").decide(make_request())
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "policy_violation")

    def test_fail_closed_on_missing_artifact(self):
        result = make_provider(mode="missing_artifact").decide(make_request())
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "missing_model_artifact")

    def test_fail_closed_with_no_backend(self):
        provider = StationLMProvider(None, default_route="defer")
        result = provider.decide(make_request())
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "missing_model_artifact")

    def test_fail_closed_on_timeout(self):
        result = make_provider(mode="timeout").decide(make_request(deadline_ms=30))
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "timeout")

    def test_fail_closed_on_backend_exception(self):
        class Broken:
            model_id = "brokenmodel"
            def manifest(self): return {}
            def available(self): return True
            def decide(self, request): raise RuntimeError("boom")
        provider = StationLMProvider(Broken(), default_route="defer")
        result = provider.decide(make_request())
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "backend_error")

    def test_default_route_outside_allowed_uses_first_route(self):
        provider = StationLMProvider(FakeDecisionModel(mode="invalid_schema"),
                                     default_route="not-in-routes")
        result = provider.decide(make_request())
        self.assertEqual(result.proposal.route, ROUTES[0])

    def test_custom_policy_is_enforced(self):
        provider = StationLMProvider(FakeDecisionModel(seed=5), default_route="defer",
                                     policy=lambda raw, proposal: "always_deny")
        result = provider.decide(make_request())
        self.assertTrue(result.fallback)
        self.assertEqual(result.receipt.fallback_reason, "policy_violation")

    def test_provider_protocol_surface(self):
        provider = make_provider()
        self.assertEqual(provider.name, "station_lm")
        self.assertFalse(provider.supports_tools("anything"))
        self.assertEqual(provider.list_models(), ["fake-decision-v0"])
        packet = {"task_id": "task1", "allowed_routes": list(ROUTES), "goal": "x"}
        req = ChatRequest(model="station_lm",
                          messages=(Message(Role.USER, json.dumps(packet)),))
        resp = provider.chat(req)
        payload = json.loads(resp.content)
        self.assertEqual(resp.finish_reason, "stop")
        self.assertTrue(resp.metadata["advisory"])
        self.assertIn(payload["proposal"]["route"], ROUTES)
        chunks = list(provider.stream(req))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].finish_reason, "stop")
        async_resp = asyncio.run(provider.achat(req))
        self.assertEqual(async_resp.content, resp.content)
        async def collect():
            return [c async for c in provider.astream(req)]
        self.assertEqual(len(asyncio.run(collect())), 1)

    def test_chat_rejects_non_json_request(self):
        provider = make_provider()
        req = ChatRequest(model="station_lm",
                          messages=(Message(Role.USER, "not json"),))
        with self.assertRaises(ProviderError):
            provider.chat(req)


class ModelRegistryTests(unittest.TestCase):
    def manifest(self, model_id="modelA", receipt=None):
        return ModelManifest(
            model_id=model_id, model_hash=HASH, tokenizer_hash="b" * 64,
            dataset_manifest_hash="c" * 64, training_config={"lr": 0.1},
            code_commit="d" * 40, seed=1, qualification_receipt=receipt,
            model_card={"name": model_id, "version": "1",
                        "intended_use": "advisory routing", "limitations": "stub"})

    def test_manifest_validation(self):
        for kwargs in ({"model_hash": "zz"}, {"code_commit": "XYZ"},
                       {"seed": -1}, {"model_card": {"name": "x"}},
                       {"qualification_receipt": "short"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ContractError):
                self.manifest(**kwargs)
        with self.assertRaises(ContractError):
            ModelManifest.from_dict({"model_id": "x", "bogus": 1})

    def test_happy_path_state_machine(self):
        reg = ModelRegistry()
        reg.register(self.manifest())
        self.assertEqual(reg.state_of("modelA"), "candidate")
        reg.transition("modelA", "staged")
        reg.transition("modelA", "qualified", qualification_receipt="e" * 64)
        self.assertEqual(reg.state_of("modelA"), "qualified")
        self.assertEqual(reg.qualified_manifest("modelA").model_id, "modelA")
        history = reg.get("modelA").history
        self.assertEqual([h["to"] for h in history],
                         ["candidate", "staged", "qualified"])
        self.assertEqual(history[-1]["qualification_receipt"], "e" * 64)

    def test_qualification_requires_receipt(self):
        reg = ModelRegistry()
        reg.register(self.manifest())
        reg.transition("modelA", "staged")
        with self.assertRaises(ContractError):
            reg.transition("modelA", "qualified")
        # Manifest-attached receipt also satisfies the gate.
        reg.register(self.manifest("modelB", receipt="f" * 64))
        reg.transition("modelB", "staged")
        reg.transition("modelB", "qualified")
        self.assertEqual(reg.state_of("modelB"), "qualified")

    def test_illegal_transitions_rejected(self):
        reg = ModelRegistry()
        reg.register(self.manifest())
        for target in ("qualified", "rejected"):  # rejected needs reason
            with self.assertRaises(ContractError):
                reg.transition("modelA", target)
        with self.assertRaises(ContractError):
            reg.transition("modelA", "bogus")
        with self.assertRaises(ContractError):
            reg.transition("ghost", "staged")
        reg.transition("modelA", "rejected", reason="failed qualification")
        with self.assertRaises(ContractError):  # rejected is terminal
            reg.transition("modelA", "candidate")

    def test_rollback_and_reregister_rules(self):
        reg = ModelRegistry()
        reg.register(self.manifest())
        with self.assertRaises(ContractError):
            reg.register(self.manifest("modelA", receipt="e" * 64))  # changed manifest
        self.assertIs(reg.register(self.manifest()).manifest, self.manifest())
        reg.transition("modelA", "staged")
        reg.transition("modelA", "qualified", qualification_receipt="e" * 64)
        with self.assertRaises(ContractError):
            reg.rollback("modelA", "")
        reg.rollback("modelA", "schema-invalid spike")
        self.assertEqual(reg.state_of("modelA"), "rejected")
        with self.assertRaises(ContractError):
            reg.qualified_manifest("modelA")


class RollbackMonitorTests(unittest.TestCase):
    def provider_with_monitor(self, mode, **monitor_kwargs):
        monitor = RollbackMonitor(**monitor_kwargs)
        provider = StationLMProvider(FakeDecisionModel(mode=mode),
                                   default_route="defer", monitor=monitor)
        return provider, monitor

    def test_immediate_authority_and_artifact_triggers(self):
        for mode, condition in (("authority_violation", "authority_violation"),
                                ("missing_artifact", "missing_model_artifact")):
            provider, monitor = self.provider_with_monitor(mode)
            provider.decide(make_request())
            self.assertTrue(monitor.triggered)
            self.assertEqual(monitor.trigger.condition, condition)
            # Latched: subsequent calls short-circuit to fallback.
            result = provider.decide(make_request(task_id="task2"))
            self.assertEqual(result.receipt.fallback_reason, "rollback_triggered")

    def test_schema_invalid_rate_spike(self):
        provider, monitor = self.provider_with_monitor(
            "invalid_schema", window=10, schema_invalid_rate=0.5)
        provider.decide(make_request())
        self.assertFalse(monitor.triggered)  # 1/1 is 100% >= 0.5 -> immediate
        # With a healthy mix the rate stays below threshold.
        monitor.reset()
        provider2 = StationLMProvider(FakeDecisionModel(seed=1), default_route="defer",
                                      monitor=monitor)
        for i in range(4):
            provider2.decide(make_request(task_id=f"ok{i}"))
        self.assertFalse(monitor.triggered)
        provider3 = StationLMProvider(FakeDecisionModel(mode="invalid_schema"),
                                      default_route="defer", monitor=monitor)
        provider3.decide(make_request(task_id="bad1"))
        self.assertFalse(monitor.triggered)
        provider3.decide(make_request(task_id="bad2"))
        self.assertTrue(monitor.triggered)
        self.assertEqual(monitor.trigger.condition, "schema_invalid_rate_spike")

    def test_false_non_escalation_spike(self):
        monitor = RollbackMonitor(window=10, false_non_escalation_rate=0.5)
        provider = StationLMProvider(FakeDecisionModel(mode="non_escalation"),
                                     default_route="defer", monitor=monitor)
        for i in range(2):
            result = provider.decide(make_request(task_id=f"risk{i}"))
            monitor._records[-1]["expected_escalation"] = True  # authoritative truth
        self.assertTrue(monitor.triggered)
        self.assertEqual(monitor.trigger.condition, "false_non_escalation_spike")

    def test_latency_regression(self):
        monitor = RollbackMonitor(window=10, latency_regression_factor=2.0,
                                  baseline_latency_ms=1)
        provider = StationLMProvider(FakeDecisionModel(seed=1, latency_ms=50),
                                     default_route="defer", monitor=monitor)
        provider.decide(make_request())
        self.assertTrue(monitor.triggered)
        self.assertEqual(monitor.trigger.condition, "latency_regression")

    def test_reset_clears_latch(self):
        provider, monitor = self.provider_with_monitor("missing_artifact")
        provider.decide(make_request())
        self.assertTrue(monitor.triggered)
        monitor.reset()
        self.assertFalse(monitor.triggered)

    def test_threshold_validation(self):
        for kwargs in ({"window": 0}, {"schema_invalid_rate": 0},
                       {"false_non_escalation_rate": 2},
                       {"latency_regression_factor": 0.5},
                       {"baseline_latency_ms": 0}):
            with self.assertRaises(ContractError):
                RollbackMonitor(**kwargs)


class ShadowModeTests(unittest.TestCase):
    def authoritative(self, request):
        return "local:qwen2.5-coder:7b"

    def test_shadow_returns_authoritative_and_logs_pair(self):
        hook = ShadowModeHook(self.authoritative, make_provider(seed=9))
        route = hook.decide(make_request())
        self.assertEqual(route, "local:qwen2.5-coder:7b")
        self.assertEqual(len(hook.pairs), 1)
        pair = hook.pairs[0]
        self.assertEqual(pair.authoritative_route, route)
        self.assertIsNotNone(pair.advisory_receipt_hash)
        self.assertIn(pair.agreement, (True, False))
        self.assertEqual(pair.advisory_fallback, False)

    def test_shadow_contains_advisory_failure(self):
        class Exploding(StationLMProvider):
            def decide(self, request): raise RuntimeError("kaboom")
        hook = ShadowModeHook(self.authoritative,
                              Exploding(FakeDecisionModel(), default_route="defer"))
        route = hook.decide(make_request())
        self.assertEqual(route, "local:qwen2.5-coder:7b")  # unaffected
        pair = hook.pairs[0]
        self.assertIsNone(pair.agreement)
        self.assertTrue(pair.advisory_fallback)

    def test_shadow_rejects_bad_authoritative_route(self):
        hook = ShadowModeHook(lambda req: "elsewhere", make_provider())
        with self.assertRaises(ContractError):
            hook.decide(make_request())

    def test_sink_and_disagreement_report(self):
        captured = []
        hook = ShadowModeHook(self.authoritative, make_provider(seed=9),
                              sink=captured.append)
        hook.decide(make_request())
        hook.decide(make_request(task_id="task2"))
        self.assertEqual(len(captured), 2)
        report = hook.disagreement_report()
        self.assertEqual(report["pairs"], 2)
        self.assertEqual(len(report["pairs_digest"]), 64)


if __name__ == "__main__":
    unittest.main()
