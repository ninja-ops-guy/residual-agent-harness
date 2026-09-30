"""Machine-readable, exact-tuple qualification for execution substrates."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..core import ContractError, canonical, digest

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_STATUSES = {"PASS", "FAIL", "BLOCKED", "UNKNOWN"}


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")
    return value


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ContractError(f"{name} must be a lowercase sha256 digest")
    return value


def _unique(values: Iterable[str], name: str) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ContractError(f"{name} entries must be non-empty strings")
    if len(result) != len(set(result)):
        raise ContractError(f"{name} contains duplicates")
    return tuple(sorted(result))


@dataclass(frozen=True)
class SubstrateQualificationTuple:
    """The exact environment to which a qualification verdict applies."""

    substrate_name: str
    substrate_version: str
    substrate_source_identity: str
    driver: str
    platform_class: str
    agent_profile: str
    agent_identity: str
    image_digest: str
    requested_policy_digest: str
    provider_set_digest: str
    inference_route_digest: str
    schema_version: str = "residual.substrate-tuple.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "residual.substrate-tuple.v1":
            raise ContractError("unsupported substrate tuple schema")
        for name in (
            "substrate_name", "substrate_version", "substrate_source_identity",
            "driver", "platform_class", "agent_profile", "agent_identity",
        ):
            _text(getattr(self, name), name)
        for name in (
            "image_digest", "requested_policy_digest", "provider_set_digest",
            "inference_route_digest",
        ):
            _sha256(getattr(self, name), name)

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "substrate_name": self.substrate_name,
            "substrate_version": self.substrate_version,
            "substrate_source_identity": self.substrate_source_identity,
            "driver": self.driver,
            "platform_class": self.platform_class,
            "agent_profile": self.agent_profile,
            "agent_identity": self.agent_identity,
            "image_digest": self.image_digest,
            "requested_policy_digest": self.requested_policy_digest,
            "provider_set_digest": self.provider_set_digest,
            "inference_route_digest": self.inference_route_digest,
        }

    @property
    def tuple_digest(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class QualificationGate:
    gate_id: str
    status: str
    evidence_digest: str
    attempt: int = 1
    required: bool = True
    detail_code: str = ""

    def __post_init__(self) -> None:
        _text(self.gate_id, "gate_id")
        if self.status not in _ALLOWED_STATUSES:
            raise ContractError("invalid qualification gate status")
        _sha256(self.evidence_digest, "evidence_digest")
        if type(self.attempt) is not int or self.attempt < 1:
            raise ContractError("attempt must be a positive integer")
        if type(self.required) is not bool:
            raise ContractError("required must be boolean")
        if self.detail_code and (not isinstance(self.detail_code, str) or not self.detail_code.strip()):
            raise ContractError("detail_code must be a non-empty string when provided")

    def payload(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "status": self.status,
            "evidence_digest": self.evidence_digest,
            "attempt": self.attempt,
            "required": self.required,
            "detail_code": self.detail_code,
        }


@dataclass(frozen=True)
class SubstrateQualificationRecord:
    """Evidence-backed capabilities for one exact substrate tuple.

    A PASS is derived mechanically: every required gate must PASS. Capabilities
    are exposed only for PASS records; a caller cannot mark the record PASS by
    setting a free-form field.
    """

    qualification_tuple: SubstrateQualificationTuple
    gates: tuple[QualificationGate, ...]
    capabilities: tuple[str, ...]
    evidence_root_digest: str
    limitations: tuple[str, ...] = ()
    schema_version: str = "residual.substrate-qualification.v1"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != "residual.substrate-qualification.v1":
            raise ContractError("unsupported substrate qualification schema")
        if not isinstance(self.qualification_tuple, SubstrateQualificationTuple):
            raise ContractError("qualification_tuple is required")
        if not self.gates:
            raise ContractError("qualification record requires gates")
        if any(not isinstance(gate, QualificationGate) for gate in self.gates):
            raise ContractError("invalid qualification gate")
        identities = [(gate.gate_id, gate.attempt) for gate in self.gates]
        if len(identities) != len(set(identities)):
            raise ContractError("duplicate gate attempt identity")
        _unique(self.capabilities, "capabilities")
        _unique(self.limitations, "limitations")
        _sha256(self.evidence_root_digest, "evidence_root_digest")
        canonical(dict(self.metadata))

    @property
    def required_gates(self) -> tuple[QualificationGate, ...]:
        return tuple(gate for gate in self.gates if gate.required)

    @property
    def overall(self) -> str:
        statuses = {gate.status for gate in self.required_gates}
        if "FAIL" in statuses:
            return "FAIL"
        if "BLOCKED" in statuses:
            return "BLOCKED"
        if "UNKNOWN" in statuses:
            return "UNKNOWN"
        if statuses == {"PASS"}:
            return "PASS"
        return "UNKNOWN"

    @property
    def qualified_capabilities(self) -> frozenset[str]:
        return frozenset(self.capabilities if self.overall == "PASS" else ())

    def payload(self) -> dict[str, Any]:
        gates = sorted(
            (gate.payload() for gate in self.gates),
            key=lambda row: (row["gate_id"], row["attempt"]),
        )
        return {
            "schema_version": self.schema_version,
            "tuple": self.qualification_tuple.payload(),
            "tuple_digest": self.qualification_tuple.tuple_digest,
            "gates": gates,
            "overall": self.overall,
            "capabilities": sorted(self.capabilities),
            "limitations": sorted(self.limitations),
            "evidence_root_digest": self.evidence_root_digest,
            "metadata": dict(self.metadata),
        }

    @property
    def record_digest(self) -> str:
        return digest(self.payload())


class SubstrateQualificationRegistry:
    """Append-only in-memory view of qualification records.

    Different attempts for the same exact tuple may coexist only if they have
    distinct record digests. Resolution is fail closed: more than one current
    PASS for a tuple is considered ambiguous unless the caller pins a digest.
    """

    def __init__(self) -> None:
        self._records: dict[str, dict[str, SubstrateQualificationRecord]] = {}

    def add(self, record: SubstrateQualificationRecord) -> str:
        if not isinstance(record, SubstrateQualificationRecord):
            raise ContractError("registry requires a qualification record")
        tuple_digest = record.qualification_tuple.tuple_digest
        bucket = self._records.setdefault(tuple_digest, {})
        existing = bucket.get(record.record_digest)
        if existing is not None and existing.payload() != record.payload():
            raise ContractError("qualification record digest collision")
        bucket[record.record_digest] = record
        return record.record_digest

    def get(
        self,
        qualification_tuple: SubstrateQualificationTuple,
        *,
        record_digest: str | None = None,
    ) -> SubstrateQualificationRecord | None:
        bucket = self._records.get(qualification_tuple.tuple_digest, {})
        if record_digest is not None:
            _sha256(record_digest, "record_digest")
            return bucket.get(record_digest)
        passes = [record for record in bucket.values() if record.overall == "PASS"]
        if len(passes) > 1:
            raise ContractError("multiple PASS records require record_digest pinning")
        if len(passes) == 1:
            return passes[0]
        # With no PASS, return the sole record only when unambiguous. This makes
        # diagnostics available without selecting between contradictory attempts.
        return next(iter(bucket.values())) if len(bucket) == 1 else None

    def qualified_capabilities(
        self,
        qualification_tuple: SubstrateQualificationTuple,
        *,
        record_digest: str | None = None,
    ) -> frozenset[str]:
        record = self.get(qualification_tuple, record_digest=record_digest)
        if record is None:
            return frozenset()
        return record.qualified_capabilities

    def require(
        self,
        qualification_tuple: SubstrateQualificationTuple,
        capability: str,
        *,
        record_digest: str | None = None,
    ) -> SubstrateQualificationRecord:
        _text(capability, "capability")
        record = self.get(qualification_tuple, record_digest=record_digest)
        if record is None:
            raise ContractError("no unambiguous qualification record for exact tuple")
        if record.overall != "PASS":
            raise ContractError(f"substrate qualification is {record.overall}, not PASS")
        if capability not in record.qualified_capabilities:
            raise ContractError(f"capability is not qualified: {capability}")
        return record

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        rows = []
        for tuple_digest in sorted(self._records):
            for record_digest in sorted(self._records[tuple_digest]):
                record = self._records[tuple_digest][record_digest]
                rows.append({
                    "tuple_digest": tuple_digest,
                    "record_digest": record_digest,
                    "overall": record.overall,
                    "capabilities": sorted(record.qualified_capabilities),
                    "limitations": sorted(record.limitations),
                })
        return tuple(rows)


def provider_set_digest(provider_refs: Iterable[str]) -> str:
    return digest({"providers": sorted(_unique(provider_refs, "provider_refs"))})


def inference_route_digest(inference_route_ref: str | None) -> str:
    return digest({"inference_route_ref": inference_route_ref})
