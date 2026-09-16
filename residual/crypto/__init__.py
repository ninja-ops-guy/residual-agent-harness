"""Track L — cryptographic provider abstraction, backup encryption, key rotation.

Requirement IDs (RFC 2119):

- L-R1: All cryptographic operations MUST go through a ``CryptoProvider``
  implementation; no module performs ad-hoc signing or encryption.
- L-R2: A ``KmsProvider`` interface MUST abstract KMS/HSM backends; a local
  development provider MUST be available for offline tests and MUST NOT be
  used as a production default without explicit opt-in.
- L-R3: Backup encryption MUST use AES-256-GCM with random 96-bit nonces.
  When the ``cryptography`` package is installed it MUST be used; otherwise
  a documented, pure-stdlib AES-GCM fallback (dev/test only) is used.
- L-R4: Key rotation MUST keep retired keys verifiable for a bounded
  verification window and MUST reject verification after the window closes.
"""
from .provider import (
    CryptoProvider,
    KmsProvider,
    LocalDevCryptoProvider,
    LocalKmsProvider,
    aesgcm_decrypt,
    aesgcm_encrypt,
    backend_name,
)
from .rotation import KeyRecord, KeyRing

__all__ = [
    "CryptoProvider", "KmsProvider", "LocalDevCryptoProvider", "LocalKmsProvider",
    "KeyRecord", "KeyRing", "aesgcm_encrypt", "aesgcm_decrypt", "backend_name",
]
