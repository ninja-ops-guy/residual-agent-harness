from residual.orchestrator.flow_benchmark import (
    BENCHMARK_SCHEMA,
    benchmark_cases,
    run_flow_benchmark,
)


def test_benchmark_has_distinct_single_reviewed_swarm_cases():
    ids = {case.case_id for case in benchmark_cases()}
    assert {"single", "reviewed", "swarm"} <= ids


def test_benchmark_report_separates_measured_and_modeled_claims():
    report = run_flow_benchmark(iterations=5)
    assert report["schema_version"] == BENCHMARK_SCHEMA
    assert report["evidence_level"] == "development_fixture"
    assert report["simulation"] is True
    assert report["summary"]["live_execution_improvement_proven"] is False
    assert "counterfactual" in report["cases"][0]
    assert "Real timings" in report["summary"]["claim_boundary"]


def test_flow_hash_is_stable_across_benchmark_recompiles():
    report = run_flow_benchmark(iterations=5)
    assert report["summary"]["all_flow_hashes_stable"] is True
    assert all(case["flow_hash_stable"] for case in report["cases"])


def test_staged_flow_reduces_modeled_model_call_surface():
    report = run_flow_benchmark(iterations=5)
    for case in report["cases"]:
        assert case["model_stage_count"] < case["counterfactual"]["model_call_count"]
        assert case["modeled_model_call_reduction_pct"] >= 25.0


def test_staged_flow_reduces_modeled_token_ceiling():
    report = run_flow_benchmark(iterations=5)
    for case in report["cases"]:
        assert case["declared_model_token_ceiling"] < case["counterfactual"]["model_token_ceiling"]
        assert case["modeled_token_ceiling_reduction_pct"] >= 20.0


def test_stage_scoping_reduces_tool_capability_surface():
    report = run_flow_benchmark(iterations=5)
    for case in report["cases"]:
        surface = case["capability_surface"]
        assert surface["granted_tool_stage_pairs"] < surface["unrestricted_tool_stage_pairs"]
        assert surface["reduction_pct"] > 0


def test_benchmark_thresholds_signal_architecture_efficiency_without_live_claim():
    report = run_flow_benchmark(iterations=5)
    assert report["threshold_results"]["model_calls"] is True
    assert report["threshold_results"]["token_ceiling"] is True
    assert report["threshold_results"]["determinism"] is True
    # Timing is deliberately not asserted here: CI hardware variance belongs in the
    # benchmark report, not in a unit-test flake.
