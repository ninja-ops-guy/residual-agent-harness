"""OIDC-issued JWT access tokens verified against an operator-pinned JWKS.

No network requests occur inside authentication or a database transaction. Keys
are loaded by the host and expire; rotate/reload them explicitly. This is a JWT
resource-server adapter, not an OAuth authorization-code/login implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hmac
import math
import time
from urllib.parse import urlsplit

from ..core import ContractError, strict_json


class AuthenticationError(PermissionError):
    pass


@dataclass(frozen=True)
class Principal:
    subject: str
    issuer: str
    roles: frozenset[str]


class OIDCAuthenticator:
    def __init__(self, *, issuer: str, audience: str, jwks: dict,
                 allowed_roles: tuple[str, ...] = ("operator",), role_claim: str = "roles",
                 required_scope: str = "residual:review", max_token_age_s: int = 900,
                 key_ttl_s: int = 3600):
        import jwt
        url = urlsplit(issuer)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or not audience or not required_scope):
            raise ContractError("OIDC requires a fixed HTTPS issuer, audience and review scope")
        if not allowed_roles or any(not isinstance(x, str) or not x for x in allowed_roles):
            raise ContractError("OIDC requires a nonempty role allowlist")
        if type(max_token_age_s) is not int or not 1 <= max_token_age_s <= 3600:
            raise ContractError("token age must be in 1..3600 seconds")
        if type(key_ttl_s) is not int or not 1 <= key_ttl_s <= 86400:
            raise ContractError("JWKS lifetime must be in 1..86400 seconds")
        keys = jwks.get("keys") if isinstance(jwks, dict) else None
        if not isinstance(keys, list) or not 1 <= len(keys) <= 32:
            raise ContractError("JWKS must contain 1..32 public verification keys")
        self._keys = {}
        for raw in keys:
            if not isinstance(raw, dict) or "d" in raw or raw.get("use", "sig") != "sig":
                raise ContractError("JWKS contains a private or non-signing key")
            alg = {"RSA": "RS256", "EC": "ES256"}.get(raw.get("kty"))
            kid = raw.get("kid")
            if (not alg or raw.get("alg", alg) != alg or not isinstance(kid, str)
                    or not 1 <= len(kid) <= 128 or kid in self._keys
                    or (alg == "ES256" and raw.get("crv") != "P-256")
                    or ("key_ops" in raw and raw["key_ops"] != ["verify"])):
                raise ContractError("unsupported or ambiguous verification key")
            key = jwt.PyJWK.from_dict(raw, algorithm=alg).key
            if alg == "RS256" and key.key_size < 2048:
                raise ContractError("RSA verification keys must be at least 2048 bits")
            self._keys[kid] = (key, alg)
        self.issuer, self.audience = issuer, audience
        self.allowed_roles = frozenset(allowed_roles)
        self.role_claim, self.required_scope = role_claim, required_scope
        self.max_token_age_s, self.key_ttl_s = max_token_age_s, key_ttl_s
        self._loaded_at = time.monotonic()

    def principal(self, token: str) -> Principal:
        import jwt
        try:
            if (not isinstance(token, str) or not 1 <= len(token) <= 16384
                    or time.monotonic() - self._loaded_at >= self.key_ttl_s):
                raise ValueError()
            header = jwt.get_unverified_header(token)
            if any(k in header for k in ("jku", "x5u", "jwk", "crit")):
                raise ValueError()
            key, alg = self._keys[header["kid"]]
            if header.get("alg") != alg:
                raise ValueError()
            claims = jwt.decode(token, key, algorithms=[alg], issuer=self.issuer,
                audience=self.audience, options={"require": ["exp", "iat", "iss", "aud", "sub"]})
            if claims["iss"] != self.issuer or not isinstance(claims["sub"], str) or not 1 <= len(claims["sub"]) <= 256:
                raise ValueError()
            if any((type(claims[n]) not in (int, float) or not math.isfinite(claims[n])) for n in ("exp", "iat")):
                raise ValueError()
            age = time.time() - claims["iat"]
            if not 0 <= age <= self.max_token_age_s or not claims["iat"] < claims["exp"]:
                raise ValueError()
            roles, scopes = claims.get(self.role_claim, []), claims.get("scope", "")
            if (not isinstance(roles, list) or len(roles) > 64
                    or any(not isinstance(r, str) for r in roles) or not isinstance(scopes, str)
                    or self.required_scope not in scopes.split()):
                raise ValueError()
            authorized = frozenset(roles) & self.allowed_roles
            if not authorized:
                raise ValueError()
            return Principal(claims["sub"], self.issuer, authorized)
        except Exception:
            raise AuthenticationError("operator authentication failed") from None

    def __call__(self, record: dict, response: str, role: str) -> bool:
        try:
            intent = strict_json(response)
            if (set(intent) != {"access_token", "challenge_id", "challenge_signature", "decision"}
                    or intent["challenge_id"] != record["challenge_id"]
                    or intent["decision"] != record.get("_requested_decision", "approve")
                    or not hmac.compare_digest(intent["challenge_signature"], record["signature"])):
                return False
            return role in self.principal(intent["access_token"]).roles
        except Exception:
            return False

    def identity(self, response: str) -> dict[str, str]:
        principal = self.principal(strict_json(response)["access_token"])
        return {"subject": principal.subject, "issuer": principal.issuer}
