"""Azure deployment routing with escaped path components and explicit API version."""
from urllib.parse import quote,urlencode
from .openai_adapter import OpenAIAdapter
from ..core import ProviderError


class AzureAdapter(OpenAIAdapter):
    name='azure'
    def __init__(self,api_key=None,endpoint=None,api_version='2024-10-21',timeout=120.0,output_token_field='max_completion_tokens'):
        if not endpoint: raise ProviderError(provider=self.name,code='config')
        super().__init__(api_key,endpoint,timeout=timeout,output_token_field=output_token_field)
        self.endpoint,self.api_version=self.base_url,api_version
    def _headers(self): return {'Content-Type':'application/json',**({'api-key':self.api_key} if self.api_key else {})}
    def _request_url(self,req,stream): return self.endpoint+'/openai/deployments/'+quote(req.model,safe='')+'/chat/completions?'+urlencode({'api-version':self.api_version})
    def _build_body(self,req,stream=False):
        body=super()._build_body(req,stream); body.pop('model'); return body
    def list_models(self):
        raise ProviderError(provider=self.name,code='not_implemented')
    def supports_tools(self,model): return False  # deployment names do not identify model capabilities
