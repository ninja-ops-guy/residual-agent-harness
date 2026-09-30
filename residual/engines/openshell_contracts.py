"""Immutable contracts for the RESIDUAL OpenShell R0 adapter.

These contracts are vendor-neutral on purpose. They bind RESIDUAL authority,
requested execution state, observable OpenShell state, and artifact identity
without pretending that a vendor success response is a RESIDUAL verdict.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..core import ContractError, canonical, digest

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_EXACT = {
    "api_key", "apikey", "secret", "password", "passwd", "private_key",
    "access_key", "credential", "credentials", "token", "access_token",
    "refresh_token", "bearer_token",
}
_SECRET_SUFFIXES = (
    "_api_key", "_secret", "_password", "_passwd", "_private_key",
    "_access_key", "_credential", "_credentials", "_access_token",
    "_refresh_token", "_bearer_token",
)
_REFERENCE_SUFFIXES = (
    "_ref", "_refs", "_id", "_ids", "_name", "_names",
    "_digest", "_digests", "_hash", "_hashes",
)


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")
    return value


def _hex_digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ContractError(f"{name} must be a lowercase sha256 digest")
    return value


def _string_tuple(values: Sequence[str], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ContractError(f"{name} must be a sequence")
    result = tuple(values)
    if not allow_empty and not result:
        raise ContractError(f"{name} must not be empty")
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ContractError(f"{name} entries must be non-empty strings")
    if len(result) != len(set(result)):
        raise ContractError(f"{name} contains duplicates")
    return result


def assert_no_inline_secrets(value: Any, *, path: str = "root") -> None:
    """Reject obvious inline-secret fields before request construction.

    This is deliberately structural rather than heuristic scanning of arbitrary
    string values. Identifiers such as provider_ref or credential_id remain
    allowed, while api_key/token/password style fields fail closed.
    """
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            lower = key.lower()
            normalized = lower.replace("-", "_")
            suspicious = normalized in _SECRET_EXACT or normalized.endswith(_SECRET_SUFFIXES)
            if suspicious and not normalized.endswith(_REFERENCE_SUFFIXES):
                raise ContractError(f"inline secret field is not allowed at {path}.{key}")
            assert_no_inline_secrets(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_no_inline_secrets(child, path=f"{path}[{index}]")


@dataclass(frozen=True)
class OpenShellLaunchConfig:
    """Exact launch inputs supplied by RESIDUAL authority."""

    mission_id: str
    attempt_id: str
    authority_ref: str
    agent_profile: str
    agent_command_argv: tuple[str, ...]
    image_ref: str
    image_digest: str
    compute_driver_requirement: str
    sandbox_profile: str
    provider_refs: tuple[str, ...] = ()
    provider_profile_digests: Mapping[str, str] = field(default_factory=dict)
    inference_route_ref: str | None = None
    resource_budget: Mapping[str, int] = field(default_factory=dict)
    timeout_s: int = 300
    expected_outputs: tuple[str, ...] = ()
    output_contract_digest: str = field(default_factory=lambda: digest({"outputs": []}))
    correlation_ids: Mapping[str, str] = field(default_factory=dict)
    created_at: str = "UNSPECIFIED"

    def __post_init__(self) -> None:
        for name in (
            "mission_id", "attempt_id", "authority_ref", "agent_profile",
            "image_ref", "compute_driver_requirement", "sandbox_profile",
            "created_at",
        ):
            _required_text(getattr(self, name), name)
        _hex_digest(self.image_digest, "image_digest")
        _hex_digest(self.output_contract_digest, "output_contract_digest")
        _string_tuple(self.agent_command_argv, "agent_command_argv", allow_empty=False)
        _string_tuple(self.provider_refs, "provider_refs")
        if not isinstance(self.provider_profile_digests, Mapping):
            raise ContractError("provider_profile_digests must be a mapping")
        for provider_id, profile_digest in self.provider_profile_digests.items():
            _required_text(provider_id, "provider_profile_digests key")
            _hex_digest(profile_digest, "provider_profile_digest")
        if self.provider_profile_digests and set(self.provider_profile_digests) != set(self.provider_refs):
            raise ContractError("provider_profile_digests keys must match provider_refs")
        _string_tuple(self.expected_outputs, "expected_outputs")
        if self.inference_route_ref is not None:
            _required_text(self.inference_route_ref, "inference_route_ref")
        if type(self.timeout_s) is not int or self.timeout_s <= 0:
            raise ContractError("timeout_s must be a positive integer")
        if not isinstance(self.resource_budget, Mapping):
            raise ContractError("resource_budget must be a mapping")
        for key, value in self.resource_budget.items():
            _required_text(key, "resource_budget key")
            if type(value) is not int or value <= 0:
                raise ContractError("resource_budget values must be positive integers")
        if not isinstance(self.correlation_ids, Mapping):
            raise ContractError("correlation_ids must be a mapping")
        for key, value in self.correlation_ids.items():
            _required_text(key, "correlation_ids key")
            _required_text(value, "correlation_ids value")
        assert_no_inline_secrets(self.payload())

    def payload(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "attempt_id": self.attempt_id,
            "authority_ref": self.authority_ref,
            "agent_profile": self.agent_profile,
            "agent_command_argv": list(self.agent_command_argv),
            "image_ref": self.image_ref,
            "image_digest": self.image_digest,
            "compute_driver_requirement": self.compute_driver_requirement,
            "sandbox_profile": self.sandbox_profile,
            "provider_refs": list(self.provider_refs),
            "provider_profile_digests": {
                key: self.provider_profile_digests[key]
                for key in sorted(self.provider_profile_digests)
            },
            "inference_route_ref": self.inference_route_ref,
            "resource_budget": dict(self.resource_budget),
            "timeout_s": self.timeout_s,
            "expected_outputs": list(self.expected_outputs),
            "output_contract_digest": self.output_contract_digest,
            "correlation_ids": dict(self.correlation_ids),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class OpenShellExecutionRequest:
    schema_version: str
    request_id: str
    mission_id: str
    task_id: str
    attempt_id: str
    task_spec_digest: str
    context_digest: str
    authority_ref: str
    engine_name: str
    engine_version: str
    agent_profile: str
    agent_command_argv: tuple[str, ...]
    image_ref: str
    image_digest: str
    compute_driver_requirement: str
    sandbox_profile: str
    requested_policy_digest: str
    provider_refs: tuple[str, ...]
    provider_profile_digests: Mapping[str, str]
    inference_route_ref: str | None
    resource_budget: Mapping[str, int]
    timeout_s: int
    expected_outputs: tuple[str, ...]
    output_contract_digest: str
    correlation_ids: Mapping[str, str]
    created_at: str

    def __post_init__(self) -> None:
        if self.schema_version != "residual.openshell-request.v1":
            raise ContractError("unsupported OpenShell request schema")
        for name in (
            "request_id", "mission_id", "task_id", "attempt_id", "authority_ref",
            "engine_name", "engine_version", "agent_profile", "image_ref",
            "compute_driver_requirement", "sandbox_profile", "created_at",
        ):
            _required_text(getattr(self, name), name)
        for name in (
            "task_spec_digest", "context_digest", "image_digest",
            "requested_policy_digest", "output_contract_digest",
        ):
            _hex_digest(getattr(self, name), name)
        _string_tuple(self.agent_command_argv, "agent_command_argv", allow_empty=False)
        _string_tuple(self.provider_refs, "provider_refs")
        if not isinstance(self.provider_profile_digests, Mapping):
            raise ContractError("provider_profile_digests must be a mapping")
        for provider_id, profile_digest in self.provider_profile_digests.items():
            _required_text(provider_id, "provider_profile_digests key")
            _hex_digest(profile_digest, "provider_profile_digest")
        if self.provider_profile_digests and set(self.provider_profile_digests) != set(self.provider_refs):
            raise ContractError("provider_profile_digests keys must match provider_refs")
        _string_tuple(self.expected_outputs, "expected_outputs")
        if self.inference_route_ref is not None:
            _required_text(self.inference_route_ref, "inference_route_ref")
        if type(self.timeout_s) is not int or self.timeout_s <= 0:
            raise ContractError("timeout_s must be a positive integer")
        canonical(dict(self.resource_budget))
        canonical(dict(self.correlation_ids))
        assert_no_inline_secrets(self.payload())

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "task_spec_digest": self.task_spec_digest,
            "context_digest": self.context_digest,
            "authority_ref": self.authority_ref,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "agent_profile": self.agent_profile,
            "agent_command_argv": list(self.agent_command_argv),
            "image_ref": self.image_ref,
            "image_digest": self.image_digest,
            "compute_driver_requirement": self.compute_driver_requirement,
            "sandbox_profile": self.sandbox_profile,
            "requested_policy_digest": self.requested_policy_digest,
            "provider_refs": list(self.provider_refs),
            "provider_profile_digests": {
                key: self.provider_profile_digests[key]
                for key in sorted(self.provider_profile_digests)
            },
            "inference_route_ref": self.inference_route_ref,
            "resource_budget": dict(self.resource_budget),
            "timeout_s": self.timeout_s,
            "expected_outputs": list(self.expected_outputs),
            "output_contract_digest": self.output_contract_digest,
            "correlation_ids": dict(self.correlation_ids),
            "created_at": self.created_at,
        }

    @property
    def request_digest(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class OpenShellArtifact:
    artifact_id: str
    path: str
    byte_length: int
    sha256: str
    media_type: str
    producing_request_digest: str

    def __post_init__(self) -> None:
        for name in ("artifact_id", "path", "media_type"):
            _required_text(getattr(self, name), name)
        if type(self.byte_length) is not int or self.byte_length < 0:
            raise ContractError("byte_length must be a nonnegative integer")
        _hex_digest(self.sha256, "sha256")
        _hex_digest(self.producing_request_digest, "producing_request_digest")

    @classmethod
    def from_bytes(
        cls,
        artifact_id: str,
        path: str,
        data: bytes,
        *,
        producing_request_digest: str,
        media_type: str = "application/octet-stream",
    ) -> "OpenShellArtifact":
        if not isinstance(data, bytes):
            raise ContractError("artifact data must be bytes")
        return cls(
            artifact_id=artifact_id,
            path=path,
            byte_length=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            media_type=media_type,
            producing_request_digest=producing_request_digest,
        )

    def payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "byte_length": self.byte_length,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "producing_request_digest": self.producing_request_digest,
        }


@dataclass(frozen=True)
class OpenShellExecutionEvidence:
    schema_version: str
    request_digest: str
    residual_source_identity: str
    openshell_identity: str
    nemoclaw_identity: str | None
    sandbox_id: str
    sandbox_generation: str
    compute_driver: str
    platform_class: str
    image_digest: str
    agent_identity: str
    requested_policy_digest: str
    base_policy_digest: str | None
    effective_policy_digest: str | None
    policy_revision: str | None
    provider_attachment_refs: tuple[str, ...]
    inference_route_ref: str | None
    started_at: str
    ended_at: str
    normalized_outcome: str
    vendor_outcome: str
    exit_code: int | None
    stdout_digest: str
    stderr_digest: str
    security_log_digest: str
    lifecycle_log_digest: str
    artifact_manifest_digest: str
    engine_result_digest: str
    first_failure: Mapping[str, Any] | None
    evidence_completeness: str

    def __post_init__(self) -> None:
        if self.schema_version != "residual.openshell-evidence.v1":
            raise ContractError("unsupported OpenShell evidence schema")
        for name in (
            "residual_source_identity", "openshell_identity", "sandbox_id",
            "sandbox_generation", "compute_driver", "platform_class",
            "agent_identity", "started_at", "ended_at", "normalized_outcome",
            "vendor_outcome",
        ):
            _required_text(getattr(self, name), name)
        for name in (
            "request_digest", "image_digest", "requested_policy_digest",
            "stdout_digest", "stderr_digest", "security_log_digest",
            "lifecycle_log_digest", "artifact_manifest_digest",
            "engine_result_digest",
        ):
            _hex_digest(getattr(self, name), name)
        if self.base_policy_digest is not None:
            _hex_digest(self.base_policy_digest, "base_policy_digest")
        if self.effective_policy_digest is not None:
            _hex_digest(self.effective_policy_digest, "effective_policy_digest")
        if self.nemoclaw_identity is not None:
            _required_text(self.nemoclaw_identity, "nemoclaw_identity")
        if self.policy_revision is not None:
            _required_text(self.policy_revision, "policy_revision")
        if self.inference_route_ref is not None:
            _required_text(self.inference_route_ref, "inference_route_ref")
        _string_tuple(self.provider_attachment_refs, "provider_attachment_refs")
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise ContractError("exit_code must be an integer or None")
        if self.evidence_completeness not in {"complete", "partial", "unknown"}:
            raise ContractError("invalid evidence_completeness")
        if self.first_failure is not None:
            canonical(dict(self.first_failure))
        assert_no_inline_secrets(self.payload())

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_digest": self.request_digest,
            "residual_source_identity": self.residual_source_identity,
            "openshell_identity": self.openshell_identity,
            "nemoclaw_identity": self.nemoclaw_identity,
            "sandbox_id": self.sandbox_id,
            "sandbox_generation": self.sandbox_generation,
            "compute_driver": self.compute_driver,
            "platform_class": self.platform_class,
            "image_digest": self.image_digest,
            "agent_identity": self.agent_identity,
            "requested_policy_digest": self.requested_policy_digest,
            "base_policy_digest": self.base_policy_digest,
            "effective_policy_digest": self.effective_policy_digest,
            "policy_revision": self.policy_revision,
            "provider_attachment_refs": list(self.provider_attachment_refs),
            "inference_route_ref": self.inference_route_ref,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "normalized_outcome": self.normalized_outcome,
            "vendor_outcome": self.vendor_outcome,
            "exit_code": self.exit_code,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "security_log_digest": self.security_log_digest,
            "lifecycle_log_digest": self.lifecycle_log_digest,
            "artifact_manifest_digest": self.artifact_manifest_digest,
            "engine_result_digest": self.engine_result_digest,
            "first_failure": None if self.first_failure is None else dict(self.first_failure),
            "evidence_completeness": self.evidence_completeness,
        }

    @property
    def evidence_digest(self) -> str:
        return digest(self.payload())
