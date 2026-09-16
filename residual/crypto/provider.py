"""CryptoProvider abstraction and KMS/HSM interface (Track L).

Implements L-R1 (single CryptoProvider surface for sign/verify/encrypt/decrypt),
L-R2 (KmsProvider interface with a local development KMS), and L-R3 (AES-256-GCM
backup encryption; ``cryptography`` backend preferred, documented stdlib fallback
otherwise).
"""
from __future__ import annotations

import hashlib
import hmac
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..core import ContractError, identifier

try:  # L-R3: prefer the audited backend when available.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM

    _HAVE_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover - environment dependent
    _AESGCM = None
    _HAVE_CRYPTOGRAPHY = False

from ._aesgcm_fallback import fallback_aesgcm_decrypt, fallback_aesgcm_encrypt, random_nonce

TAG_LEN = 16
KEY_LEN = 32  # AES-256
NONCE_LEN = 12


def backend_name() -> str:
    """Report which AES-GCM backend is active (auditability for L-R3)."""
    return "cryptography" if _HAVE_CRYPTOGRAPHY else "stdlib-fallback"


def aesgcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b"",
                   nonce: bytes | None = None) -> bytes:
    """AES-GCM encrypt; returns nonce || ciphertext || tag."""
    if len(key) != KEY_LEN:
        raise ContractError("AES-256-GCM requires a 32-byte key")
    nonce = random_nonce() if nonce is None else nonce
    if len(nonce) != NONCE_LEN:
        raise ContractError("AES-GCM nonce must be 12 bytes")
    if _HAVE_CRYPTOGRAPHY:
        ct = _AESGCM(key).encrypt(nonce, plaintext, aad or None)
    else:
        ct = fallback_aesgcm_encrypt(key, nonce, plaintext, aad)
    return nonce + ct


def aesgcm_decrypt(key: bytes, blob: bytes, aad: bytes = b"") -> bytes:
    """Decrypt a blob produced by :func:`aesgcm_encrypt`."""
    if len(key) != KEY_LEN:
        raise ContractError("AES-256-GCM requires a 32-byte key")
    if len(blob) < NONCE_LEN + TAG_LEN:
        raise ContractError("ciphertext blob too short")
    nonce, ct = blob[:NONCE_LEN], blob[NONCE_LEN:]
    try:
        if _HAVE_CRYPTOGRAPHY:
            return _AESGCM(key).decrypt(nonce, ct, aad or None)
        return fallback_aesgcm_decrypt(key, nonce, ct, aad)
    except ContractError:
        raise
    except Exception as exc:  # cryptography raises InvalidTag etc.
        raise ContractError("AES-GCM decryption failed") from exc


class CryptoProvider(ABC):
    """Abstract crypto surface. Implements L-R1.

    Implementations MUST provide HMAC- or signature-grade sign/verify and
    AEAD-grade encrypt/decrypt. Key material MUST NOT be exposed by the
    interface.
    """

    provider_id = "abstract"

    @abstractmethod
    def sign(self, data: bytes, *, key_id: str | None = None) -> bytes:
        ...

    @abstractmethod
    def verify(self, data: bytes, signature: bytes, *, key_id: str | None = None) -> bool:
        ...

    @abstractmethod
    def encrypt(self, plaintext: bytes, aad: bytes = b"", *, key_id: str | None = None) -> bytes:
        ...

    @abstractmethod
    def decrypt(self, blob: bytes, aad: bytes = b"", *, key_id: str | None = None) -> bytes:
        ...


class KmsProvider(ABC):
    """KMS/HSM abstraction. Implements L-R2.

    Production deployments SHOULD back this with a cloud KMS or PKCS#11 HSM;
    key material MUST stay inside the KMS and only wrapped (encrypted) keys
    may leave it.
    """

    kms_id = "abstract"

    @abstractmethod
    def wrap_key(self, plaintext_key: bytes, *, kek_id: str) -> bytes:
        """Encrypt (wrap) a data-encryption key under a KEK."""
        ...

    @abstractmethod
    def unwrap_key(self, wrapped: bytes, *, kek_id: str) -> bytes:
        ...

    @abstractmethod
    def generate_data_key(self, *, kek_id: str) -> tuple[bytes, bytes]:
        """Return (plaintext_dek, wrapped_dek)."""
        ...


