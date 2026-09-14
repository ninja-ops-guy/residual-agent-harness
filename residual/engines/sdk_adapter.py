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
        if not isinstance(raw_output,dict):
            return EngineResult(candidate=candidate,raw_metadata={"adapter":self.name,"sdk_refusal_advisory":refused,"residual_policy_authoritative":True})
        token_usage=raw_output.get("token_usage")
        if token_usage is not None and (type(token_usage) is not int or token_usage < 0):
            token_usage=None
        tool_calls=raw_output.get("tool_calls",())
        if not isinstance(tool_calls,(list,tuple)) or any(not isinstance(x,dict) for x in tool_calls): tool_calls=()
        trace=raw_output.get("engine_trace",())
        if not isinstance(trace,(list,tuple)) or any(not isinstance(x,dict) for x in trace): trace=()
        supplied=raw_output.get("raw_metadata",{})
        if not isinstance(supplied,dict): supplied={}
        metadata={**supplied,"adapter":self.name,"sdk_refusal_advisory":refused,"residual_policy_authoritative":True}
        # Explicit top-level measurement fields are accepted for SDK callbacks so
        # evaluation can preserve provider-reported usage without parsing text.
        for key in ("provenance","gpu_time_ms","api_cost_usd","provider","model"):
            if key in raw_output: metadata[key]=raw_output[key]
        return EngineResult(candidate=candidate,tool_calls=tuple(tool_calls),token_usage=token_usage,
                            engine_trace=tuple(trace),raw_metadata=metadata)
class ClaudeSDKEngine(_SDKEngine): name="claude-sdk"
class OpenAIAssistantsEngine(_SDKEngine): name="openai-assistants"
