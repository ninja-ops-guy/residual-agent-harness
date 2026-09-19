"""Production Microsoft Entra helpers for the Copilot Studio integration."""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable

from ...core import ContractError, identifier, strict_json
from ...iam.crypto import RSAPublicKey, b64url_decode
from ...iam.oidc import OIDCClient, OIDCSettings
from .auth import CopilotIdentityVerifier

_MAX_JWKS_BYTES=1024*1024
_MAX_GRAPH_BYTES=1024*1024


def _uint(value:str,name:str)->int:
    if not isinstance(value,str) or not value:
        raise ContractError(f"invalid JWKS {name}")
    raw=b64url_decode(value)
    if not raw: raise ContractError(f"invalid JWKS {name}")
    return int.from_bytes(raw,"big")


class _NoCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        old=urllib.parse.urlsplit(req.full_url)
        new=urllib.parse.urlsplit(newurl)
        if new.scheme!="https" or new.hostname!=old.hostname:
            raise ContractError("identity endpoint cross-host redirect refused")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class EntraJWKSProvider:
    """Bounded, tenant-fixed JWKS cache with refresh-on-unknown-kid."""

    def __init__(self,tenant_id:str,*,cache_ttl_s:float=3600,timeout_s:float=10,
                 clock:Callable[[],float]=time.monotonic,opener=None):
        if not isinstance(tenant_id,str) or not tenant_id.strip():
            raise ContractError("tenant_id is required")
        if type(cache_ttl_s) not in (int,float) or not 60<=cache_ttl_s<=86400:
            raise ContractError("JWKS cache TTL is out of bounds")
        if type(timeout_s) not in (int,float) or not 1<=timeout_s<=30:
            raise ContractError("JWKS timeout is out of bounds")
        self.tenant_id=tenant_id.strip()
        quoted=urllib.parse.quote(self.tenant_id,safe="")
        self.url=f"https://login.microsoftonline.com/{quoted}/discovery/v2.0/keys"
        self.cache_ttl_s=float(cache_ttl_s); self.timeout_s=float(timeout_s); self.clock=clock
        self._opener=opener or urllib.request.build_opener(_NoCrossHostRedirect())
        self._keys={}; self._expires=0.0; self._lock=threading.RLock()

    def _fetch(self):
        req=urllib.request.Request(self.url,headers={"Accept":"application/json","User-Agent":"RESIDUAL-Entra-JWKS/1"})
        try:
            with self._opener.open(req,timeout=self.timeout_s) as resp:
                if getattr(resp,"status",200)!=200: raise ContractError("Entra JWKS request failed")
                raw=resp.read(_MAX_JWKS_BYTES+1)
        except ContractError: raise
        except Exception as exc: raise ContractError("Entra JWKS unavailable") from exc
        if len(raw)>_MAX_JWKS_BYTES: raise ContractError("Entra JWKS response exceeds limit")
        try: data=strict_json(raw.decode("utf-8"))
        except Exception as exc: raise ContractError("Entra JWKS response is invalid") from exc
        if not isinstance(data,dict) or not isinstance(data.get("keys"),list):
            raise ContractError("Entra JWKS response missing keys")
        keys={}
        for item in data["keys"]:
            if not isinstance(item,dict) or item.get("kty")!="RSA": continue
            kid=item.get("kid")
            if not isinstance(kid,str) or not kid or len(kid)>256: continue
            if item.get("use") not in (None,"sig"): continue
            if item.get("alg") not in (None,"RS256"): continue
            try: key=RSAPublicKey(_uint(item["n"],"n"),_uint(item["e"],"e"))
            except (KeyError,ContractError): continue
            keys[kid]=key
        if not keys: raise ContractError("Entra JWKS contained no usable RS256 keys")
        self._keys=keys; self._expires=self.clock()+self.cache_ttl_s

    def __call__(self,kid):
        if not isinstance(kid,str) or not kid: return None
        with self._lock:
            if self.clock()>=self._expires: self._fetch()
            key=self._keys.get(kid)
            if key is None:
                self._fetch()
                key=self._keys.get(kid)
            return key


GraphTokenProvider=Callable[[],str]


