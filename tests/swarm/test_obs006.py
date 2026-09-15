"""Deterministic fixture tests for SPEC-SWARM-OBS-006 (OBS-R1..R8).

Every metric family and every aggregation invariant is exercised against the
frozen fixture in residual.telemetry.fixtures. Gate C: identical inputs must
produce identical report hashes, and a fresh fixture run must rebuild all
paper-facing metrics from observations alone.
"""
from __future__ import annotations

import json

import pytest

from residual.telemetry import (
    ALL_KINDS,
    ALL_PHASES,
    FIXTURE_ID,
    EvidenceError,
    LabelCardinalityError,
    LabelSanitizer,
    TelemetryCollector,
    build_fixture_observations,
    build_reliability_report,
    build_telemetry_registry,
    render_telemetry_prometheus,
)
from residual.telemetry.schema import (
    OBSERVATION_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    hash_observations,
)

P = "residual_obs"


@pytest.fixture()
def observations():
    return build_fixture_observations()


@pytest.fixture()
def collector(observations):
    c = TelemetryCollector()
    for obs in observations:
        c.ingest(obs)
    return c


@pytest.fixture()
def report(collector):
    return build_reliability_report(
        collector.observations, experiment_id=FIXTURE_ID,
        source_identity={"commit": "fixture-commit"})


# --------------------------------------------------------------------------
# OBS-R1: metric families for execution, acceptance, rejection, verification,
# integration, conflicts, retries, resource consumption, orchestration timing.
# --------------------------------------------------------------------------

def test_registry_defines_all_metric_families():
    reg = build_telemetry_registry()
    for name in (
        f"{P}_executions_total", f"{P}_acceptances_total",
        f"{P}_rejections_total", f"{P}_verifications_total",
        f"{P}_verification_seconds", f"{P}_integrations_total",
        f"{P}_conflicts_total", f"{P}_retries_total",
        f"{P}_resource_units_total", f"{P}_phase_seconds",
    ):
        assert name in reg.metrics, f"missing family {name}"


def test_execution_family_counts(collector):
    samples = collector.registry[f"{P}_executions_total"].samples()
    assert samples[("code", "pass")] == 2.0
    assert samples[("analysis", "fail")] == 1.0
    assert sum(samples.values()) == 3.0


def test_acceptance_family_counts(collector):
    samples = collector.registry[f"{P}_acceptances_total"].samples()
    assert samples[("code",)] == 2.0


def test_rejection_family_counts(collector):
    samples = collector.registry[f"{P}_rejections_total"].samples()
    assert samples[("analysis", "verification")] == 1.0


def test_verification_family_counts_and_histogram(collector):
    samples = collector.registry[f"{P}_verifications_total"].samples()
    assert samples[("code", "pass")] == 2.0
    assert samples[("analysis", "fail")] == 1.0
    hist = collector.registry[f"{P}_verification_seconds"].samples()
    assert hist[("code",)]["count"] == 2
    assert hist[("code",)]["sum"] == pytest.approx(0.5)


def test_integration_family_counts(collector):
    samples = collector.registry[f"{P}_integrations_total"].samples()
    assert samples[("integrated",)] == 1.0
    assert samples[("conflicted",)] == 1.0


def test_conflicts_family_counts(collector):
    samples = collector.registry[f"{P}_conflicts_total"].samples()
    assert samples[("write_write",)] == 1.0


def test_retries_family_counts(collector):
    samples = collector.registry[f"{P}_retries_total"].samples()
    assert samples[("analysis",)] == 1.0


def test_resource_family_accumulates_amounts(collector):
    samples = collector.registry[f"{P}_resource_units_total"].samples()
    assert samples[("tokens_input",)] == 810.0
    assert samples[("tokens_output",)] == 210.0
    assert samples[("cpu_seconds",)] == pytest.approx(3.5)


