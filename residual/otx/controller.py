"""Orchestration Tax Controller — SPEC-SWARM-OTX-003.

Learns when swarming helps and when orchestration overhead exceeds its
benefit. The controller is deterministic given (configuration, estimator
state, task), which is what makes Gate C replay exact.

Requirement map:
* OTX-R2 ``orchestration_tax`` — data-derived tax per (task, topology).
* OTX-R4 ``record_outcome`` — predicted-vs-observed comparison per task.
* OTX-R5 ``select_topology`` — configurable deployment threshold walks to
  simpler topologies when predicted tax is too high.
* OTX-R6 ``evaluate_fixture`` — multi-granularity evaluation on the
  frozen fixture.
* OTX-R7 ``_utility`` — quality-adjusted utility (reliability-weighted).
* OTX-R8 — every choice appends a :class:`TopologyObservation`.

Integration points with the existing harness: engine selection stays
with ``residual.engines.router.CapabilityRouter`` (this controller picks
*how many / which roles*, not which engine); run lifecycle events flow
through ``residual.async_io.coordinator.AsyncRunCoordinator``; station
scheduling (``residual.station``) supplies the actual per-phase timings
that callers pass to :meth:`record_outcome`.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

from .estimator import TaxModel
from .models import SIMPLEST_TOPOLOGY, TOPOLOGIES, Phase, PhaseTiming, Task, Topology
from .observation import (
    CandidatePrediction,
    ObservationLog,
    ObservedResult,
    TaxComparison,
    TopologyObservation,
)


@dataclass(frozen=True)
class ControllerConfig:
    """Controller configuration; part of every observation's inputs."""

    deployment_tax_threshold: float = 3.0    # OTX-R5: above this, go simpler
    latency_penalty: float = 0.05            # weight of predicted seconds in utility
    topologies: Tuple[str, ...] = ("single", "pair", "swarm")

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["topologies"] = list(self.topologies)
        return d


