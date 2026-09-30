"""Station-authorized admission for execution-substrate qualification.

Content hashes prove integrity, not authority.  A qualification record can only
influence production routing after a trusted Station key signs an admission over
that exact record digest in a dedicated signature domain.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core import ContractError, canonical, digest, strict_json
from .qualification import (
    SubstrateQualificationRecord,
    SubstrateQualificationRegistry,
    SubstrateQualificationTuple,
)

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
except ImportError:  # fail closed; there is deliberately no symmetric fallback
    InvalidSignature = None
    serialization = None
    Ed25519PrivateKey = Ed25519PublicKey = None


ADMISSION_SCHEMA = "residual.substrate-qualification-admission.v1"
SIGNATURE_DOMAIN = b"residual.substrate.qualification-admission.v1\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_hash(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ContractError(f"{name} must be a lowercase sha256 digest")
    return value


@dataclass(frozen=True)
class QualificationAdmission:
    """Domain-separated Station authorization for one exact PASS record."""

    record_digest: str
    tuple_digest: str
    station_key_id: str
    issued_at_ns: int
    station_signature: str
    schema_version: str = ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ADMISSION_SCHEMA:
            raise ContractError("unsupported substrate qualification admission schema")
        for name in ("record_digest", "tuple_digest", "station_key_id"):
            _require_hash(getattr(self, name), name)
        if type(self.issued_at_ns) is not int or self.issued_at_ns <= 0:
            raise ContractError("qualification admission issued_at_ns is required")
        if (
            not isinstance(self.station_signature, str)
            or len(self.station_signature) != 128
            or any(ch not in "0123456789abcdef" for ch in self.station_signature)
        ):
            raise ContractError("qualification admission signature must be Ed25519 hex")

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_digest": self.record_digest,
            "tuple_digest": self.tuple_digest,
            "station_key_id": self.station_key_id,
            "issued_at_ns": self.issued_at_ns,
        }

    @property
    def admission_hash(self) -> str:
        return digest(self.unsigned_payload())

    def payload(self) -> dict[str, Any]:
        return {
            **self.unsigned_payload(),
            "admission_hash": self.admission_hash,
            "station_signature": self.station_signature,
        }

    @classmethod
    def from_payload(cls, value: dict[str, Any]) -> "QualificationAdmission":
        if not isinstance(value, dict):
            raise ContractError("qualification admission must be an object")
        data = strict_json(canonical(value))
        expected = {
            "schema_version",
            "record_digest",
            "tuple_digest",
            "station_key_id",
            "issued_at_ns",
            "admission_hash",
            "station_signature",
        }
        if set(data) != expected:
            raise ContractError("qualification admission keys do not match schema")
        expected_hash = data.pop("admission_hash")
        try:
            admission = cls(**data)
        except (TypeError, ValueError) as exc:
            raise ContractError("invalid qualification admission") from exc
        if expected_hash != admission.admission_hash:
            raise ContractError("qualification admission hash mismatch")
        return admission

    @classmethod
    def issue(
        cls,
        record: SubstrateQualificationRecord,
        private_key: Any,
        *,
        issued_at_ns: int,
    ) -> "QualificationAdmission":
        """Issue with an Ed25519 key under the substrate-specific domain.

        Production Station code may use the same underlying Ed25519 identity as
        other Station receipts, but this helper does not reuse their signature
        domain and does not expose or serialize private material.
        """
        if record.overall != "PASS":
            raise ContractError("only PASS qualification records may be admitted")
        if Ed25519PrivateKey is None or not isinstance(private_key, Ed25519PrivateKey):
            raise ContractError("cryptography Ed25519 support is required")
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        station_key_id = _sha256_bytes(public_key)
        unsigned = cls(
            record_digest=record.record_digest,
            tuple_digest=record.qualification_tuple.tuple_digest,
            station_key_id=station_key_id,
            issued_at_ns=issued_at_ns,
            station_signature="00" * 64,
        )
        signature = private_key.sign(
            SIGNATURE_DOMAIN + unsigned.admission_hash.encode("ascii")
        ).hex()
        return cls(
            record_digest=unsigned.record_digest,
            tuple_digest=unsigned.tuple_digest,
            station_key_id=station_key_id,
            issued_at_ns=issued_at_ns,
            station_signature=signature,
        )

    def verify(
        self,
        record: SubstrateQualificationRecord,
        station_public_key: bytes,
    ) -> bool:
        if record.overall != "PASS":
            return False
        if self.record_digest != record.record_digest:
            return False
        if self.tuple_digest != record.qualification_tuple.tuple_digest:
            return False
        if (
            Ed25519PublicKey is None
            or not isinstance(station_public_key, bytes)
            or len(station_public_key) != 32
        ):
            return False
        if _sha256_bytes(station_public_key) != self.station_key_id:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(station_public_key).verify(
                bytes.fromhex(self.station_signature),
                SIGNATURE_DOMAIN + self.admission_hash.encode("ascii"),
            )
            return True
        except (ValueError, InvalidSignature):
            return False


class AdmittedQualificationRegistry:
    """Qualification view that exposes only Station-admitted PASS records."""

    def __init__(
        self,
        evidence_registry: SubstrateQualificationRegistry | None = None,
    ) -> None:
        self._evidence = evidence_registry or SubstrateQualificationRegistry()
        self._admissions: dict[str, QualificationAdmission] = {}

    @property
    def evidence_registry(self) -> SubstrateQualificationRegistry:
        return self._evidence

    def admit(
        self,
        record: SubstrateQualificationRecord,
        admission: QualificationAdmission,
        *,
        station_public_key: bytes,
    ) -> str:
        if not isinstance(record, SubstrateQualificationRecord):
            raise ContractError("admission requires a qualification record")
        if not isinstance(admission, QualificationAdmission):
            raise ContractError("admission requires QualificationAdmission")
        if not admission.verify(record, station_public_key):
            raise ContractError("qualification admission signature is invalid")
        self._evidence.add(record)
        existing = self._admissions.get(record.record_digest)
        if existing is not None and existing.payload() != admission.payload():
            raise ContractError("qualification record has conflicting admissions")
        self._admissions[record.record_digest] = admission
        return admission.admission_hash

    def admission_for(self, record_digest: str) -> QualificationAdmission | None:
        _require_hash(record_digest, "record_digest")
        return self._admissions.get(record_digest)

    def get(
        self,
        qualification_tuple: SubstrateQualificationTuple,
        *,
        record_digest: str | None = None,
    ) -> SubstrateQualificationRecord | None:
        if record_digest is not None:
            _require_hash(record_digest, "record_digest")
            if record_digest not in self._admissions:
                return None
            record = self._evidence.get(
                qualification_tuple,
                record_digest=record_digest,
            )
            return record if record is not None and record.overall == "PASS" else None

        candidates = [
            record
            for record in self._evidence.records()
            if record.qualification_tuple.tuple_digest
            == qualification_tuple.tuple_digest
            and record.record_digest in self._admissions
            and record.overall == "PASS"
        ]
        if len(candidates) > 1:
            raise ContractError(
                "multiple admitted PASS records require record_digest pinning"
            )
        return candidates[0] if candidates else None

    def qualified_capabilities(
        self,
        qualification_tuple: SubstrateQualificationTuple,
        *,
        record_digest: str | None = None,
    ) -> frozenset[str]:
        record = self.get(qualification_tuple, record_digest=record_digest)
        return frozenset() if record is None else record.qualified_capabilities

    def require(
        self,
        qualification_tuple: SubstrateQualificationTuple,
        capability: str,
        *,
        record_digest: str | None = None,
    ) -> SubstrateQualificationRecord:
        if not isinstance(capability, str) or not capability.strip():
            raise ContractError("capability is required")
        record = self.get(qualification_tuple, record_digest=record_digest)
        if record is None:
            raise ContractError(
                "no Station-admitted PASS qualification for exact tuple"
            )
        if capability not in record.qualified_capabilities:
            raise ContractError(f"capability is not qualified: {capability}")
        return record

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        rows = []
        for record in self._evidence.records():
            admission = self._admissions.get(record.record_digest)
            rows.append({
                "tuple_digest": record.qualification_tuple.tuple_digest,
                "record_digest": record.record_digest,
                "overall": record.overall,
                "station_admitted": admission is not None,
                "admission_hash": (
                    None if admission is None else admission.admission_hash
                ),
                "station_key_id": (
                    None if admission is None else admission.station_key_id
                ),
                "qualified_capabilities": (
                    sorted(record.qualified_capabilities)
                    if admission is not None and record.overall == "PASS"
                    else []
                ),
            })
        return tuple(rows)



@dataclass(frozen=True)
class QualificationAdmissionBundle:
    """Content-addressed set of Station admissions, separate from evidence ledger."""

    admissions: tuple[QualificationAdmission, ...]
    schema_version: str = "residual.substrate-qualification-admission-bundle.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "residual.substrate-qualification-admission-bundle.v1":
            raise ContractError("unsupported qualification admission bundle schema")
        if any(not isinstance(item, QualificationAdmission) for item in self.admissions):
            raise ContractError("admission bundle contains invalid entry")
        record_digests = [item.record_digest for item in self.admissions]
        if len(record_digests) != len(set(record_digests)):
            raise ContractError("admission bundle contains duplicate record admission")

    def payload(self) -> dict[str, Any]:
        rows = sorted(
            (item.payload() for item in self.admissions),
            key=lambda row: row["record_digest"],
        )
        return {
            "schema_version": self.schema_version,
            "admissions": rows,
        }

    @property
    def bundle_digest(self) -> str:
        return digest(self.payload())

    def write(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical(self.payload()) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "QualificationAdmissionBundle":
        value = strict_json(Path(path).read_text(encoding="utf-8"))
        return cls.from_payload(value)

    @classmethod
    def from_payload(
        cls,
        value: dict[str, Any],
    ) -> "QualificationAdmissionBundle":
        if not isinstance(value, dict):
            raise ContractError("qualification admission bundle must be an object")
        data = strict_json(canonical(value))
        if set(data) != {"schema_version", "admissions"}:
            raise ContractError("qualification admission bundle keys do not match schema")
        if data["schema_version"] != "residual.substrate-qualification-admission-bundle.v1":
            raise ContractError("unsupported qualification admission bundle schema")
        if not isinstance(data["admissions"], list):
            raise ContractError("qualification admission bundle admissions must be a list")
        return cls(
            tuple(QualificationAdmission.from_payload(row) for row in data["admissions"]),
            schema_version=data["schema_version"],
        )

    def admitted_registry(
        self,
        evidence_registry: SubstrateQualificationRegistry,
        *,
        trusted_public_keys: dict[str, bytes],
    ) -> AdmittedQualificationRegistry:
        if not isinstance(evidence_registry, SubstrateQualificationRegistry):
            raise ContractError("admission bundle requires evidence registry")
        if not isinstance(trusted_public_keys, dict):
            raise ContractError("trusted_public_keys must map key ids to raw public keys")

        records = {
            record.record_digest: record
            for record in evidence_registry.records()
        }
        admitted = AdmittedQualificationRegistry(evidence_registry)
        for admission in self.admissions:
            record = records.get(admission.record_digest)
            if record is None:
                raise ContractError(
                    "admission references record absent from evidence ledger"
                )
            public_key = trusted_public_keys.get(admission.station_key_id)
            if public_key is None:
                raise ContractError(
                    "admission signer is not in trusted Station key set"
                )
            admitted.admit(
                record,
                admission,
                station_public_key=public_key,
            )
        return admitted
