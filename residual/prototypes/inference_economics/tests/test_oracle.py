import pytest

from residual.prototypes.inference_economics.fixtures import scenario_to_stream
from residual.prototypes.inference_economics.oracle import IndependentOracle
from residual.prototypes.inference_economics.scenarios import (
    ALL_SCENARIOS,
    SCENARIO_UNKNOWN_EVIDENCE,
    SCENARIO_VERIFIER_BOUND,
)
from residual.prototypes.inference_economics.stages import Stage


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_oracle_counts_are_nonnegative(scenario):
    stream = scenario_to_stream(scenario)
    assert IndependentOracle.attempt_count(stream) >= 0
    assert IndependentOracle.verifier_terminal_count(stream) >= 0
    assert IndependentOracle.accepted_count(stream) >= 0
    assert IndependentOracle.integrated_count(stream) >= 0


def test_verifier_bound_queue_oracle_sees_three_parallel_verifiers():
    stream = scenario_to_stream(SCENARIO_VERIFIER_BOUND)
    assert IndependentOracle.queue_depth_at(stream, 1_600, Stage.VERIFICATION) == 3
    assert IndependentOracle.queue_depth_at(stream, 101_600, Stage.VERIFICATION) == 0


def test_queue_transitions_are_sorted_and_exact():
    stream = scenario_to_stream(SCENARIO_VERIFIER_BOUND)
    transitions = IndependentOracle.queue_transitions(stream, Stage.VERIFICATION)
    assert transitions[0] == {"at_ns": 1_600, "depth": 3}
    assert transitions[-1] == {"at_ns": 101_600, "depth": 0}


def test_unknown_wall_time_is_not_zero():
    stream = scenario_to_stream(SCENARIO_UNKNOWN_EVIDENCE)
    assert IndependentOracle.wall_time_ns(stream) is None
    assert all(value is None for value in IndependentOracle.throughput_rates(stream).values())


def test_unknown_otx_inputs_are_null_not_zero_for_observed_missing_phases():
    stream = scenario_to_stream(SCENARIO_UNKNOWN_EVIDENCE)
    inputs = IndependentOracle.otx_input_totals_ns(stream)
    assert inputs["worker_execution"] is None
    assert inputs["verification"] is None
    assert inputs["coordination"] is None


def test_oracle_dominant_share_validation():
    stream = scenario_to_stream(ALL_SCENARIOS[0])
    with pytest.raises(ValueError):
        IndependentOracle.bottleneck_class(stream, dominant_share=0)
