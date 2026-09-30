"""Exact-release Python SDK binding for the OpenShell R0 adapter.

This module deliberately does not import OpenShell private protobuf modules and
does not construct authentication state. The caller supplies an already-created
public SandboxClient plus an exact-release binding that translates RESIDUAL's
policy IR into the upstream SandboxSpec and reconstructs the effective execution
state.

That keeps unstable vendor wire details outside RESIDUAL core while still using
the public SDK lifecycle/exec surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

from ..core import ContractError
from .openshell_client import OpenShellRunResult, OpenShellSandboxState
from .openshell_contracts import OpenShellExecutionRequest
from .openshell_policy import CompiledOpenShellPolicy


class OpenShellSDKBindingError(RuntimeError):
    """The upstream SDK cannot prove the exact release binding required by R0."""


class SandboxSpecFactory(Protocol):
    def __call__(
        self,
        request: OpenShellExecutionRequest,
        policy: CompiledOpenShellPolicy,
    ) -> Any: ...


class SandboxStateResolver(Protocol):
    def __call__(
        self,
        sdk_client: Any,
        sandbox_ref: Any,
        request: OpenShellExecutionRequest,
        policy: CompiledOpenShellPolicy,
    ) -> OpenShellSandboxState: ...


class ArtifactCollector(Protocol):
    def __call__(
        self,
        sdk_client: Any,
        sandbox_name: str,
        workspace: str,
        paths: Sequence[str],
    ) -> Mapping[str, bytes]: ...


class ObservationCollector(Protocol):
    def __call__(
        self,
        sdk_client: Any,
        sandbox_name: str,
        workspace: str,
    ) -> tuple[
        Sequence[Mapping[str, Any]],
        Sequence[Mapping[str, Any]],
    ]: ...


class CandidateParser(Protocol):
    def __call__(
        self,
        exec_result: Any,
        artifacts: Mapping[str, bytes],
    ) -> Any: ...


@dataclass(frozen=True)
class PythonSDKReleaseBinding:
    """Release-specific translation and evidence hooks.

    The binding is where exact OpenShell-version knowledge belongs. A binding
    must be independently reviewed/qualified for the version/source identity it
    names. RESIDUAL core never imports openshell._proto.
    """

    sdk_version: str
    openshell_source_identity: str
    spec_factory: SandboxSpecFactory
    state_resolver: SandboxStateResolver
    artifact_collector: ArtifactCollector
    observation_collector: ObservationCollector
    candidate_parser: CandidateParser

    def __post_init__(self) -> None:
        for name in ("sdk_version", "openshell_source_identity"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{name} is required")
        for name in (
            "spec_factory",
            "state_resolver",
            "artifact_collector",
            "observation_collector",
            "candidate_parser",
        ):
            if not callable(getattr(self, name)):
                raise ContractError(f"{name} must be callable")


@dataclass
class _SandboxBinding:
    name: str
    request: OpenShellExecutionRequest
    policy: CompiledOpenShellPolicy


class PythonSDKOpenShellClient:
    """OpenShellClient implementation over the public Python SDK surface.

    The supplied sdk_client is expected to provide the documented public
    methods health, create, wait_ready, get, exec, delete, and wait_deleted.

    Authentication is intentionally out of scope here. Construct the SDK client
    outside RESIDUAL and pass it in; secrets must not enter this object.
    """

    def __init__(
        self,
        sdk_client: Any,
        *,
        workspace: str,
        binding: PythonSDKReleaseBinding,
    ) -> None:
        if sdk_client is None:
            raise ContractError("sdk_client is required")
        if not isinstance(workspace, str) or not workspace.strip():
            raise ContractError("workspace is required")
        if not isinstance(binding, PythonSDKReleaseBinding):
            raise ContractError("PythonSDKReleaseBinding is required")
        self._sdk = sdk_client
        self._workspace = workspace
        self._binding = binding
        self._sandboxes: dict[str, _SandboxBinding] = {}

    @property
    def binding(self) -> PythonSDKReleaseBinding:
        return self._binding

    def _health_version(self) -> str:
        response = self._sdk.health()
        version = getattr(response, "version", None)
        if not isinstance(version, str) or not version.strip():
            raise OpenShellSDKBindingError("OpenShell health response lacks version")
        return version

    def _require_exact_release(self) -> None:
        observed = self._health_version()
        if observed != self._binding.sdk_version:
            raise OpenShellSDKBindingError(
                "OpenShell SDK/gateway version mismatch: "
                f"expected {self._binding.sdk_version!r}, observed {observed!r}"
            )

    def health(self) -> bool:
        try:
            self._require_exact_release()
            return True
        except Exception:
            return False

    def _sandbox_name(self, request: OpenShellExecutionRequest) -> str:
        return "residual-" + request.request_digest[:24]

    def create_sandbox(
        self,
        request: OpenShellExecutionRequest,
        policy: CompiledOpenShellPolicy,
    ) -> OpenShellSandboxState:
        self._require_exact_release()
        spec = self._binding.spec_factory(request, policy)
        if spec is None:
            raise OpenShellSDKBindingError("release binding returned no SandboxSpec")

        name = self._sandbox_name(request)
        sandbox = self._sdk.create(
            workspace=self._workspace,
            spec=spec,
            name=name,
            labels={
                "residual_request_digest": request.request_digest,
                "residual_attempt_id": request.attempt_id,
            },
        )
        sandbox_id = getattr(sandbox, "id", None)
        sandbox_name = getattr(sandbox, "name", None)
        if not isinstance(sandbox_id, str) or not sandbox_id.strip():
            raise OpenShellSDKBindingError("OpenShell create returned empty sandbox id")
        if sandbox_name != name:
            raise OpenShellSDKBindingError("OpenShell create returned unexpected sandbox name")

        self._sdk.wait_ready(
            name,
            workspace=self._workspace,
            timeout_seconds=request.timeout_s,
        )
        refreshed = self._sdk.get(name, workspace=self._workspace)
        state = self._binding.state_resolver(
            self._sdk,
            refreshed,
            request,
            policy,
        )
        if state.sandbox_id != sandbox_id:
            raise OpenShellSDKBindingError(
                "release binding resolved a different sandbox identity after create"
            )
        if state.openshell_identity != self._binding.openshell_source_identity:
            raise OpenShellSDKBindingError(
                "release binding source identity differs from frozen OpenShell source"
            )

        self._sandboxes[sandbox_id] = _SandboxBinding(
            name=name,
            request=request,
            policy=policy,
        )
        return state

    def _bound(self, sandbox_id: str) -> _SandboxBinding:
        try:
            return self._sandboxes[sandbox_id]
        except KeyError as exc:
            raise OpenShellSDKBindingError("unknown or already-destroyed sandbox id") from exc

    def inspect_sandbox(self, sandbox_id: str) -> OpenShellSandboxState:
        self._require_exact_release()
        bound = self._bound(sandbox_id)
        ref = self._sdk.get(bound.name, workspace=self._workspace)
        state = self._binding.state_resolver(
            self._sdk,
            ref,
            bound.request,
            bound.policy,
        )
        if state.sandbox_id != sandbox_id:
            raise OpenShellSDKBindingError("sandbox identity changed during inspection")
        if state.openshell_identity != self._binding.openshell_source_identity:
            raise OpenShellSDKBindingError("OpenShell source identity drifted")
        return state

    def run(
        self,
        sandbox_id: str,
        request: OpenShellExecutionRequest,
    ) -> OpenShellRunResult:
        self._require_exact_release()
        bound = self._bound(sandbox_id)
        if bound.request.request_digest != request.request_digest:
            raise OpenShellSDKBindingError("run request differs from created sandbox request")

        started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        result = self._sdk.exec(
            bound.name,
            list(request.agent_command_argv),
            workspace=self._workspace,
            timeout_seconds=request.timeout_s,
            no_login_shell=True,
        )
        ended_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        exit_code = getattr(result, "exit_code", None)
        stdout = getattr(result, "stdout", None)
        stderr = getattr(result, "stderr", None)
        if type(exit_code) is not int:
            raise OpenShellSDKBindingError("OpenShell exec result lacks integer exit_code")
        if not isinstance(stdout, str) or not isinstance(stderr, str):
            raise OpenShellSDKBindingError("OpenShell exec result lacks text stdout/stderr")

        artifacts = dict(self._binding.artifact_collector(
            self._sdk,
            bound.name,
            self._workspace,
            request.expected_outputs,
        ))
        for path, data in artifacts.items():
            if not isinstance(path, str) or not isinstance(data, bytes):
                raise OpenShellSDKBindingError(
                    "artifact collector must return path-to-bytes mappings"
                )

        lifecycle, security = self._binding.observation_collector(
            self._sdk,
            bound.name,
            self._workspace,
        )
        lifecycle_rows = tuple(dict(row) for row in lifecycle)
        security_rows = tuple(dict(row) for row in security)
        candidate = self._binding.candidate_parser(result, artifacts)

        if exit_code == 0:
            outcome = "SUCCEEDED"
            first_failure = None
        else:
            outcome = "FAILED"
            first_failure = {
                "class": "UPSTREAM_EXEC_NONZERO",
                "exit_code": exit_code,
            }

        return OpenShellRunResult(
            candidate=candidate,
            normalized_outcome=outcome,
            vendor_outcome="completed" if exit_code == 0 else "nonzero_exit",
            exit_code=exit_code,
            stdout=stdout.encode("utf-8"),
            stderr=stderr.encode("utf-8"),
            artifacts=artifacts,
            lifecycle_events=lifecycle_rows,
            security_observations=security_rows,
            first_failure=first_failure,
            started_at=started_at,
            ended_at=ended_at,
        )

    def destroy_sandbox(self, sandbox_id: str) -> None:
        self._require_exact_release()
        bound = self._bound(sandbox_id)
        deletion = self._sdk.delete(
            bound.name,
            workspace=self._workspace,
            allow_missing=True,
        )
        expected_id = getattr(deletion, "sandbox_id", None)
        if not isinstance(expected_id, str) or not expected_id.strip():
            raise OpenShellSDKBindingError(
                "OpenShell delete response lacks sandbox identity"
            )
        if expected_id != sandbox_id:
            raise OpenShellSDKBindingError(
                "OpenShell delete response identifies a different sandbox"
            )
        self._sdk.wait_deleted(
            bound.name,
            workspace=self._workspace,
            expected_sandbox_id=expected_id,
        )
        del self._sandboxes[sandbox_id]
