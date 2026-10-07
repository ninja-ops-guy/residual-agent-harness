"""Pure-stdlib cryptographic primitives for Enterprise IAM.

Implements ENT1-R1 (token/assertion signing primitives for SAML 2.0 and
OIDC) using only the standard library: HMAC-SHA256 and PKCS#1 v1.5 RSA
over SHA-256, plus compact JWS/JWT encode/decode. No third-party
dependencies, fully deterministic and testable without network access.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ..core import ContractError, canonical


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    if not isinstance(value, str):
        raise ContractError("base64url value must be a string")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as exc:  # noqa: BLE001 - normalize to ContractError
        raise ContractError("invalid base64url encoding") from exc


def hmac_sha256_sign(key: bytes, message: bytes) -> bytes:
    if not isinstance(key, bytes) or not key:
        raise ContractError("hmac key must be non-empty bytes")
    return hmac.new(key, message, hashlib.sha256).digest()


def hmac_sha256_verify(key: bytes, message: bytes, signature: bytes) -> bool:
    return hmac.compare_digest(hmac_sha256_sign(key, message), signature)


# ---------------------------------------------------------------------------
# Pure-python RSA (PKCS#1 v1.5, SHA-256). Implements ENT1-R1.
# ---------------------------------------------------------------------------

_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


@dataclass(frozen=True)
class RSAPublicKey:
    """RSA public key (modulus, exponent). Implements ENT1-R1."""

    n: int
    e: int = 65537

    def __post_init__(self):
        if type(self.n) is not int or self.n < 256 or type(self.e) is not int or self.e < 3:
            raise ContractError("invalid RSA public key")


@dataclass(frozen=True)
class RSAPrivateKey:
    """RSA private key. Implements ENT1-R1."""

    n: int
    d: int
    e: int = 65537

    def __post_init__(self):
        if type(self.n) is not int or self.n < 256 or type(self.d) is not int or self.d < 3:
            raise ContractError("invalid RSA private key")

    @property
    def public_key(self) -> RSAPublicKey:
        return RSAPublicKey(self.n, self.e)


def _is_probable_prime(candidate: int, rounds: int = 16) -> bool:
    if candidate < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if candidate % prime == 0:
            return candidate == prime
    d = candidate - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = secrets.randbelow(candidate - 3) + 2
        x = pow(a, d, candidate)
        if x in (1, candidate - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, candidate)
            if x == candidate - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


def rsa_generate_keypair(bits: int = 1024) -> RSAPrivateKey:
    """Generate an RSA keypair with pure python math. Implements ENT1-R1.

    Intended for tests and development fixtures; production deployments
    should plug in keys from the IdP via a key provider.
    """
    if type(bits) is not int or bits < 512 or bits % 2 != 0:
        raise ContractError("bits must be an even integer >= 512")
    e = 65537
    while True:
        p = _generate_prime(bits // 2)
        q = _generate_prime(bits // 2)
        if p == q:
            continue
        phi = (p - 1) * (q - 1)
        if phi % e == 0:
            continue
        n = p * q
        d = pow(e, -1, phi)
        return RSAPrivateKey(n=n, d=d, e=e)


def _emsa_pkcs1_v1_5_encode(message: bytes, em_len: int) -> bytes:
    digest = hashlib.sha256(message).digest()
    t = _SHA256_DER_PREFIX + digest
    if em_len < len(t) + 11:
        raise ContractError("RSA modulus too short for PKCS#1 v1.5 SHA-256")
    return b"\x00\x01" + b"\xff" * (em_len - len(t) - 3) + b"\x00" + t


def rsa_pkcs1v15_sign_sha256(key: RSAPrivateKey, message: bytes) -> bytes:
    """Sign a message with RSA PKCS#1 v1.5 over SHA-256. Implements ENT1-R1."""
    if not isinstance(key, RSAPrivateKey):
        raise ContractError("rsa sign requires an RSAPrivateKey")
    k = (key.n.bit_length() + 7) // 8
    em = _emsa_pkcs1_v1_5_encode(message, k)
    signature = pow(int.from_bytes(em, "big"), key.d, key.n)
    return signature.to_bytes(k, "big")


def rsa_pkcs1v15_verify_sha256(key: RSAPublicKey, message: bytes, signature: bytes) -> bool:
    """Verify an RSA PKCS#1 v1.5 SHA-256 signature. Implements ENT1-R1."""
    if not isinstance(key, RSAPublicKey) or not isinstance(signature, bytes):
        raise ContractError("rsa verify requires an RSAPublicKey and byte signature")
    k = (key.n.bit_length() + 7) // 8
    if len(signature) != k:
        return False
    try:
        em = _emsa_pkcs1_v1_5_encode(message, k)
    except ContractError:
        return False
    recovered = pow(int.from_bytes(signature, "big"), key.e, key.n).to_bytes(k, "big")
    return hmac.compare_digest(em, recovered)


