from ai_providers import ChatResponse
from residual.eval_frozen import live
from residual.eval_frozen.workload import development_workload


class FakeProvider:
    name = "ollama"
    def list_models(self):
        return ["tiny:test"]
    def chat(self, req):
        return ChatResponse(
            model=req.model,
            content="42",
            usage={"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8},
        )


class FakeRegistry:
    def get(self, name):
        assert name == "ollama"
        return FakeProvider()


def test_live_worker_uses_provider_and_real_usage(monkeypatch):
    monkeypatch.setattr(live, "DEFAULT_REGISTRY", FakeRegistry())
    task = development_workload().task("arith-01")
    obs = live.run_live_worker(task, 0, provider="ollama", model="tiny:test")
    assert obs.correct is True
    assert obs.content == "42"
    assert obs.input_tokens == 7
    assert obs.output_tokens == 1
    assert obs.latency_ms >= 0


def test_probe_ollama_fails_closed_for_missing_model(monkeypatch):
    monkeypatch.setattr(live, "DEFAULT_REGISTRY", FakeRegistry())
    try:
        live.probe_provider(provider="ollama", model="missing:test")
    except Exception as exc:
        assert getattr(exc, "code", None) == "model_not_found"
    else:
        raise AssertionError("missing Ollama model must fail closed")
