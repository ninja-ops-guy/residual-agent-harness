from __future__ import annotations

from residual.factory.loop_runtime.state import MissionStatus, ProgressVector
from .metrics import MetricsRegistry


class LoopMetrics:
    """Low-cardinality M5 metrics. Per-goal detail belongs in traces/receipts, not labels."""

    def __init__(self, registry: MetricsRegistry):
        self.registry = registry

    def iteration(self, *, mode: str, progress: ProgressVector, escalated: bool) -> None:
        self.registry["residual_loop_iterations_total"].inc((mode,))
        self.registry["residual_loop_residual_mass"].set((mode,), progress.residual_mass)
        self.registry["residual_loop_progress_delta"].set((mode,), progress.progress_delta)
        if progress.tree_changed:
            self.registry["residual_loop_accepted_tree_changes_total"].inc((mode,))
        if progress.repeated_failure:
            self.registry["residual_loop_repeated_failure_total"].inc((mode,))
        if progress.churn:
            self.registry["residual_loop_churn_total"].inc((mode,))
        if escalated:
            self.registry["residual_loop_escalations_total"].inc((mode,))

    def terminal(self, *, mode: str, status: MissionStatus) -> None:
        self.registry["residual_loop_completion_total"].inc((mode, status.value))
        if status == MissionStatus.STAGNATED:
            self.registry["residual_loop_stagnation_total"].inc((mode,))
