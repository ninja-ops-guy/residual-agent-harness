"""Tests for SPEC-SWARM-OTX-003 — Orchestration Tax Controller.

Traceability: docs/swarm/otx-003.md maps each OTX-R* requirement to the
tests below.
"""
from __future__ import annotations

import json
import random

import pytest

from residual.otx import (
    ControllerConfig,
    FrozenWorkloadFixture,
    NormalInverseGamma,
    ObservationLog,
    OrchestrationTaxController,
    Phase,
    PhaseTiming,
    Task,
    TOPOLOGIES,
    default_fixture,
    replay_decisions,
    simulate_execution,
    verify_replay,
)
from residual.otx import evidence as otx_evidence


def run_experiment(controller, task, rng):
    obs = controller.select_topology(task)
    timing, success, quality = simulate_execution(task, obs.selected_topology, rng)
    comparison = controller.record_outcome(obs.observation_id, timing, success, quality)
    return obs, timing, comparison


# --------------------------------------------------------------------- OTX-R1
class TestR1DecomposedTiming:
    def test_all_seven_phases_measured_separately(self):
        timing = PhaseTiming({p: float(i + 1) for i, p in enumerate(Phase.ALL)})
        assert set(timing.breakdown()) == set(Phase.ALL)
        assert timing.breakdown()[Phase.PLANNING] == 1.0
        assert timing.breakdown()[Phase.COORDINATION] == 7.0

    def test_overhead_excludes_worker_execution(self):
        timing = PhaseTiming({Phase.WORKER_EXECUTION: 10.0, Phase.PLANNING: 1.0, Phase.COORDINATION: 2.0})
        assert timing.coordination_overhead_s == 3.0
        assert timing.total_s == 13.0
        assert timing.observed_tax() == pytest.approx(0.3)

    def test_simulator_emits_per_phase_breakdown_for_swarm(self):
        rng = random.Random(7)
        task = Task("t", "synthesis", "project", value=4.0, size=6.0)
        timing, _, _ = simulate_execution(task, "swarm", rng)
        bd = timing.breakdown()
        for phase in Phase.ALL:  # swarm activates every phase
            assert bd[phase] > 0.0, phase
        pair_timing, _, _ = simulate_execution(task, "pair", rng)
        assert pair_timing.phase_seconds(Phase.PLANNING) == 0.0
        assert pair_timing.phase_seconds(Phase.VERIFICATION) > 0.0

    def test_unknown_phase_rejected(self):
        with pytest.raises(ValueError):
            PhaseTiming({"nonsense": 1.0})


# --------------------------------------------------------------------- OTX-R2
class TestR2DataDerivedTax:
    def test_tax_is_function_of_task_and_topology(self):
        c = OrchestrationTaxController()
        task = Task("t", "lookup", "atomic")
        taxes = {topo: c.orchestration_tax(task, topo) for topo in ("single", "pair", "swarm")}
        assert taxes["swarm"] > taxes["pair"] > taxes["single"]

    def test_tax_updates_from_observed_data(self):
        c = OrchestrationTaxController()
        task = Task("t", "lookup", "atomic")
        before = c.orchestration_tax(task, "single")
        obs = c.select_topology(Task("t0", "lookup", "atomic"))
        # force the observation onto "single" by direct model update path
        low = PhaseTiming({Phase.WORKER_EXECUTION: 10.0, Phase.SCHEDULING: 0.1, Phase.INTEGRATION: 0.1})
        c.model.observe("lookup", "single", low, True)
        after = c.orchestration_tax(task, "single")
        assert after != before
        assert after < before  # observed tax (0.02) pulled the estimate down

    def test_tax_not_a_fixed_constant_across_classes(self):
        c = OrchestrationTaxController()
        rng = random.Random(3)
        for i in range(6):
            run_experiment(c, Task(f"l{i}", "lookup", "atomic", size=0.5), rng)
            run_experiment(c, Task(f"s{i}", "synthesis", "project", value=4.0, size=6.0), rng)
        t_lookup = c.orchestration_tax(Task("p", "lookup", "atomic"), "swarm")
        t_synth = c.orchestration_tax(Task("p", "synthesis", "project"), "swarm")
        assert t_lookup != t_synth


