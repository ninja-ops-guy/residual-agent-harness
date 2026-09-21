"""Frozen statistical procedures for EXP-M6-SLM (EVALUATION-PROTOCOL.md section 7).

Stdlib-only implementations of:

* 95% percentile PAIRED bootstrap CIs (10,000 resamples) resampled at the
  ``contamination_group`` level (never individual items), preserving pairing
  across configurations evaluated on identical groups;
* McNemar's test for paired binary comparisons (exact binomial variant when
  discordant pairs < 25, otherwise chi-square with continuity correction);
* Holm-Bonferroni multiple-comparison correction at family alpha = 0.05.

Seeds MUST be drawn from the frozen seed list in order; the seed index is
recorded per run by the caller.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Mapping, Sequence, Tuple

# Frozen seed list (EVALUATION-PROTOCOL.md section 7). Callers must draw from
# this list in order and record the seed index per run.
FROZEN_SEEDS: Tuple[int, ...] = (20260920, 4117, 89123, 777001, 5551212)

BOOTSTRAP_RESAMPLES = 10_000
FAMILY_ALPHA = 0.05
MCNEMAR_EXACT_THRESHOLD = 25  # exact binomial when discordant pairs < 25


def frozen_seed(seed_index: int) -> int:
    """Return the frozen seed at ``seed_index`` (0-based, in frozen order)."""
    return FROZEN_SEEDS[seed_index]


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile on pre-sorted values."""
    if not sorted_values:
        raise ValueError("percentile of empty sequence")
    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])
    rank = (q / 100.0) * (n - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(sorted_values[lo])
    frac = rank - lo
    return float(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac)


def _group_rows(
    rows: Sequence[Mapping[str, object]], group_key: str = "contamination_group"
) -> Dict[object, List[Mapping[str, object]]]:
    groups: Dict[object, List[Mapping[str, object]]] = {}
    for row in rows:
        groups.setdefault(row[group_key], []).append(row)
    return groups


def paired_bootstrap_ci(
    rows: Sequence[Mapping[str, object]],
    statistic: Callable[[Sequence[Mapping[str, object]]], float],
    *,
    seed: int,
    resamples: int = BOOTSTRAP_RESAMPLES,
    alpha: float = FAMILY_ALPHA,
    group_key: str = "contamination_group",
) -> Dict[str, float]:
    """95% percentile paired bootstrap CI resampling contamination groups.

    ``rows`` are per-item/per-mission observations sharing a
    ``contamination_group``; whole groups are resampled with replacement so
    pairing across configurations on identical groups is preserved when the
    same procedure is applied to paired configurations with the same seed.

    Returns {"point", "lo", "hi", "resamples", "seed"}.
    """
    if seed not in FROZEN_SEEDS:
        raise ValueError(
            "seed %r not in frozen seed list %s" % (seed, FROZEN_SEEDS)
        )
    if not rows:
        raise ValueError("bootstrap requires at least one observation")
    groups = _group_rows(rows, group_key)
    group_ids = sorted(groups, key=str)
    point = float(statistic(rows))
    rng = random.Random(seed)
    estimates: List[float] = []
    for _ in range(resamples):
        sampled = [groups[group_ids[rng.randrange(len(group_ids))]]
                   for _ in range(len(group_ids))]
        flat = [row for chunk in sampled for row in chunk]
        estimates.append(float(statistic(flat)))
    estimates.sort()
    lo = _percentile(estimates, 100.0 * alpha / 2.0)
    hi = _percentile(estimates, 100.0 * (1.0 - alpha / 2.0))
    return {
        "point": point,
        "lo": lo,
        "hi": hi,
        "resamples": float(resamples),
        "seed": float(seed),
    }


def mean_statistic(field: str) -> Callable[[Sequence[Mapping[str, object]]], float]:
    """Statistic factory: mean of a numeric per-row field."""
    def _stat(rows: Sequence[Mapping[str, object]]) -> float:
        return sum(float(r[field]) for r in rows) / len(rows)
    return _stat


def mcnemar_exact(b: int, c: int) -> Dict[str, object]:
    """McNemar's test for paired binary outcomes.

    ``b`` = discordant pairs where config A succeeds and B fails;
    ``c`` = discordant pairs where A fails and B succeeds.
    Exact two-sided binomial test (p = 0.5) when b + c < 25; otherwise
    chi-square with continuity correction (p-value via the chi-square(1)
    survival function, which has a closed form through erfc).

    Returns {"b", "c", "statistic", "p_value", "method"}.
    """
    if b < 0 or c < 0:
        raise ValueError("discordant counts must be non-negative")
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "statistic": 0.0, "p_value": 1.0,
                "method": "exact"}
    if n < MCNEMAR_EXACT_THRESHOLD:
        k = min(b, c)
        # Two-sided exact binomial: 2 * P(X <= k) for X ~ Bin(n, 0.5),
        # capped at 1.0 (standard McNemar exact convention).
        tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
        p_value = min(1.0, 2.0 * tail)
        return {"b": b, "c": c, "statistic": float(abs(b - c)),
                "p_value": p_value, "method": "exact"}
    chi2 = (abs(b - c) - 1.0) ** 2 / n  # continuity-corrected
    # chi-square(1) survival function: P(X >= x) = erfc(sqrt(x/2))
    p_value = math.erfc(math.sqrt(chi2 / 2.0))
    return {"b": b, "c": c, "statistic": chi2, "p_value": p_value,
            "method": "chi2_continuity_corrected"}


def holm_bonferroni(p_values: Sequence[float],
                    alpha: float = FAMILY_ALPHA) -> Dict[str, object]:
    """Holm-Bonferroni step-down correction over a family of tests.

    Returns {"adjusted": [...], "rejected": [...], "alpha": alpha} where
    ``adjusted[i]`` is the Holm-adjusted p-value for the input at index i and
    ``rejected[i]`` is True iff that test survives at family ``alpha``.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = min(1.0, (m - rank) * p_values[idx])
        running_max = max(running_max, adj)  # enforce monotonicity
        adjusted[idx] = running_max
    rejected = [adjusted[i] < alpha for i in range(m)]
    return {"adjusted": adjusted, "rejected": rejected, "alpha": alpha}
