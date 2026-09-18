"""Orca-derived staged flow IR for RESIDUAL.

This module borrows architectural ideas (stages, resumability, capability gates,
adaptive simple-vs-reviewed-vs-swarm flows) without depending on Orca at runtime.

The flow is an additive execution *view* over an existing orchestrator Plan. It does
not replace the authoritative requirement graph, approval gate, WorkerContract,
Evidence Fabric, verifier, or deterministic integrator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..core import ContractError, digest

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _strings(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ContractError(f"{name} must be a sequence")
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ContractError(f"{name} entries must be non-empty strings")
        out.append(value.strip())
    if len(set(out)) != len(out):
        raise ContractError(f"{name} entries must be unique")
    return tuple(sorted(out))


class StageKind(str, Enum):
    DETERMINISTIC = "deterministic"
    AGENT = "agent"
    REVIEW = "review"
    SWARM = "swarm"
    HUMAN_GATE = "human-gate"


class ExecutionProfile(str, Enum):
    SINGLE = "single"
    REVIEWED = "reviewed"
    SWARM = "swarm"


@dataclass(frozen=True)
class CapabilityGrant:
    tools: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    network: bool = False
    workspace_write: bool = False

    def __post_init__(self):
        object.__setattr__(self, "tools", _strings(self.tools, "tools"))
        object.__setattr__(self, "paths", _strings(self.paths, "paths"))
        if type(self.network) is not bool or type(self.workspace_write) is not bool:
            raise ContractError("capability booleans must be bool")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tools": list(self.tools),
            "paths": list(self.paths),
            "network": self.network,
            "workspace_write": self.workspace_write,
        }

    def authorize(
        self,
        *,
        tool: str | None = None,
        path: str | None = None,
        network: bool = False,
        write: bool = False,
    ) -> None:
        if tool is not None and tool not in self.tools:
            raise ContractError(f"tool outside stage capability: {tool}")
        if path is not None:
            normalized = path.replace("\\", "/").lstrip("./")
            if not any(normalized == p.rstrip("/") or normalized.startswith(p.rstrip("/") + "/")
                       for p in self.paths):
                raise ContractError(f"path outside stage capability: {path}")
        if network and not self.network:
            raise ContractError("network outside stage capability")
        if write and not self.workspace_write:
            raise ContractError("workspace write outside stage capability")


@dataclass(frozen=True)
class StageBudget:
    max_tokens: int = 0
    max_seconds: float = 60.0
    max_attempts: int = 1

    def __post_init__(self):
        if type(self.max_tokens) is not int or self.max_tokens < 0:
            raise ContractError("max_tokens must be a nonnegative integer")
        if not isinstance(self.max_seconds, (int, float)) or self.max_seconds <= 0:
            raise ContractError("max_seconds must be positive")
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ContractError("max_attempts must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "max_seconds": float(self.max_seconds),
            "max_attempts": self.max_attempts,
        }


@dataclass(frozen=True)
class FlowStage:
    stage_id: str
    name: str
    kind: StageKind
    requirement_ids: tuple[str, ...] = ()
    packet_ids: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    capability: CapabilityGrant = CapabilityGrant()
    budget: StageBudget = StageBudget()
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.stage_id, str) or not self.stage_id.strip():
            raise ContractError("stage_id must be non-empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ContractError("stage name must be non-empty")
        if not isinstance(self.kind, StageKind):
            raise ContractError("stage kind must be StageKind")
        object.__setattr__(self, "requirement_ids", _strings(self.requirement_ids, "requirement_ids"))
        object.__setattr__(self, "packet_ids", _strings(self.packet_ids, "packet_ids"))
        object.__setattr__(self, "depends_on", _strings(self.depends_on, "depends_on"))
        if self.stage_id in self.depends_on:
            raise ContractError("stage cannot depend on itself")
        if not isinstance(self.reason, str):
            raise ContractError("stage reason must be a string")
        if self.kind is StageKind.DETERMINISTIC and self.budget.max_tokens != 0:
            raise ContractError("deterministic stage must have zero model-token budget")

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "kind": self.kind.value,
            "requirement_ids": list(self.requirement_ids),
            "packet_ids": list(self.packet_ids),
            "depends_on": list(self.depends_on),
            "capability": self.capability.to_dict(),
            "budget": self.budget.to_dict(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ResidualFlow:
    plan_hash: str
    profile: ExecutionProfile
    stages: tuple[FlowStage, ...]
    schema_version: str = "residual.flow.v1"

    def __post_init__(self):
        if not isinstance(self.plan_hash, str) or not _HASH_RE.fullmatch(self.plan_hash):
            raise ContractError("plan_hash must be a lowercase sha256 digest")
        if not isinstance(self.profile, ExecutionProfile):
            raise ContractError("profile must be ExecutionProfile")
        if not self.stages:
            raise ContractError("flow requires at least one stage")
        ids = [s.stage_id for s in self.stages]
        if len(ids) != len(set(ids)):
            raise ContractError("duplicate stage ids")
        seen: set[str] = set()
        for stage in self.stages:
            missing = set(stage.depends_on) - seen
            if missing:
                raise ContractError(f"stage depends on missing or later stages: {sorted(missing)}")
            seen.add(stage.stage_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_hash": self.plan_hash,
            "profile": self.profile.value,
            "stages": [s.to_dict() for s in self.stages],
        }

    @property
    def flow_hash(self) -> str:
        return digest(self.to_dict())

    def stage(self, stage_id: str) -> FlowStage:
        for stage in self.stages:
            if stage.stage_id == stage_id:
                return stage
        raise ContractError(f"unknown stage: {stage_id}")


@dataclass(frozen=True)
class StageCheckpoint:
    flow_hash: str
    stage_id: str
    input_hash: str
    output_hash: str
    repo_head_before: str
    repo_head_after: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("flow_hash", "input_hash", "output_hash"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
                raise ContractError(f"{name} must be a lowercase sha256 digest")
        if not self.stage_id:
            raise ContractError("checkpoint stage_id must be non-empty")
        if not self.repo_head_before or not self.repo_head_after:
            raise ContractError("checkpoint repository heads must be non-empty")
        object.__setattr__(self, "evidence_ids", _strings(self.evidence_ids, "evidence_ids"))


@dataclass(frozen=True)
class ResumeDecision:
    reusable: bool
    reason: str


def validate_resume(
    flow: ResidualFlow,
    checkpoint: StageCheckpoint,
    *,
    expected_input_hash: str,
    current_repo_head: str,
) -> ResumeDecision:
    if checkpoint.flow_hash != flow.flow_hash:
        return ResumeDecision(False, "flow-hash-mismatch")
    try:
        flow.stage(checkpoint.stage_id)
    except ContractError:
        return ResumeDecision(False, "stage-missing")
    if checkpoint.input_hash != expected_input_hash:
        return ResumeDecision(False, "input-hash-mismatch")
    if checkpoint.repo_head_after != current_repo_head:
        return ResumeDecision(False, "repository-head-mismatch")
    return ResumeDecision(True, "exact-checkpoint-binding")


class StageDoor:
    """Named capability gate; downstream RESIDUAL policy remains authoritative."""

    @staticmethod
    def authorize(
        stage: FlowStage,
        *,
        tool: str | None = None,
        path: str | None = None,
        network: bool = False,
        write: bool = False,
    ) -> None:
        if not isinstance(stage, FlowStage):
            raise ContractError("StageDoor requires a FlowStage")
        stage.capability.authorize(tool=tool, path=path, network=network, write=write)


class FlowCompiler:
    """Compile an existing Plan into a deterministic staged execution view."""

    REVIEW_RISK = 2.0
    SWARM_RISK = 6.0
    SWARM_PACKETS = 4

    def profile_for(self, plan: Any) -> ExecutionProfile:
        max_risk = max((r.score for r in plan.risk_reports), default=0.0)
        if max_risk >= self.SWARM_RISK or len(plan.packets) >= self.SWARM_PACKETS:
            return ExecutionProfile.SWARM
        if plan.ambiguity.has_ambiguity or max_risk >= self.REVIEW_RISK or len(plan.packets) >= 2:
            return ExecutionProfile.REVIEWED
        return ExecutionProfile.SINGLE

    def compile(self, plan: Any) -> ResidualFlow:
        from .plan import Plan

        if not isinstance(plan, Plan):
            raise ContractError("flow compilation requires an orchestrator Plan")

        profile = self.profile_for(plan)
        stages: list[FlowStage] = [
            FlowStage(
                "prepare",
                "Prepare deterministic execution context",
                StageKind.DETERMINISTIC,
                capability=CapabilityGrant(tools=("orchestrator.compile",)),
                budget=StageBudget(max_tokens=0, max_seconds=30, max_attempts=1),
                reason="mechanical plan-to-flow compilation",
            )
        ]

        root_dep = "prepare"
        if plan.ambiguity.has_ambiguity:
            stages.append(FlowStage(
                "human-gate",
                "Resolve plan ambiguity",
                StageKind.HUMAN_GATE,
                requirement_ids=tuple(sorted({f.requirement_id for f in plan.ambiguity.flags})),
                depends_on=("prepare",),
                capability=CapabilityGrant(tools=("hitl.approve",)),
                budget=StageBudget(max_tokens=0, max_seconds=3600, max_attempts=1),
                reason="ambiguous requirements require explicit operator authority",
            ))
            root_dep = "human-gate"

        risk_by_packet = {r.packet_id: r for r in plan.risk_reports}
        exec_ids_by_level: dict[int, list[str]] = {}
        for packet in plan.packets:
            previous = exec_ids_by_level.get(packet.level - 1, [])
            deps = tuple(previous) if previous else (root_dep,)
            report = risk_by_packet[packet.packet_id]
            kind = StageKind.SWARM if profile is ExecutionProfile.SWARM else StageKind.AGENT
            stage_id = f"execute-{packet.packet_id}"
            tools = ("swarm.execute",) if kind is StageKind.SWARM else ("agent.execute",)
            tokens = 8000 if kind is StageKind.SWARM else (4000 if profile is ExecutionProfile.REVIEWED else 2500)
            stages.append(FlowStage(
                stage_id,
                f"Execute {packet.packet_id}",
                kind,
                requirement_ids=packet.requirement_ids,
                packet_ids=(packet.packet_id,),
                depends_on=deps,
                capability=CapabilityGrant(
                    tools=tools,
                    paths=packet.files,
                    network=report.external_io_count > 0,
                    workspace_write=bool(packet.files),
                ),
                budget=StageBudget(max_tokens=tokens, max_seconds=900, max_attempts=2),
                reason=f"profile={profile.value}; risk={report.score:.1f}",
            ))
            exec_ids_by_level.setdefault(packet.level, []).append(stage_id)

        exec_ids = tuple(s.stage_id for s in stages if s.kind in {StageKind.AGENT, StageKind.SWARM})
        verification_deps = exec_ids
        if profile in {ExecutionProfile.REVIEWED, ExecutionProfile.SWARM}:
            stages.append(FlowStage(
                "review",
                "Review implementation evidence",
                StageKind.REVIEW,
                depends_on=exec_ids,
                capability=CapabilityGrant(tools=("review.inspect",)),
                budget=StageBudget(max_tokens=2000, max_seconds=300, max_attempts=2),
                reason="explicit review required by execution profile",
            ))
            verification_deps = ("review",)

        stages.append(FlowStage(
            "verify",
            "Run deterministic verification",
            StageKind.DETERMINISTIC,
            depends_on=verification_deps,
            capability=CapabilityGrant(tools=("verifier.run",)),
            budget=StageBudget(max_tokens=0, max_seconds=900, max_attempts=1),
            reason="mechanical qualification remains outside model authority",
        ))
        stages.append(FlowStage(
            "integrate",
            "Apply deterministic integration",
            StageKind.DETERMINISTIC,
            depends_on=("verify",),
            capability=CapabilityGrant(
                tools=("integrator.apply",),
                paths=tuple(sorted({path for packet in plan.packets for path in packet.files})),
                workspace_write=True,
            ),
            budget=StageBudget(max_tokens=0, max_seconds=300, max_attempts=1),
            reason="integration is deterministic and still subject to existing M4 authority",
        ))
        return ResidualFlow(plan_hash=plan.plan_hash, profile=profile, stages=tuple(stages))
