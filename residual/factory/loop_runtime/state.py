from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Mapping

from residual.core import Obligation, digest


class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class ObligationState(str, Enum):
    UNRESOLVED = "unresolved"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class MissionStatus(str, Enum):
    COMPLETE = "complete"
    EXHAUSTED = "exhausted"
    STAGNATED = "stagnated"
    ABORTED = "aborted"
    FAILED = "failed"


class CapabilityFloor(str, Enum):
    DEFAULT = "default"
    HIGHER = "higher"


class ParallelismHint(str, Enum):
    NONE = "none"
    ALLOW = "allow"
    PREFER = "prefer"


class Urgency(str, Enum):
    NONE = "none"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True)
class VerificationResultRef:
    verification_id: str
    status: VerificationStatus
    accepted_tree_hash: str | None
    evidence_root: str | None
    receipt_ref: str | None = None


@dataclass(frozen=True)
class FactoryResultSet:
    factory_run_id: str
    accepted_tree_hash: str | None
    accepted_evidence_root: str | None
    rejected_evidence_root: str | None
    verification_results: tuple[VerificationResultRef, ...]
    residual_obligations: tuple[Obligation, ...]
    obligation_states: Mapping[str, ObligationState]
    receipt_refs: tuple[str, ...] = ()
    cost: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        ids = [obligation.id for obligation in self.residual_obligations]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate residual obligation id")
        if self.cost < 0:
            raise ValueError("factory result cost must be nonnegative")


@dataclass(frozen=True)
class ResidualWorkSet:
    obligations: tuple[Obligation, ...]
    attempt_counts: Mapping[str, int]
    failure_fingerprints: Mapping[str, str]


@dataclass(frozen=True)
class DeduplicationMaterial:
    input_artifact_hashes: tuple[str, ...]
    worker_contract_hash: str


@dataclass(frozen=True)
class ExecutionIntent:
    urgency: Urgency = Urgency.NORMAL
    capability_floor: CapabilityFloor = CapabilityFloor.DEFAULT
    parallelism: ParallelismHint = ParallelismHint.ALLOW
    rationale: str = "initial_execution"
    deduplication_keys: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProgressVector:
    residual_mass: float
    progress_delta: float
    accepted_obligations: int
    obligation_resolved_delta: int
    tree_changed: bool
    churn: bool
    repeated_failure: bool


@dataclass(frozen=True)
class GoalEvaluation:
    complete: bool
    missing: tuple[str, ...]
    failed: tuple[str, ...]
    unknown: tuple[str, ...]


@dataclass(frozen=True)
class LoopMissionState:
    goal_id: str
    iteration: int = 0
    accepted_tree_hash: str | None = None
    accepted_evidence_root: str | None = None
    residual_mass: float = 0.0
    previous_residual_mass: float | None = None
    no_progress_streak: int = 0
    escalation_cooldown: int = 0
    spent_cost: Decimal = Decimal("0")
    elapsed_s: float = 0.0
    failure_fingerprint_counts: Mapping[str, int] = field(default_factory=dict)
    status: MissionStatus | None = None


@dataclass(frozen=True)
class LoopIterationRecord:
    goal_id: str
    iteration: int
    factory_run_id: str
    input_tree_hash: str | None
    output_tree_hash: str | None
    accepted_evidence_root: str | None
    rejected_evidence_root: str | None
    residual_ids: tuple[str, ...]
    receipt_refs: tuple[str, ...]
    progress: ProgressVector
    intent: ExecutionIntent
    failure_fingerprint: str

    @property
    def record_hash(self) -> str:
        return digest({
            "goal_id": self.goal_id,
            "iteration": self.iteration,
            "factory_run_id": self.factory_run_id,
            "input_tree_hash": self.input_tree_hash,
            "output_tree_hash": self.output_tree_hash,
            "accepted_evidence_root": self.accepted_evidence_root,
            "rejected_evidence_root": self.rejected_evidence_root,
            "residual_ids": list(self.residual_ids),
            "receipt_refs": list(self.receipt_refs),
            "progress": vars(self.progress),
            "intent": {
                "urgency": self.intent.urgency.value,
                "capability_floor": self.intent.capability_floor.value,
                "parallelism": self.intent.parallelism.value,
                "rationale": self.intent.rationale,
                "deduplication_keys": dict(self.intent.deduplication_keys),
            },
            "failure_fingerprint": self.failure_fingerprint,
        })


@dataclass(frozen=True)
class MissionResult:
    status: MissionStatus
    state: LoopMissionState
    iterations: tuple[LoopIterationRecord, ...]
    goal_evaluation: GoalEvaluation | None
    reason: str
