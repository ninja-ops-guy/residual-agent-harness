"""OpenID Connect (OIDC) authentication for Enterprise IAM.

Implements ENT1-R1: OIDC ID-token validation (HS256 and RS256 JWS) with
pure stdlib code and pluggable key providers. Provider presets for
Okta, Azure AD (Entra ID), Ping Identity, Auth0, and OneLogin share a
single generic client — no custom configuration per provider.

Implements ENT1-R7 partially by exposing the IdP-reported ``amr``
(authentication methods reference) so MFA can be delegated to the IdP.

All failures raise ContractError so callers can record access-denied
observations (ENT1-R6).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core import ContractError
from .crypto import jwt_decode
from .saml import Identity

#: Provider presets implementing ENT1-R1. Only the issuer/endpoint URL
#: shape differs per provider; token validation is identical for all.
OIDC_PROVIDERS: dict[str, dict[str, str]] = {
    "okta": {
        "issuer_pattern": "https://{org}.okta.com/oauth2/{auth_server}",
        "jwks_path": "/v1/keys",
        "authorization_path": "/v1/authorize",
        "token_path": "/v1/token",
    },
    "azure_ad": {
        "issuer_pattern": "https://login.microsoftonline.com/{tenant}/v2.0",
        "jwks_path": "/discovery/v2.0/keys",
        "authorization_path": "/oauth2/v2.0/authorize",
        "token_path": "/oauth2/v2.0/token",
    },
    "ping": {
        "issuer_pattern": "https://{org}.pingidentity.com/as",
        "jwks_path": "/jwks",
        "authorization_path": "/authorize",
        "token_path": "/token",
    },
    "auth0": {
        "issuer_pattern": "https://{org}.auth0.com/",
        "jwks_path": ".well-known/jwks.json",
        "authorization_path": "authorize",
        "token_path": "oauth/token",
    },
    "onelogin": {
        "issuer_pattern": "https://{org}.onelogin.com/oidc/2",
        "jwks_path": "/certs",
        "authorization_path": "/auth",
        "token_path": "/token",
    },
}


@dataclass(frozen=True)
class OIDCSettings:
    """Generic OIDC relying-party settings. Implements ENT1-R1."""

    issuer: str
    client_id: str
    jwks_url: str = ""
    authorization_url: str = ""
    token_url: str = ""
    clock_skew: int = 60

    def __post_init__(self):
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ContractError("oidc issuer is required")
        if not isinstance(self.client_id, str) or not self.client_id.strip():
            raise ContractError("oidc client_id is required")
        if type(self.clock_skew) is not int or self.clock_skew < 0:
            raise ContractError("clock_skew must be a nonnegative integer")


def provider_settings(provider: str, *, issuer: str, client_id: str, **kwargs: Any) -> OIDCSettings:
    """Build OIDCSettings from a known provider preset. Implements ENT1-R1:
    identical settings shape for Okta, Azure AD, Ping, Auth0, OneLogin."""
    if provider not in OIDC_PROVIDERS:
        raise ContractError(f"unknown OIDC provider {provider!r}")
    preset = OIDC_PROVIDERS[provider]
    base = issuer.rstrip("/")
    kwargs.setdefault("jwks_url", base + "/" + preset["jwks_path"].lstrip("/"))
    kwargs.setdefault("authorization_url", base + "/" + preset["authorization_path"].lstrip("/"))
    kwargs.setdefault("token_url", base + "/" + preset["token_path"].lstrip("/"))
    return OIDCSettings(issuer=issuer, client_id=client_id, **kwargs)


class OIDCClient:
    """Validates OIDC ID tokens and produces Identity objects.

    Implements ENT1-R1. ``key_provider`` is a callable (kid) -> key or a
    mapping of kid to key, supporting both HS256 (byte keys) and RS256
    (RSAPublicKey) tokens so tests need no network access.
    """

    def __init__(self, settings: OIDCSettings, key_provider: Any):
        if not isinstance(settings, OIDCSettings):
            raise ContractError("settings must be OIDCSettings")
        if key_provider is None:
            raise ContractError("a key provider is required")
        self.settings = settings
        self.key_provider = key_provider

    def authenticate(self, id_token: str, *, now: int, nonce: str | None = None) -> Identity:
        """Verify an ID token and return the authenticated Identity.

        Implements ENT1-R1 (and feeds ENT1-R7 via ``amr``)."""
        if not isinstance(id_token, str) or not id_token:
            raise ContractError("id_token is required")
        payload = jwt_decode(
            id_token,
            self.key_provider,
            now=now,
            issuer=self.settings.issuer,
            audience=self.settings.client_id,
            leeway=self.settings.clock_skew,
        )
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise ContractError("id token requires a sub claim")
        if nonce is not None and payload.get("nonce") != nonce:
            raise ContractError("id token nonce mismatch")
        amr = payload.get("amr")
        if amr is None:
            amr = ()
        elif isinstance(amr, str):
            if not amr.strip():
                raise ContractError("amr claim entries must be non-empty strings")
            amr = (amr,)
        elif isinstance(amr, (list, tuple)):
            if any(not isinstance(a, str) or not a.strip() for a in amr):
                raise ContractError("amr claim must contain only non-empty strings")
            amr = tuple(amr)
        else:
            raise ContractError("amr claim must be a string or list of strings")
        attributes = {
            k: v
            for k, v in payload.items()
            if k not in ("iss", "sub", "aud", "exp", "nbf", "iat", "nonce", "amr", "auth_time")
        }
        return Identity(
            subject=subject,
            issuer=payload["iss"],
            attributes=attributes,
            not_on_or_after=payload.get("exp"),
            authn_instant=payload.get("auth_time", payload.get("iat")),
            amr=tuple(amr),
        )
