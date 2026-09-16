"""Soak harness tests: load generation, failure injection, metrics, harness."""
import pytest

from residual.soak import (
    FailureInjector,
    InjectionMix,
    LoadGenerator,
    SoakConfig,
    SoakHarness,
    SoakMetrics,
    make_task,
)
from residual.soak.tasks import NETOPS_TEMPLATES, SECOPS_TEMPLATES


def test_load_generator_enforces_n9_r9_minimum():
    with pytest.raises(ValueError, match=">= 1000"):
        LoadGenerator(tasks_per_day=100)
    gen = LoadGenerator(tasks_per_day=100, enforce_minimum=False)
    assert len(list(gen.tasks_for_day(0))) == 100


def test_load_generator_configurable_and_deterministic():
    gen = LoadGenerator(seed=5, tasks_per_day=50, enforce_minimum=False)
    day0 = [t.to_dict() for t in gen.tasks_for_day(0)]
    day0b = [t.to_dict() for t in gen.tasks_for_day(0)]
    assert day0 == day0b
    day1 = [t.to_dict() for t in gen.tasks_for_day(1)]
    assert day0 != day1


def test_task_templates_cover_netops_and_secops():
    gen = LoadGenerator(seed=5, tasks_per_day=200, enforce_minimum=False)
    domains = {t.domain for t in gen.tasks_for_day(0)}
    assert domains == {"netops", "secops"}
    assert NETOPS_TEMPLATES and SECOPS_TEMPLATES


def test_make_task_serialization_roundtrip():
    t = make_task(1, 2, 3)
    from residual.soak.tasks import SyntheticTask
    assert SyntheticTask.from_dict(t.to_dict()) == t


def test_failure_injection_deterministic_and_typed():
    mix = InjectionMix(bad_config_rate=0.5, missing_dependency_rate=0.5,
                       injection_attempt_rate=0.0, contract_violation_rate=0.0)
    inj = FailureInjector(seed=11, mix=mix)
    kinds = {inj.fault_for(0, i).kind for i in range(200)}
    assert kinds <= {"bad_config", "missing_dependency"}
    assert inj.fault_for(3, 7) == inj.fault_for(3, 7)


def test_injection_mix_validation():
    with pytest.raises(ValueError):
        InjectionMix(bad_config_rate=1.2)
    with pytest.raises(ValueError):
        InjectionMix(bad_config_rate=0.6, missing_dependency_rate=0.6)


def test_metrics_rates_on_hand_fed_events():
    m = SoakMetrics()
    for _ in range(10):
        m.record({"accepted": True, "cache_eligible": True, "cache_hit": True,
                  "tokens_used": 30, "tokens_uncached": 100})
    for _ in range(10):
        m.record({"accepted": True, "cache_eligible": True, "cache_hit": False,
                  "tokens_used": 100, "tokens_uncached": 100, "escalated": True})
    # one adversarial blocked, one adversarial missed (FN)
    m.record({"accepted": False, "adversarial": True, "blocked": True})
    m.record({"accepted": True, "adversarial": True, "blocked": False})
    # one intentional failure with recovery, one clean brake FP
    m.record({"accepted": False, "intentional_failure": True, "recovery_seconds": 30.0})
    m.record({"accepted": False, "brake_fired": True})

    assert m.tasks_executed == 24
    assert m.cache_hit_rate == pytest.approx(0.5)
    assert m.token_savings_rate == pytest.approx(1 - (300 + 1000) / 2000)
    assert m.brake_fn_rate == pytest.approx(0.5)
    assert m.escalation_rate == pytest.approx(10 / 24)
    assert m.mttr_seconds == pytest.approx(30.0)
    # clean tasks = 24 - 2 adversarial - 1 intentional = 21; 1 FP
    assert m.brake_fp_rate == pytest.approx(1 / 21)


def test_metrics_merge_and_roundtrip():
    a = SoakMetrics(tasks_executed=3, accepted=2, rejected=1, tokens_used=10,
                    tokens_uncached=20, recovery_times_seconds=[5.0])
    b = SoakMetrics(tasks_executed=2, accepted=2, cache_hits=1, cache_eligible=1,
                    recovery_times_seconds=[15.0])
    a.merge(b)
    assert a.tasks_executed == 5 and a.mttr_seconds == pytest.approx(10.0)
    clone = SoakMetrics.from_dict(a.to_dict())
    assert clone.to_dict() == a.to_dict()


def test_target_checks_flags_failures():
    m = SoakMetrics(tasks_executed=100, accepted=100, cache_eligible=100,
                    cache_hits=10, tokens_used=900, tokens_uncached=1000,
                    escalated=50, unhandled_exceptions=1)
    checks = m.target_checks()
    assert not checks["cache_hit_rate"]["passed"]
    assert not checks["escalation_rate"]["passed"]
    assert not checks["unhandled_exceptions"]["passed"]
    assert not checks["token_savings"]["passed"]  # 10% < 40%


def _small_harness(tmp_path, **cfg_kwargs):
    cfg = SoakConfig(total_days=2, tasks_per_day=60, **cfg_kwargs)
    return SoakHarness(cfg, b"test-station-key",
                       state_path=str(tmp_path / "state.json"),
                       enforce_load_minimum=False)


def test_harness_run_and_targets(tmp_path):
    h = _small_harness(tmp_path)
    h.run()
    assert h.state.days_completed == 2
    assert h.state.metrics.tasks_executed == 120
    payload = h.report(signed=False)
    assert payload["totals"]["tasks_executed"] == 120
    assert payload["all_targets_passed"]
    rates = payload["rates"]
    assert rates["cache_hit_rate"] >= 0.60  # calibrated generator
    assert rates["token_savings_rate"] >= 0.40


def test_harness_deterministic(tmp_path):
    h1 = SoakHarness(SoakConfig(total_days=1, tasks_per_day=40), b"k",
                     enforce_load_minimum=False)
    h2 = SoakHarness(SoakConfig(total_days=1, tasks_per_day=40), b"k",
                     enforce_load_minimum=False)
    h1.run()
    h2.run()
    assert h1.state.metrics.to_dict() == h2.state.metrics.to_dict()


def test_harness_zero_unhandled_exceptions(tmp_path):
    # heavy injection: everything injected, still no unhandled exceptions
    h = _small_harness(tmp_path, injection_mix=InjectionMix(
        bad_config_rate=0.3, missing_dependency_rate=0.3,
        injection_attempt_rate=0.2, contract_violation_rate=0.2))
    h.run()
    payload = h.report(signed=False)
    assert payload["totals"]["unhandled_exceptions"] == 0
    assert payload["totals"]["rejected"] > 0
    assert payload["rates"]["mttr_seconds"] > 0
