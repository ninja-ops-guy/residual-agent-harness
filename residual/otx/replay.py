"""Exact decision replay for SPEC-SWARM-OTX-003 (Gate C).

Given the stored observation log, rebuild a fresh controller, fold each
observation's outcome in sequence order, and re-derive every topology
decision. Because :class:`OrchestrationTaxController` is deterministic
given (config, estimator state, task), replayed decisions MUST match the
stored selections exactly.
"""
from __future__ import annotations

from typing import Dict, Iterable, List

from .models import PhaseTiming, Task
from .observation import TopologyObservation


def replay_decisions(config, observations: Iterable[TopologyObservation]) -> List[Dict[str, object]]:
    """Replay stored observations; return per-observation match records."""
    from .controller import OrchestrationTaxController  # avoid import cycle

    ordered = sorted(observations, key=lambda o: o.sequence)
    controller = OrchestrationTaxController(config=config)
    results: List[Dict[str, object]] = []

    for stored in ordered:
        t = stored.inputs["task"]
        task = Task(
            task_id=t["task_id"],
            task_class=t["task_class"],
            granularity=t["granularity"],
            value=t["value"],
            size=t["size"],
        )
        replayed = controller.select_topology(task)
        match = replayed.selected_topology == stored.selected_topology
        results.append(
            {
                "observation_id": stored.observation_id,
                "stored_topology": stored.selected_topology,
                "replayed_topology": replayed.selected_topology,
                "stored_utility": next(
                    c.predicted_utility for c in stored.candidates if c.topology == stored.selected_topology
                ),
                "replayed_utility": next(
                    c.predicted_utility for c in replayed.candidates if c.topology == replayed.selected_topology
                ),
                "match": match,
            }
        )
        # fold the stored outcome so the next decision sees the same state
        if stored.result is not None:
            controller.record_outcome(
                replayed.observation_id,
                PhaseTiming(dict(stored.result.timing_breakdown)),
                stored.result.success,
                stored.result.quality_score,
            )
    return results


def verify_replay(config, observations: Iterable[TopologyObservation]) -> Dict[str, object]:
    records = replay_decisions(config, observations)
    mismatches = [r for r in records if not r["match"]]
    return {
        "total": len(records),
        "matched": len(records) - len(mismatches),
        "mismatches": mismatches,
        "exact": not mismatches,
    }
