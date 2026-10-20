from dataclasses import replace
import json

import pytest

from residual.prototypes.inference_economics.bundle import (
    BUNDLE_SCHEMA,
    NON_CLAIMS,
    build_bundle,
    bundle_to_json,
)
from residual.prototypes.inference_economics.events import Event, EventStream
from residual.prototypes.inference_economics.fixtures import scenario_to_stream
from residual.prototypes.inference_economics.scenarios import ALL_SCENARIOS


SOURCE_COMMIT = "candidate-commit"
SOURCE_TREE = "candidate-tree"
TEST_RESULTS = {
    "command": "python -m pytest residual/prototypes/inference_economics/tests -q",
    "passed": 123,
    "failed": 0,
    "status": "PASS",
}


def streams():
    return {
        scenario.name: scenario_to_stream(
            scenario,
            source_commit=SOURCE_COMMIT,
            source_tree=SOURCE_TREE,
        )
        for scenario in ALL_SCENARIOS
    }


def bundle():
    return build_bundle(
        list(ALL_SCENARIOS),
        streams(),
        SOURCE_COMMIT,
        SOURCE_TREE,
        test_results=TEST_RESULTS,
        config={"classifier_dominant_share": 0.5},
    )


def test_bundle_contains_required_contract_sections():
    value = bundle()
    assert value.schema == BUNDLE_SCHEMA
    assert value.source_commit == SOURCE_COMMIT
    assert value.source_tree == SOURCE_TREE
    assert set(value.scenario_manifest) == {scenario.name for scenario in ALL_SCENARIOS}
    assert set(value.normative_streams) == set(value.scenario_manifest)
    assert set(value.oracle_results) == set(value.scenario_manifest)
    assert set(value.prototype_results) == set(value.scenario_manifest)
    assert set(value.replay_results) == set(value.scenario_manifest)
    assert set(value.policy_results) == {"pressure", "cache", "escalation", "routing"}
    assert value.test_results == TEST_RESULTS
    assert value.non_claims == NON_CLAIMS


def test_bundle_retains_actual_normative_streams_not_only_hashes():
    value = bundle()
    first = value.normative_streams[ALL_SCENARIOS[0].name][0]
    assert first["seq"] == 0
    assert first["observation"]["source_commit"] == SOURCE_COMMIT
    assert first["observation"]["source_tree"] == SOURCE_TREE
    assert "resources" in first["observation"]


def test_bundle_oracle_and_primary_classifier_match_frozen_expectation():
    value = bundle()
    for scenario in ALL_SCENARIOS:
        expected = scenario.expected_bottleneck.value
        assert value.oracle_results[scenario.name]["bottleneck"] == expected
        assert value.prototype_results[scenario.name]["bottleneck"] == expected


def test_bundle_retains_queue_oracle_and_otx_inputs():
    value = bundle()
    verifier = value.oracle_results["verifier_bound"]
    assert verifier["queue_transitions"]["verification"][0]["depth"] == 3
    assert "worker_execution" in verifier["otx_inputs_ns"]


def test_bundle_retains_full_replay_hashes():
    value = bundle()
    for result in value.replay_results.values():
        assert result["replay_ok"] is True
        assert len(result["stream_hash"]) == 64
        assert len(result["metrics_hash"]) == 64


def test_bundle_hash_is_deterministic_across_creation_times():
    assert bundle().bundle_hash == bundle().bundle_hash


def test_bundle_json_is_strict_and_contains_no_nan_tokens():
    payload = bundle_to_json(bundle())
    decoded = json.loads(payload)
    assert decoded["bundle_hash"] == bundle().bundle_hash
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_bundle_rejects_missing_test_results():
    with pytest.raises(ValueError, match="test_results"):
        build_bundle(list(ALL_SCENARIOS), streams(), SOURCE_COMMIT, SOURCE_TREE, test_results={})


def test_bundle_rejects_scenario_stream_manifest_mismatch():
    values = streams()
    values.pop(ALL_SCENARIOS[0].name)
    with pytest.raises(ValueError, match="exactly match"):
        build_bundle(list(ALL_SCENARIOS), values, SOURCE_COMMIT, SOURCE_TREE, test_results=TEST_RESULTS)


def test_bundle_rejects_stream_with_stale_source_identity():
    values = streams()
    name = ALL_SCENARIOS[0].name
    original = values[name]
    events = list(original)
    events[0] = Event(events[0].seq, replace(events[0].observation, source_commit="stale"))
    values[name] = EventStream(events)
    with pytest.raises(ValueError, match="source identity"):
        build_bundle(list(ALL_SCENARIOS), values, SOURCE_COMMIT, SOURCE_TREE, test_results=TEST_RESULTS)
