"""Headless Factory Mode primitives for Residual's multi-swarm platform."""

from .compiler import CompileResult, RequirementCompiler
from .models import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from .evidence_bus import (
    ArtifactBinding, EvidenceBus, EvidenceError, FactoryStationIssuer,
    StationIdentity, VerificationDecision, WorkerReceipt,
)

__all__ = [
    "CompileResult",
    "ExecutionPlan",
    "FactoryTask",
    "FrozenPlan",
    "Requirement",
    "RequirementCompiler",
    "ArtifactBinding",
    "EvidenceBus",
    "EvidenceError",
    "FactoryStationIssuer",
    "StationIdentity",
    "VerificationDecision",
    "WorkerReceipt",
]
