"""SPEC-SWARM-EVAL-001: frozen reliability evaluation.

Compares raw/unconstrained execution (R0) against progressively stronger
Residual control layers (R1-R5) while holding worker/model capability,
prompting policy, inference settings, task corpus, tool environment, and
grader constant. All fixture runs use deterministic scripted engines; live
model runs are separately labeled and never mixed into fixture aggregates.
"""
from __future__ import annotations

from .workload import FrozenTask, FrozenWorkload, development_workload
from .economics import build_swarm5_evidence, fixture_observations
from .configs import CONFIGURATIONS, CONTROLLED_CONSTANTS, ExperimentConfig, get_config
from .runner import RunRecord, RunState, run_study, recompute_from_records
from .metrics import SliceMetrics, compute_slice_metrics
from .report import build_report, report_csv_rows, plotting_inputs
from .evidence import build_evidence_artifact, write_evidence_artifact
from .acceptance_binding import (
    CHAIN_SCHEMA,
    AcceptanceBindingError,
    FreshRunRegistry,
    MeasuredRunEvidence,
    RunIdentityRecord,
    SchedulerObservation,
    SchedulerTopologyEvidence,
    VerifierQualification,
    WorkloadTaskMapping,
    chain_fresh_record,
    validate_and_issue_acceptance,
    validate_prerequisites,
    verify_acceptance_artifact,
    verify_run_identity_chain,
)

__all__ = [
    "FrozenTask",
    "FrozenWorkload",
    "development_workload",
    "CONFIGURATIONS",
    "CONTROLLED_CONSTANTS",
    "ExperimentConfig",
    "get_config",
    "RunRecord",
    "RunState",
    "run_study",
    "recompute_from_records",
    "SliceMetrics",
    "compute_slice_metrics",
    "build_report",
    "report_csv_rows",
    "plotting_inputs",
    "build_evidence_artifact",
    "write_evidence_artifact",
    "build_swarm5_evidence", "fixture_observations",
    "AcceptanceBindingError",
    "CHAIN_SCHEMA",
    "FreshRunRegistry",
    "MeasuredRunEvidence",
    "RunIdentityRecord",
    "SchedulerObservation",
    "SchedulerTopologyEvidence",
    "VerifierQualification",
    "WorkloadTaskMapping",
    "chain_fresh_record",
    "validate_and_issue_acceptance",
    "validate_prerequisites",
    "verify_acceptance_artifact",
    "verify_run_identity_chain",
]