# ---------------------------------------------------------------------------
# JWS / JWT. Implements ENT1-R1 (OIDC) and ENT1-R6 (auditable token events).
# ---------------------------------------------------------------------------

KeyProvider = Callable[[str | None], Any]
"""Resolve a key by key id (kid). May return bytes (HMAC), RSAPublicKey,
RSAPrivateKey, or a mapping of kid to key."""


def _resolve_key(provider: Any, kid: str | None) -> Any:
    if callable(provider):
        return provider(kid)
    if isinstance(provider, Mapping):
        if kid is not None and kid in provider:
            return provider[kid]
        if len(provider) == 1:
            return next(iter(provider.values()))
        raise ContractError("unknown key id")
    return provider


def _sign(alg: str, key: Any, message: bytes) -> bytes:
    if alg == "HS256":
        if not isinstance(key, bytes):
            raise ContractError("HS256 requires a byte key")
        return hmac_sha256_sign(key, message)
    if alg == "RS256":
        private = key if isinstance(key, RSAPrivateKey) else None
        if private is None:
            raise ContractError("RS256 signing requires an RSAPrivateKey")
        return rsa_pkcs1v15_sign_sha256(private, message)
    raise ContractError(f"unsupported JWT algorithm {alg!r}")


def _verify(alg: str, key: Any, message: bytes, signature: bytes) -> bool:
    if alg == "HS256":
        return isinstance(key, bytes) and hmac_sha256_verify(key, message, signature)
    if alg == "RS256":
        public = key.public_key if isinstance(key, RSAPrivateKey) else key
        return isinstance(public, RSAPublicKey) and rsa_pkcs1v15_verify_sha256(public, message, signature)
    raise ContractError(f"unsupported JWT algorithm {alg!r}")


def jwt_encode(payload: dict, key: Any, alg: str = "HS256", headers: dict | None = None) -> str:
    """Encode a signed JWT (HS256 or RS256). Implements ENT1-R1."""
    if not isinstance(payload, dict):
        raise ContractError("jwt payload must be a dict")
    header = {"alg": alg, "typ": "JWT"}
    if headers:
        header.update(headers)
        header["alg"] = alg
    signing_input = (
        b64url_encode(canonical(header).encode("utf-8"))
        + "."
        + b64url_encode(canonical(payload).encode("utf-8"))
    ).encode("ascii")
    signature = _sign(alg, key, signing_input)
    return signing_input.decode("ascii") + "." + b64url_encode(signature)


def jwt_decode(
    token: str,
    key_provider: Any,
    *,
    now: int,
    issuer: str | None = None,
    audience: str | None = None,
    leeway: int = 0,
    allowed_algs: tuple[str, ...] = ("HS256", "RS256"),
) -> dict:
    """Verify and decode a JWT. Implements ENT1-R1.

    Validates signature, exp, nbf, iat, iss, and aud. Raises
    ContractError on any validation failure; the caller is expected to
    record an access-denied observation (ENT1-R6).
    """
    if not isinstance(token, str):
        raise ContractError("jwt must be a string")
    parts = token.split(".")
    if len(parts) != 3:
        raise ContractError("jwt must have three segments")
    signing_input = parts[0] + "." + parts[1]
    try:
        header = json.loads(b64url_decode(parts[0]))
        payload = json.loads(b64url_decode(parts[1]))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ContractError("malformed jwt") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ContractError("malformed jwt")
    alg = header.get("alg")
    if alg not in allowed_algs or alg == "none":
        raise ContractError("jwt algorithm not allowed")
    signature = b64url_decode(parts[2])
    key = _resolve_key(key_provider, header.get("kid"))
    if key is None or not _verify(alg, key, signing_input.encode("ascii"), signature):
        raise ContractError("jwt signature verification failed")
    if type(now) is not int or type(leeway) is not int or leeway < 0:
        raise ContractError("now/leeway must be integers")
    exp = payload.get("exp")
    if exp is not None and (type(exp) is not int or now > exp + leeway):
        raise ContractError("jwt expired")
    nbf = payload.get("nbf")
    if nbf is not None and (type(nbf) is not int or now < nbf - leeway):
        raise ContractError("jwt not yet valid")
    iat = payload.get("iat")
    if iat is not None and type(iat) is not int:
        raise ContractError("jwt iat must be an integer")
    if issuer is not None and payload.get("iss") != issuer:
        raise ContractError("jwt issuer mismatch")
    if audience is not None:
        aud = payload.get("aud")
        audiences = aud if isinstance(aud, list) else [aud]
        if audience not in audiences:
            raise ContractError("jwt audience mismatch")
    return payload
