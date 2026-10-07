from __future__ import annotations
import time
from typing import Any
from ._isolated import run_isolated
from .protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec

def _invoke_graph(graph: Any, payload: dict) -> Any:
    if hasattr(graph, "invoke"): return graph.invoke(payload)
    if hasattr(graph, "run"): return graph.run(payload)
    raise TypeError("LangGraph object must provide invoke() or run()")

class LangGraphEngine:
    name = "langgraph"; capability_class = "agent_graph"; locality = "local"
    def __init__(self, graph: Any, *, version="unknown", capabilities=("agent",), timeout_s=300.0):
        self.graph, self.version, self._capabilities, self._timeout_s = graph, version, frozenset(capabilities), timeout_s
    def supports(self, capability): return capability in self._capabilities
    def health(self): return EngineHealth.HEALTHY if self.graph is not None else EngineHealth.UNAVAILABLE
    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        t0=time.monotonic(); raw=run_isolated(_invoke_graph,self.graph,{"task":task.input,"context":dict(context.values)},timeout_s=self._timeout_s); result=self.normalize(raw)
        return EngineResult(result.candidate,result.tool_calls,result.token_usage,int((time.monotonic()-t0)*1000),result.engine_trace,result.raw_metadata)
    def normalize(self, raw_output):
        return EngineResult(candidate=raw_output.get("output",raw_output) if isinstance(raw_output,dict) else raw_output, raw_metadata={"adapter":self.name})
