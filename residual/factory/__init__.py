"""Headless Factory Mode primitives for Residual's multi-swarm platform."""

from .compiler import CompileResult, RequirementCompiler
from .models import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from .evidence_bus import (
    ArtifactBinding, EvidenceBus, EvidenceError, FactoryStationIssuer,
    StationIdentity, VerificationDecision, WorkerReceipt,
)
from .m4_evidence import (
    EvidenceIntegrationPlan,
    IntegrationConflict,
    M4EvidenceError,
    PlannedArtifact,
    ReadyDagSnapshot,
    ReceiptBackedM4,
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
    "EvidenceIntegrationPlan",
    "IntegrationConflict",
    "M4EvidenceError",
    "PlannedArtifact",
    "ReadyDagSnapshot",
    "ReceiptBackedM4",
]
