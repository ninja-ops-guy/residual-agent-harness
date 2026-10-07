"""Native Ollama chat, model discovery and pull progress."""
import json
from ._http import HTTPAdapter,usage_values,finish,validate_url,encode
from ..core import ChatResponse,StreamChunk,ToolCall,ProviderError,Role


class OllamaAdapter(HTTPAdapter):
    name='ollama'
    allowed_extra={'keep_alive','think'}
    def __init__(self,base_url='http://localhost:11434',timeout=300.0,api_key=None):
        self.base_url=validate_url(base_url,self.name); self.timeout,self.api_key=timeout,api_key
    def _headers(self): return {**super()._headers(),**({'Authorization':'Bearer '+self.api_key} if self.api_key else {})}
    def _request_url(self,req,stream): return self.base_url+'/api/chat'
    @staticmethod
    def _msg(m):
        d={'role':m.role.value,'content':m.content}
        if m.role==Role.TOOL:
            d['tool_name']=m.name or ''; d['tool_call_id']=m.tool_call_id
        if m.tool_calls: d['tool_calls']=[{'function':{'name':t.name,'arguments':json.loads(t.arguments)}} for t in m.tool_calls]
        return d
    def _build_body(self,req,stream=False):
        body={'model':req.model,'messages':[self._msg(m) for m in req.messages],'stream':stream}; opts={}
        for key,v in [('temperature',req.temperature),('num_predict',req.max_tokens),('stop',list(req.stop) if req.stop else None),('seed',req.seed)]:
            if v is not None: opts[key]=v
        if opts: body['options']=opts
        if req.response_schema is not None: body['format']=req.response_schema
        if req.tools: body['tools']=[{'type':'function','function':{'name':t.name,'description':t.description,'parameters':t.parameters}} for t in req.tools]
        return self._options(req,body)
    @staticmethod
    def _usage(data): return usage_values(data.get('prompt_eval_count'),data.get('eval_count'),cached=data.get('prompt_eval_cached_count'))
    @staticmethod
    def _calls(msg):
        return tuple(ToolCall(t.get('id') or 'call_'+str(i),t['function']['name'],json.dumps(t['function']['arguments']) if isinstance(t['function']['arguments'],dict) else t['function']['arguments']) for i,t in enumerate(msg.get('tool_calls',[])))
    def _parse(self,data,model):
        if data.get('done') is not True: raise ProviderError(provider=self.name,code='stream_incomplete')
        msg=data['message']; calls=self._calls(msg)
        return ChatResponse(data.get('model') or model,msg.get('content') or '',calls,finish(data.get('done_reason') or ('tool_calls' if calls else 'stop')),self._usage(data),data)
    def _chunks(self,data,state):
        msg=data.get('message') or {}
        if msg.get('content'): yield StreamChunk(content=msg['content'])
        for t in self._calls(msg):
            state['tools']=True; yield StreamChunk(tool_call=t)
        if data.get('done') is True: yield StreamChunk(finish_reason=finish(data.get('done_reason') or ('tool_calls' if state.get('tools') else 'stop')),usage=self._usage(data))
    def list_models(self): return sorted(m['name'] for m in self._json(self.base_url+'/api/tags')['models'])
    def pull(self,model):
        if not isinstance(model,str) or not model or len(model)>200: raise ProviderError(provider=self.name,code='invalid_request')
        for event in self._events(self.base_url+'/api/pull',encode({'model':model,'stream':True}),ndjson=True):
            if event.get('error'): raise ProviderError(provider=self.name,code='invalid_response')
            yield event
    def supports_tools(self,model):
        return 'tools' in self._json(self.base_url+'/api/show',encode({'model':model})).get('capabilities',[])
