"""Residual orchestration track (Swarm 4 / track I).

Pipeline: Intent -> RequirementCompiler -> RequirementGraph ->
AmbiguityDetector -> WorkPartitioner -> RiskEstimator -> Plan ->
ApprovalGate (HITL-gated).

Requirement IDs (RFC 2119 language lives in each module docstring):
ORCH-I-R1..R3   intent schema (intent.py)
ORCH-I-R4..R6   requirement DAG (requirements.py)
ORCH-I-R7..R8   requirement compiler (compiler.py)
ORCH-I-R9..R10  ambiguity detector (ambiguity.py)
ORCH-I-R11..R13 work partitioner (partition.py)
ORCH-I-R14..R15 risk estimation (risk.py)
ORCH-I-R16..R18 plan hash and approval (plan.py)
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
    "Orchestrator",
]
