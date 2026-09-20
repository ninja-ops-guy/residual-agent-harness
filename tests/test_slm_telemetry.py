"""SLM telemetry tests: fake clocks, fake power samplers, no network/GPU."""
import io
import json
import pytest

from residual.telemetry.slm import (
    SLM_TELEMETRY_SCHEMA_VERSION, DecisionContextRecorder, PriceTable,
    Recorder, TelemetryConfig,
)


class FakeClock:
    def __init__(self):
        self.t = 1000.0
    def __call__(self):
        self.t += 0.25
        return self.t


class FakePower:
    def __init__(self, watts):
        self.watts = watts
    def sample_watts(self):
        return self.watts


def make_recorder(enabled=True, power=None):
    sink = io.StringIO()
    r = Recorder(TelemetryConfig(enabled=enabled), clock=FakeClock(),
                 wall_clock=FakeClock(), power_sampler=power, sink=sink)
    return r, sink


def lines(sink):
    return [json.loads(l) for l in sink.getvalue().strip().splitlines() if l]


def test_disabled_config_is_noop():
    r, sink = make_recorder(enabled=False, power=FakePower(100.0))
    assert r.record_inference_call(model="gpt-4o", tokens_in=10, tokens_out=5, latency_ms=3.0) == {}
    assert sink.getvalue() == ""


def test_realized_cost_from_pinned_price_table():
    r, sink = make_recorder(power=FakePower(200.0))
    ev = r.record_inference_call(model="gpt-4o", provider="openai",
                                 tokens_in=1_000_000, tokens_out=500_000,
                                 latency_ms=900.0, verification_status="verified_success")
    assert ev["estimate"] is False
    assert ev["cost"]["inference_usd"] == pytest.approx(2.50 + 5.00)
    assert ev["cost"]["energy_wh"] == pytest.approx(200.0 * 900.0 / 3_600_000.0)
    assert ev["energy_measurable"] is True
    assert ev["cost"]["frontier_calls"] == 1
    assert ev["price_table_version"]
    assert ev["schema_version"] == SLM_TELEMETRY_SCHEMA_VERSION
    assert ev["verification"]["status"] == "verified_success"
    assert r.model_call_counts["gpt-4o"] == 1 and r.frontier_call_count == 1


def test_unpriced_model_yields_null_cost_and_logged_degradation():
    r, sink = make_recorder(power=FakePower(None))
    ev = r.record_inference_call(model="mystery-model", tokens_in=1, tokens_out=1, latency_ms=1.0)
    assert ev["cost"]["inference_usd"] is None       # unknown stays unknown
    assert ev["energy_measurable"] is False
    reasons = [d["reason"] for d in r.degradations]
    assert "unpriced_model" in reasons and "power_unmeasurable" in reasons
    kinds = [e["kind"] for e in lines(sink)]
    assert "telemetry_degradation" in kinds


def test_decision_context_labels_counterfactuals_as_estimates():
    r, sink = make_recorder()
    d = DecisionContextRecorder(r)
    ev = d.record_decision(
        selected_model="ollama-local", selected_worker="w-1",
        alternatives=[{"model": "ollama-local", "worker_id": "w-1"},
                      {"model": "gpt-4o", "worker_id": None}],
        assumed_tokens_in=1000, assumed_tokens_out=500,
        escalation_required=False, escalation_taken=False)
    assert ev["estimate"] is True
    assert ev["selected"]["model"] == "ollama-local"
    alt = {a["model"]: a for a in ev["alternatives"]}
    assert alt["gpt-4o"]["estimate"] is True
    assert alt["gpt-4o"]["counterfactual_cost_usd"] == pytest.approx(
        (1000 * 2.50 + 500 * 10.00) / 1_000_000.0)
    assert alt["ollama-local"]["available"] is True


def test_escalation_outcome_vocabulary_and_correctness():
    r, sink = make_recorder()
    d = DecisionContextRecorder(r)
    ev = d.record_escalation_outcome(decision_id="d1", required=True, taken=False,
                                     classification="false_non_escalation")
    assert ev["escalation"]["classification"] == "false_non_escalation"
    assert ev["escalation_correct"] is False
    ev2 = d.record_escalation_outcome(decision_id="d2", required=False, taken=True,
                                      classification="unnecessary_escalation")
    assert ev2["escalation_correct"] is False


def test_operator_active_seconds_recorded():
    r, sink = make_recorder()
    ev = r.record_operator_active(seconds=120.0, worker_id="w-9")
    assert ev["cost"]["operator_active_seconds"] == 120.0


def test_fail_open_on_sink_write_error():
    class BadSink:
        def write(self, _):
            raise OSError("disk full")
    r = Recorder(TelemetryConfig(enabled=True), clock=FakeClock(),
                 wall_clock=FakeClock(), sink=BadSink())
    ev = r.record_inference_call(model="gpt-4o", tokens_in=1, tokens_out=1, latency_ms=1.0)
    assert ev["cost"]["inference_usd"] is not None   # event built despite sink failure
    assert any(d["reason"] == "sink_write_failed" for d in r.degradations)


def test_summary_reports_realized_totals_only():
    r, _ = make_recorder()
    r.record_inference_call(model="gpt-4o", tokens_in=1, tokens_out=1, latency_ms=1.0)
    s = r.summary()
    assert s["frontier_calls"] == 1 and "savings" not in json.dumps(s).lower()


def test_router_integration_fail_open():
    from ai_providers.core import ChatRequest, ChatResponse, Message, Role
    from ai_providers.router import Router

    class FakeRegistry:
        def get(self, name):
            class P:
                def chat(self, req):
                    return ChatResponse(req.model, "ok",
                                        usage={"prompt_tokens": 10, "completion_tokens": 4})
            return P()

    r, _ = make_recorder(power=FakePower(None))
    router = Router(registry=FakeRegistry(), default_provider="openai", slm_recorder=r)
    resp = router.chat("gpt-4o", ChatRequest("gpt-4o", (Message(Role.USER, "hi"),)))
    assert resp.content == "ok"
    kinds = [e["kind"] for e in r.events]
    assert "inference_call" in kinds
    call = next(e for e in r.events if e["kind"] == "inference_call")
    assert call["tokens"] == {"in": 10, "out": 4}
    assert call["cost"]["latency_ms"] is not None

    # Exploding recorder must not affect the authoritative route.
    class Boom:
        def record_inference_call(self, **kw):
            raise RuntimeError("boom")
    router2 = Router(registry=FakeRegistry(), default_provider="openai", slm_recorder=Boom())
    assert router2.chat("gpt-4o", ChatRequest("gpt-4o", (Message(Role.USER, "hi"),))).content == "ok"
    assert router2.observation_errors == 1
