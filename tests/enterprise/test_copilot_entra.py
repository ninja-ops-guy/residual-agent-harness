"""Offline qualification for production Entra/JWKS/Graph helpers."""
from __future__ import annotations

import json
from io import BytesIO

import pytest

from residual.core import ContractError
from residual.iam.crypto import b64url_encode, jwt_encode, rsa_generate_keypair
from residual.integrations.copilot_studio.entra import (
    EntraDeploymentConfig, EntraJWKSProvider, MicrosoftGraphGroupResolver,
)


class Response:
    def __init__(self,body,status=200):
        self.body=body if isinstance(body,bytes) else json.dumps(body).encode()
        self.status=status
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,n=-1): return self.body if n<0 else self.body[:n]


class Opener:
    def __init__(self,responses):
        self.responses=list(responses); self.requests=[]
    def open(self,req,timeout=None):
        self.requests.append((req.full_url,req.get_method(),dict(req.header_items()),req.data,timeout))
        if not self.responses: raise OSError("no scripted response")
        item=self.responses.pop(0)
        if isinstance(item,Exception): raise item
        return item


def _jwk(key,kid="kid-1"):
    n=key.public_key.n.to_bytes((key.public_key.n.bit_length()+7)//8,"big")
    e=key.public_key.e.to_bytes((key.public_key.e.bit_length()+7)//8,"big")
    return {"kty":"RSA","kid":kid,"use":"sig","alg":"RS256","n":b64url_encode(n),"e":b64url_encode(e)}


def test_jwks_provider_uses_fixed_tenant_endpoint_and_decodes_rsa():
    key=rsa_generate_keypair(1024); opener=Opener([Response({"keys":[_jwk(key)]})])
    provider=EntraJWKSProvider("tenant-a",opener=opener)
    public=provider("kid-1")
    assert public==key.public_key
    assert opener.requests[0][0]=="https://login.microsoftonline.com/tenant-a/discovery/v2.0/keys"


def test_unknown_kid_forces_single_refresh():
    key1=rsa_generate_keypair(1024); key2=rsa_generate_keypair(1024)
    opener=Opener([Response({"keys":[_jwk(key1,"old")]}),Response({"keys":[_jwk(key2,"new")]})])
    provider=EntraJWKSProvider("tenant-a",opener=opener)
    assert provider("old")==key1.public_key
    assert provider("new")==key2.public_key
    assert len(opener.requests)==2


def test_jwks_rejects_oversized_or_unusable_document():
    provider=EntraJWKSProvider("tenant-a",opener=Opener([Response(b"x"*(1024*1024+1))]))
    with pytest.raises(ContractError): provider("x")
    provider=EntraJWKSProvider("tenant-a",opener=Opener([Response({"keys":[{"kty":"oct","kid":"x"}]})]))
    with pytest.raises(ContractError): provider("x")


def test_graph_group_resolver_queries_only_configured_ids():
    opener=Opener([Response({"value":["group-a"]})])
    resolver=MicrosoftGraphGroupResolver("tenant-a",frozenset({"group-a","group-b"}),lambda:"service-token",opener=opener)
    assert tuple(resolver("tenant-a","user-object"))==("group-a",)
    url,method,headers,body,_=opener.requests[0]
    assert url=="https://graph.microsoft.com/v1.0/users/user-object/checkMemberGroups"
    assert method=="POST"
    assert set(json.loads(body)["groupIds"])=={"group-a","group-b"}
    assert headers["Authorization"]=="Bearer service-token"


def test_graph_resolver_rejects_tenant_and_unrequested_group():
    resolver=MicrosoftGraphGroupResolver("tenant-a",frozenset({"group-a"}),lambda:"token",opener=Opener([]))
    with pytest.raises(ContractError,match="tenant"): resolver("tenant-b","user")
    resolver=MicrosoftGraphGroupResolver("tenant-a",frozenset({"group-a"}),lambda:"token",opener=Opener([Response({"value":["evil-group"]})]))
    with pytest.raises(ContractError,match="unrequested"): resolver("tenant-a","user")


def test_deployment_config_builds_real_rs256_verifier():
    key=rsa_generate_keypair(1024)
    config=EntraDeploymentConfig("tenant-a","residual-api",frozenset({"copilot-app"}))
    provider=lambda kid:key.public_key if kid=="kid-1" else None
    verifier=config.build_verifier(jwks_provider=provider)
    token=jwt_encode({
        "iss":config.issuer,"sub":"subject","aud":config.audience,
        "iat":1000,"exp":1100,"tid":"tenant-a","oid":"user",
        "scp":"access_as_user","groups":["firmware-group"],"azp":"copilot-app",
    },key,alg="RS256",headers={"kid":"kid-1"})
    principal=verifier.verify(token,now=1050)
    assert principal.tenant_id=="tenant-a"
    assert principal.object_id=="user"
    assert principal.groups==frozenset({"firmware-group"})
