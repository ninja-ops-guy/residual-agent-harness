"""Bounded "RESIDUAL builds RESIDUAL" admission contracts.

This module makes self-development a governed execution mode rather than a
special privilege.  The first lane can author, test, export and deterministically
integrate into a disposable candidate, but it can never mutate accepted state or
merge by itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core import ContractError, canonical, digest
from .admission import AdmittedQualificationRegistry
from .qualification import SubstrateQualificationTuple


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")
    return value


@dataclass(frozen=True)
class SelfBuildContract:
    mission_id: str
    authority_ref: str
    source_identity: str
    disposable_target_id: str
    allowed_write_paths: tuple[str, ...]
    test_commands: tuple[tuple[str, ...], ...]
    expected_artifacts: tuple[str, ...]
    required_substrate_capabilities: tuple[str, ...] = (
        "sandboxed_execution",
        "filesystem_policy",
        "artifact_manifest",
    )
    repository_write_authority: bool = False
    accepted_state_write_authority: bool = False
    merge_authority: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "residual.self-build-contract.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "residual.self-build-contract.v1":
            raise ContractError("unsupported self-build contract schema")
        for name in (
            "mission_id", "authority_ref", "source_identity", "disposable_target_id",
        ):
            _text(getattr(self, name), name)
        if not self.allowed_write_paths:
            raise ContractError("self-build contract requires allowed_write_paths")
        for path in self.allowed_write_paths:
            _text(path, "allowed_write_path")
            if path in {"/", ".", ".."}:
                raise ContractError("self-build write scope is too broad")
        if len(self.allowed_write_paths) != len(set(self.allowed_write_paths)):
            raise ContractError("duplicate self-build write path")
        if not self.test_commands:
            raise ContractError("self-build contract requires bounded tests")
        for command in self.test_commands:
            if not command or any(not isinstance(part, str) or not part for part in command):
                raise ContractError("test commands must be non-empty argv tuples")
        if not self.expected_artifacts:
            raise ContractError("self-build contract requires expected artifacts")
        if len(self.expected_artifacts) != len(set(self.expected_artifacts)):
            raise ContractError("duplicate expected artifact")
        if not self.required_substrate_capabilities:
            raise ContractError("self-build contract requires substrate capabilities")
        if any(
            not isinstance(capability, str) or not capability.strip()
            for capability in self.required_substrate_capabilities
        ):
            raise ContractError("invalid self-build substrate capability")
        if any((
            self.repository_write_authority,
            self.accepted_state_write_authority,
            self.merge_authority,
        )):
            raise ContractError(
                "R0 self-build cannot hold repository-write, accepted-state, or merge authority"
            )
        canonical(dict(self.metadata))

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "authority_ref": self.authority_ref,
            "source_identity": self.source_identity,
            "disposable_target_id": self.disposable_target_id,
            "allowed_write_paths": sorted(self.allowed_write_paths),
            "test_commands": [list(command) for command in self.test_commands],
            "expected_artifacts": sorted(self.expected_artifacts),
            "required_substrate_capabilities": sorted(
                set(self.required_substrate_capabilities)
            ),
            "repository_write_authority": self.repository_write_authority,
            "accepted_state_write_authority": self.accepted_state_write_authority,
            "merge_authority": self.merge_authority,
            "metadata": dict(self.metadata),
        }

    @property
    def contract_digest(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class SelfBuildAdmission:
    contract_digest: str
    qualification_tuple_digest: str
    qualification_record_digest: str
    qualified_capabilities: tuple[str, ...]
    verdict: str = "ADMITTED"
    schema_version: str = "residual.self-build-admission.v1"

    def __post_init__(self) -> None:
        if self.verdict != "ADMITTED":
            raise ContractError("self-build admission verdict must be ADMITTED")


def admit_self_build(
    contract: SelfBuildContract,
    qualification_tuple: SubstrateQualificationTuple,
    registry: AdmittedQualificationRegistry,
    *,
    record_digest: str,
) -> SelfBuildAdmission:
    if not isinstance(contract, SelfBuildContract):
        raise ContractError("self-build admission requires SelfBuildContract")
    record = registry.get(qualification_tuple, record_digest=record_digest)
    if record is None:
        raise ContractError("pinned substrate qualification record is unavailable")
    if record.overall != "PASS":
        raise ContractError(f"self-build substrate qualification is {record.overall}")
    missing = sorted(
        set(contract.required_substrate_capabilities) - record.qualified_capabilities
    )
    if missing:
        raise ContractError(
            "self-build substrate capabilities are not qualified: " + ",".join(missing)
        )
    return SelfBuildAdmission(
        contract_digest=contract.contract_digest,
        qualification_tuple_digest=qualification_tuple.tuple_digest,
        qualification_record_digest=record.record_digest,
        qualified_capabilities=tuple(sorted(record.qualified_capabilities)),
    )


@dataclass(frozen=True)
class SelfBuildCompletionEvidence:
    """Evidence proving bounded authoring reached integration but not accepted state."""

    contract_digest: str
    qualification_record_digest: str
    artifact_manifest_digest: str
    byte_verification_digest: str
    independent_verifier_digest: str
    deterministic_integration_receipt_digest: str
    disposable_target_id: str
    merge_performed: bool = False
    accepted_state_mutated: bool = False
    repository_write_by_agent: bool = False
    schema_version: str = "residual.self-build-completion.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "residual.self-build-completion.v1":
            raise ContractError("unsupported self-build completion schema")
        for name in (
            "contract_digest", "qualification_record_digest",
            "artifact_manifest_digest", "byte_verification_digest",
            "independent_verifier_digest", "deterministic_integration_receipt_digest",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ContractError(f"{name} must be a lowercase sha256 digest")
        _text(self.disposable_target_id, "disposable_target_id")
        if self.merge_performed or self.accepted_state_mutated or self.repository_write_by_agent:
            raise ContractError(
                "R0 self-build completion cannot include merge, accepted-state mutation, "
                "or agent repository write"
            )

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_digest": self.contract_digest,
            "qualification_record_digest": self.qualification_record_digest,
            "artifact_manifest_digest": self.artifact_manifest_digest,
            "byte_verification_digest": self.byte_verification_digest,
            "independent_verifier_digest": self.independent_verifier_digest,
            "deterministic_integration_receipt_digest":
                self.deterministic_integration_receipt_digest,
            "disposable_target_id": self.disposable_target_id,
            "merge_performed": self.merge_performed,
            "accepted_state_mutated": self.accepted_state_mutated,
            "repository_write_by_agent": self.repository_write_by_agent,
        }

    @property
    def receipt_digest(self) -> str:
        return digest(self.payload())

    @property
    def status(self) -> str:
        return "SELF_BUILD_BOUNDED_PASS"
