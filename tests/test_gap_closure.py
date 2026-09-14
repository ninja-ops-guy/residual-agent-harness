import asyncio
import unittest
from types import SimpleNamespace

from residual.async_io import AsyncTelemetryClient, AsyncObservationSink
from residual.engines import CapabilityRouter, EngineHealth, EngineResult
from residual.lifecycle import ModuleLifecycleBus, bind_trajectory, bind_tui
from residual.observability import MetricsRegistry, ObservationMetricsBridge, render_prometheus


class Engine:
    version = "1"
    capability_class = "test"

    def __init__(self, name, locality):
        self.name, self.locality = name, locality

    def supports(self, capability):
        return capability == "x"

    def health(self):
        return EngineHealth.HEALTHY

    def normalize(self, value):
        return EngineResult(value)

    def execute(self, task, context):
        return EngineResult(task.input)


class GapClosureTests(unittest.TestCase):
    def test_router_is_deterministic_and_local_first(self):
        router = CapabilityRouter()
        router.register(Engine("z-cloud", "cloud"), ("x",))
        router.register(Engine("a-local", "local"), ("x",))
        self.assertEqual(router.select("x").name, "a-local")

    def test_lifecycle_bus_is_crash_isolated(self):
        bus = ModuleLifecycleBus()
        seen = []
        bus.subscribe("x", lambda kind, payload: (_ for _ in ()).throw(RuntimeError()))
        bus.subscribe("x", lambda kind, payload: seen.append(payload["v"]))
        bus.emit("x", {"v": 1})
        self.assertEqual(seen, [1])

    def test_trajectory_binding_records_on_close(self):
        class Recorder:
            def __init__(self):
                self.calls = []

            def record(self, spec_hash, steps, brakes, outcome):
                self.calls.append((spec_hash, steps, brakes, outcome))
                return "trajectory"

        bus = ModuleLifecycleBus()
        recorder = Recorder()
        bind_trajectory(bus, recorder)
        bus.emit("run_opened", {"run_id": "r1"})
        bus.emit("custom", {"event": "check_evaluated", "run_id": "r1",
                            "check_name": "mechanical", "check_type": "mechanical",
                            "result": "pass", "duration_ms": 2.0})
        result = SimpleNamespace(run_id="r1", spec_hash="a" * 64,
                                 tripped_brakes=(), outcome=SimpleNamespace(value="success"))
        bus.emit("run_closed", {"run_id": "r1", "result": result})
        self.assertEqual(len(recorder.calls), 1)
        self.assertEqual(recorder.calls[0][1][0].verdict, "pass")

    def test_tui_binding_consumes_wildcard_events(self):
        class Collector:
            def __init__(self):
                self.seen = []

            def on_event(self, kind, payload):
                self.seen.append((kind, payload["v"]))

        bus = ModuleLifecycleBus()
        collector = Collector()
        binding = bind_tui(bus, collector)
        bus.emit("checkpoint", {"v": 3})
        self.assertEqual(collector.seen, [("checkpoint", 3)])
        binding.close()
        bus.emit("checkpoint", {"v": 4})
        self.assertEqual(collector.seen, [("checkpoint", 3)])

    def test_metrics_bridge(self):
        registry = MetricsRegistry()
        bridge = ObservationMetricsBridge(registry)
        bridge("llm.response", {"provider": "p", "usage": {"total_tokens": 7}})
        self.assertIn('residual_tokens_total{provider="p"} 7.0', render_prometheus(registry))


class AsyncGapTests(unittest.IsolatedAsyncioTestCase):
    async def test_telemetry_cache(self):
        async def fetch():
            return {"ok": 1}

        client = AsyncTelemetryClient(fetch, refresh_interval_s=.01, max_telemetry_age_s=1)
        client.start()
        await asyncio.sleep(.03)
        self.assertEqual(client.get_current_metrics(), {"ok": 1})
        await client.cancel()

    async def test_sink_flush(self):
        batches = []

        async def down(batch):
            batches.extend(batch)

        sink = AsyncObservationSink(down, flush_interval_s=.01)
        sink.emit("x", {"a": 1})
        await sink.flush()
        self.assertEqual(batches[0]["kind"], "x")


if __name__ == "__main__":
    unittest.main()
