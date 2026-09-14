"""Evaluation surfaces for Residual research and publication evidence.

The package retains the older SPEC-TEN-001/T10 evaluation harness and also exposes
SPEC-EVAL-001 system-level evidence for the M4 Factory path. The two contracts remain
separate because T10 requires at least ten simulated repeats while SPEC-EVAL-001
requires at least three controlled runs and a signed system-level comparison report.
"""

from .workload import FrozenWorkload, WorkloadTask
from .ablations import ABLATIONS, Ablation
from .faults import Fault, FaultInjector
from .runner import (
    DynamicSwarmBackend,
    EvaluationRunner,
    FixedSwarmBackend,
    RunConfiguration,
    SingleAgentBackend,
    SwarmBackend,
    TaskResult,
)
from .stats import Comparison, mann_whitney_u, summary_stats, welch_t_test
from .report import EvaluationReport
from .spec_eval import (
    CostAnalysis,
    CostRates,
    EvaluationRunEvidence,
    ExecutionControls,
    RunCounters,
    SignedComparisonReport,
    SpecEvalError,
    SpecEvaluationEvidence,
    SystemMetrics,
)

__all__ = [
    "ABLATIONS",
    "Ablation",
    "Comparison",
    "CostAnalysis",
    "CostRates",
    "DynamicSwarmBackend",
    "EvaluationReport",
    "EvaluationRunEvidence",
    "EvaluationRunner",
    "ExecutionControls",
    "Fault",
    "FaultInjector",
    "FixedSwarmBackend",
    "FrozenWorkload",
    "RunConfiguration",
    "RunCounters",
    "SignedComparisonReport",
    "SingleAgentBackend",
    "SpecEvalError",
    "SpecEvaluationEvidence",
    "SwarmBackend",
    "SystemMetrics",
    "TaskResult",
    "WorkloadTask",
    "mann_whitney_u",
    "summary_stats",
    "welch_t_test",
]
