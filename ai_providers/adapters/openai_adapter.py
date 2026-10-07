"""OpenAI Chat Completions and explicitly configured compatible endpoints."""
from ._http import HTTPAdapter, extract_usage, finish, validate_url
from ..core import ChatResponse, StreamChunk, ToolCall, Role


class OpenAIAdapter(HTTPAdapter):
    name = 'openai'
    allowed_extra = {'top_p', 'frequency_penalty', 'presence_penalty', 'reasoning_effort'}

    def __init__(self, api_key=None, base_url='https://api.openai.com/v1', organization=None, timeout=120.0,
                 output_token_field='max_completion_tokens'):
        self.base_url = validate_url(base_url, self.name)
        self.api_key, self.organization, self.timeout = api_key, organization, timeout
        if output_token_field not in {'max_tokens', 'max_completion_tokens'}: raise ValueError('Invalid output-limit field')
        self.output_token_field = output_token_field

    def _headers(self):
        h = super()._headers()
        if self.api_key: h['Authorization'] = 'Bearer ' + self.api_key
        if self.organization: h['OpenAI-Organization'] = self.organization
        return h

    def _request_url(self, req, stream): return self.base_url + '/chat/completions'

    @staticmethod
    def _msg_to_openai(m):
        d = {'role': m.role.value, 'content': m.content}
        if m.name: d['name'] = m.name
        if m.tool_call_id: d['tool_call_id'] = m.tool_call_id
        if m.tool_calls:
            d['tool_calls'] = [{'id': t.id, 'type': 'function', 'function': {'name': t.name, 'arguments': t.arguments}} for t in m.tool_calls]
        return d

    @staticmethod
    def _tool_to_openai(t):
        return {'type':'function', 'function':{'name':t.name, 'description':t.description, 'parameters':t.parameters}}

    def _build_body(self, req, stream=False):
        body = {'model':req.model, 'messages':[self._msg_to_openai(m) for m in req.messages], 'stream':stream}
        if req.tools: body['tools'] = [self._tool_to_openai(t) for t in req.tools]
        if req.temperature is not None: body['temperature'] = req.temperature
        if req.max_tokens is not None: body[self.output_token_field] = req.max_tokens
        if req.stop: body['stop'] = list(req.stop)
        if req.seed is not None: body['seed'] = req.seed
        if req.response_schema is not None:
            body['response_format'] = {'type':'json_object'}
            from ._http import encode
            body['messages'].insert(0, {'role':'system','content':'Return only JSON matching this schema: ' + encode(req.response_schema).decode()})
        if stream: body['stream_options'] = {'include_usage':True}
        return self._options(req, body)

    def _parse(self, data, model):
        choice = data['choices'][0]; msg = choice['message']
        calls = tuple(ToolCall(t['id'], t['function']['name'], t['function']['arguments']) for t in msg.get('tool_calls', []))
        if msg.get('refusal'): reason = 'content_filter'
        else: reason = finish(choice.get('finish_reason'))
        return ChatResponse(data.get('model') or model, msg.get('content') or '', calls, reason, extract_usage(data), data)

    def _chunks(self, data, state):
        if data.get('_done'): return
        usage = extract_usage(data)
        choices = data.get('choices', [])
        if not choices:
            if usage: yield StreamChunk(usage=usage)
            return
        choice = choices[0]; delta = choice.get('delta') or {}
        if delta.get('content') is not None: yield StreamChunk(content=delta['content'])
        for t in delta.get('tool_calls', []):
            index = t['index']; tc = state.setdefault(index, {'id':'', 'name':'', 'arguments':''})
            fn = t.get('function') or {}
            for k, v in [('id',t.get('id')),('name',fn.get('name')),('arguments',fn.get('arguments'))]:
                if v: tc[k] += v
        if choice.get('finish_reason'):
            for index in sorted(state): yield StreamChunk(tool_call=ToolCall(**state[index]))
            state.clear()
            yield StreamChunk(finish_reason=finish(choice['finish_reason']), usage=usage)
        elif usage: yield StreamChunk(usage=usage)

    def list_models(self):
        return sorted(m['id'] for m in self._json(self.base_url + '/models')['data'])

    def supports_tools(self, model):
        # Protocol capability; unknown compatible models must be checked by the operator.
        return self.name == 'openai' and model.startswith(('gpt-', 'o1', 'o3', 'o4'))


class OpenAICompatibleAdapter(OpenAIAdapter):
    name = 'openai_compatible'
