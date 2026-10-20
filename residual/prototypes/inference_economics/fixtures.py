"""Frozen scenario -> validated EventStream conversion."""

from .events import Event, EventStream, SCHEMA_REVISION
from .scenarios import Scenario
from .stages import StageObservation


def scenario_to_stream(
    scenario: Scenario,
    run_id: str = "run-001",
    source_commit: str = "fixture-commit",
    source_tree: str = "fixture-tree",
) -> EventStream:
    events = []
    for i, step in enumerate(scenario.steps):
        events.append(Event(
            seq=i,
            observation=StageObservation(
                run_id=run_id,
                obligation_id=step.obligation_id,
                task_class="test",
                topology="single",
                engine_class="synthetic",
                source_commit=source_commit,
                source_tree=source_tree,
                stage=step.stage,
                monotonic_start_ns=step.start_ns,
                monotonic_end_ns=step.end_ns,
                outcome=step.outcome,
                evidence_class="simulated",
                schema_revision=SCHEMA_REVISION,
                attempt_id=step.attempt_id,
                resources=step.resources,
            ),
        ))
    return EventStream(events)
