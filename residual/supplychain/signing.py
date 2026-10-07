"""Release signing with hardware-protected keys. Implements ENT5-R1.

Every release MUST be cryptographically signed, the signature MUST
cover the release artifact, and the signing key MUST be managed with
hardware protection (HSM or equivalent). The :class:`HSMSigner`
interface models a PKCS#11-style signer whose private key never
leaves the device. :class:`SoftwareTestSigner` is a deterministic
HMAC-SHA256 signer behind the same interface, for offline tests only
(it is explicitly marked non-hardware and is rejected by
:func:`sign_release` unless ``allow_software=True``).
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from residual.core import ContractError, canonical, digest


@runtime_checkable
class HSMSigner(Protocol):
    """PKCS#11-style signer interface. Implements ENT5-R1.

    Real implementations talk to an HSM (or equivalent, e.g. a cloud
    KMS); the private key material is never exportable. ``hardware``
    MUST be True for production signers.
    """

    key_id: str
    hardware: bool

    def sign(self, payload: bytes) -> bytes:
        """Return a signature over ``payload``. Implements ENT5-R1."""
        ...


@dataclass(frozen=True)
class SoftwareTestSigner:
    """HMAC-SHA256 signer behind the HSMSigner interface, for tests only.

    Implements ENT5-R1 for offline/test environments where no HSM or
    Ed25519 support exists in the stdlib. ``hardware`` is False, so
    production signing paths must opt in to accept it.
    """

    key_id: str = "software-test-key"
    hardware: bool = False
    secret: bytes = b"residual-test-signing-key"

    def __post_init__(self):
        if not isinstance(self.secret, bytes) or len(self.secret) < 16:
            raise ContractError("test signer secret must be >= 16 bytes")

    def sign(self, payload: bytes) -> bytes:
        """Sign with HMAC-SHA256. Implements ENT5-R1 (test mode)."""
        return hmac.new(self.secret, payload, hashlib.sha256).digest()

    def verify(self, payload: bytes, signature: bytes) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)


@dataclass(frozen=True)
class BuildManifest:
    """Reproducible build manifest: hashes of inputs and outputs.

    Implements ENT5-R1 (manifest is signed with the release) and
    ENT5-R8 (manifest is the input to reproducibility verification).
    ``inputs`` and ``outputs`` map relative paths to sha256 hex digests.
    """

    version: str
    inputs: dict[str, str]
    outputs: dict[str, str]
    environment: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version:
            raise ContractError("manifest version required")
        for table_name, table in (("inputs", self.inputs), ("outputs", self.outputs)):
            if not isinstance(table, dict):
                raise ContractError(f"manifest {table_name} must be a dict")
            for path, sha in table.items():
                if not isinstance(path, str) or not path:
                    raise ContractError(f"manifest {table_name} path invalid")
                _check_sha256(sha)

    @property
    def sha256(self) -> str:
        """Deterministic manifest digest. Implements ENT5-R8."""
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "environment": dict(self.environment),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildManifest":
        if not isinstance(data, dict):
            raise ContractError("manifest must be a dict")
        return cls(
            version=data.get("version", ""),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            environment=data.get("environment", {}),
        )


@dataclass(frozen=True)
class SignedRelease:
    """A release artifact plus its signature. Implements ENT5-R1."""

    artifact_sha256: str
    signature: bytes
    key_id: str
    hardware: bool
    manifest: BuildManifest | None = None

    def __post_init__(self):
        _check_sha256(self.artifact_sha256)
        if not isinstance(self.signature, bytes) or not self.signature:
            raise ContractError("signature must be nonempty bytes")
        if not isinstance(self.key_id, str) or not self.key_id:
            raise ContractError("key_id required")
        if type(self.hardware) is not bool:
            raise ContractError("hardware flag must be bool")

    def signing_payload(self) -> bytes:
        """Canonical bytes the signature covers. Implements ENT5-R1."""
        body: dict = {"artifact_sha256": self.artifact_sha256}
        if self.manifest is not None:
            body["manifest_sha256"] = self.manifest.sha256
        return canonical(body).encode("utf-8")


def sign_release(
    artifact_sha256: str,
    signer: HSMSigner,
    manifest: BuildManifest | None = None,
    allow_software: bool = False,
) -> SignedRelease:
    """Sign a release artifact. Implements ENT5-R1.

    The signing key MUST be hardware-protected; software signers are
    rejected unless ``allow_software`` is explicitly set (tests only).
    """
    if not isinstance(signer, HSMSigner):
        raise ContractError("signer must implement the HSMSigner interface")
    if not signer.hardware and not allow_software:
        raise ContractError("ENT5-R1: signing key MUST be hardware protected (HSM or equivalent)")
    # Signature covers artifact digest (and manifest digest if present).
    body: dict = {"artifact_sha256": artifact_sha256}
    if manifest is not None:
        body["manifest_sha256"] = manifest.sha256
    signature = signer.sign(canonical(body).encode("utf-8"))
    return SignedRelease(
        artifact_sha256=artifact_sha256,
        signature=signature,
        key_id=signer.key_id,
        hardware=signer.hardware,
        manifest=manifest,
    )


def verify_release(release: SignedRelease, signer: HSMSigner) -> bool:
    """Verify a release signature against its payload. Implements ENT5-R1."""
    if not isinstance(release, SignedRelease):
        raise ContractError("release must be a SignedRelease")
    expected = signer.sign(release.signing_payload())
    return hmac.compare_digest(expected, release.signature) or expected == release.signature


def hash_file_bytes(data: bytes) -> str:
    """SHA-256 hex digest of artifact bytes. Implements ENT5-R1."""
    return hashlib.sha256(data).hexdigest()


def _check_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ContractError("expected sha256 hex digest")
    try:
        int(value, 16)
    except ValueError:
        raise ContractError("expected sha256 hex digest")
