"""Local statistics pipeline (stdlib-only) for evaluation results.

The legacy independent-sample Mann-Whitney U and Welch tests remain available.
Confirmatory R0-R5 experiments should prefer the paired/block helpers below when
the same task/model/seed is observed under multiple configurations. Paired
reports include effect size and deterministic bootstrap uncertainty rather than
reducing the result to a p-value.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from statistics import NormalDist
from typing import Dict, Mapping, Sequence, Tuple


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
    """Two-sided Mann-Whitney U test with continuity and tie correction."""
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
        avg_rank = (i + j) / 2.0 + 1.0
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
    if var_u <= 0:
        return u, 1.0
    z = (u - mean_u + 0.5) / math.sqrt(var_u)
    p = 2.0 * _normal_cdf(z)
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


def paired_differences(a: Sequence[float], b: Sequence[float]) -> list[float]:
    if len(a) != len(b) or not a:
        raise ValueError("paired samples must be non-empty and equal length")
    return [float(x) - float(y) for x, y in zip(a, b)]


def paired_t_test(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    """Paired t-test over per-block differences; returns (t, df, p_two_sided)."""
    diffs = paired_differences(a, b)
    if len(diffs) < 2:
        raise ValueError("paired_t_test requires at least two pairs")
    mean = statistics.fmean(diffs)
    stdev = statistics.stdev(diffs)
    if stdev == 0.0:
        return (0.0 if mean == 0.0 else math.copysign(math.inf, mean),
                float(len(diffs) - 1), 1.0 if mean == 0.0 else 0.0)
    t = mean / (stdev / math.sqrt(len(diffs)))
    df = float(len(diffs) - 1)
    p = 2.0 * (1.0 - student_t_cdf(abs(t), df))
    return t, df, max(0.0, min(1.0, p))


def cohens_dz(a: Sequence[float], b: Sequence[float]) -> float:
    """Standardized paired effect size (mean difference / SD of differences)."""
    diffs = paired_differences(a, b)
    if len(diffs) < 2:
        raise ValueError("cohens_dz requires at least two pairs")
    mean = statistics.fmean(diffs)
    stdev = statistics.stdev(diffs)
    if stdev == 0.0:
        return 0.0 if mean == 0.0 else math.copysign(math.inf, mean)
    return mean / stdev


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires data")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0,1]")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = q * (len(sorted_values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(sorted_values[lo])
    weight = pos - lo
    return float(sorted_values[lo]) * (1.0 - weight) + float(sorted_values[hi]) * weight


def paired_bootstrap_mean_ci(
    a: Sequence[float], b: Sequence[float], *, confidence: float = 0.95,
    iterations: int = 5000, seed: int = 20260916,
) -> Tuple[float, float, float]:
    """Deterministic percentile bootstrap CI for the paired mean difference."""
    diffs = paired_differences(a, b)
    if iterations < 100:
        raise ValueError("bootstrap iterations must be >= 100")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0,1)")
    rng = random.Random(seed)
    n = len(diffs)
    draws = sorted(statistics.fmean(diffs[rng.randrange(n)] for _ in range(n))
                   for _ in range(iterations))
    alpha = 1.0 - confidence
    return statistics.fmean(diffs), _percentile(draws, alpha / 2.0), _percentile(draws, 1.0 - alpha / 2.0)


def holm_bonferroni(p_values: Mapping[str, float]) -> Dict[str, float]:
    """Family-wise error correction returning monotone Holm-adjusted p-values."""
    for label, p in p_values.items():
        if not 0.0 <= float(p) <= 1.0:
            raise ValueError(f"invalid p-value for {label!r}")
    ordered = sorted((float(p), label) for label, p in p_values.items())
    m = len(ordered)
    adjusted: Dict[str, float] = {}
    running = 0.0
    for i, (p, label) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[label] = running
    return adjusted


def paired_normal_approx_n(effect_size: float, *, alpha: float = 0.05, power: float = 0.80) -> int:
    """Approximate paired-sample size for a standardized effect before data collection.

    This is a planning/sensitivity approximation, not a substitute for a full
    design-specific power analysis.
    """
    d = abs(float(effect_size))
    if d <= 0.0 or not 0.0 < alpha < 1.0 or not 0.0 < power < 1.0:
        raise ValueError("effect_size must be nonzero and alpha/power must be in (0,1)")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1.0 - alpha / 2.0)
    z_power = normal.inv_cdf(power)
    return max(2, math.ceil(((z_alpha + z_power) / d) ** 2))


@dataclass(frozen=True)
class Comparison:
    metric: str
    config_a: str
    config_b: str
    stats_a: Dict[str, float]
    stats_b: Dict[str, float]
    test: str
    statistic: float
    p_value: float
    alpha: float

    @property
    def significant(self) -> bool:
        return self.p_value < self.alpha

    def to_dict(self) -> Dict[str, object]:
        return {
            "metric": self.metric, "config_a": self.config_a, "config_b": self.config_b,
            "stats_a": self.stats_a, "stats_b": self.stats_b, "test": self.test,
            "statistic": self.statistic, "p_value": self.p_value, "alpha": self.alpha,
            "significant": self.significant,
        }


@dataclass(frozen=True)
class PairedComparison:
    metric: str
    config_a: str
    config_b: str
    n_pairs: int
    mean_difference: float
    ci_low: float
    ci_high: float
    effect_size_dz: float
    statistic: float
    degrees_freedom: float
    p_value: float
    alpha: float
    bootstrap_seed: int
    bootstrap_iterations: int

    @property
    def significant(self) -> bool:
        return self.p_value < self.alpha

    def to_dict(self) -> Dict[str, object]:
        return {
            "metric": self.metric, "config_a": self.config_a, "config_b": self.config_b,
            "n_pairs": self.n_pairs, "mean_difference": self.mean_difference,
            "confidence_interval": [self.ci_low, self.ci_high],
            "effect_size_dz": self.effect_size_dz, "test": "paired_t",
            "statistic": self.statistic, "degrees_freedom": self.degrees_freedom,
            "p_value": self.p_value, "alpha": self.alpha, "significant": self.significant,
            "bootstrap_seed": self.bootstrap_seed, "bootstrap_iterations": self.bootstrap_iterations,
        }


def compare_samples(
    metric: str, config_a: str, a: Sequence[float], config_b: str, b: Sequence[float],
    test: str = "mann_whitney_u", alpha: float = 0.05,
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


def compare_paired(
    metric: str, config_a: str, a: Sequence[float], config_b: str, b: Sequence[float], *,
    alpha: float = 0.05, confidence: float = 0.95, bootstrap_iterations: int = 5000,
    bootstrap_seed: int = 20260916,
) -> PairedComparison:
    diffs = paired_differences(a, b)
    t, df, p = paired_t_test(a, b)
    mean, low, high = paired_bootstrap_mean_ci(
        a, b, confidence=confidence, iterations=bootstrap_iterations, seed=bootstrap_seed)
    return PairedComparison(
        metric=metric, config_a=config_a, config_b=config_b, n_pairs=len(diffs),
        mean_difference=mean, ci_low=low, ci_high=high, effect_size_dz=cohens_dz(a, b),
        statistic=t, degrees_freedom=df, p_value=p, alpha=alpha,
        bootstrap_seed=bootstrap_seed, bootstrap_iterations=bootstrap_iterations,
    )
