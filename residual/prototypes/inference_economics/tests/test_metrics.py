from dataclasses import asdict

import pytest

from residual.prototypes.inference_economics.events import Event, EventStream, SCHEMA_REVISION
from residual.prototypes.inference_economics.fixtures import scenario_to_stream
from residual.prototypes.inference_economics.metrics import (
    classify_bottleneck,
    compute_latency,
    compute_pressure,
    compute_resource_accounting,
    compute_throughput,
    obligation_latencies,
    otx_projection,
    percentile,
    stage_distributions,
    stage_utilizations,
)
from residual.prototypes.inference_economics.oracle import IndependentOracle
from residual.prototypes.inference_economics.scenarios import ALL_SCENARIOS, SCENARIO_UNKNOWN_EVIDENCE
from residual.prototypes.inference_economics.stages import ResourceSignals, Stage, StageObservation


def _obs(seq, obligation, stage, start, end, outcome="PASS", resources=None):
    return Event(seq, StageObservation(
        run_id="divergence",
        obligation_id=obligation,
        task_class="test",
        topology="single",
        engine_class="synthetic",
        source_commit="c",
        source_tree="t",
        stage=stage,
        monotonic_start_ns=start,
        monotonic_end_ns=end,
        outcome=outcome,
        evidence_class="simulated",
        schema_revision=SCHEMA_REVISION,
        resources=resources or ResourceSignals(),
    ))


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_primary_classifier_matches_frozen_expected_scenarios(scenario):
    assert classify_bottleneck(scenario_to_stream(scenario)) == scenario.expected_bottleneck


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_independent_classifier_matches_frozen_expected_scenarios(scenario):
    assert IndependentOracle.bottleneck_class(scenario_to_stream(scenario)) == scenario.expected_bottleneck


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_primary_and_independent_throughput_agree(scenario):
    stream = scenario_to_stream(scenario)
    assert asdict(compute_throughput(stream)) | {} == IndependentOracle.throughput_rates(stream) | {
        "correct_accepted_goodput": None,
        "correct_integrated_goodput": None,
    }


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_primary_and_independent_latency_agree(scenario):
    stream = scenario_to_stream(scenario)
    assert asdict(compute_latency(stream)) == IndependentOracle.latency_breakdown(stream)


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_primary_and_independent_obligation_latencies_agree(scenario):
    stream = scenario_to_stream(scenario)
    assert [asdict(item) for item in obligation_latencies(stream)] == IndependentOracle.obligation_latencies(stream)


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_primary_and_independent_stage_utilization_agree(scenario):
    stream = scenario_to_stream(scenario)
    primary = {item.stage: item.utilization for item in stage_utilizations(stream)}
    assert primary == IndependentOracle.stage_occupied_ratios(stream)


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda scenario: scenario.name)
def test_primary_and_independent_otx_inputs_agree(scenario):
    stream = scenario_to_stream(scenario)
    projection = otx_projection(stream)
    primary_ns = {
        phase: None if value is None else round(value * 1_000_000_000)
        for phase, value in projection.phase_seconds.items()
    }
    assert primary_ns == IndependentOracle.otx_input_totals_ns(stream)


def test_unknown_evidence_never_becomes_zero_throughput_or_latency():
    stream = scenario_to_stream(SCENARIO_UNKNOWN_EVIDENCE)
    throughput = compute_throughput(stream)
    latency = compute_latency(stream)
    assert throughput.attempt_throughput is None
    assert throughput.accepted_goodput is None
    assert throughput.integrated_goodput is None
    assert latency.ttfw_ns is None
    assert latency.tte_ns is None
    assert latency.tta_ns is None
    assert latency.tti_ns is None


def test_unknown_evidence_never_becomes_complete_otx_or_pressure():
    stream = scenario_to_stream(SCENARIO_UNKNOWN_EVIDENCE)
    projection = otx_projection(stream)
    pressure = compute_pressure(stream)
    assert projection.complete is False
    assert projection.phase_seconds["worker_execution"] is None
    assert projection.observed_tax is None
    assert pressure.active_workers is None
    assert pressure.active_verifiers is None
    assert pressure.integration_queue_depth is None


