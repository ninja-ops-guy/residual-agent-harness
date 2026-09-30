"""Client boundary for OpenShell.

R0 intentionally defines a protocol and test fixture rather than embedding a
CLI parser or assuming an unstable upstream SDK surface. A live implementation
must translate the RESIDUAL policy IR to an exact qualified OpenShell release.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from ..core import ContractError
from .openshell_contracts import OpenShellExecutionRequest
from .openshell_policy import CompiledOpenShellPolicy


@dataclass(frozen=True)
class OpenShellSandboxState:
    sandbox_id: str
    generation: str
    openshell_identity: str
    nemoclaw_identity: str | None
    compute_driver: str
    platform_class: str
    agent_identity: str
    image_digest: str
    residual_policy_digest: str
    base_policy_digest: str | None
    effective_policy_digest: str | None
    policy_revision: str | None
    provider_attachment_refs: tuple[str, ...] = ()
    inference_route_ref: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "sandbox_id", "generation", "openshell_identity", "compute_driver",
            "platform_class", "agent_identity", "image_digest",
            "residual_policy_digest",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{name} is required")


@dataclass(frozen=True)
class OpenShellRunResult:
    candidate: Any
    normalized_outcome: str
    vendor_outcome: str
    exit_code: int | None
    stdout: bytes = b""
    stderr: bytes = b""
    artifacts: Mapping[str, bytes] | None = None
    lifecycle_events: tuple[Mapping[str, Any], ...] = ()
    security_observations: tuple[Mapping[str, Any], ...] = ()
    first_failure: Mapping[str, Any] | None = None
    started_at: str = "UNSPECIFIED"
    ended_at: str = "UNSPECIFIED"

    def __post_init__(self) -> None:
        if self.normalized_outcome not in {
            "SUCCEEDED", "FAILED", "TIMED_OUT", "POLICY_DENIED",
            "PROVIDER_FAILED", "SANDBOX_LOST", "ADAPTER_FAILED", "UNKNOWN",
        }:
            raise ContractError("invalid OpenShell normalized outcome")
        if not isinstance(self.vendor_outcome, str) or not self.vendor_outcome.strip():
            raise ContractError("vendor_outcome is required")
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise ContractError("exit_code must be an integer or None")
        if not isinstance(self.stdout, bytes) or not isinstance(self.stderr, bytes):
            raise ContractError("stdout and stderr must be bytes")
        if self.artifacts is not None:
            for path, data in self.artifacts.items():
                if not isinstance(path, str) or not path.strip() or not isinstance(data, bytes):
                    raise ContractError("artifacts must map non-empty paths to bytes")
        for name in ("started_at", "ended_at"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{name} is required")


@runtime_checkable
class OpenShellClient(Protocol):
    """Machine-readable OpenShell client boundary.

    No method here grants RESIDUAL authority. The adapter independently checks
    requested/effective policy binding and normalizes evidence.
    """

    def health(self) -> bool: ...

    def create_sandbox(
        self,
        request: OpenShellExecutionRequest,
        policy: CompiledOpenShellPolicy,
    ) -> OpenShellSandboxState: ...

    def inspect_sandbox(self, sandbox_id: str) -> OpenShellSandboxState: ...

    def run(
        self,
        sandbox_id: str,
        request: OpenShellExecutionRequest,
    ) -> OpenShellRunResult: ...

    def destroy_sandbox(self, sandbox_id: str) -> None: ...
