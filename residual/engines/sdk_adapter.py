from __future__ import annotations
import time
from typing import Any, Callable
from ._isolated import run_isolated
from .protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec

def _call(fn:Callable,task_input:Any,context:dict)->Any: return fn(task_input,context)
class _SDKEngine:
    capability_class="sdk_agent"; locality="cloud"
    def __init__(self,execute_fn:Callable,*,version="unknown",capabilities=("agent",),timeout_s=300.0): self._fn,self.version,self._capabilities,self._timeout_s=execute_fn,version,frozenset(capabilities),timeout_s
    def supports(self,capability): return capability in self._capabilities
    def health(self): return EngineHealth.HEALTHY if callable(self._fn) else EngineHealth.UNAVAILABLE
    def execute(self,task:TaskSpec,context:ContextAssembly)->EngineResult:
        t0=time.monotonic(); raw=run_isolated(_call,self._fn,task.input,dict(context.values),timeout_s=self._timeout_s); norm=self.normalize(raw)
        return EngineResult(norm.candidate,norm.tool_calls,norm.token_usage,int((time.monotonic()-t0)*1000),norm.engine_trace,norm.raw_metadata)
    def normalize(self,raw_output):
        refused=bool(raw_output.get("refused") or raw_output.get("refusal")) if isinstance(raw_output,dict) else False
        candidate=raw_output.get("output",raw_output.get("candidate",raw_output)) if isinstance(raw_output,dict) else raw_output
        return EngineResult(candidate=candidate,raw_metadata={"adapter":self.name,"sdk_refusal_advisory":refused,"residual_policy_authoritative":True})
class ClaudeSDKEngine(_SDKEngine): name="claude-sdk"
class OpenAIAssistantsEngine(_SDKEngine): name="openai-assistants"
