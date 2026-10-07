"""Anthropic Messages with tool round trips, stream usage and normalized outcomes."""
import json
from ._http import HTTPAdapter, usage_values, cached_usage, finish, validate_url, encode
from ..core import ChatResponse, StreamChunk, ToolCall, Role


class AnthropicAdapter(HTTPAdapter):
    name = 'anthropic'
    API_VERSION = '2023-06-01'
    allowed_extra = {'top_p', 'top_k'}
    def __init__(self, api_key=None, base_url='https://api.anthropic.com', timeout=120.0):
        self.base_url = validate_url(base_url,self.name)
        self.api_key,self.timeout = api_key,timeout
    def _headers(self):
        return {**super()._headers(),'anthropic-version':self.API_VERSION, **({'x-api-key':self.api_key} if self.api_key else {})}
    def _request_url(self,req,stream): return self.base_url + '/v1/messages'
    @staticmethod
    def _msg(m):
        if m.role == Role.TOOL: return {'role':'user','content':[{'type':'tool_result','tool_use_id':m.tool_call_id,'content':m.content}]}
        blocks = ([{'type':'text','text':m.content}] if m.content else [])
        blocks += [{'type':'tool_use','id':t.id,'name':t.name,'input':json.loads(t.arguments)} for t in m.tool_calls]
        return {'role':m.role.value,'content':blocks or m.content}
    def _build_body(self,req,stream=False):
        system = '\n'.join(m.content for m in req.messages if m.role == Role.SYSTEM)
        if req.response_schema is not None: system += '\nReturn only JSON matching: '+encode(req.response_schema).decode()
        body={'model':req.model,'messages':[self._msg(m) for m in req.messages if m.role != Role.SYSTEM],'max_tokens':req.max_tokens or 4096,'stream':stream}
        if system: body['system']=system
        if req.temperature is not None: body['temperature']=req.temperature
        if req.stop: body['stop_sequences']=list(req.stop)
        if req.tools: body['tools']=[{'name':t.name,'description':t.description,'input_schema':t.parameters} for t in req.tools]
        return self._options(req,body)
    @staticmethod
    def _usage(data):
        return cached_usage(data.get('usage') or {}, 'input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')
    def _parse(self,data,model):
        blocks=data['content']; calls=tuple(ToolCall(b['id'],b['name'],json.dumps(b['input'])) for b in blocks if b['type']=='tool_use')
        return ChatResponse(data.get('model') or model,''.join(b['text'] for b in blocks if b['type']=='text'),calls,finish(data.get('stop_reason')),self._usage(data),data)
    def _chunks(self,event,state):
        kind=event.get('type')
        if kind=='message_start': state['usage']=dict(event.get('message',{}).get('usage',{}))
        elif kind=='content_block_start':
            b=event['content_block']
            if b['type']=='tool_use': state.setdefault('tools',{})[event['index']]={'id':b['id'],'name':b['name'],'arguments':''}
        elif kind=='content_block_delta':
            d=event['delta']
            if d['type']=='text_delta': yield StreamChunk(content=d['text'])
            elif d['type']=='input_json_delta': state['tools'][event['index']]['arguments'] += d['partial_json']
        elif kind=='content_block_stop':
            t=state.get('tools',{}).pop(event['index'],None)
            if t:
                t['arguments']=t['arguments'] or '{}'
                yield StreamChunk(tool_call=ToolCall(**t))
        elif kind=='message_delta':
            state.setdefault('usage',{}).update(event.get('usage',{}))
            reason=event.get('delta',{}).get('stop_reason')
            if reason: yield StreamChunk(finish_reason=finish(reason), usage=self._usage({'usage':state['usage']}))
    def list_models(self):
        result=[]; url=self.base_url+'/v1/models?limit=100'
        for _ in range(20):
            data=self._json(url); result.extend(m['id'] for m in data['data'])
            if not data.get('has_more'): return sorted(set(result))
            from urllib.parse import urlencode
            url=self.base_url+'/v1/models?'+urlencode({'limit':100,'after_id':data['last_id']})
        from ..core import ProviderError
        raise ProviderError(provider=self.name,code='response_too_large')
    def supports_tools(self,model): return model.startswith('claude-')
