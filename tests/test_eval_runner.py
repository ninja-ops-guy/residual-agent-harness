"""Runner, ablations, fault injection, and report serialization tests."""
import json

import pytest

from residual.eval import (
    ABLATIONS,
    EvaluationReport,
    EvaluationRunner,
    FaultInjector,
    FrozenWorkload,
)
from residual.eval.faults import FaultSpec, standard_faults
from residual.eval.runner import (
    DEFAULT_CONFIGURATIONS,
    DynamicSwarmBackend,
    FixedSwarmBackend,
    RunConfiguration,
    SingleAgentBackend,
)


@pytest.fixture()
def workload():
    return FrozenWorkload.standard(cases=6)


def test_three_configurations_present():
    kinds = {c.backend_kind for c in DEFAULT_CONFIGURATIONS}
    assert kinds == {"single_agent", "fixed_swarm", "dynamic_swarm"}


def test_runner_enforces_t10_r1_minimum_repeats(workload):
    runner = EvaluationRunner(workload, ABLATIONS)
    with pytest.raises(ValueError, match="n >= 10"):
        runner.run_configuration(DEFAULT_CONFIGURATIONS[0], repeats=5)


def test_runner_deterministic_with_seed(workload):
    runner = EvaluationRunner(workload, ABLATIONS)
    cfg = DEFAULT_CONFIGURATIONS[0]
    r1 = runner.run_configuration(cfg, repeats=10)
    r2 = runner.run_configuration(cfg, repeats=10)
    assert r1["runs"] == r2["runs"]
    assert len(r1["runs"]) == 10 * len(workload.tasks)


def test_runner_unknown_ablation_rejected(workload):
    runner = EvaluationRunner(workload, ABLATIONS)
    cfg = RunConfiguration(name="x", backend_kind="single_agent", ablation="nope")
    with pytest.raises(ValueError, match="unknown ablation"):
        runner.run_configuration(cfg, repeats=10)


def test_fault_injection_deterministic_and_recorded():
    injector = FaultInjector([FaultSpec("bad_config", probability=1.0)], seed=9)
    f1 = injector.inject("t-1", 0)
    f2 = injector.inject("t-1", 0)
    assert f1 is not None and f1.kind == "bad_config"
    assert (f1.kind, f1.detail) == (f2.kind, f2.detail)


def test_fault_injection_zero_probability():
    injector = FaultInjector(standard_faults(0.0), seed=9)
    assert injector.inject("t-1", 0) is None


def test_fault_runs_flagged_in_results(workload):
    injector = FaultInjector([FaultSpec("timeout", probability=1.0)], seed=3)
    runner = EvaluationRunner(workload, ABLATIONS, injector)
    res = runner.run_configuration(DEFAULT_CONFIGURATIONS[0], repeats=10)
    assert all(r["fault"] == "timeout" for r in res["runs"])


def test_backends_constructible_and_named():
    assert SingleAgentBackend().name == "single_agent"
    assert FixedSwarmBackend(size=4).name == "fixed_swarm_4"
    assert DynamicSwarmBackend(min_size=1, max_size=8).name == "dynamic_swarm"
    with pytest.raises(ValueError):
        FixedSwarmBackend(size=0)
    with pytest.raises(ValueError):
        DynamicSwarmBackend(min_size=4, max_size=2)


def test_report_structure_and_raw_data(workload):
    runner = EvaluationRunner(workload, ABLATIONS)
    results = [runner.run_configuration(c, repeats=10) for c in DEFAULT_CONFIGURATIONS]
    report = EvaluationReport(workload, results)
    summary = report.summarize()

    assert summary["schema_version"] == "residual.eval.report.v1"
    assert summary["workload"]["manifest_hash"] == workload.manifest_hash
    assert len(summary["configurations"]) == 3
    for cfg in summary["configurations"]:
        for metric in ("elapsed_ms", "tokens_used", "success"):
            m = cfg["metrics"][metric]
            assert {"n", "mean", "median", "stdev", "min", "max"} <= set(m)
    # baseline (single_agent) vs both swarm configs, two metrics each
    assert len(summary["comparisons_vs_baseline"]) == 4
    for comp in summary["comparisons_vs_baseline"]:
        assert comp["config_a"] == "single_agent"
        assert 0.0 <= comp["p_value"] <= 1.0
    # T10-R3: raw data preserved
    total_raw = sum(len(v) for v in summary["raw_runs"].values())
    assert total_raw == 3 * 10 * len(workload.tasks)
    # JSON round trip
    parsed = EvaluationReport.from_json(report.to_json())
    assert parsed["workload"]["manifest_hash"] == workload.manifest_hash
    json.dumps(summary)  # fully serializable


def test_report_rejects_tampered_workload(workload):
    runner = EvaluationRunner(workload, ABLATIONS)
    results = [runner.run_configuration(DEFAULT_CONFIGURATIONS[0], repeats=10)]
    data = workload.to_dict()
    data["tasks"][0]["prompt"] = "tampered"
    with pytest.raises(ValueError):
        EvaluationReport(FrozenWorkload.from_dict(data), results)


def test_ablation_registry_complete():
    assert set(ABLATIONS) == {"full", "no_cache", "no_brakes", "no_escalation", "no_swarm_memory"}
    assert not ABLATIONS["full"].disabled_features
    assert ABLATIONS["no_cache"].disables("cache")
    assert ABLATIONS["no_swarm_memory"].disables("cache")


def test_no_cache_ablation_eliminates_cache_hits(workload):
    runner = EvaluationRunner(workload, ABLATIONS)
    cfg = RunConfiguration(name="nc", backend_kind="single_agent", ablation="no_cache")
    res = runner.run_configuration(cfg, repeats=10)
    assert not any(r["cache_hit"] for r in res["runs"])
