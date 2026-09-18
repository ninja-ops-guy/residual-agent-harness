"""Strict Microsoft Entra v2 signing-key discovery for the Copilot gateway.

The provider is deliberately single-tenant for the first enterprise pilot.
Metadata/JWKS URLs are derived from the configured tenant, never from an
unverified token or request body. It caches usable RS256 keys, refreshes on a
bounded interval, and performs one immediate refresh for an unknown kid so
normal Microsoft signing-key rollover does not require a process restart.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from ...core import ContractError
from ...iam.crypto import RSAPublicKey, b64url_decode
from ...iam.oidc import OIDCClient, OIDCSettings


DEFAULT_REFRESH_SECONDS = 24 * 60 * 60
MAX_DOCUMENT_BYTES = 512 * 1024


def _guid(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a GUID")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ContractError(f"{name} must be a GUID") from None
    if str(parsed).lower() != value.lower():
        raise ContractError(f"{name} must use canonical GUID form")
    return str(parsed)


@dataclass(frozen=True)
class EntraV2Endpoints:
    tenant_id: str
    issuer: str
    metadata_url: str
    jwks_url: str

    @classmethod
    def for_tenant(cls, tenant_id: str) -> "EntraV2Endpoints":
        tenant = _guid(tenant_id, "tenant_id")
        base = f"https://login.microsoftonline.com/{tenant}"
        return cls(
            tenant_id=tenant,
            issuer=f"{base}/v2.0",
            metadata_url=f"{base}/v2.0/.well-known/openid-configuration",
            jwks_url=f"{base}/discovery/v2.0/keys",
        )


class HTTPSJSONFetcher:
    """Bounded HTTPS JSON fetcher used only with trusted configured URLs."""

    def __init__(self, *, timeout: float = 10.0):
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
            raise ContractError("fetch timeout must be between 0 and 60 seconds")
        self.timeout = float(timeout)

    def __call__(self, url: str) -> dict[str, Any]:
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "login.microsoftonline.com"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ContractError("OIDC metadata fetch URL is not trusted")
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "residual-copilot-entra-key-provider/1",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.geturl() != url:
                    raise ContractError("OIDC metadata redirect is not allowed")
                if getattr(response, "status", 200) != 200:
                    raise ContractError("OIDC metadata endpoint returned non-200")
                raw = response.read(MAX_DOCUMENT_BYTES + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            raise ContractError("OIDC metadata fetch failed") from None
        if len(raw) > MAX_DOCUMENT_BYTES:
            raise ContractError("OIDC metadata document exceeds size limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ContractError("OIDC metadata endpoint returned invalid JSON") from None
        if not isinstance(value, dict):
            raise ContractError("OIDC metadata document must be a JSON object")
        return value


class EntraJWKSProvider:
    """Callable key-id to RSAPublicKey provider for RESIDUAL OIDCClient."""

    def __init__(
        self,
        tenant_id: str,
        *,
        fetch_json: Callable[[str], dict[str, Any]] | None = None,
        refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.endpoints = EntraV2Endpoints.for_tenant(tenant_id)
        if type(refresh_seconds) is not int or not 60 <= refresh_seconds <= 7 * 86400:
            raise ContractError("refresh_seconds must be between 60 and 604800")
        if not callable(clock):
            raise ContractError("clock must be callable")
        self.fetch_json = fetch_json or HTTPSJSONFetcher()
        if not callable(self.fetch_json):
            raise ContractError("fetch_json must be callable")
        self.refresh_seconds = refresh_seconds
        self.clock = clock
        self._lock = threading.RLock()
        self._keys: dict[str, RSAPublicKey] = {}
        self._refreshed_at: float | None = None

    @staticmethod
    def _rsa_key(
        value: dict[str, Any],
        expected_issuer: str,
    ) -> tuple[str, RSAPublicKey] | None:
        if value.get("kty") != "RSA":
            return None
        if value.get("use") not in (None, "sig"):
            return None
        if value.get("alg") not in (None, "RS256"):
            return None
        kid = value.get("kid")
        modulus = value.get("n")
        exponent = value.get("e")
        if not all(
            isinstance(item, str) and item
            for item in (kid, modulus, exponent)
        ):
            raise ContractError("Entra RSA signing key is missing kid/n/e")
        key_issuer = value.get("issuer")
        if key_issuer is not None and key_issuer != expected_issuer:
            raise ContractError(
                "Entra signing-key issuer does not match configured tenant"
            )
        n = int.from_bytes(b64url_decode(modulus), "big")
        e = int.from_bytes(b64url_decode(exponent), "big")
        if n < 256 or e < 3:
            raise ContractError("Entra RSA signing key is invalid")
        return kid, RSAPublicKey(n=n, e=e)

    def _fetch(self) -> dict[str, RSAPublicKey]:
        metadata = self.fetch_json(self.endpoints.metadata_url)
        if metadata.get("issuer") != self.endpoints.issuer:
            raise ContractError(
                "Entra metadata issuer does not match configured tenant"
            )
        if metadata.get("jwks_uri") != self.endpoints.jwks_url:
            raise ContractError(
                "Entra metadata jwks_uri does not match configured tenant"
            )
        document = self.fetch_json(self.endpoints.jwks_url)
        raw_keys = document.get("keys")
        if not isinstance(raw_keys, list) or not raw_keys:
            raise ContractError("Entra JWKS document contains no keys")
        keys: dict[str, RSAPublicKey] = {}
        for raw in raw_keys:
            if not isinstance(raw, dict):
                raise ContractError("Entra JWKS key entries must be objects")
            parsed = self._rsa_key(raw, self.endpoints.issuer)
            if parsed is None:
                continue
            kid, key = parsed
            if kid in keys:
                raise ContractError("Entra JWKS contains duplicate kid")
            keys[kid] = key
        if not keys:
            raise ContractError(
                "Entra JWKS contains no usable RS256 signing keys"
            )
        return keys

    def refresh(self) -> None:
        keys = self._fetch()
        refreshed_at = float(self.clock())
        with self._lock:
            self._keys = keys
            self._refreshed_at = refreshed_at

    def __call__(self, kid: str | None) -> RSAPublicKey:
        if not isinstance(kid, str) or not kid:
            raise ContractError("Entra access token requires a kid header")
        now = float(self.clock())
        with self._lock:
            stale = (
                self._refreshed_at is None
                or now - self._refreshed_at >= self.refresh_seconds
            )
            if not stale and kid in self._keys:
                return self._keys[kid]
        if stale:
            self.refresh()
            with self._lock:
                key = self._keys.get(kid)
                if key is not None:
                    return key
        self.refresh()
        with self._lock:
            key = self._keys.get(kid)
            if key is None:
                raise ContractError("unknown Entra signing-key id")
            return key


def build_entra_v2_oidc_client(
    *,
    tenant_id: str,
    audience: str,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> OIDCClient:
    """Build the single-tenant production OIDC client used by the pilot."""
    tenant = _guid(tenant_id, "tenant_id")
    api_audience = _guid(audience, "audience")
    endpoints = EntraV2Endpoints.for_tenant(tenant)
    provider = EntraJWKSProvider(
        tenant,
        fetch_json=fetch_json,
        refresh_seconds=refresh_seconds,
        clock=clock,
    )
    settings = OIDCSettings(
        issuer=endpoints.issuer,
        client_id=api_audience,
        jwks_url=endpoints.jwks_url,
        clock_skew=60,
    )
    return OIDCClient(settings, provider)
