"""M3 Evidence Bus: Station-signed receipts are the only trusted Factory handoff.

Artifacts and receipt metadata commit atomically in SQLite. Raw worker output is
never exposed by this API and is not copied into the artifact store before a
passing Station decision exists. Consumers must verify signatures and hashes
locally before reading bytes.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from residual.core import canonical, strict_json
from .worker_contract import WorkerContractError

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
except ImportError:  # fail closed; no symmetric fallback is silently substituted
    InvalidSignature = None
    Ed25519PrivateKey = Ed25519PublicKey = None
    serialization = None


RECEIPT_SCHEMA = "factory-worker-receipt-v1"
SIGNATURE_DOMAIN = b"residual.factory.worker-receipt.v1\n"


class EvidenceError(WorkerContractError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _require_hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise EvidenceError(f"invalid {name}")
    return value


@dataclass(frozen=True, slots=True)
class VerificationDecision:
    requirements_met: tuple[tuple[str, bool], ...]
    results: tuple[tuple[str, str], ...]
    verdict: str
    verifier_identity: str
    verifier_revision: str

    def __post_init__(self):
        if self.verdict not in {"pass", "fail", "unknown"}:
            raise EvidenceError("invalid verification verdict")
        if not isinstance(self.verifier_identity, str) or not self.verifier_identity.strip():
            raise EvidenceError("verifier identity required")
        _require_hash(self.verifier_revision, "verifier revision")
        reqs = tuple(sorted((str(k), bool(v)) for k, v in self.requirements_met))
        checks = tuple(sorted((str(k), str(v)) for k, v in self.results))
        if len({k for k, _ in reqs}) != len(reqs) or len({k for k, _ in checks}) != len(checks):
            raise EvidenceError("duplicate verification keys")
        if any(v not in {"pass", "fail", "unknown", "skipped"} for _, v in checks):
            raise EvidenceError("invalid check result")
        object.__setattr__(self, "requirements_met", reqs)
        object.__setattr__(self, "results", checks)

    def to_dict(self) -> dict[str, Any]:
        return {"requirements_met": [list(x) for x in self.requirements_met],
                "results": [list(x) for x in self.results], "verdict": self.verdict,
                "verifier_identity": self.verifier_identity,
                "verifier_revision": self.verifier_revision}


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    path: str
    sha256: str | None
    size_bytes: int
    deleted: bool = False

    def __post_init__(self):
        if not isinstance(self.path, str) or not self.path or self.path.startswith("/") or ".." in Path(self.path).parts:
            raise EvidenceError("invalid artifact path")
        if self.deleted:
            if self.sha256 is not None or self.size_bytes != 0:
                raise EvidenceError("deleted artifact cannot carry bytes")
        else:
            _require_hash(self.sha256, "artifact hash")
            if type(self.size_bytes) is not int or self.size_bytes < 0:
                raise EvidenceError("invalid artifact size")

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "size_bytes": self.size_bytes,
                "deleted": self.deleted}


@dataclass(frozen=True, slots=True)
class WorkerReceipt:
    receipt_id: str
    execution_plan_hash: str
    task_id: str
    worker_id: str
    swarm_id: str
    attempt_id: str
    engine_name: str
    engine_version: str
    input_commit: str
    output_commit: str
    contract_hash: str
    artifacts: tuple[ArtifactBinding, ...]
    requirements_met: tuple[tuple[str, bool], ...]
    verification_results: tuple[tuple[str, str], ...]
    overall_verdict: str
    verifier_identity: str
    verifier_revision: str
    parent_receipts: tuple[str, ...] = ()
    supersedes: str | None = None
    issued_at_ns: int = 0
    station_key_id: str = ""
    station_signature: str = ""
    schema_version: str = RECEIPT_SCHEMA

    def __post_init__(self):
        if self.schema_version != RECEIPT_SCHEMA:
            raise EvidenceError("unsupported receipt schema")
        for name in ("execution_plan_hash", "contract_hash", "verifier_revision"):
            _require_hash(getattr(self, name), name)
        if self.supersedes is not None:
            _require_hash(self.supersedes, "supersedes")
        for parent in self.parent_receipts:
            _require_hash(parent, "parent receipt")
        if len(set(self.parent_receipts)) != len(self.parent_receipts):
            raise EvidenceError("duplicate parent receipt")
        if self.overall_verdict != "pass":
            raise EvidenceError("only passing decisions can issue WorkerReceipt")
        if type(self.issued_at_ns) is not int or self.issued_at_ns <= 0:
            raise EvidenceError("receipt issued_at_ns required")
        if not all(isinstance(v, str) and v for v in (self.receipt_id, self.task_id, self.worker_id,
                self.swarm_id, self.attempt_id, self.engine_name, self.engine_version,
                self.input_commit, self.output_commit, self.verifier_identity,
                self.station_key_id, self.station_signature)):
            raise EvidenceError("receipt identity fields required")
        arts = tuple(sorted(self.artifacts, key=lambda x: x.path))
        if len({x.path for x in arts}) != len(arts):
            raise EvidenceError("duplicate receipt artifact path")
        object.__setattr__(self, "artifacts", arts)
        object.__setattr__(self, "parent_receipts", tuple(sorted(self.parent_receipts)))
        object.__setattr__(self, "requirements_met", tuple(sorted(self.requirements_met)))
        object.__setattr__(self, "verification_results", tuple(sorted(self.verification_results)))

    def unsigned_payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "receipt_id": self.receipt_id,
                "execution_plan_hash": self.execution_plan_hash, "task_id": self.task_id,
                "worker_id": self.worker_id, "swarm_id": self.swarm_id,
                "attempt_id": self.attempt_id, "engine_name": self.engine_name,
                "engine_version": self.engine_version, "input_commit": self.input_commit,
                "output_commit": self.output_commit, "contract_hash": self.contract_hash,
                "artifacts": [x.to_dict() for x in self.artifacts],
                "requirements_met": [list(x) for x in self.requirements_met],
                "verification_results": [list(x) for x in self.verification_results],
                "overall_verdict": self.overall_verdict,
                "verifier_identity": self.verifier_identity,
                "verifier_revision": self.verifier_revision,
                "parent_receipts": list(self.parent_receipts), "supersedes": self.supersedes,
                "issued_at_ns": self.issued_at_ns, "station_key_id": self.station_key_id}

    @property
    def receipt_hash(self) -> str:
        return _hash(self.unsigned_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_payload(), "receipt_hash": self.receipt_hash,
                "station_signature": self.station_signature}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkerReceipt":
        if not isinstance(value, dict):
            raise EvidenceError("receipt must be an object")
        value = strict_json(canonical(value))
        expected_hash = value.pop("receipt_hash", None)
        try:
            value["artifacts"] = tuple(ArtifactBinding(**x) for x in value["artifacts"])
            value["requirements_met"] = tuple(tuple(x) for x in value["requirements_met"])
            value["verification_results"] = tuple(tuple(x) for x in value["verification_results"])
            value["parent_receipts"] = tuple(value.get("parent_receipts", ()))
            receipt = cls(**value)
        except (TypeError, KeyError, ValueError) as exc:
            raise EvidenceError("invalid receipt") from exc
        if expected_hash != receipt.receipt_hash:
            raise EvidenceError("receipt hash mismatch")
        return receipt


class StationIdentity:
    """Local Ed25519 identity. Private material is never serialized into receipts."""
    def __init__(self, private_key):
        if Ed25519PrivateKey is None or not isinstance(private_key, Ed25519PrivateKey):
            raise EvidenceError("cryptography Ed25519 support is required")
        self._private = private_key
        self._public = private_key.public_key()
        self.key_id = _sha256(self.public_bytes())

    @classmethod
    def generate(cls) -> "StationIdentity":
        if Ed25519PrivateKey is None:
            raise EvidenceError("cryptography Ed25519 support is required")
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def load_private(cls, path: str | Path) -> "StationIdentity":
        if serialization is None:
            raise EvidenceError("cryptography Ed25519 support is required")
        data = Path(path).read_bytes()
        key = serialization.load_pem_private_key(data, password=None)
        return cls(key)

    def save_private(self, path: str | Path) -> None:
        path = Path(path)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            data = self._private.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
            os.write(fd, data); os.fsync(fd)
        finally:
            os.close(fd)

    def public_bytes(self) -> bytes:
        return self._public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def sign(self, payload_hash: str) -> str:
        _require_hash(payload_hash, "receipt hash")
        return self._private.sign(SIGNATURE_DOMAIN + payload_hash.encode("ascii")).hex()

    @staticmethod
    def verify(receipt: WorkerReceipt, public_key: bytes) -> bool:
        if Ed25519PublicKey is None or len(public_key) != 32:
            return False
        if _sha256(public_key) != receipt.station_key_id:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                bytes.fromhex(receipt.station_signature),
                SIGNATURE_DOMAIN + receipt.receipt_hash.encode("ascii"))
            return True
        except (ValueError, InvalidSignature):
            return False
