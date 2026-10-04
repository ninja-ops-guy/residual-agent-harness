"""Versioned receipt integrity. A valid hash is never verification authority."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .authority import AuthorityCoercionRejected
from .core import ContractError, canonical, digest, identifier, strict_json
from .verifier import CheckResult


RECEIPT_SCHEMA = "residual.station.receipt.v3"
RECEIPT_SCHEMA_V2 = "residual.station.receipt.v2"
LEGACY_RECEIPT_SCHEMA = "residual.station.receipt.v1"
CACHE_SCHEMA = "residual.station.cache.v1"


def hash_id(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise AuthorityCoercionRejected(
            code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
            reason="expected a lowercase SHA-256 digest")
    return value


def verifier_id(value: str) -> str:
    if not isinstance(value, str) or value.count(":") != 1:
        raise AuthorityCoercionRejected(
            code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
            reason="verifier name must be domain:evaluator")
    for part in value.split(":"):
        identifier(part)
    return value


def _domain_hash(schema: str, payload: dict) -> str:
    return hashlib.sha256((schema + "\n" + canonical(payload)).encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class ReceiptReference:
    task_id: str
    receipt_hash: str

    def __post_init__(self):
        identifier(self.task_id)
        hash_id(self.receipt_hash)


@dataclass(frozen=True)
class StationReceipt:
    task_id: str
    cache_key: str
    value_hash: str
    verifier_name: str
    verifier_revision: str
    verdict: CheckResult
    kernel_revision: str
    parent_receipts: tuple[ReceiptReference, ...] = ()
    engine_name: str = "unknown"
    engine_version: str = "unknown"
    _schema_version: str = field(default=RECEIPT_SCHEMA, init=False, repr=False, compare=False)

    def __post_init__(self):
        identifier(self.task_id)
        for value in (self.cache_key, self.value_hash, self.verifier_revision):
            hash_id(value)
        if self.kernel_revision:
            hash_id(self.kernel_revision)
        verifier_id(self.verifier_name)
        if not isinstance(self.engine_name, str) or not self.engine_name.strip():
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="receipt engine_name is required")
        if not isinstance(self.engine_version, str) or not self.engine_version.strip():
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="receipt engine_version is required")
        try:
            verdict = CheckResult(self.verdict)
        except (ValueError, TypeError):
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="invalid receipt verdict") from None
        if verdict == CheckResult.SKIPPED:
            raise AuthorityCoercionRejected(
                code="UNPROVEN_ACCEPTANCE", fail_closed_state="UNPROVEN",
                reason="skipped checks cannot issue receipts")
        object.__setattr__(self, "verdict", verdict)
        if not isinstance(self.parent_receipts, (tuple, list)) or any(
                not isinstance(r, ReceiptReference) for r in self.parent_receipts):
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="parent receipts must be typed references")
        refs = tuple(sorted(self.parent_receipts))
        if len({r.task_id for r in refs}) != len(refs) or any(r.task_id == self.task_id for r in refs):
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="duplicate or self-dependent receipt")
        object.__setattr__(self, "parent_receipts", refs)

    def payload(self) -> dict:
        payload = {
            "task_id": self.task_id,
            "cache_key": self.cache_key,
            "value_hash": self.value_hash,
            "verifier_name": self.verifier_name,
            "verifier_revision": self.verifier_revision,
            "verdict": self.verdict.value,
            "parent_receipts": [asdict(r) for r in self.parent_receipts],
        }
        if self._schema_version in (RECEIPT_SCHEMA, RECEIPT_SCHEMA_V2):
            payload.update(engine_name=self.engine_name, engine_version=self.engine_version)
        if self._schema_version == RECEIPT_SCHEMA:
            payload["kernel_revision"] = self.kernel_revision
        return payload

    @property
    def receipt_hash(self) -> str:
        return _domain_hash(self._schema_version, self.payload())

    def to_dict(self) -> dict:
        return {"schema_version": self._schema_version, "hash_algorithm": "sha256",
                "receipt_hash": self.receipt_hash, "payload": self.payload()}

    @classmethod
    def from_dict(cls, envelope: dict) -> "StationReceipt":
        try:
            if set(envelope) != {"schema_version", "hash_algorithm", "receipt_hash", "payload"}:
                raise ValueError()
            schema = envelope["schema_version"]
            if schema not in {RECEIPT_SCHEMA, RECEIPT_SCHEMA_V2, LEGACY_RECEIPT_SCHEMA} or envelope["hash_algorithm"] != "sha256":
                raise ValueError()
            payload = envelope["payload"]
            v1_fields = {"task_id", "cache_key", "value_hash", "verifier_name", "verifier_revision", "verdict", "parent_receipts"}
            expected = v1_fields | ({"engine_name", "engine_version"} if schema in (RECEIPT_SCHEMA, RECEIPT_SCHEMA_V2) else set())
            expected |= {"kernel_revision"} if schema == RECEIPT_SCHEMA else set()
            if set(payload) != expected or not isinstance(payload["parent_receipts"], list):
                raise ValueError()
            if _domain_hash(schema, payload) != envelope["receipt_hash"]:
                raise ValueError()
            kwargs = {**payload, "parent_receipts": tuple(ReceiptReference(**p) for p in payload["parent_receipts"])}
            if schema == LEGACY_RECEIPT_SCHEMA:
                kwargs.update(engine_name="unknown", engine_version="unknown", kernel_revision="")
            elif schema == RECEIPT_SCHEMA_V2:
                kwargs["kernel_revision"] = ""
            receipt = cls(**kwargs)
            object.__setattr__(receipt, "_schema_version", schema)
            # Reject noncanonical parent order or any normalization of wire data.
            if receipt.payload() != payload or receipt.receipt_hash != envelope["receipt_hash"]:
                raise ValueError()
            return receipt
        except (ValueError, TypeError, KeyError, AttributeError):
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="invalid receipt envelope or integrity mismatch") from None

    @classmethod
    def from_json(cls, text: str) -> "StationReceipt":
        # A receipt envelope that cannot even be parsed cannot be bound as
        # evidence (EVD-001); strict_json failures surface as untyped
        # ContractErrors from shared plumbing, so re-raise them typed here.
        try:
            return cls.from_dict(strict_json(text))
        except AuthorityCoercionRejected:
            raise
        except ContractError as exc:
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason=str(exc)) from exc

    def matches(self, *, value: Any, cache_key: str, verifier_name: str,
                verifier_revision: str, parents: tuple[ReceiptReference, ...],
                engine_name: str | None = None, engine_version: str | None = None,
                kernel_revision: str | None = None) -> bool:
        """Check integrity/context only. The caller MUST still run the host verifier."""
        return (self.verdict == CheckResult.PASS and self.value_hash == digest(value)
                and self.cache_key == cache_key and self.verifier_name == verifier_name
                and self.verifier_revision == verifier_revision
                and self.parent_receipts == tuple(sorted(parents))
                and (engine_name is None or self.engine_name == engine_name)
                and (engine_version is None or self.engine_version == engine_version)
                and (kernel_revision is None or self.kernel_revision == kernel_revision))


def cache_key(*, project_id: str, task_id: str, goal_hash: str, contract_hash: str,
              verifier_name: str, verifier_revision: str, check_type: str,
              artifacts: dict[str, str], parents: tuple[ReceiptReference, ...]) -> str:
    identifier(project_id)
    identifier(task_id)
    verifier_id(verifier_name)
    for h in (goal_hash, contract_hash, verifier_revision, *artifacts.values()):
        hash_id(h)
    if check_type not in {"mechanical", "structural", "judge"}:
        raise AuthorityCoercionRejected(
            code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
            reason="unknown check type")
    for name in artifacts:
        identifier(name)
    refs = tuple(sorted(parents))
    if len({r.task_id for r in refs}) != len(refs) or any(r.task_id == task_id for r in refs):
        raise AuthorityCoercionRejected(
            code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
            reason="invalid prerequisite references")
    return _domain_hash(CACHE_SCHEMA, {"schema_version": CACHE_SCHEMA, "hash_algorithm": "sha256",
        "project_id": project_id, "task_id": task_id, "goal_hash": goal_hash,
        "contract_hash": contract_hash, "verifier_name": verifier_name,
        "verifier_revision": verifier_revision, "check_type": check_type,
        "artifacts": artifacts, "parent_receipts": [asdict(r) for r in refs]})


def validate_receipt_graph(receipts: dict[str, StationReceipt], dependencies: dict[str, tuple[str, ...]]) -> None:
    """Validate an exact prerequisite DAG without granting acceptance."""
    if set(receipts) != set(dependencies):
        raise AuthorityCoercionRejected(
            code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
            reason="missing receipt or dependency declaration")
    resolved = set()
    for tid, receipt in receipts.items():
        deps = dependencies[tid]
        if receipt.task_id != tid or len(set(deps)) != len(deps) or set(deps) - receipts.keys():
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="invalid receipt graph")
        expected = tuple(sorted(ReceiptReference(d, receipts[d].receipt_hash) for d in deps))
        if receipt.parent_receipts != expected:
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="prerequisite receipt mismatch")
    while len(resolved) < len(receipts):
        ready = {t for t, deps in dependencies.items() if set(deps) <= resolved} - resolved
        if not ready:
            raise AuthorityCoercionRejected(
                code="UNBOUND_EVIDENCE_SOURCE", fail_closed_state="NO_EXECUTION",
                reason="receipt dependency cycle")
        resolved |= ready