def test_orchestration_timing_family_one_series_per_phase(collector):
    hist = collector.registry[f"{P}_phase_seconds"].samples()
    for phase in ALL_PHASES:
        assert hist[(phase,)]["count"] == 1
    assert hist[("worker_runtime",)]["sum"] == pytest.approx(4.5)


def test_fixture_covers_every_observation_kind(observations):
    assert {o["kind"] for o in observations} == set(ALL_KINDS)


# --------------------------------------------------------------------------
# OBS-R2: Prometheus-compatible export, not authoritative state.
# --------------------------------------------------------------------------

def test_prometheus_export_format(collector):
    text = render_telemetry_prometheus(collector)
    assert f"# TYPE {P}_executions_total counter" in text
    assert f"# TYPE {P}_phase_seconds histogram" in text
    assert f'{P}_executions_total{{task_class="code",outcome="pass"}} 2.0' in text
    # histogram bucket + sum/count lines
    assert f'{P}_phase_seconds_bucket{{phase="planning",le="+Inf"}} 1' in text
    assert f'{P}_phase_seconds_count{{phase="verification"}} 1' in text


def test_prometheus_export_is_not_authoritative():
    from residual.telemetry import exporter
    assert exporter.AUTHORITATIVE is False


def test_export_is_deterministic(collector):
    assert render_telemetry_prometheus(collector) == render_telemetry_prometheus(collector)


# --------------------------------------------------------------------------
# OBS-R3: bounded label cardinality; no task/content IDs; overflow bucket.
# --------------------------------------------------------------------------

def test_forbidden_label_keys_rejected():
    san = LabelSanitizer()
    for key in ("task_id", "content_id", "prompt", "worker_id"):
        with pytest.raises(LabelCardinalityError):
            san.sanitize({key: "abc-123"})


def test_allowlist_values_pass_through():
    san = LabelSanitizer()
    assert san.sanitize({"task_class": "code"}) == {"task_class": "code"}


def test_non_allowlist_values_fold_into_overflow():
    san = LabelSanitizer()
    out = san.sanitize({"task_class": "some-unique-task-slug-987"})
    assert out == {"task_class": "__other__"}
    assert san.overflow_counts()["task_class"] == 1


def test_cardinality_bounded_under_adversarial_values():
    san = LabelSanitizer()
    for i in range(500):
        san.sanitize({"task_class": f"unique-class-{i}"})
    distinct = {san.sanitize({"task_class": f"unique-class-{i}"})["task_class"]
                for i in range(500)}
    assert "__other__" in distinct
    # allowlist (5) + overflow bucket == hard upper bound
    assert len(distinct) <= 6


def test_no_raw_ids_in_fixture_labels(collector):
    text = render_telemetry_prometheus(collector)
    for forbidden in ("task_id", "content_id", "prompt", "worker_id", "run_id"):
        assert forbidden not in text


# --------------------------------------------------------------------------
# OBS-R4: reports recompute from raw observations and reject bad evidence.
# --------------------------------------------------------------------------

def test_report_recomputes_acceptance_from_observations(report):
    agg = report["report"]["aggregates"]["acceptance"]["value"]
    assert agg["accepted"] == 2 and agg["rejected"] == 1
    assert agg["acceptance_rate"] == pytest.approx(2 / 3)
    assert agg["rejection_rate"] == pytest.approx(1 / 3)


def test_report_recomputes_correctness_independently(report):
    corr = report["report"]["aggregates"]["correctness"]["value"]
    # 5 labeled observations (3 executions + 2 acceptances); 3 correct.
    assert corr["labeled"] == 5 and corr["correct"] == 3
    assert corr["p_x"] == pytest.approx(3 / 5)
    assert corr["p_x_given_acceptance"] == pytest.approx(1 / 2)


def test_report_rejects_corrupt_observation_missing_field():
    bad = build_fixture_observations() + [
        {"kind": "execution", "schema_version": OBSERVATION_SCHEMA_VERSION,
         "task_class": "code"}]  # missing outcome/worker_seconds
    with pytest.raises(EvidenceError):
        build_reliability_report(bad)