class OrchestrationTaxController:
    """Learns per-task-class orchestration tax and picks topologies."""

    def __init__(self, config: Optional[ControllerConfig] = None, log: Optional[ObservationLog] = None) -> None:
        self.config = config or ControllerConfig()
        for name in self.config.topologies:
            if name not in TOPOLOGIES:
                raise ValueError(f"unknown topology {name!r}")
        self.model = TaxModel(TOPOLOGIES)
        self.log = log or ObservationLog()
        self._seq = 0

    # ------------------------------------------------------------------ OTX-R2
    def orchestration_tax(self, task: Task, topology: str) -> float:
        """Data-derived predicted orchestration tax for (task, topology).

        The tax is the posterior mean overhead-to-productive-work ratio
        conditioned on the task class; it is *estimated from observations*,
        never a fixed constant.
        """
        return self.model.predicted_tax(task.task_class, topology)

    # ------------------------------------------------------------------ OTX-R7
    def _utility(self, task: Task, topology: str) -> float:
        """Quality-adjusted utility: reliability-weighted value minus
        latency cost. A faster-but-less-reliable topology cannot win on
        latency alone because value is scaled by predicted reliability."""
        reliability = self.model.predicted_reliability(task.task_class, topology)
        latency = self.model.predicted_total_s(task.task_class, topology)
        return reliability * task.value - self.config.latency_penalty * latency

    def _candidates(self, task: Task) -> List[CandidatePrediction]:
        preds: List[CandidatePrediction] = []
        for name in self.config.topologies:
            preds.append(
                CandidatePrediction(
                    topology=name,
                    predicted_tax=self.model.predicted_tax(task.task_class, name),
                    tax_std=self.model.tax_uncertainty(task.task_class, name),
                    predicted_worker_s=self.model.predicted_worker_s(task.task_class, name),
                    predicted_total_s=self.model.predicted_total_s(task.task_class, name),
                    predicted_reliability=self.model.predicted_reliability(task.task_class, name),
                    predicted_utility=self._utility(task, name),
                )
            )
        return preds

    # ------------------------------------------------------------------ OTX-R5/R8
    def select_topology(self, task: Task) -> TopologyObservation:
        """Choose a topology and emit a fully populated observation (OTX-R8)."""
        candidates = self._candidates(task)
        best = max(candidates, key=lambda c: (c.predicted_utility, -TOPOLOGIES[c.topology].complexity_rank, c.topology))
        selected, reason = best.topology, "max_utility"

        # OTX-R5: configurable deployment threshold — if the predicted tax
        # of the utility winner exceeds the threshold, walk down to the
        # simplest topology whose predicted tax is within budget.
        if best.predicted_tax > self.config.deployment_tax_threshold:
            ordered = sorted(candidates, key=lambda c: TOPOLOGIES[c.topology].complexity_rank)
            for cand in ordered:  # simplest first
                if cand.predicted_tax <= self.config.deployment_tax_threshold:
                    selected, reason = cand.topology, "deployment_threshold"
                    break
            else:
                selected, reason = SIMPLEST_TOPOLOGY, "deployment_threshold"

        self._seq += 1
        # Full snapshots are large; a digest keeps the observation compact
        # while still binding it to the estimator state at decision time
        # (replay rebuilds state by folding outcomes, so no information
        # needed for reproduction is lost).
        snapshot_digest = hashlib.sha256(
            json.dumps(self.model.snapshot(), sort_keys=True).encode("utf-8")
        ).hexdigest()
        obs = TopologyObservation(
            observation_id=f"otx-{self._seq:06d}",
            sequence=self._seq,
            inputs={
                "task": {
                    "task_id": task.task_id,
                    "task_class": task.task_class,
                    "granularity": task.granularity,
                    "value": task.value,
                    "size": task.size,
                },
                "config": self.config.to_dict(),
            },
            candidates=candidates,
            selected_topology=selected,
            selection_reason=reason,
            model_snapshot={"sha256": snapshot_digest},
        )
        self.log.append(obs)
        return obs

    # ------------------------------------------------------------------ OTX-R3/R4
    def record_outcome(
        self,
        observation_id: str,
        timing: PhaseTiming,
        success: bool,
        quality_score: Optional[float] = None,
    ) -> TaxComparison:
        """Fold an experimental outcome into the model and compare
        predicted vs observed tax (OTX-R4)."""
        obs = self.log.by_id(observation_id)
        task_class = obs.inputs["task"]["task_class"]
        topology = obs.selected_topology
        predicted_tax = next(c.predicted_tax for c in obs.candidates if c.topology == topology)
        tax_std = next(c.tax_std for c in obs.candidates if c.topology == topology)

        observed_tax = self.model.observe(task_class, topology, timing, success)

        comparison = TaxComparison(
            predicted_tax=predicted_tax,
            observed_tax=observed_tax,
            error=observed_tax - predicted_tax,
            abs_error=abs(observed_tax - predicted_tax),
            within_1_std=abs(observed_tax - predicted_tax) <= max(tax_std, 1e-9),
        )
        obs.result = ObservedResult(
            timing_breakdown=timing.breakdown(),
            observed_tax=observed_tax,
            observed_total_s=timing.total_s,
            success=bool(success),
            quality_score=float(quality_score if quality_score is not None else (1.0 if success else 0.0)),
        )
        obs.comparison = comparison
        return comparison

    # ------------------------------------------------------------------ OTX-R6
    def evaluate_fixture(self, fixture, simulate=None, seed: int = 0) -> Dict[str, object]:
        """Run the frozen fixture across all granularities, returning
        per-granularity metrics. ``simulate`` defaults to the seeded
        reference simulator (used by tests/evidence; production callers
        supply real station timings via ``record_outcome`` instead)."""
        simulate = simulate or simulate_execution
        rng = random.Random(seed if seed else fixture.seed)
        per_granularity: Dict[str, Dict[str, float]] = {}
        decisions: Dict[str, Dict[str, int]] = {}
        for gran in fixture.granularities():
            errors: List[float] = []
            decisions[gran] = {}
            for task in fixture.slice(gran):
                obs = self.select_topology(task)
                timing, success, quality = simulate(task, obs.selected_topology, rng)
                comparison = self.record_outcome(obs.observation_id, timing, success, quality)
                errors.append(comparison.abs_error)
                decisions[gran][obs.selected_topology] = decisions[gran].get(obs.selected_topology, 0) + 1
            per_granularity[gran] = {
                "tasks": len(errors),
                "mean_abs_tax_error": sum(errors) / len(errors) if errors else 0.0,
            }
        return {
            "workload_hash": fixture.workload_hash,
            "granularities": {g: {**per_granularity[g], "decisions": decisions[g]} for g in fixture.granularities()},
            "observations": len(self.log),
        }

    # ------------------------------------------------------------------ Gate C
    def replay_decisions(self, observations) -> List[Dict[str, object]]:
        """Rebuild estimator state from stored outcomes and re-derive each
        topology decision exactly (deterministic reproduction, Gate C)."""
        from .replay import replay_decisions  # local import to avoid cycle

        return replay_decisions(self.config, observations)