# --------------------------------------------------------------------- OTX-R3
class TestR3BayesianUpdating:
    def test_nig_posterior_converges_and_shrinks_uncertainty(self):
        est = NormalInverseGamma.prior(mu=5.0, kappa=1.0, alpha=2.0, beta=1.0)
        std0 = est.mean_std
        for _ in range(20):
            est.update(1.0)
        assert est.mean == pytest.approx(1.0, abs=0.2)
        assert est.mean_std < std0

    def test_estimates_conditioned_per_task_class(self):
        c = OrchestrationTaxController()
        high = PhaseTiming({Phase.WORKER_EXECUTION: 1.0, Phase.COORDINATION: 4.0})
        low = PhaseTiming({Phase.WORKER_EXECUTION: 4.0, Phase.COORDINATION: 1.0})
        for _ in range(5):
            c.model.observe("classA", "pair", high, True)
            c.model.observe("classB", "pair", low, True)
        assert c.model.predicted_tax("classA", "pair") > c.model.predicted_tax("classB", "pair")
        assert c.model.sample_count("classA", "pair") == 5
        assert c.model.sample_count("classB", "pair") == 5

    def test_uncertainty_reported_and_decreases_with_samples(self):
        c = OrchestrationTaxController()
        unc0 = c.model.tax_uncertainty("lookup", "single")
        timing = PhaseTiming({Phase.WORKER_EXECUTION: 2.0, Phase.SCHEDULING: 0.2})
        for _ in range(4):
            c.model.observe("lookup", "single", timing, True)
        assert c.model.tax_uncertainty("lookup", "single") < unc0

    def test_reliability_beta_updates(self):
        c = OrchestrationTaxController()
        r0 = c.model.predicted_reliability("lookup", "single")
        timing = PhaseTiming({Phase.WORKER_EXECUTION: 1.0})
        for _ in range(3):
            c.model.observe("lookup", "single", timing, False)
        assert c.model.predicted_reliability("lookup", "single") < r0


# --------------------------------------------------------------------- OTX-R4
class TestR4PredictedVsObserved:
    def test_every_outcome_produces_comparison(self):
        c = OrchestrationTaxController()
        rng = random.Random(11)
        for i in range(5):
            obs, _, comparison = run_experiment(c, Task(f"t{i}", "lookup", "atomic"), rng)
            assert comparison.predicted_tax >= 0.0
            assert comparison.observed_tax >= 0.0
            assert comparison.abs_error == pytest.approx(abs(comparison.observed_tax - comparison.predicted_tax))
            stored = c.log.by_id(obs.observation_id)
            assert stored.comparison is not None
            assert stored.result is not None

    def test_prediction_improves_with_learning(self):
        c = OrchestrationTaxController()
        rng = random.Random(23)
        errors = []
        for i in range(12):
            task = Task(f"t{i}", "lookup", "composite", size=1.0)
            obs = c.select_topology(task)
            timing, success, quality = simulate_execution(task, obs.selected_topology, rng)
            errors.append(c.record_outcome(obs.observation_id, timing, success, quality).abs_error)
        early = sum(errors[:4]) / 4
        late = sum(errors[-4:]) / 4
        assert late <= early


# --------------------------------------------------------------------- OTX-R5
class TestR5DeploymentThreshold:
    def test_threshold_forces_simpler_topology(self):
        # High-tax class for swarm: tiny task.
        c = OrchestrationTaxController(ControllerConfig(deployment_tax_threshold=1.0))
        timing = PhaseTiming({  # teach the model that swarm tax is huge here
            Phase.PLANNING: 2.0, Phase.SCHEDULING: 1.0, Phase.CONTEXT_PACKAGING: 2.0,
            Phase.WORKER_EXECUTION: 0.5, Phase.VERIFICATION: 1.0, Phase.INTEGRATION: 1.0,
            Phase.COORDINATION: 2.0,
        })
        for _ in range(4):
            c.model.observe("micro", "swarm", timing, True)
        task = Task("m", "micro", "atomic", value=100.0, size=0.1)  # value so high utility wants swarm
        obs = c.select_topology(task)
        assert obs.selected_topology != "swarm"
        assert obs.selection_reason == "deployment_threshold"

    def test_threshold_is_configurable(self):
        loose = OrchestrationTaxController(ControllerConfig(deployment_tax_threshold=10.0))
        strict = OrchestrationTaxController(ControllerConfig(deployment_tax_threshold=0.01))
        task = Task("x", "synthesis", "project", value=4.0, size=6.0)
        assert loose.select_topology(task).selected_topology == "swarm"
        assert strict.select_topology(task).selected_topology == "single"

    def test_threshold_off_by_default_behaviour_preserved(self):
        c = OrchestrationTaxController(ControllerConfig(deployment_tax_threshold=float("inf")))
        obs = c.select_topology(Task("x", "synthesis", "project", value=4.0, size=6.0))
        assert obs.selection_reason == "max_utility"


