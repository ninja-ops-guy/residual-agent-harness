"""Qualification artifacts for the v1 authority-type invariant family.

This module does not grant runtime authority. It binds adversarial attack
definitions to an exact candidate/contract, records what was observed, and
derives qualification only when both the expected rejection reason and the
expected fail-closed state are satisfied.

The parent invariant INV-AUTH-000 is deliberately derived only over the six
declared v1 child coercions. It is not a claim about undeclared type pairs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping

from residual.core import ContractError, canonical, strict_json


PARENT_INVARIANT = "INV-AUTH-000"
AUTH_CHILDREN: dict[str, tuple[str, str]] = {
    "INV-AUTH-EVD-001": ("OBSERVATION", "EVIDENCE"),
    "INV-AUTH-IDN-002": ("IDENTITY", "AUTHORITY"),
    "INV-AUTH-ACC-003": ("TEST_RESULT", "ACCEPTANCE"),
    "INV-AUTH-CTR-004": ("INTERPRETATION", "CONTRACT"),
    "INV-AUTH-AMB-005": ("AMBIGUOUS_INTENT", "EXECUTABLE_AUTHORITY"),
    "INV-AUTH-AUT-006": ("SUGGESTION", "AUTHORIZATION"),
}
ATTACK_MANIFEST_SCHEMA = "residual.auth.attack-manifest.v1"
ATTACK_RECEIPT_SCHEMA = "residual.auth.attack-execution-receipt.v1"
QUALIFICATION_RECORD_SCHEMA = "residual.auth.qualification-record.v1"

_HASH64 = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FAILURE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _require_hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _HASH64.fullmatch(value):
        raise ContractError(f"{name} must be a lowercase sha256 digest")
    return value


def _require_git_oid(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _GIT_OID.fullmatch(value):
        raise ContractError(f"{name} must be a lowercase 40- or 64-hex git object id")
    return value


def _require_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ContractError(f"{name} must be a bounded identifier")
    return value


def _require_failure_code(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _FAILURE_CODE.fullmatch(value):
        raise ContractError(f"{name} must be a machine-readable uppercase failure code")
    return value


@dataclass(frozen=True, slots=True)
class FailClosedState:
    """Normalized fail-closed predicates.

    Observed state may contain more predicates than expected. Qualification
    succeeds only when every expected predicate is present with the exact
    expected value.
    """

    predicates: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        normalized: list[tuple[str, str]] = []
        seen: set[str] = set()
        for item in self.predicates:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ContractError("fail-closed state predicates must be key/value pairs")
            key, value = item
            _require_id(key, "fail-closed predicate")
            if not isinstance(value, str) or not value or len(value) > 160:
                raise ContractError("fail-closed predicate values must be bounded non-empty text")
            if key in seen:
                raise ContractError("duplicate fail-closed predicate")
            seen.add(key)
            normalized.append((key, value))
        if not normalized:
            raise ContractError("fail-closed state requires at least one predicate")
        object.__setattr__(self, "predicates", tuple(sorted(normalized)))

    @classmethod
    def from_mapping(cls, value: Mapping[str, str]) -> "FailClosedState":
        if not isinstance(value, Mapping):
            raise ContractError("fail-closed state must be an object")
        return cls(tuple((str(k), v) for k, v in value.items()))

    def to_dict(self) -> dict[str, str]:
        return dict(self.predicates)

    def satisfies(self, expected: "FailClosedState") -> bool:
        observed = self.to_dict()
        return all(observed.get(key) == value for key, value in expected.predicates)


@dataclass(frozen=True, slots=True)
class AttackManifest:
    attack_id: str
    invariant_id: str
    target_head: str
    target_tree: str
    target_contract_id: str
    attack_input_hash: str
    expected_fail_closed_state: FailClosedState
    expected_failure_code: str
    schema_version: str = ATTACK_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ATTACK_MANIFEST_SCHEMA:
            raise ContractError("unsupported authority attack manifest schema")
        _require_id(self.attack_id, "attack_id")
        if self.invariant_id not in AUTH_CHILDREN:
            raise ContractError("attack manifest must name one declared v1 AUTH child invariant")
        _require_git_oid(self.target_head, "target_head")
        _require_git_oid(self.target_tree, "target_tree")
        _require_hash(self.target_contract_id, "target_contract_id")
        _require_hash(self.attack_input_hash, "attack_input_hash")
        _require_failure_code(self.expected_failure_code, "expected_failure_code")
        if not isinstance(self.expected_fail_closed_state, FailClosedState):
            raise ContractError("expected_fail_closed_state must be a FailClosedState")

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "attack_id": self.attack_id,
            "invariant_id": self.invariant_id,
            "target_head": self.target_head,
            "target_tree": self.target_tree,
            "target_contract_id": self.target_contract_id,
            "attack_input_hash": self.attack_input_hash,
            "expected_fail_closed_state": self.expected_fail_closed_state.to_dict(),
            "expected_failure_code": self.expected_failure_code,
        }

    @property
    def manifest_hash(self) -> str:
        return _digest(self.unsigned_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_payload(), "manifest_hash": self.manifest_hash}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AttackManifest":
        if not isinstance(value, dict):
            raise ContractError("attack manifest must be an object")
        raw = strict_json(canonical(value))
        expected_hash = raw.pop("manifest_hash", None)
        try:
            raw["expected_fail_closed_state"] = FailClosedState.from_mapping(
                raw["expected_fail_closed_state"])
            manifest = cls(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError("invalid authority attack manifest") from exc
        if expected_hash is not None and expected_hash != manifest.manifest_hash:
            raise ContractError("authority attack manifest hash mismatch")
        return manifest


@dataclass(frozen=True, slots=True)
class AttackExecutionReceipt:
    """Observed execution of one exact attack manifest.

    receipt_hash is computed over unsigned_payload() and therefore never hashes
    itself. The qualification record, not this receipt, binds the receipt hash
    to the PASS/FAIL conclusion.
    """

    attack_manifest_hash: str
    candidate_head: str
    candidate_tree: str
    contract_id: str
    runner_identity: str
    observed_failure_code: str
    observed_fail_closed_state: FailClosedState
    evidence_hashes: tuple[str, ...]
    issued_at_ns: int
    schema_version: str = ATTACK_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != ATTACK_RECEIPT_SCHEMA:
            raise ContractError("unsupported authority attack receipt schema")
        _require_hash(self.attack_manifest_hash, "attack_manifest_hash")
        _require_git_oid(self.candidate_head, "candidate_head")
        _require_git_oid(self.candidate_tree, "candidate_tree")
        _require_hash(self.contract_id, "contract_id")
        _require_id(self.runner_identity, "runner_identity")
        _require_failure_code(self.observed_failure_code, "observed_failure_code")
        if not isinstance(self.observed_fail_closed_state, FailClosedState):
            raise ContractError("observed_fail_closed_state must be a FailClosedState")
        hashes = tuple(self.evidence_hashes)
        if not hashes:
            raise ContractError("attack execution receipt requires at least one evidence hash")
        for value in hashes:
            _require_hash(value, "evidence hash")
        if len(set(hashes)) != len(hashes):
            raise ContractError("duplicate evidence hash")
        if type(self.issued_at_ns) is not int or self.issued_at_ns <= 0:
            raise ContractError("issued_at_ns must be a positive integer")
        object.__setattr__(self, "evidence_hashes", tuple(sorted(hashes)))

    def unsigned_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "attack_manifest_hash": self.attack_manifest_hash,
            "candidate_head": self.candidate_head,
            "candidate_tree": self.candidate_tree,
            "contract_id": self.contract_id,
            "runner_identity": self.runner_identity,
            "observed_failure_code": self.observed_failure_code,
            "observed_fail_closed_state": self.observed_fail_closed_state.to_dict(),
            "evidence_hashes": list(self.evidence_hashes),
            "issued_at_ns": self.issued_at_ns,
        }

    @property
    def receipt_hash(self) -> str:
        return _digest(self.unsigned_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_payload(), "receipt_hash": self.receipt_hash}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AttackExecutionReceipt":
        if not isinstance(value, dict):
            raise ContractError("attack execution receipt must be an object")
        raw = strict_json(canonical(value))
        expected_hash = raw.pop("receipt_hash", None)
        try:
            raw["observed_fail_closed_state"] = FailClosedState.from_mapping(
                raw["observed_fail_closed_state"])
            raw["evidence_hashes"] = tuple(raw["evidence_hashes"])
            receipt = cls(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError("invalid authority attack execution receipt") from exc
        if expected_hash is not None and expected_hash != receipt.receipt_hash:
            raise ContractError("authority attack execution receipt hash mismatch")
        return receipt


@dataclass(frozen=True, slots=True)
class QualificationRecord:
    invariant_id: str
    attack_id: str
    result: str
    candidate_head: str
    candidate_tree: str
    contract_id: str
    source_type: str
    target_type: str
    attack_manifest_hash: str
    evidence_receipt_hash: str
    expected_failure_code: str
    observed_failure_code: str
    expected_fail_closed_state: FailClosedState
    observed_fail_closed_state: FailClosedState
    failure_reasons: tuple[str, ...] = ()
    schema_version: str = QUALIFICATION_RECORD_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != QUALIFICATION_RECORD_SCHEMA:
            raise ContractError("unsupported authority qualification record schema")
        if self.invariant_id not in AUTH_CHILDREN:
            raise ContractError("qualification record must name one declared AUTH child invariant")
        _require_id(self.attack_id, "attack_id")
        if self.result not in {"PASS", "FAIL"}:
            raise ContractError("qualification result must be PASS or FAIL")
        _require_git_oid(self.candidate_head, "candidate_head")
        _require_git_oid(self.candidate_tree, "candidate_tree")
        _require_hash(self.contract_id, "contract_id")
        _require_hash(self.attack_manifest_hash, "attack_manifest_hash")
        _require_hash(self.evidence_receipt_hash, "evidence_receipt_hash")
        _require_failure_code(self.expected_failure_code, "expected_failure_code")
        _require_failure_code(self.observed_failure_code, "observed_failure_code")
        expected_types = AUTH_CHILDREN[self.invariant_id]
        if (self.source_type, self.target_type) != expected_types:
            raise ContractError("qualification source/target types do not match invariant")
        reasons = tuple(self.failure_reasons)
        if self.result == "PASS" and reasons:
            raise ContractError("passing qualification cannot carry failure reasons")
        if self.result == "FAIL" and not reasons:
            raise ContractError("failing qualification requires a reason")
        object.__setattr__(self, "failure_reasons", reasons)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "invariant_id": self.invariant_id,
            "attack_id": self.attack_id,
            "result": self.result,
            "candidate_head": self.candidate_head,
            "candidate_tree": self.candidate_tree,
            "contract_id": self.contract_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "attack_manifest_hash": self.attack_manifest_hash,
            "evidence_receipt_hash": self.evidence_receipt_hash,
            "expected_failure_code": self.expected_failure_code,
            "observed_failure_code": self.observed_failure_code,
            "expected_fail_closed_state": self.expected_fail_closed_state.to_dict(),
            "observed_fail_closed_state": self.observed_fail_closed_state.to_dict(),
            "failure_reasons": list(self.failure_reasons),
        }


def qualify(manifest: AttackManifest, receipt: AttackExecutionReceipt) -> QualificationRecord:
    """Compare an attack execution against the exact manifest.

    A matching rejection code is necessary but insufficient: the observed state
    must also satisfy every expected fail-closed predicate, and the receipt must
    be bound to the manifest's exact HEAD/TREE/contract tuple.
    """

    if not isinstance(manifest, AttackManifest) or not isinstance(receipt, AttackExecutionReceipt):
        raise ContractError("qualify requires an AttackManifest and AttackExecutionReceipt")

    reasons: list[str] = []
    if receipt.attack_manifest_hash != manifest.manifest_hash:
        reasons.append("ATTACK_MANIFEST_MISMATCH")
    if receipt.candidate_head != manifest.target_head:
        reasons.append("TARGET_HEAD_MISMATCH")
    if receipt.candidate_tree != manifest.target_tree:
        reasons.append("TARGET_TREE_MISMATCH")
    if receipt.contract_id != manifest.target_contract_id:
        reasons.append("TARGET_CONTRACT_MISMATCH")
    if receipt.observed_failure_code != manifest.expected_failure_code:
        reasons.append("FAILURE_CODE_MISMATCH")
    if not receipt.observed_fail_closed_state.satisfies(manifest.expected_fail_closed_state):
        reasons.append("FAIL_CLOSED_STATE_MISMATCH")

    source_type, target_type = AUTH_CHILDREN[manifest.invariant_id]
    return QualificationRecord(
        invariant_id=manifest.invariant_id,
        attack_id=manifest.attack_id,
        result="PASS" if not reasons else "FAIL",
        candidate_head=manifest.target_head,
        candidate_tree=manifest.target_tree,
        contract_id=manifest.target_contract_id,
        source_type=source_type,
        target_type=target_type,
        attack_manifest_hash=manifest.manifest_hash,
        evidence_receipt_hash=receipt.receipt_hash,
        expected_failure_code=manifest.expected_failure_code,
        observed_failure_code=receipt.observed_failure_code,
        expected_fail_closed_state=manifest.expected_fail_closed_state,
        observed_fail_closed_state=receipt.observed_fail_closed_state,
        failure_reasons=tuple(reasons),
    )


def qualification_report(records: Iterable[QualificationRecord]) -> dict[str, Any]:
    """Derive INV-AUTH-000 from exactly one result for each declared child.

    The six records must also target one identical candidate HEAD/TREE/contract.
    No 7/7 score is produced because the parent is a theorem over the child set.
    """

    records = tuple(records)
    by_id: dict[str, QualificationRecord] = {}
    duplicate = False
    for record in records:
        if not isinstance(record, QualificationRecord):
            raise ContractError("qualification report requires QualificationRecord values")
        if record.invariant_id in by_id:
            duplicate = True
        by_id[record.invariant_id] = record

    missing = sorted(set(AUTH_CHILDREN) - set(by_id))
    extra = sorted(set(by_id) - set(AUTH_CHILDREN))
    targets = {
        (r.candidate_head, r.candidate_tree, r.contract_id)
        for r in records
    }
    common_target = next(iter(targets)) if len(targets) == 1 else None
    all_pass = (
        not duplicate
        and not missing
        and not extra
        and len(records) == len(AUTH_CHILDREN)
        and common_target is not None
        and all(by_id[i].result == "PASS" for i in AUTH_CHILDREN)
    )

    return {
        "schema_version": "residual.auth.qualification-report.v1",
        "child_result": f"{sum(1 for i in AUTH_CHILDREN if by_id.get(i) and by_id[i].result == 'PASS')}/{len(AUTH_CHILDREN)}",
        "parent_invariant": PARENT_INVARIANT,
        "parent_result": "PASS" if all_pass else "FAIL",
        "candidate_head": common_target[0] if common_target else None,
        "candidate_tree": common_target[1] if common_target else None,
        "contract_id": common_target[2] if common_target else None,
        "missing_invariants": missing,
        "duplicate_invariant": duplicate,
        "child_results": {
            invariant_id: by_id[invariant_id].result if invariant_id in by_id else "MISSING"
            for invariant_id in AUTH_CHILDREN
        },
    }
