from __future__ import annotations

import math

import pytest

from residual.eval.stats import (
    cohens_dz,
    compare_paired,
    holm_bonferroni,
    paired_bootstrap_mean_ci,
    paired_normal_approx_n,
    paired_t_test,
)


def test_paired_analysis_uses_within_block_differences():
    # Every block improves by exactly 2 despite a very wide between-block range.
    a = [102, 202, 302, 402, 502]
    b = [100, 200, 300, 400, 500]
    t, df, p = paired_t_test(a, b)
    assert math.isinf(t) and t > 0
    assert df == 4
    assert p == 0.0
    assert math.isinf(cohens_dz(a, b))


def test_bootstrap_is_deterministic_and_contains_observed_mean():
    a = [10, 13, 12, 16, 18, 20, 25, 24]
    b = [9, 11, 11, 13, 17, 18, 20, 22]
    first = paired_bootstrap_mean_ci(a, b, iterations=1000, seed=123)
    second = paired_bootstrap_mean_ci(a, b, iterations=1000, seed=123)
    assert first == second
    mean, low, high = first
    assert low <= mean <= high


def test_compare_paired_reports_effect_uncertainty_and_identity():
    result = compare_paired(
        "accepted_correctness", "R4", [0.8, 0.9, 0.7, 1.0, 0.9],
        "R0", [0.5, 0.6, 0.6, 0.7, 0.6], bootstrap_iterations=500, bootstrap_seed=5,
    )
    doc = result.to_dict()
    assert doc["n_pairs"] == 5
    assert doc["mean_difference"] > 0
    assert doc["effect_size_dz"] > 0
    assert doc["confidence_interval"][0] <= doc["mean_difference"] <= doc["confidence_interval"][1]
    assert doc["bootstrap_seed"] == 5


def test_holm_bonferroni_monotone_adjustment():
    adjusted = holm_bonferroni({"a": 0.01, "b": 0.02, "c": 0.20})
    assert adjusted["a"] == pytest.approx(0.03)
    assert adjusted["b"] == pytest.approx(0.04)
    assert adjusted["c"] == pytest.approx(0.20)
    assert all(0 <= p <= 1 for p in adjusted.values())


def test_power_planning_requires_more_pairs_for_smaller_effects():
    large = paired_normal_approx_n(0.8, alpha=0.05, power=0.8)
    small = paired_normal_approx_n(0.3, alpha=0.05, power=0.8)
    assert large >= 2
    assert small > large
