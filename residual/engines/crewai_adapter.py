from __future__ import annotations
import time
from typing import Any
from ._isolated import run_isolated
from .protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec

def _kickoff(crew: Any, inputs: dict) -> Any:
    for attr in ("human_input","human_input_enabled","hitl","require_human_input"):
        if hasattr(crew,attr):
            try: setattr(crew,attr,False)
            except Exception: pass
    if not hasattr(crew,"kickoff"): raise TypeError("CrewAI object must provide kickoff()")
    return crew.kickoff(inputs=inputs)

class CrewAIEngine:
    name="crewai"; capability_class="multi_agent"; locality="local"
    def __init__(self,crew:Any,*,version="unknown",capabilities=("agent",),timeout_s=300.0): self.crew,self.version,self._capabilities,self._timeout_s=crew,version,frozenset(capabilities),timeout_s
    def supports(self,capability): return capability in self._capabilities
    def health(self): return EngineHealth.HEALTHY if self.crew is not None else EngineHealth.UNAVAILABLE
    def execute(self,task:TaskSpec,context:ContextAssembly)->EngineResult:
        t0=time.monotonic(); raw=run_isolated(_kickoff,self.crew,{"task":task.input,"context":dict(context.values)},timeout_s=self._timeout_s); norm=self.normalize(raw)
        return EngineResult(norm.candidate,norm.tool_calls,norm.token_usage,int((time.monotonic()-t0)*1000),norm.engine_trace,norm.raw_metadata)
    def normalize(self,raw_output): return EngineResult(candidate=getattr(raw_output,"raw",raw_output),raw_metadata={"adapter":self.name,"residual_hitl_authoritative":True})
