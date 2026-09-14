"""SPEC-SWARM-EVAL-001 tests: frozen reliability evaluation (swarm A).

Covers Gates A (every requirement tested), B (evidence artifact with exact
identity), and C (P(X), P(A), P(X|A) recomputed from retained raw records).
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from residual.core import ContractError, digest
from residual.eval import (
    CONFIGURATIONS,
    CONTROLLED_CONSTANTS,
    FrozenTask,
    FrozenWorkload,
    RunRecord,
    RunState,
    build_evidence_artifact,
    build_report,
    compute_slice_metrics,
    development_workload,
    get_config,
    plotting_inputs,
    recompute_from_records,
    report_csv_rows,
    run_study,
    write_evidence_artifact,
)
from residual.eval.__main__ import run_fixture_study
from residual.eval.configs import constants_agree
from residual.eval.workload import SCHEMA_VERSION, workload_from_json

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def workload():
    return development_workload()


@pytest.fixture(scope="module")
def records(workload):
    return run_study(workload, repeats=3)


@pytest.fixture(scope="module")
def report(workload, records):
    return build_report(workload, records)


# --- EVAL-R1: versioned FrozenWorkload with immutable hash -----------------

def test_r1_schema_version_and_hash_stable(workload):
    assert workload.schema_version == SCHEMA_VERSION
    assert workload.sha256 == workload.sha256
    rebuilt = workload_from_json(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "name": workload.name,
        "seed": workload.seed,
        "tasks": [task.payload() for task in workload.tasks],
        "sha256": workload.sha256,
    }))
    assert rebuilt.sha256 == workload.sha256


def test_r1_hash_covers_every_task_field(workload):
    task = workload.tasks[0]
    mutated = FrozenTask(task_id=task.task_id, family=task.family,
                         slice=task.slice, prompt=task.prompt + "!",
                         expected=task.expected, fault_label=task.fault_label)
    changed = FrozenWorkload(name=workload.name, seed=workload.seed,
                             tasks=(mutated,) + workload.tasks[1:])
    assert changed.sha256 != workload.sha256


def test_r1_hash_mismatch_rejected(workload):
    document = {
        "schema_version": SCHEMA_VERSION,
        "name": workload.name,
        "seed": workload.seed,
        "tasks": [task.payload() for task in workload.tasks],
        "sha256": digest("tampered"),
    }
    with pytest.raises(ContractError):
        workload_from_json(json.dumps(document))


def test_r1_duplicate_task_ids_rejected():
    task = FrozenTask(task_id="t1", family="f", slice="evaluation",
                      prompt="p", expected="e")
    with pytest.raises(ContractError):
        FrozenWorkload(name="w", seed=1, tasks=(task, task))


def test_r1_workload_is_frozen_dataclass(workload):
    with pytest.raises(Exception):
        workload.tasks[0].prompt = "mutated"  # type: ignore[misc]


# --- EVAL-R2: configurations R0-R5 -----------------------------------------

def test_r2_six_configurations_r0_to_r5():
    assert [c.config_id for c in CONFIGURATIONS] == ["R0", "R1", "R2", "R3", "R4", "R5"]
    labels = {c.config_id: c.label for c in CONFIGURATIONS}
    assert "raw" in labels["R0"]
    assert "orchestrated" in labels["R1"]
    assert "contracted" in labels["R2"]
    assert "verified" in labels["R3"]
    assert "COVD" in labels["R4"]
    assert "swarm" in labels["R5"]


def test_r2_control_layers_cumulative():
    assert CONFIGURATIONS[0].control_layers == ()
    for earlier, later in zip(CONFIGURATIONS, CONFIGURATIONS[1:]):
        assert set(earlier.control_layers) <= set(later.control_layers)


# --- EVAL-R3: constants held across ablations ------------------------------

def test_r3_constants_identical_across_configs():
    assert constants_agree()
    for config in CONFIGURATIONS:
        assert config.constants is CONTROLLED_CONSTANTS
        assert config.constants["model"]["model_id"] == "deterministic-engine-v1"
        assert config.constants["grader"]["grader_id"] == "exact-match-grader-v1"
        assert config.varied_factors == ()


def test_r3_config_hash_changes_with_layers_only():
    hashes = {c.config_id: c.sha256 for c in CONFIGURATIONS}
    assert len(set(hashes.values())) == len(CONFIGURATIONS)


# --- EVAL-R4: >=3 runs per config per slice ---------------------------------

def test_r4_at_least_three_runs_per_config_per_slice(records, workload):
    tasks = workload.slice_tasks("evaluation")
    for config in CONFIGURATIONS:
        for task in tasks:
            runs = [r for r in records
                    if r.config_id == config.config_id and r.task_id == task.task_id]
            assert len(runs) >= 3
            assert {r.repeat for r in runs} >= {0, 1, 2}


def test_r4_fewer_than_three_repeats_rejected(workload):
    with pytest.raises(ContractError):
        run_study(workload, repeats=2)


# --- EVAL-R5: X independent of A --------------------------------------------

def test_r5_correctness_and_acceptance_independent(records):
    graded = [r for r in records if r.correct is not None]
    assert graded, "fixture must produce graded runs"
    assert any(r.correct is True and not r.accepted for r in graded), \
        "correct-but-rejected runs prove X and A are scored independently"
    assert any(r.correct is False and r.accepted for r in graded), \
        "R0-style false accepts must exist to exercise X != A"


def test_r5_worker_correctness_invariant_to_control_layers(workload):
    """Holding capability constant: the same worker draw drives every config,
    so raw correctness X is identical across configs for a given (task,
    repeat); only acceptance A changes."""
    from residual.eval.runner import _worker_correct

    for config in CONFIGURATIONS:
        for task in workload.slice_tasks("evaluation"):
            for repeat in range(3):
                expected = task.fault_label is None and _worker_correct(
                    get_config("R0"), task, repeat, workload.sha256)
                assert _worker_correct(config, task, repeat, workload.sha256) == expected


# --- EVAL-R6: metric families ------------------------------------------------

def test_r6_all_metric_families_present(report):
    required = {"aer_far", "isr", "assr", "acceptance_coverage",
                "false_rejection_rate", "fcr", "throughput_runs_per_sec",
                "latency_ms_mean", "latency_ms_p50", "latency_ms_p95",
                "rework_per_run", "conflicts_total", "conflict_rate",
                "verifier_rejection_rate", "input_tokens", "output_tokens",
                "cost_usd_total", "cost_per_accepted_correct_usd"}
    assert len(report["metrics"]) == len(CONFIGURATIONS)  # one slice
    for entry in report["metrics"]:
        assert required <= set(entry)


def test_r6_metric_definitions(records):
    rows = [r for r in records if r.config_id == "R0"]
    m = compute_slice_metrics("R0", "evaluation", rows)
    n = len(rows)
    accepted = [r for r in rows if r.accepted]
    incorrect = [r for r in rows if r.correct is False]
    correct = [r for r in rows if r.correct is True]
    # R0 has no acceptance boundary.
    assert m.acceptance_coverage == 1.0
    assert m.aer_far == pytest.approx(
        sum(1 for r in accepted if r.correct is False) / len(accepted))
    assert m.isr == (sum(1 for r in incorrect if not r.accepted) / len(incorrect)
                     if incorrect else None)
    assert m.assr == pytest.approx(sum(1 for r in rows if r.correct is True
                                       and r.accepted) / n)
    assert m.false_rejection_rate == pytest.approx(
        sum(1 for r in correct if not r.accepted) / len(correct))
    fault = [r for r in rows if r.fault_label is not None]
    assert m.fcr == pytest.approx(
        sum(1 for r in fault if r.fault_caught is True) / len(fault))


def test_r6_fcr_none_without_fault_labels(records, workload):
    no_fault = [r for r in records if r.fault_label is None and r.config_id == "R3"]
    # strip fault labels by building records for tasks without them only
    tasks = [t for t in workload.slice_tasks("evaluation") if t.fault_label is None]
    rows = [r for r in no_fault if r.task_id in {t.task_id for t in tasks}]
    m = compute_slice_metrics("R3", "evaluation", rows)
    assert m.fcr is None


def test_r6_control_layers_change_outcomes(records):
    by_config = {}
    for config_id in ("R0", "R3", "R4"):
        rows = [r for r in records if r.config_id == config_id]
        by_config[config_id] = compute_slice_metrics(config_id, "evaluation", rows)
    # Verified configs suppress incorrect artifacts better than raw R0.
    assert by_config["R3"].isr > by_config["R0"].isr
    assert by_config["R3"].aer_far < by_config["R0"].aer_far
    # R4/R5 pay an orchestration tax: higher latency and cost than R0.
    assert by_config["R4"].latency_ms_mean > by_config["R0"].latency_ms_mean
    assert by_config["R4"].cost_usd_total > by_config["R0"].cost_usd_total


# --- EVAL-R7: paired run records ---------------------------------------------

def test_r7_paired_records_enable_task_level_comparison(records, workload):
    tasks = workload.slice_tasks("evaluation")
    for task in tasks:
        for repeat in range(3):
            paired = {(r.config_id) for r in records
                      if r.task_id == task.task_id and r.repeat == repeat}
            assert paired == {c.config_id for c in CONFIGURATIONS}
    # record ids unique and bound to the workload hash
    ids = [r.record_id for r in records]
    assert len(ids) == len(set(ids))
    assert all(r.workload_sha256 == workload.sha256 for r in records)


# --- EVAL-R8: failed/aborted runs retained -----------------------------------

def test_r8_failures_and_aborts_stay_in_aggregates(report, records):
    assert any(r.aborted for r in records), "fixture must contain aborted runs"
    for entry in report["metrics"]:
        states = entry["state_counts"]
        assert set(states) == {"PASS", "FAIL", "REJECTED", "UNKNOWN"}
        assert sum(states.values()) == entry["runs"]
        rows = [r for r in records if r.config_id == entry["config_id"]]
        assert states["UNKNOWN"] == sum(1 for r in rows if r.aborted)
        # denominators include everything retained
        assert entry["runs"] == len(rows)
        assert entry["missing_grades"] == states["UNKNOWN"]


def test_r8_states_distinct_and_typed():
    states = {s.value for s in RunState}
    assert states == {"PASS", "FAIL", "REJECTED", "UNKNOWN"}
    assert len(states) == 4


# --- EVAL-R9: paper-ready outputs ---------------------------------------------

def test_r9_csv_rows_parseable(report):
    csv_text = report_csv_rows(report)
    lines = csv_text.strip().splitlines()
    assert len(lines) == 1 + len(CONFIGURATIONS)
    header = lines[0].split(",")
    assert "aer_far" in header and "assr" in header and "P_X_given_A" in header
    import csv as csv_module
    import io

    rows = list(csv_module.DictReader(io.StringIO(csv_text)))
    assert {row["config_id"] for row in rows} == {"R0", "R1", "R2", "R3", "R4", "R5"}


def test_r9_plotting_inputs_bound_to_report(report):
    inputs = plotting_inputs(report)
    assert inputs["source_report_sha256"] == report["report_sha256"]
    assert len(inputs["reliability_vs_cost"]) == len(CONFIGURATIONS)
    assert len(inputs["reliability_vs_latency"]) == len(CONFIGURATIONS)
    for point in inputs["reliability_vs_cost"]:
        assert set(point) == {"config_id", "assr", "cost_usd_total"}


def test_r9_report_hash_bound_and_deterministic(workload):
    first = build_report(workload, run_study(workload, repeats=3))
    second = build_report(workload, run_study(workload, repeats=3))
    assert first["report_sha256"] == second["report_sha256"]
    assert first["workload"]["sha256"] == workload.sha256
    json.dumps(first, allow_nan=False)


# --- EVAL-R10: CI fixture labeled separately from live -------------------------

def test_r10_fixture_labeled_development(report, records):
    assert report["evidence_level"] == "development_fixture"
    assert all(r.evidence_level == "development_fixture" for r in records)


def test_r10_live_runs_separately_labeled(workload):
    live_records = run_study(workload, repeats=3, evidence_level="live_model")
    assert all(r.evidence_level == "live_model" for r in live_records)
    live_report = build_report(workload, live_records, evidence_level="live_model")
    assert live_report["evidence_level"] == "live_model"


def test_r10_invalid_evidence_level_rejected(workload):
    with pytest.raises(ContractError):
        run_study(workload, repeats=3, evidence_level="unlabeled")


# --- Gate B: evidence artifact -------------------------------------------------

def test_gate_b_evidence_artifact_identity_and_contents(report, tmp_path):
    artifact = build_evidence_artifact(report, root=ROOT)
    assert artifact["schema_version"] == "residual.eval-evidence.v1"
    assert artifact["runtime"]["python"]
    src = artifact["source"]
    assert src.get("commit") or src.get("eval_source_digests")
    if src.get("commit"):
        assert len(src["commit"]) == 40
        assert len(src["tree"]) == 40
    assert artifact["frozen_inputs"]["workload"]["sha256"] == report["workload"]["sha256"]
    assert len(artifact["raw_observations"]) == len(report["records"])
    assert artifact["results"]["report_sha256"] == report["report_sha256"]
    path = write_evidence_artifact(artifact, tmp_path / "evidence.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["evidence_sha256"] == artifact["evidence_sha256"]


# --- Gate C: reproduction path ---------------------------------------------------

def test_gate_c_recompute_probabilities_from_raw_records(report, records):
    recomputed = recompute_from_records([r.payload() for r in records])
    assert recomputed == report["recomputed_probabilities"]
    for config_id, probs in recomputed.items():
        rows = [r for r in records if r.config_id == config_id]
        n = len(rows)
        assert probs["P_X"] == pytest.approx(
            sum(1 for r in rows if r.correct is True) / n)
        assert probs["P_A"] == pytest.approx(
            sum(1 for r in rows if r.accepted) / n)
        accepted = sum(1 for r in rows if r.accepted)
        expected = (sum(1 for r in rows if r.correct is True and r.accepted) / accepted
                    if accepted else math.nan)
        assert probs["P_X_given_A"] == pytest.approx(expected, nan_ok=True)


def test_gate_c_aggregate_metrics_match_recomputed(report):
    for entry in report["metrics"]:
        probs = report["recomputed_probabilities"][entry["config_id"]]
        assert entry["P_X"] == pytest.approx(probs["P_X"])
        assert entry["P_A"] == pytest.approx(probs["P_A"])


def test_gate_c_unknowns_stay_in_recompute_denominators(records):
    recomputed = recompute_from_records(records)
    for config_id, probs in recomputed.items():
        rows = [r for r in records if r.config_id == config_id]
        assert probs["n"] == len(rows)  # aborted included


# --- Acceptance: end-to-end fixture study ----------------------------------------

def test_acceptance_end_to_end_fixture_study(tmp_path):
    artifact = run_fixture_study(tmp_path, repeats=3, root=ROOT)
    assert artifact["evidence_level"] == "development_fixture"
    configs = {c["config_id"] for c in artifact["frozen_inputs"]["configurations"]}
    assert configs == {"R0", "R1", "R2", "R3", "R4", "R5"}
    for suffix in ("fixture-study.json", "fixture-study.csv",
                   "fixture-study-plot-inputs.json", "fixture-study-evidence.json"):
        assert (tmp_path / suffix).exists()
    report = json.loads((tmp_path / "fixture-study.json").read_text(encoding="utf-8"))
    assert report["report_sha256"] == artifact["results"]["report_sha256"]


def test_acceptance_cli_runs_end_to_end(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "residual.eval", "--out", str(tmp_path)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["evidence_level"] == "development_fixture"
    assert summary["configurations"] == ["R0", "R1", "R2", "R3", "R4", "R5"]