# --------------------------------------------------------------------- OTX-R6
class TestR6MultiGranularityFixture:
    def test_fixture_spans_multiple_granularities(self):
        fixture = default_fixture()
        assert fixture.granularities() == ("atomic", "composite", "project")
        assert len(fixture.task_classes()) >= 2

    def test_fixture_is_hash_bound_and_deterministic(self):
        a, b = default_fixture(), default_fixture()
        assert a.workload_hash == b.workload_hash
        assert len(a.workload_hash) == 64

    def test_evaluation_reports_per_granularity(self):
        c = OrchestrationTaxController()
        result = c.evaluate_fixture(default_fixture())
        assert set(result["granularities"]) == {"atomic", "composite", "project"}
        for gran, metrics in result["granularities"].items():
            assert metrics["tasks"] > 0
            assert "mean_abs_tax_error" in metrics
            assert sum(metrics["decisions"].values()) == metrics["tasks"]

    def test_eval_workload_adapter_integration_point(self):
        class Rec:
            def __init__(self, i):
                self.task_id, self.task_class, self.granularity = f"r{i}", "lookup", "atomic"
        class Upstream:
            name, version, workload_hash = "up", "9.9", "abc123"
            tasks = [Rec(0), Rec(1)]
        fx = FrozenWorkloadFixture.from_eval_workload(Upstream())
        assert fx.upstream_hash == "abc123"
        assert len(fx.tasks) == 2


# --------------------------------------------------------------------- OTX-R7
class TestR7QualityAdjustedUtility:
    def test_faster_but_less_reliable_cannot_win_on_latency_alone(self):
        # single is strictly faster here, but much less reliable for synthesis.
        c = OrchestrationTaxController(ControllerConfig(deployment_tax_threshold=10.0))
        task = Task("s", "synthesis", "atomic", value=4.0, size=1.5)
        timing_fast = PhaseTiming({Phase.WORKER_EXECUTION: 0.5, Phase.SCHEDULING: 0.01, Phase.INTEGRATION: 0.01})
        timing_slow = PhaseTiming({**{p: 0.3 for p in Phase.OVERHEAD}, Phase.WORKER_EXECUTION: 2.0})
        for _ in range(6):
            c.model.observe("synthesis", "single", timing_fast, False)  # fast but wrong
            c.model.observe("synthesis", "swarm", timing_slow, True)    # slow but right
        obs = c.select_topology(task)
        single = next(cd for cd in obs.candidates if cd.topology == "single")
        swarm = next(cd for cd in obs.candidates if cd.topology == "swarm")
        assert single.predicted_total_s < swarm.predicted_total_s          # single IS faster
        assert single.predicted_utility < swarm.predicted_utility          # but loses on quality
        assert obs.selected_topology == "swarm"

    def test_utility_is_reliability_weighted(self):
        c = OrchestrationTaxController()
        task = Task("t", "lookup", "atomic", value=2.0)
        cands = {cd.topology: cd for cd in c._candidates(task)}
        for topo, cd in cands.items():
            expected = cd.predicted_reliability * task.value - c.config.latency_penalty * cd.predicted_total_s
            assert cd.predicted_utility == pytest.approx(expected)


