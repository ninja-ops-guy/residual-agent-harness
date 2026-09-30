"""RESIDUAL OpenShell execution adapter R0.

This module implements the pure control/evidence path against an injected
machine-readable client. It does not shell out to OpenShell and does not claim
live OpenShell qualification. A live client is a separate post-v1 lane.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Callable, ClassVar

from ..core import ContractError, digest
from ..substrates.protocol import SubstrateHealth, SubstrateRuntimeIdentity
from ..substrates.qualification import (
    SubstrateQualificationRegistry,
    SubstrateQualificationTuple,
    inference_route_digest,
    provider_set_digest,
)
from .openshell_client import OpenShellClient, OpenShellRunResult, OpenShellSandboxState
from .openshell_contracts import (
    OpenShellArtifact,
    OpenShellExecutionEvidence,
    OpenShellExecutionRequest,
    OpenShellLaunchConfig,
    assert_no_inline_secrets,
)
from .openshell_policy import CompiledOpenShellPolicy, OpenShellPolicyEnvelope, compile_policy
from .protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec


class OpenShellExecutionError(RuntimeError):
    """Execution failed or could not be proven safe enough to admit."""

    def __init__(
        self,
        outcome: str,
        reason: str,
        *,
        evidence: OpenShellExecutionEvidence | None = None,
    ) -> None:
        super().__init__(f"{outcome}: {reason}")
        self.outcome = outcome
        self.reason = reason
        self.evidence = evidence
        self.cleanup_error: str | None = None


LaunchFactory = Callable[[TaskSpec, ContextAssembly], OpenShellLaunchConfig]
PolicyFactory = Callable[[TaskSpec, ContextAssembly], OpenShellPolicyEnvelope]


def build_execution_request(
    task: TaskSpec,
    context: ContextAssembly,
    launch: OpenShellLaunchConfig,
    policy: CompiledOpenShellPolicy,
    *,
    engine_name: str,
    engine_version: str,
) -> OpenShellExecutionRequest:
    if not isinstance(task, TaskSpec) or not isinstance(context, ContextAssembly):
        raise ContractError("OpenShell request requires TaskSpec and ContextAssembly")
    if not isinstance(launch, OpenShellLaunchConfig):
        raise ContractError("OpenShell request requires OpenShellLaunchConfig")
    if not isinstance(policy, CompiledOpenShellPolicy):
        raise ContractError("OpenShell request requires a compiled policy")

    task_payload = {
        "task_id": task.task_id,
        "capability": task.capability,
        "input": task.input,
        "metadata": dict(task.metadata),
    }
    context_payload = {"values": dict(context.values)}
    assert_no_inline_secrets(task_payload, path="task")
    assert_no_inline_secrets(context_payload, path="context")

    if tuple(sorted(launch.provider_refs)) != tuple(sorted(policy.providers)):
        raise ContractError("launch provider_refs must match compiled policy providers")
    if dict(launch.resource_budget) != dict(policy.resources):
        raise ContractError("launch resource_budget must match compiled policy resources")
    if launch.inference_route_ref != policy.inference_route_ref:
        raise ContractError("launch inference_route_ref must match compiled policy")

    request_seed = {
        "task_spec_digest": digest(task_payload),
        "context_digest": digest(context_payload),
        "engine_name": engine_name,
        "engine_version": engine_version,
        "launch": launch.payload(),
        "requested_policy_digest": policy.policy_digest,
    }
    request_id = "osr-" + digest(request_seed)[:32]

    return OpenShellExecutionRequest(
        schema_version="residual.openshell-request.v1",
        request_id=request_id,
        mission_id=launch.mission_id,
        task_id=task.task_id,
        attempt_id=launch.attempt_id,
        task_spec_digest=request_seed["task_spec_digest"],
        context_digest=request_seed["context_digest"],
        authority_ref=launch.authority_ref,
        engine_name=engine_name,
        engine_version=engine_version,
        agent_profile=launch.agent_profile,
        agent_command_argv=launch.agent_command_argv,
        image_ref=launch.image_ref,
        image_digest=launch.image_digest,
        compute_driver_requirement=launch.compute_driver_requirement,
        sandbox_profile=launch.sandbox_profile,
        requested_policy_digest=policy.policy_digest,
        provider_refs=launch.provider_refs,
        provider_profile_digests=dict(launch.provider_profile_digests),
        inference_route_ref=launch.inference_route_ref,
        resource_budget=dict(launch.resource_budget),
        timeout_s=launch.timeout_s,
        expected_outputs=launch.expected_outputs,
        output_contract_digest=launch.output_contract_digest,
        correlation_ids=dict(launch.correlation_ids),
        created_at=launch.created_at,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest(
    raw: OpenShellRunResult,
    request: OpenShellExecutionRequest,
) -> tuple[OpenShellArtifact, ...]:
    artifacts = raw.artifacts or {}
    actual = set(artifacts)
    expected = set(request.expected_outputs)
    undeclared = sorted(actual - expected)
    missing = sorted(expected - actual)
    if undeclared or missing:
        details = []
        if undeclared:
            details.append("undeclared=" + ",".join(undeclared))
        if missing:
            details.append("missing=" + ",".join(missing))
        raise OpenShellExecutionError(
            "UNKNOWN",
            "artifact set does not match frozen output contract: " + ";".join(details),
        )
    rows = []
    for index, path in enumerate(sorted(artifacts), 1):
        rows.append(OpenShellArtifact.from_bytes(
            f"artifact-{index:04d}",
            path,
            artifacts[path],
            producing_request_digest=request.request_digest,
        ))
    return tuple(rows)


def _validate_bound_state(
    state: OpenShellSandboxState,
    request: OpenShellExecutionRequest,
    policy: CompiledOpenShellPolicy,
    *,
    expected_openshell_identity: str,
    expected_nemoclaw_identity: str | None,
    expected_agent_identity: str,
    expected_environment_digest: str | None,
) -> None:
    mismatches: list[str] = []
    if state.residual_policy_digest != policy.policy_digest:
        mismatches.append("residual_policy_digest")
    if state.effective_policy_digest is None:
        mismatches.append("effective_policy_digest_unavailable")
    if state.image_digest != request.image_digest:
        mismatches.append("image_digest")
    if state.compute_driver != request.compute_driver_requirement:
        mismatches.append("compute_driver")
    if state.openshell_identity != expected_openshell_identity:
        mismatches.append("openshell_identity")
    if state.nemoclaw_identity != expected_nemoclaw_identity:
        mismatches.append("nemoclaw_identity")
    if state.agent_identity != expected_agent_identity:
        mismatches.append("agent_identity")
    if expected_environment_digest is not None and state.environment_digest != expected_environment_digest:
        mismatches.append("environment_digest")
    if tuple(sorted(state.provider_attachment_refs)) != tuple(sorted(request.provider_refs)):
        mismatches.append("provider_attachment_refs")
    if state.inference_route_ref != request.inference_route_ref:
        mismatches.append("inference_route_ref")
    if mismatches:
        raise OpenShellExecutionError(
            "UNKNOWN",
            "sandbox state does not match frozen request: " + ",".join(mismatches),
        )


@dataclass
class OpenShellExecutionEngine:
    """ExecutionEngine implementation backed by an injected OpenShell client."""

    client: OpenShellClient
    launch_factory: LaunchFactory
    policy_factory: PolicyFactory
    residual_source_identity: str
    expected_openshell_identity: str
    expected_agent_identity: str
    expected_nemoclaw_identity: str | None = None
    version: str = "r0"
    qualified_capabilities: tuple[str, ...] = ("sandboxed_execution",)
    qualification_registry: SubstrateQualificationRegistry | None = None
    qualification_tuple: SubstrateQualificationTuple | None = None
    qualification_record_digest: str | None = None
    openshell_version: str | None = None
    expected_driver: str | None = None
    expected_platform_class: str | None = None
    expected_environment_digest: str | None = None

    name: ClassVar[str] = "openshell"
    capability_class: ClassVar[str] = "sandbox_execution"
    locality: ClassVar[str] = "local"

    def __post_init__(self) -> None:
        for name in (
            "residual_source_identity",
            "expected_openshell_identity",
            "expected_agent_identity",
            "version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"{name} is required")
        if self.expected_nemoclaw_identity is not None and (
            not isinstance(self.expected_nemoclaw_identity, str)
            or not self.expected_nemoclaw_identity.strip()
        ):
            raise ContractError("expected_nemoclaw_identity must be non-empty")
        if len(self.qualified_capabilities) != len(set(self.qualified_capabilities)):
            raise ContractError("qualified_capabilities contains duplicates")
        qualification_fields = (
            self.qualification_registry,
            self.qualification_tuple,
            self.qualification_record_digest,
        )
        if any(value is not None for value in qualification_fields) and not all(
            value is not None for value in qualification_fields
        ):
            raise ContractError(
                "qualification_registry, qualification_tuple, and "
                "qualification_record_digest must be supplied together"
            )
        if self.qualification_tuple is not None:
            if self.openshell_version is None:
                self.openshell_version = self.qualification_tuple.substrate_version
            if self.expected_driver is None:
                self.expected_driver = self.qualification_tuple.driver
            if self.expected_platform_class is None:
                self.expected_platform_class = self.qualification_tuple.platform_class
            if self.expected_environment_digest is None:
                self.expected_environment_digest = self.qualification_tuple.environment_digest
            if self.qualification_tuple.substrate_name != self.name:
                raise ContractError("qualification tuple substrate_name mismatch")
            if self.qualification_tuple.substrate_source_identity != self.expected_openshell_identity:
                raise ContractError("qualification tuple OpenShell identity mismatch")

    def supports(self, capability: str) -> bool:
        if (
            self.qualification_registry is not None
            and self.qualification_tuple is not None
            and self.qualification_record_digest is not None
        ):
            return capability in self.qualification_registry.qualified_capabilities(
                self.qualification_tuple,
                record_digest=self.qualification_record_digest,
            )
        # Explicit capabilities remain only as a fixture/backward-compatible path.
        return capability in self.qualified_capabilities

    def health(self) -> EngineHealth:
        try:
            return EngineHealth.HEALTHY if self.client.health() else EngineHealth.UNAVAILABLE
        except Exception:
            return EngineHealth.UNAVAILABLE

    def substrate_identity(self) -> SubstrateRuntimeIdentity:
        if not self.openshell_version or not self.expected_driver or not self.expected_platform_class:
            raise ContractError(
                "substrate identity requires openshell_version, expected_driver, "
                "and expected_platform_class"
            )
        return SubstrateRuntimeIdentity(
            name=self.name,
            version=self.openshell_version,
            source_identity=self.expected_openshell_identity,
            driver=self.expected_driver,
            platform_class=self.expected_platform_class,
            environment_digest=(
                self.expected_environment_digest
                if self.expected_environment_digest is not None
                else digest({"environment": "unqualified"})
            ),
            locality=self.locality,
        )

    def substrate_health(self) -> SubstrateHealth:
        health = self.health()
        if health == EngineHealth.HEALTHY:
            return SubstrateHealth.HEALTHY
        if health == EngineHealth.DEGRADED:
            return SubstrateHealth.DEGRADED
        return SubstrateHealth.UNAVAILABLE

    def _require_exact_qualification(
        self,
        task: TaskSpec,
        request: OpenShellExecutionRequest,
    ) -> str | None:
        if (
            self.qualification_registry is None
            or self.qualification_tuple is None
            or self.qualification_record_digest is None
        ):
            if not self.supports(task.capability):
                raise OpenShellExecutionError(
                    "ADAPTER_FAILED",
                    f"capability is not enabled for fixture adapter: {task.capability}",
                )
            return None

        expected = self.qualification_tuple
        mismatches: list[str] = []
        if expected.substrate_name != self.name:
            mismatches.append("substrate_name")
        if expected.substrate_source_identity != self.expected_openshell_identity:
            mismatches.append("substrate_source_identity")
        if self.openshell_version is None or expected.substrate_version != self.openshell_version:
            mismatches.append("substrate_version")
        if expected.driver != request.compute_driver_requirement:
            mismatches.append("driver")
        if self.expected_platform_class is None or expected.platform_class != self.expected_platform_class:
            mismatches.append("platform_class")
        if self.expected_environment_digest is None or expected.environment_digest != self.expected_environment_digest:
            mismatches.append("environment_digest")
        if expected.agent_profile != request.agent_profile:
            mismatches.append("agent_profile")
        if expected.agent_identity != self.expected_agent_identity:
            mismatches.append("agent_identity")
        if expected.image_digest != request.image_digest:
            mismatches.append("image_digest")
        if expected.requested_policy_digest != request.requested_policy_digest:
            mismatches.append("requested_policy_digest")
        if request.provider_refs and set(request.provider_profile_digests) != set(request.provider_refs):
            mismatches.append("provider_profile_digests_incomplete")
        elif expected.provider_set_digest != provider_set_digest(request.provider_profile_digests):
            mismatches.append("provider_set_digest")
        if expected.inference_route_digest != inference_route_digest(request.inference_route_ref):
            mismatches.append("inference_route_digest")
        if mismatches:
            raise OpenShellExecutionError(
                "ADAPTER_FAILED",
                "execution request differs from qualified tuple: " + ",".join(mismatches),
            )

        try:
            record = self.qualification_registry.require(
                expected,
                task.capability,
                record_digest=self.qualification_record_digest,
            )
        except ContractError as exc:
            raise OpenShellExecutionError(
                "ADAPTER_FAILED",
                f"exact substrate qualification rejected dispatch: {exc}",
            ) from exc
        return record.record_digest

    def normalize(self, raw_output: Any) -> EngineResult:
        if not isinstance(raw_output, OpenShellRunResult):
            raise ContractError("OpenShell adapter can only normalize OpenShellRunResult")
        return EngineResult(
            candidate=raw_output.candidate,
            raw_metadata={
                "adapter": self.name,
                "normalized_outcome": raw_output.normalized_outcome,
                "vendor_outcome": raw_output.vendor_outcome,
            },
        )

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        if not self.client.health():
            raise OpenShellExecutionError("ADAPTER_FAILED", "OpenShell client is unavailable")

        launch = self.launch_factory(task, context)
        envelope = self.policy_factory(task, context)
        policy = compile_policy(envelope)
        request = build_execution_request(
            task,
            context,
            launch,
            policy,
            engine_name=self.name,
            engine_version=self.version,
        )
        qualification_record_digest = self._require_exact_qualification(task, request)

        state: OpenShellSandboxState | None = None
        evidence: OpenShellExecutionEvidence | None = None
        pending_error: OpenShellExecutionError | None = None
        result: EngineResult | None = None

        try:
            state = self.client.create_sandbox(request, policy)
            inspected = self.client.inspect_sandbox(state.sandbox_id)
            if inspected.sandbox_id != state.sandbox_id:
                raise OpenShellExecutionError(
                    "UNKNOWN",
                    "sandbox inspection identity differs from created sandbox",
                )
            _validate_bound_state(
                inspected,
                request,
                policy,
                expected_openshell_identity=self.expected_openshell_identity,
                expected_nemoclaw_identity=self.expected_nemoclaw_identity,
                expected_agent_identity=self.expected_agent_identity,
                expected_environment_digest=self.expected_environment_digest,
            )
            run_started = time.monotonic()
            raw = self.client.run(inspected.sandbox_id, request)
            run_wall_clock_ms = int((time.monotonic() - run_started) * 1000)

            manifest = _manifest(raw, request)
            manifest_payload = [item.payload() for item in manifest]
            first_failure = raw.first_failure
            if raw.normalized_outcome != "SUCCEEDED" and first_failure is None:
                first_failure = {"class": raw.normalized_outcome}
            if raw.normalized_outcome == "SUCCEEDED" and raw.first_failure is not None:
                raise OpenShellExecutionError(
                    "UNKNOWN",
                    "successful attempt contains first-failure evidence; hidden retry is not admissible",
                )
            if raw.normalized_outcome == "SUCCEEDED" and raw.exit_code not in (0, None):
                raise OpenShellExecutionError(
                    "UNKNOWN",
                    "successful outcome carries a non-zero exit code",
                )

            engine_result_digest = digest({
                "candidate": raw.candidate,
                "normalized_outcome": raw.normalized_outcome,
                "vendor_outcome": raw.vendor_outcome,
                "exit_code": raw.exit_code,
                "artifacts": manifest_payload,
            })
            evidence = OpenShellExecutionEvidence(
                schema_version="residual.openshell-evidence.v1",
                request_digest=request.request_digest,
                residual_source_identity=self.residual_source_identity,
                openshell_identity=inspected.openshell_identity,
                nemoclaw_identity=inspected.nemoclaw_identity,
                sandbox_id=inspected.sandbox_id,
                sandbox_generation=inspected.generation,
                compute_driver=inspected.compute_driver,
                platform_class=inspected.platform_class,
                environment_digest=inspected.environment_digest,
                image_digest=inspected.image_digest,
                agent_identity=inspected.agent_identity,
                requested_policy_digest=policy.policy_digest,
                base_policy_digest=inspected.base_policy_digest,
                effective_policy_digest=inspected.effective_policy_digest,
                policy_revision=inspected.policy_revision,
                provider_attachment_refs=inspected.provider_attachment_refs,
                inference_route_ref=inspected.inference_route_ref,
                started_at=raw.started_at,
                ended_at=raw.ended_at,
                normalized_outcome=raw.normalized_outcome,
                vendor_outcome=raw.vendor_outcome,
                exit_code=raw.exit_code,
                stdout_digest=_sha256_bytes(raw.stdout),
                stderr_digest=_sha256_bytes(raw.stderr),
                security_log_digest=digest([dict(row) for row in raw.security_observations]),
                lifecycle_log_digest=digest([dict(row) for row in raw.lifecycle_events]),
                artifact_manifest_digest=digest(manifest_payload),
                engine_result_digest=engine_result_digest,
                first_failure=first_failure,
                evidence_completeness="complete",
            )

            if raw.normalized_outcome != "SUCCEEDED":
                pending_error = OpenShellExecutionError(
                    raw.normalized_outcome,
                    "OpenShell execution did not succeed",
                    evidence=evidence,
                )
            else:
                result = EngineResult(
                    candidate=raw.candidate,
                    wall_clock_ms=run_wall_clock_ms,
                    engine_trace=tuple(dict(row) for row in raw.lifecycle_events),
                    raw_metadata={
                        "adapter": self.name,
                        "request_digest": request.request_digest,
                        "policy_digest": policy.policy_digest,
                        "openshell_evidence_digest": evidence.evidence_digest,
                        "openshell_evidence": evidence.payload(),
                        "artifact_manifest": manifest_payload,
                        "normalized_outcome": raw.normalized_outcome,
                        "substrate_qualification_tuple_digest":
                            None if self.qualification_tuple is None
                            else self.qualification_tuple.tuple_digest,
                        "substrate_qualification_record_digest":
                            qualification_record_digest,
                        "residual_policy_authoritative": True,
                        "candidate_state": "unverified",
                        "merge_performed": False,
                        "station_receipt_issued": False,
                    },
                )
        except OpenShellExecutionError as exc:
            pending_error = exc
        except Exception as exc:
            pending_error = OpenShellExecutionError(
                "ADAPTER_FAILED",
                f"{type(exc).__name__}: {str(exc)[:400]}",
                evidence=evidence,
            )

        if state is not None:
            try:
                self.client.destroy_sandbox(state.sandbox_id)
            except Exception as exc:
                cleanup = f"{type(exc).__name__}: {str(exc)[:400]}"
                if pending_error is not None:
                    pending_error.cleanup_error = cleanup
                else:
                    pending_error = OpenShellExecutionError(
                        "UNKNOWN",
                        "sandbox destruction failed after execution",
                        evidence=evidence,
                    )
                    pending_error.cleanup_error = cleanup

        if pending_error is not None:
            raise pending_error
        if result is None:
            raise OpenShellExecutionError("UNKNOWN", "execution produced no result")
        return result
