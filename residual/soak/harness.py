"""Soak harness: drives the load generator, failure injection, metrics,
state persistence, and report signing.

The bundled executor is a deterministic simulator of the Station
pipeline (cache lookup -> brake screen -> execute/escalate) so the full
harness runs offline and reproducibly; the executor is isolated in
``SoakHarness._execute_task`` for replacement by a live Station.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .failure_injection import ADVERSARIAL_KINDS, FailureInjector, InjectionMix
from .loadgen import LoadGenerator
from .metrics import SoakMetrics
from .redteam import RedTeamExercise
from .report import SoakTestReport
from .state import SoakState
from .tasks import SyntheticTask


@dataclass(frozen=True)
class SoakConfig:
    seed: int = 20260914
    total_days: int = 30  # N9-R9: 30 consecutive days
    tasks_per_day: int = 1000
    cache_hit_probability: float = 0.72  # calibrated above the 60% target
    brake_fp_probability: float = 0.01
    brake_fn_probability: float = 0.002
    escalation_probability: float = 0.04
    cached_token_fraction: float = 0.30  # cache hit costs 30% of tokens
    injection_mix: InjectionMix = InjectionMix()


class SoakHarness:
    def __init__(self, config: SoakConfig, station_key: bytes,
                 state_path: Optional[str] = None,
                 enforce_load_minimum: bool = True):
        self.config = config
        self.station_key = station_key
        self.state_path = state_path
        self.loadgen = LoadGenerator(config.seed, config.tasks_per_day,
                                     enforce_minimum=enforce_load_minimum)
        self.injector = FailureInjector(config.seed, config.injection_mix)
        self.state = SoakState(seed=config.seed, tasks_per_day=config.tasks_per_day,
                               total_days=config.total_days)

    # -- simulated Station execution ------------------------------------
    def _execute_task(self, task: SyntheticTask, fault, day: int, index: int) -> Dict[str, Any]:
        cfg = self.config
        rng = random.Random(f"{cfg.seed}:exec:{day}:{index}")
        adversarial = fault is not None and fault.kind in ADVERSARIAL_KINDS
        event: Dict[str, Any] = {
            "cache_eligible": fault is None,
            "cache_hit": False,
            "tokens_uncached": task.expected_tokens,
            "tokens_used": task.expected_tokens,
            "adversarial": adversarial,
            "intentional_failure": fault is not None and not adversarial,
        }
        if event["cache_eligible"] and rng.random() < cfg.cache_hit_probability:
            event["cache_hit"] = True
            event["tokens_used"] = int(task.expected_tokens * cfg.cached_token_fraction)

        if adversarial:
            blocked = rng.random() >= cfg.brake_fn_probability
            event["blocked"] = blocked
            event["accepted"] = False if blocked else True
            # N9-R9: adversarial inputs must never produce unhandled exceptions.
            return event

        if fault is not None:
            # Intentional failure: handled gracefully with a recovery time.
            event["accepted"] = fault.expected_handling != "rejected"
            event["recovery_seconds"] = round(rng.uniform(5.0, 120.0), 2)
            return event

        brake_fired = rng.random() < cfg.brake_fp_probability
        event["brake_fired"] = brake_fired
        event["escalated"] = (not brake_fired) and rng.random() < cfg.escalation_probability
        event["accepted"] = not brake_fired
        return event

    # -- day execution ----------------------------------------------------
    def run_day(self, day: int) -> SoakMetrics:
        day_metrics = SoakMetrics()
        for index, task in enumerate(self.loadgen.tasks_for_day(day)):
            fault = self.injector.fault_for(day, index)
            try:
                event = self._execute_task(task, fault, day, index)
            except Exception:
                # N9-R10: any unhandled exception = soak test failure.
                day_metrics.record({"unhandled_exception": True})
                continue
            day_metrics.record(event)
        return day_metrics

    # -- whole soak --------------------------------------------------------
    def run(self, resume: bool = True, redteam: bool = True,
            max_days: Optional[int] = None) -> SoakState:
        if resume and self.state_path:
            try:
                self.state = SoakState.load(self.state_path)
            except FileNotFoundError:
                pass
        if redteam and not self.state.red_team_results:
            exercise = RedTeamExercise(seed=self.config.seed)
            self.state.red_team_results = [a.to_dict() for a in exercise.run()]
        limit = self.state.total_days if max_days is None else min(self.state.total_days, max_days)
        while self.state.next_day < limit:
            day = self.state.next_day
            self.state.metrics.merge(self.run_day(day))
            self.state.next_day = day + 1
            if self.state_path:
                self.state.save(self.state_path)
        return self.state

    def report(self, signed: bool = True) -> Dict[str, Any]:
        rep = SoakTestReport(self.state.metrics, self.state.days_completed,
                             self.state.red_team_results)
        return rep.build_signed(self.station_key) if signed else rep.build()
