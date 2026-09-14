import asyncio,unittest
from residual.async_io import AsyncTelemetryClient,AsyncObservationSink
from residual.engines import CapabilityRouter,ContextAssembly,EngineHealth,EngineResult,TaskSpec
from residual.lifecycle import ModuleLifecycleBus
from residual.observability import MetricsRegistry,ObservationMetricsBridge,render_prometheus

class Engine:
    version="1"; capability_class="test"
    def __init__(self,name,locality): self.name,self.locality=name,locality
    def supports(self,c): return c=="x"
    def health(self): return EngineHealth.HEALTHY
    def normalize(self,x): return EngineResult(x)
    def execute(self,t,c): return EngineResult(t.input)

class GapClosureTests(unittest.TestCase):
    def test_router_is_deterministic_and_local_first(self):
        r=CapabilityRouter(); r.register(Engine("z-cloud","cloud"),("x",)); r.register(Engine("a-local","local"),("x",)); self.assertEqual(r.select("x").name,"a-local")
    def test_lifecycle_bus_is_crash_isolated(self):
        bus=ModuleLifecycleBus(); seen=[]; bus.subscribe("x",lambda k,p:(_ for _ in ()).throw(RuntimeError())); bus.subscribe("x",lambda k,p:seen.append(p["v"])); bus.emit("x",{"v":1}); self.assertEqual(seen,[1])
    def test_metrics_bridge(self):
        reg=MetricsRegistry(); bridge=ObservationMetricsBridge(reg); bridge("llm.response",{"provider":"p","usage":{"total_tokens":7}}); self.assertIn('residual_tokens_total{provider="p"} 7.0',render_prometheus(reg))

class AsyncGapTests(unittest.IsolatedAsyncioTestCase):
    async def test_telemetry_cache(self):
        async def fetch(): return {"ok":1}
        c=AsyncTelemetryClient(fetch,refresh_interval_s=.01,max_telemetry_age_s=1); c.start(); await asyncio.sleep(.03); self.assertEqual(c.get_current_metrics(),{"ok":1}); await c.cancel()
    async def test_sink_flush(self):
        batches=[]
        async def down(batch): batches.extend(batch)
        s=AsyncObservationSink(down,flush_interval_s=.01); s.emit("x",{"a":1}); await s.flush(); self.assertEqual(batches[0]["kind"],"x")

if __name__=="__main__": unittest.main()
