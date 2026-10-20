from dataclasses import replace

import pytest

from residual.prototypes.inference_economics.events import Event, EventStream, EventValidationError
from residual.prototypes.inference_economics.fixtures import scenario_to_stream
from residual.prototypes.inference_economics.replay import (
    ReplayEngine,
    ReplayError,
    metrics_hash,
    stream_hash,
)
from residual.prototypes.inference_economics.scenarios import ALL_SCENARIOS, SCENARIO_WORKER_BOUND
from residual.prototypes.inference_economics.stages import ResourceSignals


def clone_stream(stream):
    return EventStream([Event(event.seq, event.observation) for event in stream])


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_two_clean_executions_have_identical_stream_and_metrics_hashes(scenario):
    first = scenario_to_stream(scenario)
    second = scenario_to_stream(scenario)
    assert stream_hash(first) == stream_hash(second)
    assert metrics_hash(first) == metrics_hash(second)


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_replay_accepts_identical_frozen_stream(scenario):
    frozen = scenario_to_stream(scenario)
    result = ReplayEngine(frozen).replay(clone_stream(frozen))
    assert result["replay_ok"] is True
    assert result["stream_hash"] == stream_hash(frozen)


def test_source_tree_tamper_is_rejected_even_when_metrics_are_unchanged():
    frozen = scenario_to_stream(SCENARIO_WORKER_BOUND)
    events = list(frozen)
    events[0] = Event(events[0].seq, replace(events[0].observation, source_tree="tampered-tree"))
    tampered = EventStream(events)
    assert metrics_hash(tampered) == metrics_hash(frozen)
    with pytest.raises(ReplayError, match="stream hash mismatch"):
        ReplayEngine(frozen).replay(tampered)


def test_resource_signal_tamper_is_rejected():
    frozen = scenario_to_stream(SCENARIO_WORKER_BOUND)
    events = list(frozen)
    index = next(i for i, event in enumerate(events) if event.observation.stage.value == "worker_execution")
    events[index] = Event(
        events[index].seq,
        replace(events[index].observation, resources=ResourceSignals(provider_throttled=True)),
    )
    tampered = EventStream(events)
    assert ReplayEngine(frozen).verify_tamper_evidence(tampered) is True


def test_missing_terminal_event_is_rejected_by_stream_identity():
    frozen = scenario_to_stream(SCENARIO_WORKER_BOUND)
    candidate = EventStream(list(frozen)[:-1])
    with pytest.raises(ReplayError):
        ReplayEngine(frozen).replay(candidate)


def test_reordered_normative_stages_fail_closed_before_replay():
    frozen = scenario_to_stream(SCENARIO_WORKER_BOUND)
    events = list(frozen)
    worker_index = next(i for i, event in enumerate(events) if event.observation.stage.value == "worker_execution")
    evidence_index = worker_index + 1
    reordered = []
    for seq, event in enumerate(events):
        if seq == worker_index:
            source = events[evidence_index]
        elif seq == evidence_index:
            source = events[worker_index]
        else:
            source = event
        reordered.append(Event(seq, source.observation))
    with pytest.raises(EventValidationError, match="impossible stage transition"):
        EventStream(reordered)


def test_stream_hash_changes_when_attempt_identity_changes():
    frozen = scenario_to_stream(SCENARIO_WORKER_BOUND)
    events = list(frozen)
    events[0] = Event(events[0].seq, replace(events[0].observation, attempt_id="other-attempt"))
    tampered = EventStream(events)
    assert stream_hash(tampered) != stream_hash(frozen)