def test_attempt_throughput_can_exceed_accepted_goodput():
    events = []
    seq = 0
    for index, outcome in enumerate(("FAIL", "FAIL", "PASS"), start=1):
        obligation = f"o{index}"
        events.extend([
            _obs(seq, obligation, Stage.WORKER_EXECUTION, index * 100, index * 100 + 20),
            _obs(seq + 1, obligation, Stage.EVIDENCE_PUBLICATION, index * 100 + 20, index * 100 + 30),
            _obs(seq + 2, obligation, Stage.VERIFICATION, index * 100 + 30, index * 100 + 40, outcome=outcome),
        ])
        seq += 3
        if outcome == "PASS":
            events.extend([
                _obs(seq, obligation, Stage.INTEGRATION_QUEUE, index * 100 + 40, index * 100 + 45),
                _obs(seq + 1, obligation, Stage.INTEGRATION, index * 100 + 45, index * 100 + 50),
            ])
            seq += 2
    metrics = compute_throughput(EventStream(events))
    assert metrics.attempt_throughput > metrics.accepted_goodput
    assert metrics.accepted_goodput == metrics.integrated_goodput
    assert metrics.correct_accepted_goodput is None
    assert metrics.correct_integrated_goodput is None


def test_resource_accounting_preserves_missing_usage_as_unknown():
    stream = EventStream([_obs(0, "o1", Stage.WORKER_EXECUTION, 0, 10)])
    accounting = compute_resource_accounting(stream)
    assert all(value is None for value in asdict(accounting).values())


def test_resource_accounting_sums_authoritative_event_deltas():
    stream = EventStream([
        _obs(0, "o1", Stage.WORKER_EXECUTION, 0, 10, resources=ResourceSignals(prompt_tokens=10, completion_tokens=2, provider_cost=0.1)),
        _obs(1, "o1", Stage.EVIDENCE_PUBLICATION, 10, 20, resources=ResourceSignals(prompt_tokens=5, completion_tokens=1, provider_cost=0.2)),
    ])
    accounting = compute_resource_accounting(stream)
    assert accounting.prompt_tokens == 15
    assert accounting.completion_tokens == 3
    assert accounting.provider_cost == pytest.approx(0.3)
    assert accounting.cached_input_tokens is None


def test_pressure_prefers_explicit_resource_snapshot():
    resources = ResourceSignals(
        ready_frontier_depth=7,
        pending_verification_depth=3,
        integration_queue_depth=2,
        active_workers=4,
        active_verifiers=1,
        active_integrations=1,
        worker_capacity=5,
        verifier_capacity=2,
        integration_capacity=1,
    )
    stream = EventStream([_obs(0, "o1", Stage.WORKER_EXECUTION, 0, 10, resources=resources)])
    pressure = compute_pressure(stream)
    assert pressure.ready_frontier_depth == 7
    assert pressure.pending_verifications == 3
    assert pressure.integration_queue_depth == 2
    assert pressure.active_workers == 4
    assert pressure.worker_capacity == 5


def test_single_sample_median_exists_but_tail_percentiles_do_not():
    assert percentile([10_000], 50) == 10_000
    assert percentile([10_000], 95) is None
    assert percentile([10_000], 99) is None


def test_percentile_rejects_invalid_requested_percent():
    with pytest.raises(ValueError):
        percentile([1, 2], -1)
    with pytest.raises(ValueError):
        percentile([1, 2], 101)


def test_stage_distribution_retains_missing_stage_as_zero_samples():
    stream = scenario_to_stream(SCENARIO_UNKNOWN_EVIDENCE)
    distributions = {item.stage: item for item in stage_distributions(stream)}
    assert distributions["worker_execution"].samples == 0
    assert distributions["worker_execution"].p50_ns is None


def test_classifier_rejects_invalid_dominant_share():
    stream = scenario_to_stream(ALL_SCENARIOS[0])
    with pytest.raises(ValueError):
        classify_bottleneck(stream, 0)
    with pytest.raises(ValueError):
        classify_bottleneck(stream, 1.1)