def test_report_rejects_non_mapping_observation():
    with pytest.raises(EvidenceError):
        build_reliability_report(["not-a-dict"])


def test_report_rejects_wrong_schema_version():
    bad = build_fixture_observations()
    bad[0] = dict(bad[0], schema_version="obs006.observation.v999")
    with pytest.raises(EvidenceError):
        build_reliability_report(bad)


def test_report_rejects_unknown_kind_and_bad_phase():
    with pytest.raises(EvidenceError):
        build_reliability_report([{"kind": "mystery"}])
    bad = build_fixture_observations() + [
        {"kind": "orchestration_timing",
         "schema_version": OBSERVATION_SCHEMA_VERSION,
         "phase": "tea_break", "seconds": 1.0}]
    with pytest.raises(EvidenceError):
        build_reliability_report(bad)


def test_report_rejects_empty_observation_set():
    with pytest.raises(EvidenceError):
        build_reliability_report([])


def test_ingest_rejects_corrupt_observation_before_recording():
    c = TelemetryCollector()
    with pytest.raises(EvidenceError):
        c.ingest({"kind": "acceptance"})  # missing schema_version/task_class
    assert c.observations == []


# --------------------------------------------------------------------------
# OBS-R5: separate timings per orchestration phase.
# --------------------------------------------------------------------------

def test_report_exposes_separate_phase_timings(report):
    phases = report["report"]["aggregates"]["orchestration_timing"]["phases"]
    assert set(phases) == set(ALL_PHASES)
    assert phases["planning"]["total_seconds"] == pytest.approx(0.10)
    assert phases["dispatch"]["total_seconds"] == pytest.approx(0.02)
    assert phases["context_packaging"]["total_seconds"] == pytest.approx(0.15)
    assert phases["worker_runtime"]["total_seconds"] == pytest.approx(4.50)
    assert phases["verification"]["total_seconds"] == pytest.approx(0.60)
    assert phases["integration"]["total_seconds"] == pytest.approx(0.13)


def test_phase_timing_missing_is_counted_not_hidden():
    obs = [o for o in build_fixture_observations()
           if not (o["kind"] == "orchestration_timing" and o["phase"] == "dispatch")]
    rep = build_reliability_report(obs)
    ev = rep["report"]["aggregates"]["orchestration_timing"]["evidence"]
    assert ev["phases_missing"] == 1
    assert ev["completeness"] == pytest.approx(5 / 6)


# --------------------------------------------------------------------------
# OBS-R6: evidence completeness + missing-data counts beside every aggregate.
# --------------------------------------------------------------------------

def test_every_aggregate_carries_evidence_block(report):
    for name, agg in report["report"]["aggregates"].items():
        assert "evidence" in agg, f"aggregate {name} lacks evidence block"


def test_missing_field_counts_are_reported(report):
    # fixture: 1 execution missing token fields, 1 verification missing
    # verifier_identity, 1 integration missing strategy.
    ev = report["report"]["evidence_completeness"]
    assert ev["observations_with_missing_fields"] == 3
    assert ev["complete_observations"] == len(build_fixture_observations()) - 3
    assert ev["by_kind"]["execution"]["missing"] == 1
    assert ev["by_kind"]["verification"]["missing"] == 1
    assert ev["by_kind"]["integration"]["missing"] == 1
    assert ev["missing_data_counts"]["observations"] == 3


def test_completeness_ratio_bounds(report):
    for name, agg in report["report"]["aggregates"].items():
        c = agg["evidence"]["completeness"]
        assert 0.0 <= c <= 1.0, name


# --------------------------------------------------------------------------
# OBS-R7: schema version + hash on exported reports.
# --------------------------------------------------------------------------

def test_report_has_schema_version_and_hash(report):
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert isinstance(report["report_hash"], str) and len(report["report_hash"]) == 64


