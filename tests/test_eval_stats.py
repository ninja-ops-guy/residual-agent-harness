"""Stats pipeline correctness on known distributions."""
import math
import random
import statistics

import pytest

from residual.eval.stats import (
    compare_samples,
    mann_whitney_u,
    student_t_cdf,
    summary_stats,
    welch_t_test,
)


def test_summary_stats_known_values():
    s = summary_stats([2, 4, 4, 4, 5, 5, 7, 9])
    assert s["n"] == 8
    assert s["mean"] == pytest.approx(5.0)
    assert s["median"] == pytest.approx(4.5)
    assert s["stdev"] == pytest.approx(statistics.stdev([2, 4, 4, 4, 5, 5, 7, 9]))
    assert s["min"] == 2 and s["max"] == 9


def test_summary_stats_single_value():
    s = summary_stats([42])
    assert s["stdev"] == 0.0 and s["mean"] == 42.0


def test_summary_stats_empty_rejected():
    with pytest.raises(ValueError):
        summary_stats([])


def test_mann_whitney_identical_samples_not_significant():
    _u, p = mann_whitney_u([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert p == pytest.approx(1.0)


def test_mann_whitney_known_u_value():
    # Classic small example: x ranks 1,2,3 -> rank sum 6, U = 6 - 6 = 0
    u, p = mann_whitney_u([1, 2, 3], [10, 11, 12])
    assert u == pytest.approx(0.0)
    assert p < 0.25  # strong separation, small n keeps p moderate


def test_mann_whitney_separated_distributions_significant():
    rng = random.Random(0)
    a = [rng.gauss(0, 1) for _ in range(50)]
    b = [rng.gauss(3, 1) for _ in range(50)]
    _u, p = mann_whitney_u(a, b)
    assert p < 0.001


def test_mann_whitney_same_distribution_not_significant():
    rng = random.Random(1)
    a = [rng.gauss(0, 1) for _ in range(60)]
    b = [rng.gauss(0, 1) for _ in range(60)]
    _u, p = mann_whitney_u(a, b)
    assert p > 0.05


def test_mann_whitney_ties_handled():
    u, p = mann_whitney_u([1, 2, 2, 3], [2, 2, 4, 5])
    assert 0.0 <= p <= 1.0
    assert u >= 0.0


def test_welch_t_known_value():
    # Hand-computed: x=[1,2,3,4,5], y=[3,4,5,6,7]; equal var, mean diff -2,
    # s1=s2=2/5 -> t = -2/sqrt(4/5)... = -2.0, df=8, p ~= 0.0805 (tables)
    t, df, p = welch_t_test([1, 2, 3, 4, 5], [3, 4, 5, 6, 7])
    assert t == pytest.approx(-2.0)
    assert df == pytest.approx(8.0)
    assert p == pytest.approx(0.0805, abs=1e-3)


def test_student_t_cdf_matches_tables():
    # t(0, any df) = 0.5; t(1.0, df=1) = 0.75 (Cauchy); df=inf -> normal
    assert student_t_cdf(0.0, 10) == pytest.approx(0.5)
    assert student_t_cdf(1.0, 1) == pytest.approx(0.75, abs=1e-6)
    assert student_t_cdf(1.959964, 1e6) == pytest.approx(0.975, abs=1e-3)
    # symmetry
    assert student_t_cdf(-1.5, 20) == pytest.approx(1 - student_t_cdf(1.5, 20), abs=1e-9)


def test_welch_t_significant_separation():
    rng = random.Random(2)
    a = [rng.gauss(0, 1) for _ in range(30)]
    b = [rng.gauss(2, 1) for _ in range(30)]
    t, _df, p = welch_t_test(a, b)
    assert t < 0 and p < 0.01


def test_compare_samples_significance_flag():
    rng = random.Random(3)
    a = [rng.gauss(100, 5) for _ in range(40)]
    b = [rng.gauss(100, 5) for _ in range(40)]
    c = [rng.gauss(150, 5) for _ in range(40)]
    same = compare_samples("tokens", "a", a, "b", b)
    diff = compare_samples("tokens", "a", a, "c", c)
    assert not same.significant
    assert diff.significant
    d = diff.to_dict()
    assert d["test"] == "mann_whitney_u" and d["alpha"] == 0.05
    assert d["stats_a"]["n"] == 40 and math.isfinite(d["p_value"])
