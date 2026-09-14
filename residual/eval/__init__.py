"""Track J — FrozenWorkload evaluation harness.

Implements SPEC-TEN-001 requirements:

- T10-R1: FrozenWorkload evaluation (single vs fixed vs dynamic swarm)
  with n >= 10 runs per configuration; results include mean, median,
  standard deviation, and statistical significance tests (implemented
  locally on stdlib ``statistics`` — Mann-Whitney U and Welch t-test).
- T10-R3: FrozenWorkload definition and all raw evaluation data are
  preserved in the serialized report (raw run records included).
- T10-R4: Reproducibility — the FrozenWorkload is frozen and
  content-addressed (hash-locked manifest); all configurations and the
  harness live in the repo; seeded RNGs make runs deterministic.

The pre-existing ``residual/evaluation.py`` benchmark may be imported
but is not modified; this package builds under ``residual/eval/`` per
the swarm contract.
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

__all__ = [
    "ABLATIONS",
    "Ablation",
    "Comparison",
    "DynamicSwarmBackend",
    "EvaluationReport",
    "EvaluationRunner",
    "Fault",
    "FaultInjector",
    "FixedSwarmBackend",
    "FrozenWorkload",
    "RunConfiguration",
    "SingleAgentBackend",
    "SwarmBackend",
    "TaskResult",
    "WorkloadTask",
    "mann_whitney_u",
    "summary_stats",
    "welch_t_test",
]