def test_report_hash_covers_report_body(report):
    from residual.telemetry.schema import hash_object
    assert report["report_hash"] == hash_object(report["report"])


# --------------------------------------------------------------------------
# OBS-R8 + Gate C: deterministic fixtures, aggregation invariants,
# rebuild-from-observations-alone, identical hash twice.
# --------------------------------------------------------------------------

def test_fixture_is_deterministic():
    a, b = build_fixture_observations(), build_fixture_observations()
    assert a == b
    assert hash_observations(a) == hash_observations(b)


def test_identical_inputs_produce_identical_report_hash_twice():
    identity = {"commit": "fixture-commit"}
    r1 = build_reliability_report(build_fixture_observations(),
                                  experiment_id=FIXTURE_ID,
                                  source_identity=identity)
    r2 = build_reliability_report(build_fixture_observations(),
                                  experiment_id=FIXTURE_ID,
                                  source_identity=identity)
    assert r1["report_hash"] == r2["report_hash"]
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_report_hash_is_observation_order_independent():
    identity = {"commit": "fixture-commit"}
    obs = build_fixture_observations()
    r1 = build_reliability_report(obs, experiment_id=FIXTURE_ID,
                                  source_identity=identity)
    r2 = build_reliability_report(list(reversed(obs)), experiment_id=FIXTURE_ID,
                                  source_identity=identity)
    assert r1["report_hash"] == r2["report_hash"]


def test_changing_an_observation_changes_report_hash():
    identity = {"commit": "fixture-commit"}
    obs = build_fixture_observations()
    r1 = build_reliability_report(obs, experiment_id=FIXTURE_ID,
                                  source_identity=identity)
    obs[0] = dict(obs[0], worker_seconds=9.99)
    r2 = build_reliability_report(obs, experiment_id=FIXTURE_ID,
                                  source_identity=identity)
    assert r1["report_hash"] != r2["report_hash"]


def test_fresh_fixture_rebuilds_paper_metrics_from_observations_alone():
    """Acceptance: a fresh fixture run rebuilds all paper-facing metrics from
    observations alone and produces the same report hash twice."""
    identity = {"commit": "fixture-commit"}

    def paper_metrics(observations):
        rep = build_reliability_report(observations, experiment_id=FIXTURE_ID,
                                       source_identity=identity)
        agg = rep["report"]["aggregates"]
        return rep["report_hash"], {
            "P(A)": agg["acceptance"]["value"]["acceptance_rate"],
            "P(X)": agg["correctness"]["value"]["p_x"],
            "P(X|A)": agg["correctness"]["value"]["p_x_given_acceptance"],
            "verifier_rejections": agg["rejection"]["value"]["by_reason"].get("verification", 0),
            "conflicts": agg["conflicts"]["value"]["total"],
            "retries": agg["retries"]["value"]["total"],
            "tokens_input": agg["resource_consumption"]["value"]["totals"]["tokens_input"],
            "worker_runtime_seconds":
                agg["orchestration_timing"]["phases"]["worker_runtime"]["total_seconds"],
        }

    hash1, metrics1 = paper_metrics(build_fixture_observations())
    hash2, metrics2 = paper_metrics(build_fixture_observations())
    assert hash1 == hash2
    assert metrics1 == metrics2
    assert metrics1["P(A)"] == pytest.approx(2 / 3)
    assert metrics1["P(X)"] == pytest.approx(3 / 5)
    assert metrics1["P(X|A)"] == pytest.approx(1 / 2)
    assert metrics1["verifier_rejections"] == 1
    assert metrics1["conflicts"] == 1 and metrics1["retries"] == 1
    assert metrics1["tokens_input"] == 810
    assert metrics1["worker_runtime_seconds"] == pytest.approx(4.5)


