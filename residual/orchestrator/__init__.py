"""Residual orchestration track (Swarm 4 / track I).

Pipeline: Intent -> RequirementCompiler -> RequirementGraph ->
AmbiguityDetector -> WorkPartitioner -> RiskEstimator -> Plan ->
ApprovalGate (HITL-gated).

The additive flow layer compiles an existing Plan into a staged execution view;
it does not replace plan authority or the Factory/M4 trust boundary.
"""
from .intent import Intent
from .requirements import Requirement, RequirementGraph
from .compiler import RequirementCompiler, default_decompose
from .ambiguity import (AmbiguityDetector, AmbiguityFlag, AmbiguityReport,
                        MISSING_ACCEPTANCE, MISSING_MEASURABLE, MISSING_OWNER)
from .partition import WorkPacket, WorkPartitioner
from .risk import (RiskEstimator, RiskReport, DEFAULT_PROTECTED_PREFIXES,
                   FAN_OUT_WEIGHT, PROTECTED_WEIGHT, EXTERNAL_IO_WEIGHT)
from .plan import (Plan, PlanApproval, ApprovalGate, InMemoryApprovalGate,
                   HITLApprovalGate, DECISION_APPROVED, DECISION_DENIED)
from .flow import (
    CapabilityGrant,
    ExecutionProfile,
    FlowCompiler,
    FlowStage,
    ResidualFlow,
    ResumeDecision,
    StageBudget,
    StageCheckpoint,
    StageDoor,
    StageKind,
    validate_resume,
)
from .pipeline import Orchestrator

__all__ = [
    "Intent",
    "Requirement", "RequirementGraph",
    "RequirementCompiler", "default_decompose",
    "AmbiguityDetector", "AmbiguityFlag", "AmbiguityReport",
    "MISSING_ACCEPTANCE", "MISSING_MEASURABLE", "MISSING_OWNER",
    "WorkPacket", "WorkPartitioner",
    "RiskEstimator", "RiskReport", "DEFAULT_PROTECTED_PREFIXES",
    "FAN_OUT_WEIGHT", "PROTECTED_WEIGHT", "EXTERNAL_IO_WEIGHT",
    "Plan", "PlanApproval", "ApprovalGate", "InMemoryApprovalGate",
    "HITLApprovalGate", "DECISION_APPROVED", "DECISION_DENIED",
    "CapabilityGrant", "ExecutionProfile", "FlowCompiler", "FlowStage",
    "ResidualFlow", "ResumeDecision", "StageBudget", "StageCheckpoint",
    "StageDoor", "StageKind", "validate_resume",
    "Orchestrator",
]
