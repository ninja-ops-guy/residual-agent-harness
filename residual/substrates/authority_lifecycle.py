"""Lifecycle controls for Station-authorized substrate qualification.

R0 proves that a trusted Station signed an exact PASS record. R1 adds the
properties needed for distributed operation: admission freshness, explicit
revocation, and dual-signed Station-key succession.

Trust roots remain local/pinned inputs. Lifecycle artifacts may extend or revoke
that trust, but they cannot bootstrap trust from an untrusted key.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..core import ContractError, canonical, digest, strict_json
from .admission import (
    AdmittedQualificationRegistry,
    QualificationAdmission,
    QualificationAdmissionBundle,
)
from .qualification import SubstrateQualificationRegistry

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
except ImportError:  # fail closed
    InvalidSignature = None
    serialization = None
    Ed25519PrivateKey = Ed25519PublicKey = None


REVOCATION_SCHEMA = "residual.substrate-qualification-revocation.v1"
REVOCATION_DOMAIN = b"residual.substrate.qualification-revocation.v1\n"
SUCCESSOR_SCHEMA = "residual.substrate-station-key-successor.v1"
SUCCESSOR_DOMAIN = b"residual.substrate.station-key-successor.v1\n"
LIFECYCLE_BUNDLE_SCHEMA = "residual.substrate-authority-lifecycle.v1"


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_hash(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ContractError(f"{name} must be a lowercase sha256 digest")
    return value


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")
    return value


def _raw_public(private_key: Any) -> bytes:
    if Ed25519PrivateKey is None or not isinstance(private_key, Ed25519PrivateKey):
        raise ContractError("cryptography Ed25519 support is required")
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _signature_hex(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 128
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ContractError(f"{name} must be Ed25519 signature hex")
    return value


def _verify(public_key: bytes, signature_hex: str, message: bytes) -> bool:
    if (
        Ed25519PublicKey is None
        or not isinstance(public_key, bytes)
        or len(public_key) != 32
    ):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            bytes.fromhex(signature_hex),
            message,
        )
        return True
    except (ValueError, InvalidSignature):
        return False


@dataclass(frozen=True)
class QualificationRevocation:
    """Station-signed revocation of one exact qualification admission."""

    admission_hash: str
    record_digest: str
    station_key_id: str
    effective_at_ns: int
    reason_code: str
    station_signature: str
    schema_version: str = REVOCATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != REVOCATION_SCHEMA:
            raise ContractError("unsupported qualification revocation schema")
        for name in ("admission_hash", "record_digest", "station_key_id"):
            _require_hash(getattr(self, name), name)
        if type(self.effective_at_ns) is not int or self.effective_at_ns <= 0:
            raise ContractError("revocation effective_at_ns is required")
        _require_text(self.reason_code, "reason_code")
        _signature_hex(self.station_signature, "station_signature")

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "admission_hash": self.admission_hash,
            "record_digest": self.record_digest,
            "station_key_id": self.station_key_id,
            "effective_at_ns": self.effective_at_ns,
            "reason_code": self.reason_code,
        }

    @property
    def revocation_hash(self) -> str:
        return digest(self.unsigned_payload())

    def payload(self) -> dict[str, Any]:
        return {
            **self.unsigned_payload(),
            "revocation_hash": self.revocation_hash,
            "station_signature": self.station_signature,
        }

    @classmethod
    def issue(
        cls,
        admission: QualificationAdmission,
        private_key: Any,
        *,
        effective_at_ns: int,
        reason_code: str,
    ) -> "QualificationRevocation":
        public = _raw_public(private_key)
        key_id = _hash_bytes(public)
        placeholder = cls(
            admission_hash=admission.admission_hash,
            record_digest=admission.record_digest,
            station_key_id=key_id,
            effective_at_ns=effective_at_ns,
            reason_code=reason_code,
            station_signature="00" * 64,
        )
        signature = private_key.sign(
            REVOCATION_DOMAIN + placeholder.revocation_hash.encode("ascii")
        ).hex()
        return cls(
            admission_hash=placeholder.admission_hash,
            record_digest=placeholder.record_digest,
            station_key_id=key_id,
            effective_at_ns=effective_at_ns,
            reason_code=reason_code,
            station_signature=signature,
        )

    def verify(self, public_key: bytes) -> bool:
        return (
            _hash_bytes(public_key) == self.station_key_id
            and _verify(
                public_key,
                self.station_signature,
                REVOCATION_DOMAIN + self.revocation_hash.encode("ascii"),
            )
        )

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "QualificationRevocation":
        data = strict_json(canonical(dict(value)))
        expected = {
            "schema_version",
            "admission_hash",
            "record_digest",
            "station_key_id",
            "effective_at_ns",
            "reason_code",
            "revocation_hash",
            "station_signature",
        }
        if set(data) != expected:
            raise ContractError("qualification revocation keys do not match schema")
        claimed_hash = data.pop("revocation_hash")
        try:
            item = cls(**data)
        except (TypeError, ValueError) as exc:
            raise ContractError("invalid qualification revocation") from exc
        if claimed_hash != item.revocation_hash:
            raise ContractError("qualification revocation hash mismatch")
        return item


@dataclass(frozen=True)
class StationKeySuccessor:
    """Dual-signed continuity from one trusted Station key to its successor.

    The predecessor authorizes the new key; the successor countersigns the same
    transition to prove possession. Admissions issued by the predecessor after
    predecessor_retire_at_ns are not valid.
    """

    predecessor_key_id: str
    successor_public_key_hex: str
    successor_key_id: str
    activates_at_ns: int
    predecessor_retire_at_ns: int
    predecessor_signature: str
    successor_signature: str
    schema_version: str = SUCCESSOR_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SUCCESSOR_SCHEMA:
            raise ContractError("unsupported Station-key successor schema")
        _require_hash(self.predecessor_key_id, "predecessor_key_id")
        _require_hash(self.successor_key_id, "successor_key_id")
        if (
            not isinstance(self.successor_public_key_hex, str)
            or len(self.successor_public_key_hex) != 64
            or any(ch not in "0123456789abcdef" for ch in self.successor_public_key_hex)
        ):
            raise ContractError("successor public key must be raw Ed25519 hex")
        if _hash_bytes(bytes.fromhex(self.successor_public_key_hex)) != self.successor_key_id:
            raise ContractError("successor public key/id mismatch")
        if type(self.activates_at_ns) is not int or self.activates_at_ns <= 0:
            raise ContractError("successor activates_at_ns is required")
        if (
            type(self.predecessor_retire_at_ns) is not int
            or self.predecessor_retire_at_ns < self.activates_at_ns
        ):
            raise ContractError(
                "predecessor retirement must be at or after successor activation"
            )
        _signature_hex(self.predecessor_signature, "predecessor_signature")
        _signature_hex(self.successor_signature, "successor_signature")

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "predecessor_key_id": self.predecessor_key_id,
            "successor_public_key_hex": self.successor_public_key_hex,
            "successor_key_id": self.successor_key_id,
            "activates_at_ns": self.activates_at_ns,
            "predecessor_retire_at_ns": self.predecessor_retire_at_ns,
        }

    @property
    def transition_hash(self) -> str:
        return digest(self.unsigned_payload())

    def payload(self) -> dict[str, Any]:
        return {
            **self.unsigned_payload(),
            "transition_hash": self.transition_hash,
            "predecessor_signature": self.predecessor_signature,
            "successor_signature": self.successor_signature,
        }

    @classmethod
    def issue(
        cls,
        predecessor_private_key: Any,
        successor_private_key: Any,
        *,
        activates_at_ns: int,
        predecessor_retire_at_ns: int,
    ) -> "StationKeySuccessor":
        predecessor_public = _raw_public(predecessor_private_key)
        successor_public = _raw_public(successor_private_key)
        predecessor_id = _hash_bytes(predecessor_public)
        successor_id = _hash_bytes(successor_public)
        placeholder = cls(
            predecessor_key_id=predecessor_id,
            successor_public_key_hex=successor_public.hex(),
            successor_key_id=successor_id,
            activates_at_ns=activates_at_ns,
            predecessor_retire_at_ns=predecessor_retire_at_ns,
            predecessor_signature="00" * 64,
            successor_signature="00" * 64,
        )
        message = SUCCESSOR_DOMAIN + placeholder.transition_hash.encode("ascii")
        return cls(
            predecessor_key_id=predecessor_id,
            successor_public_key_hex=successor_public.hex(),
            successor_key_id=successor_id,
            activates_at_ns=activates_at_ns,
            predecessor_retire_at_ns=predecessor_retire_at_ns,
            predecessor_signature=predecessor_private_key.sign(message).hex(),
            successor_signature=successor_private_key.sign(message).hex(),
        )

    def verify(self, predecessor_public_key: bytes) -> bool:
        successor_public = bytes.fromhex(self.successor_public_key_hex)
        message = SUCCESSOR_DOMAIN + self.transition_hash.encode("ascii")
        return (
            _hash_bytes(predecessor_public_key) == self.predecessor_key_id
            and _verify(predecessor_public_key, self.predecessor_signature, message)
            and _verify(successor_public, self.successor_signature, message)
        )

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "StationKeySuccessor":
        data = strict_json(canonical(dict(value)))
        expected = {
            "schema_version",
            "predecessor_key_id",
            "successor_public_key_hex",
            "successor_key_id",
            "activates_at_ns",
            "predecessor_retire_at_ns",
            "transition_hash",
            "predecessor_signature",
            "successor_signature",
        }
        if set(data) != expected:
            raise ContractError("Station-key successor keys do not match schema")
        claimed_hash = data.pop("transition_hash")
        try:
            item = cls(**data)
        except (TypeError, ValueError) as exc:
            raise ContractError("invalid Station-key successor") from exc
        if claimed_hash != item.transition_hash:
            raise ContractError("Station-key successor hash mismatch")
        return item


@dataclass(frozen=True)
class QualificationAuthorityPolicy:
    """Local freshness policy; this policy itself is not imported as authority."""

    now_ns: int
    max_admission_age_ns: int
    max_future_skew_ns: int = 0
    min_issued_at_ns: int = 0

    def __post_init__(self) -> None:
        if type(self.now_ns) is not int or self.now_ns <= 0:
            raise ContractError("authority policy now_ns is required")
        if type(self.max_admission_age_ns) is not int or self.max_admission_age_ns <= 0:
            raise ContractError("max_admission_age_ns must be positive")
        if type(self.max_future_skew_ns) is not int or self.max_future_skew_ns < 0:
            raise ContractError("max_future_skew_ns must be nonnegative")
        if type(self.min_issued_at_ns) is not int or self.min_issued_at_ns < 0:
            raise ContractError("min_issued_at_ns must be nonnegative")

    def allows(self, admission: QualificationAdmission) -> bool:
        if admission.issued_at_ns < self.min_issued_at_ns:
            return False
        if admission.issued_at_ns > self.now_ns + self.max_future_skew_ns:
            return False
        age = self.now_ns - admission.issued_at_ns
        return age <= self.max_admission_age_ns


class StationTrustStore:
    """Pinned roots plus verified, dual-signed successor transitions."""

    def __init__(
        self,
        root_public_keys: Iterable[bytes],
        *,
        transitions: Iterable[StationKeySuccessor] = (),
        distrusted_key_ids: Iterable[str] = (),
    ) -> None:
        roots: dict[str, bytes] = {}
        for raw in root_public_keys:
            if not isinstance(raw, bytes) or len(raw) != 32:
                raise ContractError("Station trust roots must be raw Ed25519 public keys")
            roots[_hash_bytes(raw)] = raw
        if not roots:
            raise ContractError("at least one Station trust root is required")
        self._roots = roots
        self._transitions = tuple(transitions)
        self._distrusted = frozenset(
            _require_hash(value, "distrusted_key_id")
            for value in distrusted_key_ids
        )

    def _known_keys(self) -> tuple[dict[str, bytes], dict[str, int], dict[str, int]]:
        known = dict(self._roots)
        activates = {key_id: 0 for key_id in known}
        retires: dict[str, int] = {}
        pending = list(self._transitions)
        progressed = True
        while pending and progressed:
            progressed = False
            remaining = []
            for transition in sorted(
                pending,
                key=lambda item: (item.activates_at_ns, item.transition_hash),
            ):
                predecessor = known.get(transition.predecessor_key_id)
                if predecessor is None:
                    remaining.append(transition)
                    continue
                if transition.predecessor_key_id in self._distrusted:
                    raise ContractError("Station-key transition descends from distrusted key")
                if not transition.verify(predecessor):
                    raise ContractError("Station-key successor signature is invalid")
                existing = known.get(transition.successor_key_id)
                successor = bytes.fromhex(transition.successor_public_key_hex)
                if existing is not None and existing != successor:
                    raise ContractError("Station-key successor id collision")
                known[transition.successor_key_id] = successor
                activates[transition.successor_key_id] = transition.activates_at_ns
                current_retire = retires.get(transition.predecessor_key_id)
                if current_retire is not None and current_retire != transition.predecessor_retire_at_ns:
                    raise ContractError("conflicting predecessor retirement times")
                retires[transition.predecessor_key_id] = transition.predecessor_retire_at_ns
                progressed = True
            pending = remaining
        if pending:
            raise ContractError("Station-key successor chain is not rooted in trusted key")
        return known, activates, retires

    def active_issuer_keys(self, at_ns: int) -> dict[str, bytes]:
        if type(at_ns) is not int or at_ns < 0:
            raise ContractError("issuer time must be nonnegative")
        known, activates, retires = self._known_keys()
        result = {}
        for key_id, raw in known.items():
            if key_id in self._distrusted:
                continue
            if at_ns < activates.get(key_id, 0):
                continue
            retire = retires.get(key_id)
            if retire is not None and at_ns >= retire:
                continue
            result[key_id] = raw
        return result

    def verification_keys(self) -> dict[str, bytes]:
        known, _activates, _retires = self._known_keys()
        return {
            key_id: raw
            for key_id, raw in known.items()
            if key_id not in self._distrusted
        }


@dataclass(frozen=True)
class QualificationAuthorityLifecycleBundle:
    transitions: tuple[StationKeySuccessor, ...] = ()
    revocations: tuple[QualificationRevocation, ...] = ()
    schema_version: str = LIFECYCLE_BUNDLE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != LIFECYCLE_BUNDLE_SCHEMA:
            raise ContractError("unsupported authority lifecycle bundle schema")
        transition_hashes = [item.transition_hash for item in self.transitions]
        revocation_hashes = [item.revocation_hash for item in self.revocations]
        if len(transition_hashes) != len(set(transition_hashes)):
            raise ContractError("duplicate Station-key transition")
        if len(revocation_hashes) != len(set(revocation_hashes)):
            raise ContractError("duplicate qualification revocation")

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "transitions": [
                item.payload()
                for item in sorted(self.transitions, key=lambda x: x.transition_hash)
            ],
            "revocations": [
                item.payload()
                for item in sorted(self.revocations, key=lambda x: x.revocation_hash)
            ],
        }

    @property
    def bundle_digest(self) -> str:
        return digest(self.payload())

    def write(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical(self.payload()) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "QualificationAuthorityLifecycleBundle":
        return cls.from_payload(strict_json(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_payload(
        cls,
        value: Mapping[str, Any],
    ) -> "QualificationAuthorityLifecycleBundle":
        data = strict_json(canonical(dict(value)))
        if set(data) != {"schema_version", "transitions", "revocations"}:
            raise ContractError("authority lifecycle bundle keys do not match schema")
        if data["schema_version"] != LIFECYCLE_BUNDLE_SCHEMA:
            raise ContractError("unsupported authority lifecycle bundle schema")
        return cls(
            transitions=tuple(
                StationKeySuccessor.from_payload(row)
                for row in data["transitions"]
            ),
            revocations=tuple(
                QualificationRevocation.from_payload(row)
                for row in data["revocations"]
            ),
            schema_version=data["schema_version"],
        )


def build_lifecycle_admitted_registry(
    evidence_registry: SubstrateQualificationRegistry,
    admissions: QualificationAdmissionBundle,
    lifecycle: QualificationAuthorityLifecycleBundle,
    *,
    root_public_keys: Iterable[bytes],
    policy: QualificationAuthorityPolicy,
    distrusted_key_ids: Iterable[str] = (),
) -> AdmittedQualificationRegistry:
    """Build the effective authority view at a specific local time."""

    trust = StationTrustStore(
        root_public_keys,
        transitions=lifecycle.transitions,
        distrusted_key_ids=distrusted_key_ids,
    )
    evidence = {
        record.record_digest: record
        for record in evidence_registry.records()
    }

    valid_revocations: set[str] = set()
    for revocation in lifecycle.revocations:
        if revocation.effective_at_ns > policy.now_ns:
            continue
        issuer_keys = trust.active_issuer_keys(revocation.effective_at_ns)
        signer = issuer_keys.get(revocation.station_key_id)
        if signer is None or not revocation.verify(signer):
            raise ContractError("qualification revocation is not signed by active trusted key")
        valid_revocations.add(revocation.admission_hash)

    # More than one trusted Station key may re-admit the same immutable PASS
    # during a rotation overlap. Resolve to exactly one effective admission per
    # record so the R0 admitted registry stays unambiguous.
    candidates: dict[str, list[tuple[QualificationAdmission, bytes]]] = {}
    for admission in admissions.admissions:
        record = evidence.get(admission.record_digest)
        if record is None:
            raise ContractError("admission references absent qualification record")
        if admission.admission_hash in valid_revocations:
            continue
        if not policy.allows(admission):
            continue
        issuer_keys = trust.active_issuer_keys(admission.issued_at_ns)
        signer = issuer_keys.get(admission.station_key_id)
        if signer is None or not admission.verify(record, signer):
            continue
        candidates.setdefault(admission.record_digest, []).append((admission, signer))

    admitted = AdmittedQualificationRegistry(evidence_registry)
    for record_digest in sorted(candidates):
        record = evidence[record_digest]
        admission, signer = max(
            candidates[record_digest],
            key=lambda item: (item[0].issued_at_ns, item[0].admission_hash),
        )
        admitted.admit(
            record,
            admission,
            station_public_key=signer,
        )
    return admitted
