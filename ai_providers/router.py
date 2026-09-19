"""Explicit, bounded failover with one observed receipt for every actual attempt."""
from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, replace
from .core import ChatRequest, ChatResponse, ProviderError, ProviderName
from .registry import DEFAULT_REGISTRY


@dataclass(frozen=True)
class ModelRef:
    provider: str
    model: str
    @staticmethod
    def parse(s):
        if not isinstance(s,str) or not s or len(s)>600: raise ProviderError(code='invalid_request')
        if ':' in s:
            p,m=s.split(':',1)
            if p not in {v.value for v in ProviderName} or not m: raise ProviderError(code='unknown_provider')
            return ModelRef(p,m)
        return ModelRef('default',s)


class Router:
    def __init__(self,registry=None,default_provider='openai',observation_bus=None,before_attempt=None,after_attempt=None):
        self.registry=registry if registry is not None else DEFAULT_REGISTRY
        self.default_provider=ProviderName(default_provider).value
        self.bus=observation_bus
        # Accounting/policy callbacks are authoritative and deliberately NOT swallowed.
        self.before_attempt,self.after_attempt=before_attempt,after_attempt
        self.observation_errors=0

    def _emit(self,kind,payload,tags):
        if self.bus is None: return
        try:
            from observation_layer import ObservationKind
            self.bus.emit(ObservationKind(kind),payload,tags=tags,source='ai_providers.router')
        except Exception: self.observation_errors+=1

    def _candidates(self,model,failover):
        candidates=[model]+list(failover or [])
        if len(candidates)>5 or len(set(candidates))!=len(candidates): raise ProviderError(code='invalid_request')
        return candidates

    def _begin(self,candidate,req,request_id,index,stream=False):
        ref=ModelRef.parse(candidate)
        name=self.default_provider if ref.provider=='default' else ref.provider
        try: provider=self.registry.get(name)
        except ProviderError as error:
            self._emit('llm.failed', {'request_id':request_id,'attempt':index,'status':'not_dispatched','error':error.to_dict()}, {'provider':name,'model':ref.model,'request_id':request_id})
            raise
        routed=replace(req,model=ref.model)
        meta={'request_id':request_id,'attempt':index,'provider':name,'model':ref.model,'request_bytes':len(provider.wire_bytes(routed,stream)) if hasattr(provider,'wire_bytes') else None}
        if self.before_attempt: self.before_attempt(provider,routed,meta)
        tags={'provider':name,'model':ref.model,'request_id':request_id}
        self._emit('llm.request',{**meta,'n_messages':len(req.messages)},tags)
        return provider,routed,meta,tags,time.monotonic()

    def _end(self,meta,tags,start,resp=None,error=None):
        receipt={**meta,'elapsed_ms':round((time.monotonic()-start)*1000),'status':'failed' if error else 'completed',
                 'usage':dict(resp.usage) if resp else {},'finish_reason':resp.finish_reason if resp else None,
                 'response_metadata':dict(resp.metadata) if resp else {},
                 'error':error.to_dict() if error else None}
        self._emit('llm.failed' if error else 'llm.response',receipt,tags)
        if self.after_attempt: self.after_attempt(receipt)

    def chat(self,model,req,failover=None):
        request_id=uuid.uuid4().hex; last=None
        for index,candidate in enumerate(self._candidates(model,failover),1):
            provider,routed,meta,tags,start=self._begin(candidate,req,request_id,index)
            try:
                resp=provider.chat(routed)
                if not isinstance(resp,ChatResponse): raise ProviderError(provider=provider.name,code='invalid_response')
            except Exception as e:
                error=e if isinstance(e,ProviderError) else ProviderError(provider=provider.name,code='invalid_response')
                self._end(meta,tags,start,error=error); last=error
                if error.retryable: continue
                raise error from None
            self._end(meta,tags,start,resp=resp)
            return resp
        raise last or ProviderError(code='exhausted')

    def stream(self,model,req,failover=None):
        request_id=uuid.uuid4().hex; last=None
        for index,candidate in enumerate(self._candidates(model,failover),1):
            provider,routed,meta,tags,start=self._begin(candidate,req,request_id,index,stream=True)
            emitted=False; usage={}; reason='unknown'; count=0
            try:
                for chunk in provider.stream(routed):
                    emitted=True; count+=1; usage.update(chunk.usage)
                    if chunk.finish_reason: reason=chunk.finish_reason
                    self._emit('llm.stream_chunk',{'request_id':request_id,'attempt':index,'chunk':count,'content_chars':len(chunk.content or ''),'has_tool_call':chunk.tool_call is not None},tags)
                    yield chunk
            except GeneratorExit:
                self._end(meta,tags,start,error=ProviderError(provider=provider.name,code='stream_incomplete'))
                raise
            except Exception as e:
                error=e if isinstance(e,ProviderError) else ProviderError(provider=provider.name,code='invalid_response')
                self._end(meta,tags,start,error=error); last=error
                # Never concatenate a different model's stream onto an emitted prefix.
                if error.retryable and not emitted: continue
                raise error from None
            self._end(meta,tags,start,resp=ChatResponse(routed.model,'',finish_reason=reason,usage=usage))
            return
        raise last or ProviderError(code='exhausted')

    async def achat(self,model,req,failover=None):
        return await asyncio.to_thread(self.chat,model,req,failover)

    async def astream(self,model,req,failover=None):
        # Reuse the bounded-read/cancellation implementation; no optional SDK needed.
        from .adapters._http import HTTPAdapter
        router=self
        class Bound(HTTPAdapter):
            def stream(self,ignored): return router.stream(model,req,failover)
        async for chunk in Bound().astream(req): yield chunk