# --------------------------------------------------------------------------
# Reference simulator (development fixture only; labelled non-live, like
# EVAL-R10's scripted fixture). Deterministic given the seeded RNG.
# Ground truth is chosen so that "lookup" prefers ``single`` and
# "synthesis" prefers ``swarm`` once learned.
# --------------------------------------------------------------------------

_SIM_RELIABILITY: Dict[Tuple[str, str], float] = {
    ("lookup", "single"): 0.97,
    ("lookup", "pair"): 0.98,
    ("lookup", "swarm"): 0.98,
    ("synthesis", "single"): 0.55,
    ("synthesis", "pair"): 0.80,
    ("synthesis", "swarm"): 0.95,
}

_SIM_PHASE_BASE: Dict[str, Dict[str, float]] = {
    # per-phase fixed seconds; scale with workers / size below
    "single": {Phase.SCHEDULING: 0.05, Phase.INTEGRATION: 0.05},
    "pair": {Phase.SCHEDULING: 0.05, Phase.CONTEXT_PACKAGING: 0.15, Phase.VERIFICATION: 0.30, Phase.INTEGRATION: 0.05},
    "swarm": {
        Phase.PLANNING: 0.60,
        Phase.SCHEDULING: 0.20,
        Phase.CONTEXT_PACKAGING: 0.45,
        Phase.VERIFICATION: 0.30,
        Phase.INTEGRATION: 0.40,
        Phase.COORDINATION: 0.50,
    },
}


def simulate_execution(task: Task, topology: str, rng: random.Random) -> Tuple[PhaseTiming, bool, float]:
    """Seeded, deterministic-per-stream reference execution.

    Swarm parallelism divides worker time but pays fixed coordination
    costs, so small tasks are taxed heavily while large synthesis tasks
    amortise the overhead and gain reliability.
    """
    topo = TOPOLOGIES[topology]
    seconds: Dict[str, float] = {}
    for phase in topo.phases_active:
        if phase == Phase.WORKER_EXECUTION:
            continue
        base = _SIM_PHASE_BASE[topology].get(phase, 0.0)
        jitter = 1.0 + 0.1 * (rng.random() - 0.5)
        seconds[phase] = base * (1.0 + 0.25 * (task.size - 1.0)) * jitter
    worker_s = (task.size * 2.0 / topo.workers) * (1.0 + 0.1 * (rng.random() - 0.5))
    seconds[Phase.WORKER_EXECUTION] = worker_s
    reliability = _SIM_RELIABILITY[(task.task_class, topology)]
    success = rng.random() < reliability
    quality = 1.0 if success else 0.0
    return PhaseTiming(seconds), success, quality
