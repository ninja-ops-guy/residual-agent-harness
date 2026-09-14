"""Local statistics pipeline (stdlib-only) for evaluation results.

T10-R1: results MUST include mean, median, standard deviation, and
statistical significance tests. Mann-Whitney U (normal approximation
with continuity + tie correction) and Welch's t-test are implemented
locally on top of ``statistics`` and ``math``; the Student-t CDF uses a
locally implemented regularized incomplete beta function (continued
fraction, Numerical Recipes betacf).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, Sequence, Tuple


def summary_stats(values: Sequence[float]) -> Dict[str, float]:
    """Mean/median/stddev for a sample (stddev is sample stdev, n-1)."""
    vals = [float(v) for v in values]
    if not vals:
        raise ValueError("summary_stats requires at least one value")
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
    }


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def mann_whitney_u(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float]:
    """Two-sided Mann-Whitney U test.

    Returns (U, p). Uses the normal approximation with continuity
    correction and tie correction; requires n_x, n_y >= 3 for the
    approximation to be meaningful.
    """
    xs = [float(v) for v in x]
    ys = [float(v) for v in y]
    n1, n2 = len(xs), len(ys)
    if n1 < 1 or n2 < 1:
        raise ValueError("mann_whitney_u requires non-empty samples")

    combined = [(v, 0) for v in xs] + [(v, 1) for v in ys]
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * len(combined)
    tie_counts = []
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        if j > i:
            tie_counts.append(j - i + 1)
        i = j + 1

    rank_sum_x = sum(r for r, (_, group) in zip(ranks, combined) if group == 0)
    u1 = rank_sum_x - n1 * (n1 + 1) / 2.0
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    mean_u = n1 * n2 / 2.0
    n = n1 + n2
    tie_term = sum(t ** 3 - t for t in tie_counts)
    var_u = (n1 * n2 / 12.0) * ((n + 1) - tie_term / (n * (n - 1)) if n > 1 else 0.0)
    if var_u <= 0:  # all values identical
        return u, 1.0
    z = (u - mean_u + 0.5) / math.sqrt(var_u)  # continuity correction toward mean
    p = 2.0 * _normal_cdf(z)  # z <= 0 here
    return u, max(0.0, min(1.0, p))


# -- Student-t distribution CDF via regularized incomplete beta ---------
def _betacf(a: float, b: float, x: float) -> float:
    max_iter, eps, fpmin = 200, 3.0e-14, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t: float, df: float) -> float:
    """CDF of the Student-t distribution with df degrees of freedom."""
    if df <= 0:
        raise ValueError("degrees of freedom must be positive")
    x = df / (df + t * t)
    ib = _regularized_incomplete_beta(df / 2.0, 0.5, x)
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def welch_t_test(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float, float]:
    """Welch's unequal-variance t-test. Returns (t, df, p_two_sided)."""
    xs = [float(v) for v in x]
    ys = [float(v) for v in y]
    if len(xs) < 2 or len(ys) < 2:
        raise ValueError("welch_t_test requires samples of size >= 2")
    m1, m2 = statistics.fmean(xs), statistics.fmean(ys)
    v1, v2 = statistics.variance(xs), statistics.variance(ys)
    n1, n2 = len(xs), len(ys)
    s1, s2 = v1 / n1, v2 / n2
    denom = math.sqrt(s1 + s2)
    if denom == 0.0:
        return 0.0, float(n1 + n2 - 2), 1.0 if m1 == m2 else 0.0
    t = (m1 - m2) / denom
    df = (s1 + s2) ** 2 / (s1 * s1 / (n1 - 1) + s2 * s2 / (n2 - 1))
    p = 2.0 * (1.0 - student_t_cdf(abs(t), df))
    return t, df, max(0.0, min(1.0, p))


@dataclass(frozen=True)
class Comparison:
    """Pairwise comparison between two configurations' run samples."""

    metric: str
    config_a: str
    config_b: str
    stats_a: Dict[str, float]
    stats_b: Dict[str, float]
    test: str  # "mann_whitney_u" | "welch_t"
    statistic: float
    p_value: float
    alpha: float

    @property
    def significant(self) -> bool:
        return self.p_value < self.alpha

    def to_dict(self) -> Dict[str, object]:
        return {
            "metric": self.metric,
            "config_a": self.config_a,
            "config_b": self.config_b,
            "stats_a": self.stats_a,
            "stats_b": self.stats_b,
            "test": self.test,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "alpha": self.alpha,
            "significant": self.significant,
        }


def compare_samples(
    metric: str,
    config_a: str,
    a: Sequence[float],
    config_b: str,
    b: Sequence[float],
    test: str = "mann_whitney_u",
    alpha: float = 0.05,
) -> Comparison:
    stats_a = summary_stats(a)
    stats_b = summary_stats(b)
    if test == "mann_whitney_u":
        stat, p = mann_whitney_u(a, b)
    elif test == "welch_t":
        stat, _df, p = welch_t_test(a, b)
    else:
        raise ValueError(f"unknown test: {test}")
    return Comparison(metric, config_a, config_b, stats_a, stats_b, test, stat, p, alpha)
