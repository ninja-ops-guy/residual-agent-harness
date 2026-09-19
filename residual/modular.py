"""Bridge the uploaded provider contract into RESIDUAL's bounded runner interface."""
from __future__ import annotations
import json
import os
import time
from ai_providers import ChatRequest, Message, Role, ProviderName, ProviderError, Router, Registry
from ai_providers.adapters._http import validate_url
from .core import ContractError, canonical
from .providers import Provider, Reply, Usage, SYSTEM, RESPONSE_SCHEMA

PROVIDERS={
 'ollama':{'label':'Ollama','base_url':'http://127.0.0.1:11434'},
 'openai_compatible':{'label':'OpenAI-compatible','base_url':''},
 'openai':{'label':'OpenAI','base_url':'https://api.openai.com/v1'},
 'anthropic':{'label':'Anthropic','base_url':'https://api.anthropic.com'},
 'google':{'label':'Google Gemini','base_url':'https://generativelanguage.googleapis.com/v1beta'},
 'azure':{'label':'Azure OpenAI','base_url':''},
 'bedrock':{'label':'AWS Bedrock','base_url':''},
 'arena':{
     'label':'Arena API',
     'base_url':'https://api.preview.arena.ai/v1',
     'setup_url':'https://portal.api.preview.arena.ai/dashboard/keys',
     'docs_url':'https://portal.api.preview.arena.ai/docs/api-reference',
     'setup_label':'Get Arena API key',
     'setup_help':'Create a virtual Arena API key, copy it once, then paste it into RESIDUAL.'
 },
}
ENV_KEYS={'openai':'OPENAI_API_KEY','openai_compatible':'LLM_API_KEY','anthropic':'ANTHROPIC_API_KEY','google':'GEMINI_API_KEY','azure':'AZURE_OPENAI_API_KEY','ollama':'OLLAMA_API_KEY','arena':'ARENA_API_KEY'}


def normalize_profile(profile,placement,allow_empty_model=False):
    if not isinstance(profile,dict) or profile.get('kind') not in PROVIDERS: raise ContractError('Choose a supported provider')
    kind=profile['kind']; model=profile.get('model','')
    if not isinstance(model,str) or (not model and not allow_empty_model) or len(model)>500 or any(ord(c)<32 for c in model): raise ContractError('Enter a model or deployment ID')
    if placement=='local' and kind not in {'ollama','openai_compatible'}: raise ContractError('Local routes require Ollama or a compatible loopback server')
    region=profile.get('region') or 'us-east-1'
    base=profile.get('base_url') or PROVIDERS[kind]['base_url']
    if kind=='bedrock' and not base:
        import re
        if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d',region): raise ContractError('Enter a valid AWS region')
        base=f'https://bedrock-runtime.{region}.amazonaws.com'
    try: base=validate_url(base,kind,local=placement=='local')
    except ProviderError: raise ContractError('Local endpoints must use loopback; network endpoints require HTTPS without credentials or query parameters') from None
    if placement=='local' and kind=='ollama' and (model.endswith(('-cloud',':cloud')) or ':cloud-' in model): raise ContractError('Ollama cloud models belong in a cloud route')
    cap=profile.get('output_token_field','max_completion_tokens')
    if cap not in {'max_tokens','max_completion_tokens'}: raise ContractError('Invalid output-limit field')
    return {'kind':kind,'model':model,'base_url':base,'placement':placement,'output_token_field':cap,
            'region':region,'api_version':profile.get('api_version') or '2024-10-21'}


def make_adapter(profile,credentials=None):
    p=profile; kind=p['kind']; c=credentials or {}
    key=c.get('api_key') or (os.environ.get('RESIDUAL_LOCAL_API_KEY') if p.get('placement')=='local' else os.environ.get(ENV_KEYS.get(kind,'')))
    if kind=='google': key=key or os.environ.get('GOOGLE_API_KEY')
    if kind=='arena':
        from ai_providers.adapters.arena_adapter import ArenaAdapter
        return ArenaAdapter(key,p['base_url'],output_token_field=p['output_token_field'])
    if kind in {'openai','openai_compatible'}:
        from ai_providers.adapters.openai_adapter import OpenAIAdapter,OpenAICompatibleAdapter
        return (OpenAIAdapter if kind=='openai' else OpenAICompatibleAdapter)(key,p['base_url'],output_token_field=p['output_token_field'])
    if kind=='ollama':
        from ai_providers.adapters.ollama_adapter import OllamaAdapter
        return OllamaAdapter(p['base_url'],api_key=key)
    if kind=='anthropic':
        from ai_providers.adapters.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(key,p['base_url'])
    if kind=='google':
        from ai_providers.adapters.google_adapter import GoogleAdapter
        return GoogleAdapter(key,p['base_url'])
    if kind=='azure':
        from ai_providers.adapters.azure_adapter import AzureAdapter
        return AzureAdapter(key,p['base_url'],p['api_version'],output_token_field=p['output_token_field'])
    if kind=='bedrock':
        from ai_providers.adapters.bedrock_adapter import BedrockAdapter
        return BedrockAdapter(c.get('access_key') or os.environ.get('AWS_ACCESS_KEY_ID'),c.get('secret_key') or os.environ.get('AWS_SECRET_ACCESS_KEY'),
                              p['region'],c.get('session_token') or os.environ.get('AWS_SESSION_TOKEN'),base_url=p['base_url'])
    raise ContractError('Unknown provider')


def normalized_usage(usage):
    inp,out,cached=(usage.get(k) for k in ('prompt_tokens','completion_tokens','cached_prompt_tokens'))
    return Usage(inp,out,cached,'reported' if inp is not None and out is not None else 'unavailable',usage.get('cache_write_prompt_tokens'))


class ModularProvider(Provider):
    def __init__(self,profile,system=SYSTEM,schema=RESPONSE_SCHEMA,key=None,credentials=None,observation_bus=None):
        self.profile=normalize_profile(profile,profile.get('placement','local'))
        self.model,self.kind,self.placement=(self.profile[k] for k in ('model','kind','placement'))
        self.name=self.kind+':'+self.model
        self.system,self.schema=system,schema
        self.adapter=make_adapter(self.profile,credentials or ({'api_key':key} if key else {}))
        self.attempt_receipts=[]
        def retain_attempt(value):
            # Snapshot only normalized Router receipts; raw provider bodies and
            # credentials never enter this record.
            self.attempt_receipts.append(json.loads(canonical(value)))
        reg=Registry();reg.register(self.kind,lambda:self.adapter)
        self.router=Router(registry=reg,default_provider=self.kind,observation_bus=observation_bus,after_attempt=retain_attempt)
    def request(self,packet,cap):
        return ChatRequest(self.model,(Message(Role.SYSTEM,self.system),Message(Role.USER,canonical(packet))),max_tokens=cap,response_schema=self.schema)
    def payload(self,packet,max_output_tokens): return self.adapter._build_body(self.request(packet,max_output_tokens))
    def wire_size(self,packet,max_output_tokens): return len(self.adapter.wire_bytes(self.request(packet,max_output_tokens)))
    def generate(self,packet,max_output_tokens):
        start=time.monotonic();response=self.router.chat(self.kind+':'+self.model,self.request(packet,max_output_tokens))
        return Reply(response.content,normalized_usage(response.usage),(time.monotonic()-start)*1000,response.finish_reason)
