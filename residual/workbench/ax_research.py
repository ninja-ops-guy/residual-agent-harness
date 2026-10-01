"""Importable planning bench for RESIDUAL/Google AX execution experiments.

This module is intentionally side-effect free: importing it performs no network,
subprocess, filesystem, Kubernetes, AX, or RESIDUAL authority actions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Sequence
from urllib.parse import urlsplit


_AX_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,95}$")


class FaultKind(StrEnum):
    ACTOR_CRASH = "actor_crash"
    TRANSPORT_PARTITION = "transport_partition"
    FALSE_COMPLETION = "false_completion"
    STALE_GENERATION = "stale_generation"
    WORKSPACE_MUTATION = "workspace_mutation"
    CHECKPOINT_CORRUPTION = "checkpoint_corruption"
    IDENTITY_REBIND = "identity_rebind"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class Invariant(StrEnum):
    RUNTIME_STATE_IS_NOT_AUTHORITY = "runtime_state_is_not_authority"
    EXACT_EXECUTION_IDENTITY_BINDING = "exact_execution_identity_binding"
    STALE_GENERATION_CANNOT_ADVANCE = "stale_generation_cannot_advance"
    CHECKPOINT_CONTINUITY_IS_EVIDENCE_BOUND = "checkpoint_continuity_is_evidence_bound"
    WORKSPACE_PROVENANCE_IS_STABLE = "workspace_provenance_is_stable"
    NEGATIVE_AND_UNKNOWN_RESULTS_ARE_RETAINED = "negative_and_unknown_results_are_retained"


@dataclass(frozen=True, slots=True)
class AXWorkspace:
    name: str
    repo: str
    branch: str
    goal: str
    atespace: str = "default"
    repo_name: str = "origin"

    def __post_init__(self) -> None:
        _validate_ax_name(self.name, "workspace name")
        _validate_ax_name(self.atespace, "atespace")
        _validate_ax_name(self.repo_name, "repo name")
        _validate_nonempty(self.branch, "branch", 255)
        _validate_nonempty(self.goal, "goal", 4096)
        _validate_repo_url(self.repo)


@dataclass(frozen=True, slots=True)
class AXTask:
    name: str
    workspace: str
    command: tuple[str, ...]
    goal: str
    atespace: str = "default"
    image: str | None = None
    debug: bool = False
    cpu_request: str | None = None
    memory_request: str | None = None
    cpu_limit: str | None = None
    memory_limit: str | None = None

    def __post_init__(self) -> None:
        _validate_ax_name(self.name, "task name")
        _validate_ax_name(self.workspace, "workspace reference")
        _validate_ax_name(self.atespace, "atespace")
        _validate_nonempty(self.goal, "goal", 4096)
        if not self.command or len(self.command) > 64:
            raise ValueError("command must contain 1..64 arguments")
        for arg in self.command:
            _validate_nonempty(arg, "command argument", 4096)
        if self.image is not None:
            _validate_nonempty(self.image, "image", 2048)


@dataclass(frozen=True, slots=True)
class FaultInjection:
    kind: FaultKind
    trigger: str
    expected_observation: str
    expected_invariant: Invariant
    notes: str = ""

    def __post_init__(self) -> None:
        _validate_nonempty(self.trigger, "fault trigger", 4096)
        _validate_nonempty(self.expected_observation, "expected observation", 4096)
        if self.notes:
            _validate_nonempty(self.notes, "fault notes", 8192)


@dataclass(frozen=True, slots=True)
class AXExperiment:
    experiment_id: str
    hypothesis: str
    workspace: AXWorkspace
    task: AXTask
    invariants: tuple[Invariant, ...]
    faults: tuple[FaultInjection, ...] = ()
    measures: tuple[str, ...] = (
        "task_phase_transitions",
        "workspace_identity",
        "sandbox_identity",
        "checkpoint_identity",
        "artifact_digests",
        "runtime_claims",
        "verifier_disposition",
        "station_disposition",
        "latency_ms",
        "resource_usage",
    )
    protocol_revision: str = "ax-research.v1"
    notes: str = ""

    def __post_init__(self) -> None:
        if not _EXPERIMENT_ID_RE.fullmatch(self.experiment_id):
            raise ValueError("experiment_id must be 3..96 safe characters")
        _validate_nonempty(self.hypothesis, "hypothesis", 8192)
        _validate_nonempty(self.protocol_revision, "protocol_revision", 128)
        if self.workspace.name != self.task.workspace:
            raise ValueError("task.workspace must reference workspace.name")
        if self.workspace.atespace != self.task.atespace:
            raise ValueError("task and workspace must use the same atespace")
        if not self.invariants:
            raise ValueError("at least one invariant is required")
        if len(set(self.invariants)) != len(self.invariants):
            raise ValueError("duplicate invariants are not allowed")
        if len(self.faults) > 32:
            raise ValueError("at most 32 fault injections are allowed")
        if not self.measures or len(self.measures) > 64:
            raise ValueError("measures must contain 1..64 entries")
        for measure in self.measures:
            _validate_nonempty(measure, "measure", 256)
        if len(set(self.measures)) != len(self.measures):
            raise ValueError("duplicate measures are not allowed")
        if self.notes:
            _validate_nonempty(self.notes, "notes", 16384)

    def with_fault(self, fault: FaultInjection) -> "AXExperiment":
        return replace(self, faults=self.faults + (fault,))

    def with_measure(self, measure: str) -> "AXExperiment":
        _validate_nonempty(measure, "measure", 256)
        if measure in self.measures:
            return self
        return replace(self, measures=self.measures + (measure,))

    def preregistration(self) -> dict[str, Any]:
        return {
            "schema": "residual.ax-research-preregistration.v1",
            "protocol_revision": self.protocol_revision,
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "authority": False,
            "workspace": {
                "name": self.workspace.name,
                "repo": self.workspace.repo,
                "branch": self.workspace.branch,
                "goal": self.workspace.goal,
                "atespace": self.workspace.atespace,
                "repo_name": self.workspace.repo_name,
            },
            "task": {
                "name": self.task.name,
                "workspace": self.task.workspace,
                "command": list(self.task.command),
                "goal": self.task.goal,
                "atespace": self.task.atespace,
                "image": self.task.image,
                "debug": self.task.debug,
                "resources": _resource_dict(self.task),
            },
            "invariants": [item.value for item in self.invariants],
            "faults": [
                {
                    "kind": item.kind.value,
                    "trigger": item.trigger,
                    "expected_observation": item.expected_observation,
                    "expected_invariant": item.expected_invariant.value,
                    "notes": item.notes,
                }
                for item in self.faults
            ],
            "measures": list(self.measures),
            "notes": self.notes,
            "interpretation_rules": [
                "AX runtime state is an observation, never RESIDUAL acceptance.",
                "A workflow may execute successfully while the experiment outcome is FAIL, UNKNOWN, or BLOCKED.",
                "Negative, missing, rejected, stale, and contradictory observations remain in the evidence package.",
                "Suspend/resume continuity requires identity and evidence rebinding; process survival is not assumed.",
                "No experiment result grants Station authority without the normal independent verification path.",
            ],
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.preregistration(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def ax_documents(self) -> tuple[dict[str, Any], dict[str, Any]]:
        workspace_doc: dict[str, Any] = {
            "apiVersion": "ax.io/v1alpha1",
            "kind": "Workspace",
            "metadata": {
                "name": self.workspace.name,
                "atespace": self.workspace.atespace,
            },
            "spec": {
                "git": [
                    {
                        "name": self.workspace.repo_name,
                        "repo": self.workspace.repo,
                        "branch": self.workspace.branch,
                    }
                ]
            },
        }

        task_spec: dict[str, Any] = {
            "command": list(self.task.command),
            "workspaces": [
                {
                    "name": self.workspace.name,
                    "goal": self.task.goal,
                }
            ],
            "debug": self.task.debug,
        }
        if self.task.image is not None:
            task_spec["image"] = self.task.image
        resources = _resource_dict(self.task)
        if resources:
            task_spec["resources"] = resources

        task_doc: dict[str, Any] = {
            "apiVersion": "ax.io/v1alpha1",
            "kind": "Task",
            "metadata": {
                "name": self.task.name,
                "atespace": self.task.atespace,
            },
            "spec": task_spec,
        }
        return workspace_doc, task_doc

    def render_ax_stream(self) -> str:
        """Return deterministic JSON documents separated as an AX YAML stream.

        JSON is valid YAML 1.2, so this remains dependency-free and suitable for
        saving as a .yaml experiment input after human review.
        """
        return "\n---\n".join(
            json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False)
            for doc in self.ax_documents()
        ) + "\n"


class AXResearchBench:
    """Factory helpers for preregistered AX execution experiments."""

    @staticmethod
    def continuity_baseline(
        *,
        experiment_id: str,
        repo: str,
        branch: str,
        command: Sequence[str],
        hypothesis: str,
        workspace_name: str = "residual-ax21",
        task_name: str = "residual-ax21-task",
        atespace: str = "default",
        debug: bool = True,
    ) -> AXExperiment:
        workspace = AXWorkspace(
            name=workspace_name,
            repo=repo,
            branch=branch,
            goal="Prepare the exact repository revision and preserve workspace state across suspend/resume.",
            atespace=atespace,
        )
        task = AXTask(
            name=task_name,
            workspace=workspace_name,
            command=tuple(command),
            goal="Execute the bounded RESIDUAL research assignment without granting runtime state acceptance authority.",
            atespace=atespace,
            debug=debug,
        )
        return AXExperiment(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            workspace=workspace,
            task=task,
            invariants=(
                Invariant.RUNTIME_STATE_IS_NOT_AUTHORITY,
                Invariant.EXACT_EXECUTION_IDENTITY_BINDING,
                Invariant.CHECKPOINT_CONTINUITY_IS_EVIDENCE_BOUND,
                Invariant.NEGATIVE_AND_UNKNOWN_RESULTS_ARE_RETAINED,
            ),
        )

    @staticmethod
    def recommended_fault_matrix() -> tuple[FaultInjection, ...]:
        return (
            FaultInjection(
                kind=FaultKind.FALSE_COMPLETION,
                trigger="Observe AX Ready/Running after the agent command has exited or otherwise lacks the required result artifact.",
                expected_observation="RESIDUAL records the AX state but withholds acceptance until artifact and verifier evidence exist.",
                expected_invariant=Invariant.RUNTIME_STATE_IS_NOT_AUTHORITY,
            ),
            FaultInjection(
                kind=FaultKind.ACTOR_CRASH,
                trigger="Terminate the underlying actor after a durable checkpoint boundary.",
                expected_observation="Recovery is classified from retained checkpoint/workspace evidence; missing evidence stays UNKNOWN or BLOCKED.",
                expected_invariant=Invariant.CHECKPOINT_CONTINUITY_IS_EVIDENCE_BOUND,
            ),
            FaultInjection(
                kind=FaultKind.STALE_GENERATION,
                trigger="Deliver a result from the pre-resume execution generation after a new generation is bound.",
                expected_observation="The stale generation is retained as evidence but cannot advance accepted state.",
                expected_invariant=Invariant.STALE_GENERATION_CANNOT_ADVANCE,
            ),
            FaultInjection(
                kind=FaultKind.WORKSPACE_MUTATION,
                trigger="Mutate a bound file or repository identity between the preregistered baseline and verification.",
                expected_observation="Provenance mismatch is explicit; no inherited qualification or silent rebinding.",
                expected_invariant=Invariant.WORKSPACE_PROVENANCE_IS_STABLE,
            ),
            FaultInjection(
                kind=FaultKind.IDENTITY_REBIND,
                trigger="Suspend and resume so the process tree changes while logical assignment continuity is expected.",
                expected_observation="The new sandbox/process identity is rebound to the same logical assignment only with explicit continuity evidence.",
                expected_invariant=Invariant.EXACT_EXECUTION_IDENTITY_BINDING,
            ),
        )

    @classmethod
    def continuity_campaign(cls, **kwargs: Any) -> AXExperiment:
        experiment = cls.continuity_baseline(**kwargs)
        for fault in cls.recommended_fault_matrix():
            experiment = experiment.with_fault(fault)
        return experiment


def _resource_dict(task: AXTask) -> dict[str, Any]:
    requests: dict[str, str] = {}
    limits: dict[str, str] = {}
    if task.cpu_request is not None:
        requests["cpu"] = task.cpu_request
    if task.memory_request is not None:
        requests["memory"] = task.memory_request
    if task.cpu_limit is not None:
        limits["cpu"] = task.cpu_limit
    if task.memory_limit is not None:
        limits["memory"] = task.memory_limit
    result: dict[str, Any] = {}
    if requests:
        result["requests"] = requests
    if limits:
        result["limits"] = limits
    return result


def _validate_ax_name(value: str, label: str) -> None:
    if not _AX_NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must be an RFC 1123 label (lowercase, <=63 chars)")


def _validate_nonempty(value: str, label: str, max_len: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    if len(value) > max_len:
        raise ValueError(f"{label} exceeds {max_len} characters")
    if "\x00" in value:
        raise ValueError(f"{label} must not contain NUL")


def _validate_repo_url(repo: str) -> None:
    _validate_nonempty(repo, "repo", 2048)
    parsed = urlsplit(repo)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("repo must be an https URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("repo URL must not embed credentials")
    if parsed.fragment:
        raise ValueError("repo URL must not contain a fragment")


__all__ = [
    "AXExperiment",
    "AXResearchBench",
    "AXTask",
    "AXWorkspace",
    "FaultInjection",
    "FaultKind",
    "Invariant",
]