# --------------------------------------------------------------------- OTX-R8
class TestR8ObservationEmission:
    def test_every_choice_emits_complete_observation(self):
        c = OrchestrationTaxController()
        rng = random.Random(5)
        obs, _, _ = run_experiment(c, Task("t1", "lookup", "atomic"), rng)
        assert obs.inputs["task"]["task_id"] == "t1"
        assert obs.inputs["config"]["deployment_tax_threshold"] == c.config.deployment_tax_threshold
        assert {cd.topology for cd in obs.candidates} == set(c.config.topologies)
        for cd in obs.candidates:
            assert cd.predicted_tax >= 0.0
            assert cd.predicted_utility is not None
        assert obs.selected_topology in c.config.topologies
        assert obs.result is not None and obs.result.observed_tax >= 0.0
        assert obs.model_snapshot  # estimator state at decision time

    def test_observation_log_roundtrip_jsonl(self, tmp_path):
        c = OrchestrationTaxController()
        rng = random.Random(9)
        for i in range(4):
            run_experiment(c, Task(f"t{i}", "lookup", "atomic"), rng)
        path = tmp_path / "obs.jsonl"
        c.log.write(str(path))
        loaded = ObservationLog.read(str(path))
        assert len(loaded) == 4
        assert loaded.to_jsonl() == c.log.to_jsonl()
        parsed = json.loads(loaded.to_jsonl().splitlines()[0])
        assert {"inputs", "candidates", "selected_topology", "result"} <= set(parsed)


# --------------------------------------------------------------------- Gate C
class TestReplay:
    def test_replay_reproduces_decisions_exactly(self):
        c = OrchestrationTaxController()
        rng = random.Random(42)
        classes = ["lookup", "synthesis"]
        for i in range(16):
            run_experiment(c, Task(f"t{i}", classes[i % 2], "composite", value=4.0 if i % 2 else 1.0, size=1.0 + i % 3), rng)
        result = verify_replay(c.config, list(c.log))
        assert result["exact"] is True
        assert result["matched"] == result["total"] == 16

    def test_replay_from_serialised_log(self, tmp_path):
        c = OrchestrationTaxController()
        rng = random.Random(1)
        for i in range(8):
            run_experiment(c, Task(f"t{i}", "lookup", "atomic"), rng)
        path = tmp_path / "log.jsonl"
        c.log.write(str(path))
        loaded = ObservationLog.read(str(path))
        records = replay_decisions(c.config, list(loaded))
        assert all(r["match"] for r in records)

    def test_replay_detects_tampering(self):
        c = OrchestrationTaxController()
        rng = random.Random(2)
        for i in range(4):
            run_experiment(c, Task(f"t{i}", "lookup", "atomic"), rng)
        obs = list(c.log)
        obs[2].selected_topology = "swarm" if obs[2].selected_topology != "swarm" else "single"
        result = verify_replay(c.config, obs)
        assert result["exact"] is False


# --------------------------------------------------------------------- Acceptance
class TestAcceptance:
    def test_two_task_classes_learn_distinct_preferred_topologies(self):
        fixture = default_fixture()
        c = OrchestrationTaxController()
        c.evaluate_fixture(fixture, seed=fixture.seed)
        preferred = {}
        for task_class in fixture.task_classes():
            probe = next(t for t in fixture.tasks if t.task_class == task_class)
            obs = c.select_topology(probe)
            preferred[task_class] = obs.selected_topology
        assert preferred["lookup"] == "single"
        assert preferred["synthesis"] == "swarm"
        assert len(set(preferred.values())) == 2

    def test_evidence_artifact_end_to_end(self, tmp_path):
        study = otx_evidence.run_study()
        assert study["replay"]["exact"] is True
        prefs = {k: v["preferred_topology"] for k, v in study["learned_preferences"].items()}
        assert len(set(prefs.values())) >= 2
        artifact = otx_evidence.build_artifact(study, str(tmp_path))
        assert set(artifact["identity"]) >= {"git_commit", "git_tree", "python_version"}
        assert artifact["study"]["observations"]
        path = tmp_path / "results.json"
        path.write_text(json.dumps(artifact, sort_keys=True))
        reloaded = json.loads(path.read_text())
        assert reloaded["study"]["observations_sha256"] == study["observations_sha256"]
