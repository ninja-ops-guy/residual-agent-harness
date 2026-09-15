from __future__ import annotations

import time
from dataclasses import replace
from typing import Callable, Protocol, Sequence

from residual.core import Obligation
from .contract import GoalContract
from .policy import deduplication_key, next_intent
from .progress import failure_fingerprint, measure_progress, residual_mass
from .state import (
    DeduplicationMaterial,
    ExecutionIntent,
    FactoryResultSet,
    GoalEvaluation,
    LoopIterationRecord,
    LoopMissionState,
    MissionResult,
    MissionStatus,
    VerificationStatus,
)


class FactoryAdapter(Protocol):
    def run(self, obligations: tuple[Obligation, ...], intent: ExecutionIntent) -> FactoryResultSet: ...
    def deduplication_material(self, obligation: Obligation) -> DeduplicationMaterial: ...
    def cancel_inflight(self, timeout_s: float) -> None: ...


class LoopMetricsSink(Protocol):
    def iteration(self, *, mode: str, progress, escalated: bool) -> None: ...
    def terminal(self, *, mode: str, status: MissionStatus) -> None: ...


class GoalEvaluator:
    """Pure completion function over verifier outcomes and exact M4 accepted state.

    Worker prose is deliberately absent from this interface and therefore cannot
    influence continuation or completion.
    """

    def evaluate(self, contract: GoalContract, result: FactoryResultSet) -> GoalEvaluation:
        if not result.accepted_tree_hash or not result.accepted_evidence_root:
            return GoalEvaluation(False, tuple(contract.required_verification_ids), (), ())
        by_id = {item.verification_id: item for item in result.verification_results}
        missing: list[str] = []
        failed: list[str] = []
        unknown: list[str] = []
        for verification_id in contract.required_verification_ids:
            item = by_id.get(verification_id)
            if item is None:
                missing.append(verification_id)
                continue
            if item.accepted_tree_hash != result.accepted_tree_hash or item.evidence_root != result.accepted_evidence_root:
                failed.append(verification_id)
                continue
            if item.status == VerificationStatus.FAIL:
                failed.append(verification_id)
            elif item.status == VerificationStatus.UNKNOWN:
                unknown.append(verification_id)
            elif item.status != VerificationStatus.PASS:
                unknown.append(verification_id)
        return GoalEvaluation(
            complete=not (missing or failed or unknown),
            missing=tuple(missing),
            failed=tuple(failed),
            unknown=tuple(unknown),
        )