def test_aggregation_invariant_counts_match_raw_observations(collector):
    """Invariant: every family aggregate equals a direct recount of raw obs."""
    obs = collector.observations
    rep = build_reliability_report(obs, experiment_id=FIXTURE_ID,
                                   source_identity={"commit": "fixture-commit"})
    agg = rep["report"]["aggregates"]
    for kind, family in (
        ("execution", "execution"), ("acceptance", "acceptance"),
        ("rejection", "rejection"), ("verification", "verification"),
        ("integration", "integration"), ("conflict", "conflicts"),
        ("retry", "retries"),
    ):
        raw = sum(1 for o in obs if o["kind"] == kind)
        value = agg[family]["value"]
        reported = value.get("total", value.get("accepted"))
        assert reported == raw, f"{family}: {reported} != raw {raw}"
    # metric registry counts match raw counts too (derived view consistency)
    exec_samples = collector.registry[f"{P}_executions_total"].samples()
    assert sum(exec_samples.values()) == sum(
        1 for o in obs if o["kind"] == "execution")


def test_report_preserves_failures_in_denominator(report):
    """Failed executions stay in the denominator (shared rule 5)."""
    agg = report["report"]["aggregates"]["execution"]["value"]
    assert agg["total"] == 3
    assert agg["by_outcome"]["fail"] == 1


# --------------------------------------------------------------------------
# OBS-R4 hardening: numeric fields must be real, finite numbers — NaN/inf
# and bool values are rejected (fail closed, no coercion), and canonical
# JSON can never emit non-finite floats.
# --------------------------------------------------------------------------

from residual.telemetry.schema import canonical_json, validate_observation


def _resource_obs(amount):
    return {"kind": "resource", "schema_version": OBSERVATION_SCHEMA_VERSION,
            "resource": "cpu_seconds", "amount": amount}


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numeric_fields_rejected(bad):
    with pytest.raises(EvidenceError):
        validate_observation(_resource_obs(bad))
    with pytest.raises(EvidenceError):
        validate_observation({
            "kind": "execution", "schema_version": OBSERVATION_SCHEMA_VERSION,
            "task_class": "code", "outcome": "pass", "worker_seconds": bad})
    with pytest.raises(EvidenceError):
        validate_observation({
            "kind": "orchestration_timing",
            "schema_version": OBSERVATION_SCHEMA_VERSION,
            "phase": "planning", "seconds": bad})


@pytest.mark.parametrize("bad", [True, False])
def test_bool_numeric_fields_rejected(bad):
    # bool is a subclass of int; must not pass the numeric check.
    with pytest.raises(EvidenceError):
        validate_observation(_resource_obs(bad))
    with pytest.raises(EvidenceError):
        validate_observation({
            "kind": "execution", "schema_version": OBSERVATION_SCHEMA_VERSION,
            "task_class": "code", "outcome": "pass", "worker_seconds": bad})
    with pytest.raises(EvidenceError):
        validate_observation({
            "kind": "retry", "schema_version": OBSERVATION_SCHEMA_VERSION,
            "task_class": "analysis", "attempt": bad})


def test_valid_numeric_observation_still_accepted():
    obs = _resource_obs(1.25)
    assert validate_observation(obs) is obs
    obs_int = _resource_obs(810)
    assert validate_observation(obs_int) is obs_int
    # zero and negative-but-finite remain valid numeric amounts
    assert validate_observation(_resource_obs(0.0))
    assert validate_observation(_resource_obs(-1.0))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_canonical_json_refuses_non_finite_floats(bad):
    # Defense in depth: even a payload that never went through
    # validate_observation cannot be serialized to invalid strict JSON.
    with pytest.raises(EvidenceError):
        canonical_json({"amount": bad})
    with pytest.raises(EvidenceError):
        canonical_json({"nested": {"list": [1.0, bad]}})


def test_canonical_json_valid_payload_unchanged():
    assert canonical_json({"b": 1, "a": [2.5, True]}) == '{"a":[2.5,true],"b":1}'
