import pytest

from residual.prototypes.inference_economics.fixtures import scenario_to_stream
from residual.prototypes.inference_economics.queue_recon import QueueReconstructor
from residual.prototypes.inference_economics.scenarios import ALL_SCENARIOS, SCENARIO_VERIFIER_BOUND
from residual.prototypes.inference_economics.stages import Stage


def test_verifier_queue_reconstruction_matches_expected_parallel_depth():
    stream = scenario_to_stream(SCENARIO_VERIFIER_BOUND)
    transitions = QueueReconstructor(stream).transitions_for(Stage.VERIFICATION)
    assert transitions[0].depth == 3
    assert transitions[-1].depth == 0


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_all_stage_transition_reconstructions_match_independent_oracle(scenario):
    recon = QueueReconstructor(scenario_to_stream(scenario))
    for stage in Stage:
        assert recon.verify_against_oracle(stage) == []


def test_all_transitions_are_deterministically_sorted():
    recon = QueueReconstructor(scenario_to_stream(SCENARIO_VERIFIER_BOUND))
    transitions = recon.all_transitions()
    assert transitions == sorted(transitions, key=lambda item: (item.at_ns, item.stage))