class MicrosoftGraphGroupResolver:
    """Resolve only deployment-configured groups via Graph checkMemberGroups."""

    def __init__(self,tenant_id:str,candidate_group_ids:frozenset[str],
                 token_provider:GraphTokenProvider,*,timeout_s:float=10,opener=None):
        if not isinstance(tenant_id,str) or not tenant_id.strip(): raise ContractError("tenant_id required")
        if not isinstance(candidate_group_ids,frozenset) or not candidate_group_ids:
            raise ContractError("candidate_group_ids must be a non-empty frozenset")
        if any(not isinstance(g,str) or not g.strip() or len(g)>128 for g in candidate_group_ids):
            raise ContractError("invalid candidate group id")
        if not callable(token_provider): raise ContractError("Graph token_provider must be callable")
        self.tenant_id=tenant_id.strip(); self.groups=tuple(sorted(candidate_group_ids))
        self.token_provider=token_provider; self.timeout_s=float(timeout_s)
        self._opener=opener or urllib.request.build_opener(_NoCrossHostRedirect())

    def __call__(self,tenant_id:str,object_id:str)->Iterable[str]:
        if tenant_id!=self.tenant_id: raise ContractError("Graph resolver tenant mismatch")
        if not isinstance(object_id,str) or not object_id.strip(): raise ContractError("object_id required")
        token=self.token_provider()
        if not isinstance(token,str) or not token.strip(): raise ContractError("Graph service token unavailable")
        quoted=urllib.parse.quote(object_id,safe="")
        url=f"https://graph.microsoft.com/v1.0/users/{quoted}/checkMemberGroups"
        found=[]
        # Graph checkMemberGroups accepts a bounded groupIds array. Batch to
        # avoid silently exceeding provider request limits.
        for start in range(0,len(self.groups),20):
            batch=list(self.groups[start:start+20])
            body=json.dumps({"groupIds":batch},separators=(",",":")).encode()
            req=urllib.request.Request(url,data=body,method="POST",headers={
                "Authorization":"Bearer "+token.strip(),
                "Content-Type":"application/json","Accept":"application/json",
                "User-Agent":"RESIDUAL-Graph-Groups/1",
            })
            try:
                with self._opener.open(req,timeout=self.timeout_s) as resp:
                    raw=resp.read(_MAX_GRAPH_BYTES+1)
            except Exception as exc: raise ContractError("Microsoft Graph group resolution failed") from exc
            if len(raw)>_MAX_GRAPH_BYTES: raise ContractError("Microsoft Graph response exceeds limit")
            try: data=strict_json(raw.decode("utf-8"))
            except Exception as exc: raise ContractError("Microsoft Graph response invalid") from exc
            values=data.get("value") if isinstance(data,dict) else None
            if not isinstance(values,list) or any(not isinstance(v,str) for v in values):
                raise ContractError("Microsoft Graph group response invalid")
            unexpected=set(values)-set(batch)
            if unexpected: raise ContractError("Microsoft Graph returned an unrequested group")
            found.extend(values)
        return tuple(sorted(set(found)))


@dataclass(frozen=True)
class EntraDeploymentConfig:
    tenant_id:str
    api_client_id:str
    connector_client_app_ids:frozenset[str]
    delegated_scope:str="access_as_user"

    def __post_init__(self):
        if not isinstance(self.tenant_id,str) or not self.tenant_id.strip(): raise ContractError("tenant_id required")
        if not isinstance(self.api_client_id,str) or not self.api_client_id.strip(): raise ContractError("api_client_id required")
        if not isinstance(self.connector_client_app_ids,frozenset) or not self.connector_client_app_ids:
            raise ContractError("connector client app allowlist is required")
        if any(not isinstance(v,str) or not v.strip() for v in self.connector_client_app_ids):
            raise ContractError("invalid connector client app id")
        if not isinstance(self.delegated_scope,str) or not self.delegated_scope.strip():
            raise ContractError("delegated_scope required")

    @property
    def issuer(self):
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def audience(self):
        return self.api_client_id if self.api_client_id.startswith("api://") else f"api://{self.api_client_id}"

    def build_verifier(self,*,group_resolver=None,jwks_provider=None):
        keys=jwks_provider or EntraJWKSProvider(self.tenant_id)
        oidc=OIDCClient(OIDCSettings(self.issuer,self.audience,clock_skew=60),keys)
        return CopilotIdentityVerifier(
            oidc,expected_tenant=self.tenant_id,required_scope=self.delegated_scope,
            group_resolver=group_resolver,allowed_client_apps=self.connector_client_app_ids,
        )
