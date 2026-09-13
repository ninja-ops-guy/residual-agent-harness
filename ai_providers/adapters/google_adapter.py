"""Gemini generateContent; API keys stay in headers and tool signatures round-trip."""
import json
from urllib.parse import quote,urlencode
from ._http import HTTPAdapter,usage_values,finish,validate_url
from ..core import ChatResponse,StreamChunk,ToolCall,Role,ProviderError


class GoogleAdapter(HTTPAdapter):
    name='google'
    def __init__(self,api_key=None,base_url='https://generativelanguage.googleapis.com/v1beta',timeout=120.0):
        self.base_url=validate_url(base_url,self.name); self.api_key,self.timeout=api_key,timeout
    def _headers(self): return {**super()._headers(),**({'x-goog-api-key':self.api_key} if self.api_key else {})}
    def _request_url(self,req,stream):
        model=req.model.removeprefix('models/')
        return self.base_url+'/models/'+quote(model,safe='')+(':streamGenerateContent?alt=sse' if stream else ':generateContent')
    @staticmethod
    def _msg(m):
        if m.role==Role.TOOL:
            if not m.name: raise ProviderError(provider='google',code='invalid_request')
            return {'role':'user','parts':[{'functionResponse':{'name':m.name,'id':m.tool_call_id,'response':{'result':m.content}}}]}
        parts=m.metadata.get('google_parts')
        if parts is None:
            parts=([{'text':m.content}] if m.content else [])+[{'functionCall':{'id':t.id,'name':t.name,'args':json.loads(t.arguments)}} for t in m.tool_calls]
        return {'role':'model' if m.role==Role.ASSISTANT else 'user','parts':parts}
    def _build_body(self,req,stream=False):
        body={'contents':[self._msg(m) for m in req.messages if m.role!=Role.SYSTEM]}
        system='\n'.join(m.content for m in req.messages if m.role==Role.SYSTEM)
        if system: body['systemInstruction']={'parts':[{'text':system}]}
        cfg={}
        if req.max_tokens is not None: cfg['maxOutputTokens']=req.max_tokens
        if req.temperature is not None: cfg['temperature']=req.temperature
        if req.stop: cfg['stopSequences']=list(req.stop)
        if req.seed is not None: cfg['seed']=req.seed
        if req.response_schema is not None: cfg.update(responseMimeType='application/json',responseJsonSchema=req.response_schema)
        if cfg: body['generationConfig']=cfg
        if req.tools: body['tools']=[{'functionDeclarations':[{'name':t.name,'description':t.description,'parameters':t.parameters} for t in req.tools]}]
        return self._options(req,body)
    @staticmethod
    def _usage(data):
        u=data.get('usageMetadata') or {}; out=u.get('candidatesTokenCount')
        if out is not None: out += u.get('thoughtsTokenCount',0)
        return usage_values(u.get('promptTokenCount'),out,u.get('totalTokenCount'),u.get('cachedContentTokenCount'))
    def _parse(self,data,model):
        if data.get('promptFeedback',{}).get('blockReason'): return ChatResponse(model,'',finish_reason='content_filter',usage=self._usage(data))
        c=data['candidates'][0]; parts=c.get('content',{}).get('parts',[])
        calls=tuple(ToolCall(p['functionCall'].get('id') or 'call_'+str(i),p['functionCall']['name'],json.dumps(p['functionCall'].get('args',{}))) for i,p in enumerate(parts) if 'functionCall' in p)
        return ChatResponse(model,''.join(p['text'] for p in parts if 'text' in p and not p.get('thought')),calls,'tool_calls' if calls else finish(c.get('finishReason')),self._usage(data),data,{'google_parts':parts})
    def _chunks(self,data,state):
        if not data.get('candidates'):
            if data.get('usageMetadata'): yield StreamChunk(usage=self._usage(data))
            return
        parsed=self._parse(data,''); c=data['candidates'][0]
        if parsed.content: yield StreamChunk(content=parsed.content)
        for t in parsed.tool_calls: yield StreamChunk(tool_call=t)
        if c.get('finishReason'): yield StreamChunk(finish_reason=parsed.finish_reason,usage=parsed.usage)
        elif parsed.usage: yield StreamChunk(usage=parsed.usage)
    def list_models(self):
        result=[]; url=self.base_url+'/models?pageSize=100'
        for _ in range(20):
            data=self._json(url); result.extend(m['name'].removeprefix('models/') for m in data['models'] if 'generateContent' in m.get('supportedGenerationMethods',[]))
            if not data.get('nextPageToken'): return sorted(set(result))
            url=self.base_url+'/models?'+urlencode({'pageSize':100,'pageToken':data['nextPageToken']})
        raise ProviderError(provider=self.name,code='response_too_large')
    def supports_tools(self,model): return model.removeprefix('models/').startswith('gemini-')