class LoopController:
    def __init__(
        self,
        factory: FactoryAdapter,
        *,
        evaluator: GoalEvaluator | None = None,
        metrics: LoopMetricsSink | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        abort_requested: Callable[[], bool] | None = None,
        cancel_timeout_s: float = 5.0,
    ) -> None:
        self.factory = factory
        self.evaluator = evaluator or GoalEvaluator()
        self.metrics = metrics
        self.monotonic = monotonic
        self.abort_requested = abort_requested or (lambda: False)
        self.cancel_timeout_s = cancel_timeout_s

    def _dedup_keys(self, obligations: Sequence[Obligation]) -> dict[str, str]:
        return {
            obligation.id: deduplication_key(obligation, self.factory.deduplication_material(obligation))
            for obligation in obligations
        }

    @staticmethod
    def _should_abort(contract: GoalContract, state: LoopMissionState) -> str | None:
        for condition in contract.abort_conditions:
            if condition.require_no_progress and state.no_progress_streak == 0:
                continue
            if condition.budget_threshold is not None and state.spent_cost >= condition.budget_threshold:
                return "abort_condition_budget_threshold"
            if condition.time_threshold_s is not None and state.elapsed_s >= condition.time_threshold_s:
                return "abort_condition_time_threshold"
        return None

    def _abort(self, state: LoopMissionState, records: list[LoopIterationRecord], reason: str) -> MissionResult:
        self.factory.cancel_inflight(self.cancel_timeout_s)
        terminal = replace(state, status=MissionStatus.ABORTED)
        if self.metrics:
            self.metrics.terminal(mode="host-owned", status=MissionStatus.ABORTED)
        return MissionResult(MissionStatus.ABORTED, terminal, tuple(records), None, reason)

    def run(self, contract: GoalContract, obligations: tuple[Obligation, ...]) -> MissionResult:
        start = self.monotonic()
        state = LoopMissionState(goal_id=contract.goal_id)
        records: list[LoopIterationRecord] = []
        current = obligations
        previous_result: FactoryResultSet | None = None
        fingerprint_counts: dict[str, int] = {}
        intent = ExecutionIntent(deduplication_keys=self._dedup_keys(current))
        evaluation: GoalEvaluation | None = None

        for iteration in range(1, contract.max_iterations + 1):
            elapsed = self.monotonic() - start
            state = replace(state, elapsed_s=elapsed)
            if self.abort_requested():
                return self._abort(state, records, "human_or_operator_abort")
            if elapsed >= contract.max_wall_time_s:
                return self._abort(state, records, "wall_time_exhausted")
            if contract.max_cost is not None and state.spent_cost >= contract.max_cost:
                return self._abort(state, records, "cost_budget_exhausted")
            abort_reason = self._should_abort(contract, state)
            if abort_reason:
                return self._abort(state, records, abort_reason)

            result = self.factory.run(current, intent)
            elapsed = self.monotonic() - start
            fingerprint = failure_fingerprint(result)
            seen = fingerprint_counts.get(fingerprint, 0)
            fingerprint_counts[fingerprint] = seen + 1
            progress = measure_progress(previous_result, result, seen)
            evaluation = self.evaluator.evaluate(contract, result)

            no_progress = progress.progress_delta <= 0 and progress.obligation_resolved_delta == 0
            streak = state.no_progress_streak + 1 if previous_result is not None and no_progress else 0
            spent = state.spent_cost + result.cost
            cooldown = max(0, state.escalation_cooldown - 1)
            state = LoopMissionState(
                goal_id=contract.goal_id,
                iteration=iteration,
                accepted_tree_hash=result.accepted_tree_hash,
                accepted_evidence_root=result.accepted_evidence_root,
                residual_mass=residual_mass(result),
                previous_residual_mass=state.residual_mass if state.iteration else None,
                no_progress_streak=streak,
                escalation_cooldown=cooldown,
                spent_cost=spent,
                elapsed_s=elapsed,
                failure_fingerprint_counts=dict(fingerprint_counts),
                status=None,
            )
            records.append(LoopIterationRecord(
                goal_id=contract.goal_id,
                iteration=iteration,
                factory_run_id=result.factory_run_id,
                input_tree_hash=previous_result.accepted_tree_hash if previous_result else None,
                output_tree_hash=result.accepted_tree_hash,
                accepted_evidence_root=result.accepted_evidence_root,
                rejected_evidence_root=result.rejected_evidence_root,
                residual_ids=tuple(obligation.id for obligation in result.residual_obligations),
                receipt_refs=result.receipt_refs,
                progress=progress,
                intent=intent,
                failure_fingerprint=fingerprint,
            ))

            # An abort arriving during the synchronous Factory call takes
            # precedence over a late successful result. Keep completed evidence.
            if self.abort_requested():
                return self._abort(state, records, "human_or_operator_abort")
            if elapsed >= contract.max_wall_time_s:
                return self._abort(state, records, "wall_time_exhausted")

            if evaluation.complete:
                terminal = replace(state, status=MissionStatus.COMPLETE)
                if self.metrics:
                    self.metrics.iteration(mode="host-owned", progress=progress, escalated=False)
                    self.metrics.terminal(mode="host-owned", status=MissionStatus.COMPLETE)
                return MissionResult(MissionStatus.COMPLETE, terminal, tuple(records), evaluation, "goal_predicates_satisfied")

            if contract.max_cost is not None and spent >= contract.max_cost:
                return self._abort(state, records, "cost_budget_exhausted")
            abort_reason = self._should_abort(contract, state)
            if abort_reason:
                return self._abort(state, records, abort_reason)
            if not result.residual_obligations:
                terminal = replace(state, status=MissionStatus.STAGNATED)
                if self.metrics:
                    self.metrics.iteration(mode="host-owned", progress=progress, escalated=False)
                    self.metrics.terminal(mode="host-owned", status=MissionStatus.STAGNATED)
                return MissionResult(MissionStatus.STAGNATED, terminal, tuple(records), evaluation, "no_residual_work_for_incomplete_goal")
            if state.no_progress_streak >= contract.no_progress_limit:
                terminal = replace(state, status=MissionStatus.STAGNATED)
                if self.metrics:
                    self.metrics.iteration(mode="host-owned", progress=progress, escalated=False)
                    self.metrics.terminal(mode="host-owned", status=MissionStatus.STAGNATED)
                return MissionResult(MissionStatus.STAGNATED, terminal, tuple(records), evaluation, "no_progress_limit_reached")

            current = result.residual_obligations
            next_keys = self._dedup_keys(current)
            if previous_result is None:
                intent, escalated = ExecutionIntent(deduplication_keys=next_keys), False
            else:
                intent, escalated = next_intent(
                    progress, cooldown=state.escalation_cooldown, deduplication_keys=next_keys
                )
            if escalated:
                state = replace(state, escalation_cooldown=contract.escalation_cooldown_period)
            if self.metrics:
                self.metrics.iteration(mode="host-owned", progress=progress, escalated=escalated)
            previous_result = result

        terminal = replace(state, status=MissionStatus.EXHAUSTED)
        if self.metrics:
            self.metrics.terminal(mode="host-owned", status=MissionStatus.EXHAUSTED)
        return MissionResult(MissionStatus.EXHAUSTED, terminal, tuple(records), evaluation, "max_iterations_reached")