@dataclass
class LocalKmsProvider(KmsProvider):
    """Deterministic local KMS for development/tests only (L-R2).

    Derives KEKs from a local master secret via HKDF-like HMAC expansion.
    MUST NOT be used as a production default; callers must opt in explicitly
    by constructing it.
    """

    master_secret: bytes
    kms_id: str = "local-dev-kms"

    def __post_init__(self):
        if len(self.master_secret) < 16:
            raise ContractError("local KMS master secret must be at least 16 bytes")

    def _kek(self, kek_id: str) -> bytes:
        identifier(kek_id)
        return hmac.new(self.master_secret, b"kek:" + kek_id.encode("utf-8"),
                        hashlib.sha256).digest()

    def wrap_key(self, plaintext_key: bytes, *, kek_id: str) -> bytes:
        return aesgcm_encrypt(self._kek(kek_id), plaintext_key,
                              aad=b"wrap:" + kek_id.encode("utf-8"))

    def unwrap_key(self, wrapped: bytes, *, kek_id: str) -> bytes:
        return aesgcm_decrypt(self._kek(kek_id), wrapped,
                              aad=b"wrap:" + kek_id.encode("utf-8"))

    def generate_data_key(self, *, kek_id: str) -> tuple[bytes, bytes]:
        dek = os.urandom(KEY_LEN)
        return dek, self.wrap_key(dek, kek_id=kek_id)


class LocalDevCryptoProvider(CryptoProvider):
    """Local development provider (L-R1/L-R2): HMAC-SHA-256 signatures and
    AES-256-GCM encryption, with data keys optionally wrapped by a KmsProvider.

    Not for production default use; production MUST supply a KMS/HSM-backed
    provider implementing the same interface.
    """

    provider_id = "local-dev"

    def __init__(self, signing_key: bytes | None = None,
                 encryption_key: bytes | None = None,
                 kms: KmsProvider | None = None):
        self.signing_key = signing_key or os.urandom(32)
        if len(self.signing_key) < 16:
            raise ContractError("signing key must be at least 16 bytes")
        self.encryption_key = encryption_key or os.urandom(KEY_LEN)
        if len(self.encryption_key) != KEY_LEN:
            raise ContractError("encryption key must be 32 bytes")
        self.kms = kms

    def sign(self, data: bytes, *, key_id: str | None = None) -> bytes:
        if not isinstance(data, bytes):
            raise ContractError("sign data must be bytes")
        return hmac.new(self.signing_key, data, hashlib.sha256).digest()

    def verify(self, data: bytes, signature: bytes, *, key_id: str | None = None) -> bool:
        expected = self.sign(data, key_id=key_id)
        return hmac.compare_digest(expected, signature)

    def encrypt(self, plaintext: bytes, aad: bytes = b"", *, key_id: str | None = None) -> bytes:
        if not isinstance(plaintext, bytes):
            raise ContractError("plaintext must be bytes")
        return aesgcm_encrypt(self.encryption_key, plaintext, aad)

    def decrypt(self, blob: bytes, aad: bytes = b"", *, key_id: str | None = None) -> bytes:
        return aesgcm_decrypt(self.encryption_key, blob, aad)

    # -- backup path (L-R3): envelope encryption via KMS -------------------

    def encrypt_backup(self, plaintext: bytes, *, kek_id: str = "backup",
                       kms: KmsProvider | None = None) -> dict:
        """Envelope-encrypt a backup: random DEK encrypts the payload; the DEK
        is wrapped by the KMS. Returns a serializable dict."""
        kms = kms or self.kms or LocalKmsProvider(self.signing_key)
        dek, wrapped = kms.generate_data_key(kek_id=kek_id)
        try:
            blob = aesgcm_encrypt(dek, plaintext, aad=b"residual.backup.v1")
        finally:
            dek = b"\x00" * len(dek)
        return {
            "schema": "residual.backup.v1",
            "kek_id": kek_id,
            "wrapped_dek": wrapped.hex(),
            "ciphertext": blob.hex(),
            "backend": backend_name(),
        }

    def decrypt_backup(self, envelope: dict, *,
                       kms: KmsProvider | None = None) -> bytes:
        if envelope.get("schema") != "residual.backup.v1":
            raise ContractError("unknown backup envelope schema")
        kms = kms or self.kms or LocalKmsProvider(self.signing_key)
        kek_id = envelope["kek_id"]
        dek = kms.unwrap_key(bytes.fromhex(envelope["wrapped_dek"]), kek_id=kek_id)
        try:
            return aesgcm_decrypt(dek, bytes.fromhex(envelope["ciphertext"]),
                                  aad=b"residual.backup.v1")
        finally:
            dek = b"\x00" * len(dek)
