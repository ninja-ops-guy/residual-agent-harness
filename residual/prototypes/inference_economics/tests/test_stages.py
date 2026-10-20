import pytest

from residual.prototypes.inference_economics.events import (
    Event,
    EventStream,
    EventValidationError,
    SCHEMA_REVISION,
)
from residual.prototypes.inference_economics.stages import (
    MINIMUM_STAGES,
    ResourceSignals,
    Stage,
    StageObservation,
    VALID_TRANSITIONS,
)


def obs(stage, start=0, end=1, **kwargs):
    values = dict(
        run_id="run",
        obligation_id="o1",
        task_class="test",
        topology="single",
        engine_class="synthetic",
        source_commit="abc",
        source_tree="tree",
        stage=stage,
        monotonic_start_ns=start,
        monotonic_end_ns=end,
        outcome="PASS",
        evidence_class="simulated",
        schema_revision=SCHEMA_REVISION,
    )
    values.update(kwargs)
    return StageObservation(**values)


def test_canonical_stage_vocabulary_exact():
    assert [stage.value for stage in Stage] == [
        "mission_submit",
        "planning",
        "scheduling",
        "queue_wait",
        "context_packaging",
        "worker_execution",
        "evidence_publication",
        "verification",
        "integration_queue",
        "integration",
        "terminal",
    ]
    assert MINIMUM_STAGES == frozenset(Stage)


def test_transition_graph_contains_no_outbound_terminal():
    assert VALID_TRANSITIONS[Stage.TERMINAL] == frozenset()


def test_queue_wait_may_be_skipped_after_scheduling():
    assert Stage.CONTEXT_PACKAGING in VALID_TRANSITIONS[Stage.SCHEDULING]


def test_missing_timestamp_stays_unknown_duration():
    assert obs(Stage.WORKER_EXECUTION, None, 10).duration_ns is None
    assert obs(Stage.WORKER_EXECUTION, 10, None).duration_ns is None


def test_negative_duration_rejected():
    with pytest.raises(ValueError, match="negative duration"):
        obs(Stage.WORKER_EXECUTION, 10, 9)


@pytest.mark.parametrize("field", [
    "run_id", "obligation_id", "task_class", "topology", "source_commit",
    "source_tree", "outcome", "evidence_class", "schema_revision", "attempt_id",
])
def test_required_observation_identity_cannot_be_empty(field):
    with pytest.raises(ValueError, match="required observation identities"):
        obs(Stage.WORKER_EXECUTION, **{field: ""})


@pytest.mark.parametrize("field", [
    "ready_frontier_depth", "pending_verification_depth", "integration_queue_depth",
    "active_workers", "worker_capacity", "context_bytes", "prompt_tokens",
    "cache_hits", "retries", "escalations",
])
def test_negative_integer_resource_signals_rejected(field):
    with pytest.raises(ValueError, match="negative resource signal"):
        ResourceSignals(**{field: -1})


def test_negative_provider_cost_rejected():
    with pytest.raises(ValueError, match="provider_cost"):
        ResourceSignals(provider_cost=-0.01)


def test_valid_linear_stream_constructs():
    events = [
        Event(0, obs(Stage.MISSION_SUBMIT, 0, 0)),
        Event(1, obs(Stage.PLANNING, 1, 2)),
        Event(2, obs(Stage.SCHEDULING, 2, 3)),
        Event(3, obs(Stage.CONTEXT_PACKAGING, 3, 4)),
        Event(4, obs(Stage.WORKER_EXECUTION, 4, 5)),
        Event(5, obs(Stage.EVIDENCE_PUBLICATION, 5, 6)),
        Event(6, obs(Stage.VERIFICATION, 6, 7)),
        Event(7, obs(Stage.TERMINAL, 7, 7)),
    ]
    assert len(EventStream(events)) == 8


def test_duplicate_normative_identity_rejected():
    with pytest.raises(EventValidationError, match="duplicate normative"):
        EventStream([
            Event(0, obs(Stage.WORKER_EXECUTION, 0, 1)),
            Event(1, obs(Stage.WORKER_EXECUTION, 2, 3)),
        ])


def test_same_stage_on_different_attempt_is_not_duplicate():
    stream = EventStream([
        Event(0, obs(Stage.WORKER_EXECUTION, 0, 1, attempt_id="a1")),
        Event(1, obs(Stage.WORKER_EXECUTION, 2, 3, attempt_id="a2")),
    ])
    assert len(stream) == 2


def test_non_monotonic_sequence_rejected():
    with pytest.raises(EventValidationError, match="non-monotonic sequence"):
        EventStream([
            Event(1, obs(Stage.WORKER_EXECUTION, 0, 1)),
            Event(1, obs(Stage.EVIDENCE_PUBLICATION, 1, 2)),
        ])


def test_incompatible_schema_rejected():
    bad = obs(Stage.WORKER_EXECUTION, schema_revision="future.v2")
    with pytest.raises(EventValidationError, match="incompatible schema"):
        EventStream([Event(0, bad)])


def test_impossible_transition_rejected():
    with pytest.raises(EventValidationError, match="impossible stage transition"):
        EventStream([
            Event(0, obs(Stage.WORKER_EXECUTION, 0, 1)),
            Event(1, obs(Stage.INTEGRATION, 1, 2)),
        ])


def test_records_include_source_tree_attempt_and_resources():
    stream = EventStream([
        Event(0, obs(
            Stage.WORKER_EXECUTION,
            resources=ResourceSignals(prompt_tokens=3, provider_throttled=True),
        ))
    ])
    record = stream.to_records()[0]["observation"]
    assert record["source_tree"] == "tree"
    assert record["attempt_id"] == "attempt-001"
    assert record["resources"]["prompt_tokens"] == 3
    assert record["resources"]["provider_throttled"] is True
