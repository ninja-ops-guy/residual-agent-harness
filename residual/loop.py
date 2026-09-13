"""Bounded host-controlled Gather → Act → Verify passes.

The controller owns counters and lifecycle events. Optional worker observations
cannot spoof completion or budgets. Deadlines are cooperative pass boundaries;
executors remain responsible for per-call timeouts and pre-dispatch reservations.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol

from .brakes import Brake, BrakeAction, BrakeTrip, build_brakes
from .core import ContractError, digest
from .goalspec import GoalSpec
from .verifier import VerificationReport, Verifier


class RunOutcome(str, Enum):
    SUCCESS = "success"
    ESCALATED = "escalated"
    ABORTED = "aborted"
    AMENDED = "amended"  # Reserved: amendments are explicit new runs, never automatic.


@dataclass(frozen=True)
class RunResult:
    outcome: RunOutcome
    goal_id: str
    run_id: str
    total_passes: int
    total_tokens: Optional[int]
    wall_clock_s: float
    final_verification: Optional[VerificationReport] = None
    tripped_brakes: tuple[str, ...] = ()
    trip_reasons: tuple[str, ...] = ()
    amendment_reason: Optional[str] = None
    spec_hash: str = ""


class HarnessPass(Protocol):
    def run_pass(self, spec: GoalSpec, pass_number: int) -> dict:
        """Return candidate, tokens_used (host receipt; None if unknown), observations."""
        ...


@dataclass
class LoopController:
    spec: GoalSpec
    verifier: Verifier
    harness: HarnessPass
    brakes: tuple[Brake, ...] = ()
    emit: Optional[Callable[[str, dict], None]] = None
    no_progress_threshold: int = 3
    _running: bool = field(default=False, init=False, repr=False)

    def __post_init__(self):
        if not self.brakes:
            self.brakes = build_brakes(self.spec, self.no_progress_threshold)

    def _emit(self, kind: str, payload: dict) -> None:
        # Host callbacks are authoritative. Optional telemetry adapters should
        # catch delivery failures themselves (StationBus does so and counts them).
        if self.emit:
            self.emit(kind, payload)

    def run(self) -> RunResult:
        if self._running:
            raise ContractError("controller is already running")
        self._running = True
        try:
            for brake in self.brakes:
                brake.reset()
            return self._run()
        finally:
            self._running = False

    def _run(self) -> RunResult:
        run_id = str(uuid.uuid4())
        spec = self.spec
        t0 = time.monotonic()
        tokens: Optional[int] = 0
        report = None
        trips: list[BrakeTrip] = []
        self._emit("checkpoint", {"event": "run_opened", "run_id": run_id,
            "goal_id": spec.goal_id, "spec_hash": spec.content_hash,
            "max_passes": spec.max_passes, "token_budget": spec.token_budget,
            "wall_clock_budget_s": spec.wall_clock_budget_s,
            "amendment_count": spec.amendment_count, "parent_hash": spec.parent_hash})

        def record(trip):
            if not any(t.brake_name == trip.brake_name and t.recommended_action == trip.recommended_action for t in trips):
                trips.append(trip)
                self._emit("state.transition", {"from_state": "brake_armed", "to_state": "brake_tripped",
                    "brake_name": trip.brake_name, "trip_reason": trip.trip_reason,
                    "triggering_obs_hash": trip.triggering_obs_hash, "run_id": run_id})

        def feed(event):
            for brake in self.brakes:
                trip = brake.update(event)
                if trip:
                    record(trip)

        def force(name, reason, action, event):
            record(BrakeTrip(name, reason, digest(event), action))

        feed({"kind": "checkpoint", "event": "run_opened"})
        # A literal bounded range protects even hosts using a custom brake set.
        for pass_number in range(1, spec.max_passes + 1):
            trips.clear()
            if time.monotonic() - t0 >= spec.wall_clock_budget_s:
                force("budget", "wall_clock_budget_exhausted", BrakeAction.ABORT, {"pass": pass_number})
                return self._finish(RunOutcome.ABORTED, run_id, pass_number - 1, tokens, t0, report, trips, spec)
            self._emit("state.transition", {"from_state": "pass_pending", "to_state": "pass_running",
                                            "pass_number": pass_number, "run_id": run_id})
            result = self.harness.run_pass(spec, pass_number)
            if not isinstance(result, dict) or "candidate" not in result:
                raise ContractError("harness pass must return a candidate object")
            used = result.get("tokens_used")
            if type(used) is not int or used < 0:
                tokens = None
                force("budget", "usage_unknown_or_invalid", BrakeAction.ABORT, {"pass": pass_number})
            else:
                tokens += used
                feed({"kind": "llm.response", "usage": {"total_tokens": used}})
                if tokens >= spec.token_budget:
                    force("budget", "token_budget_exhausted", BrakeAction.ABORT, {"tokens": tokens})
            observations = result.get("observations", [])
            if not isinstance(observations, (list, tuple)) or len(observations) > 10000 or any(not isinstance(o, dict) for o in observations):
                raise ContractError("harness observations must be a bounded list of objects")
            # Never feed worker lifecycle/usage/verification claims as control facts.
            for obs in observations:
                if obs.get("kind") == "tool.invoked":
                    feed(obs)
            if result.get("halt") is not None:
                if result["halt"] not in {"paused", "no_runnable_tasks"}:
                    raise ContractError("unknown harness halt reason")
                force("dispatch", result["halt"], BrakeAction.ESCALATE, {"halt": result["halt"]})
            if time.monotonic() - t0 >= spec.wall_clock_budget_s:
                force("budget", "wall_clock_budget_exhausted", BrakeAction.ABORT, {"pass": pass_number})
            # Do not incur a judge call after an abort condition is established.
            if any(t.recommended_action == BrakeAction.ABORT for t in trips):
                report = None
            else:
                report = self.verifier.verify(result["candidate"], spec,
                    emit=lambda kind, payload: self._emit("custom", {"event": kind, "run_id": run_id, **payload}))
                verification = {"event": "verification_report", "goal_id": spec.goal_id,
                    "overall_pass": report.overall_pass, "primary_failure": report.primary_failure,
                    "duration_ms": report.duration_ms, "run_id": run_id}
                self._emit("custom", verification)
                feed({"kind": "custom", "payload": verification})
            if time.monotonic() - t0 >= spec.wall_clock_budget_s:
                force("budget", "wall_clock_budget_exhausted", BrakeAction.ABORT, {"pass": pass_number})
            completed = {"from_state": "pass_running", "to_state": "pass_complete",
                "pass_number": pass_number, "overall_pass": bool(report and report.overall_pass), "run_id": run_id}
            self._emit("state.transition", completed)
            feed({"kind": "state.transition", **completed})
            if pass_number == spec.max_passes and not completed["overall_pass"]:
                force("max_iteration", "max_passes_reached", BrakeAction.ESCALATE, completed)
            decision = self._decide(trips, report)
            self._emit("custom", {"event": "brake_decision", "pass_number": pass_number,
                "decision": decision.value, "tripped_brakes": [t.brake_name for t in trips], "run_id": run_id})
            outcome = RunOutcome.ABORTED if decision == BrakeAction.ABORT else RunOutcome.ESCALATED if decision == BrakeAction.ESCALATE else RunOutcome.SUCCESS if completed["overall_pass"] else None
            if outcome:
                return self._finish(outcome, run_id, pass_number, tokens, t0, report, trips, spec)
        raise AssertionError("bounded loop must terminate")

    def _decide(self, tripped: list[BrakeTrip], report: Optional[VerificationReport]) -> BrakeAction:
        actions = {t.recommended_action for t in tripped}
        if BrakeAction.ABORT in actions:
            return BrakeAction.ABORT
        if BrakeAction.ESCALATE in actions:
            return BrakeAction.ESCALATE
        return BrakeAction.CONTINUE

    def _finish(self, outcome, run_id, passes, tokens, t0, verification, tripped, spec):
        elapsed = round(time.monotonic() - t0, 3)
        result = RunResult(outcome, spec.goal_id, run_id, passes, tokens, elapsed,
            final_verification=verification, tripped_brakes=tuple(t.brake_name for t in tripped),
            trip_reasons=tuple(t.trip_reason for t in tripped), spec_hash=spec.content_hash,
            amendment_reason=spec.amendment_reason)
        self._emit("checkpoint", {"event": "run_closed", "run_id": run_id,
            "outcome": outcome.value, "total_passes": passes, "total_tokens": tokens,
            "wall_clock_s": elapsed, "tripped_brakes": list(result.tripped_brakes),
            "trip_reasons": list(result.trip_reasons), "spec_hash": spec.content_hash})
        return result
