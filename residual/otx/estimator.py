"""Uncertainty-aware estimators for SPEC-SWARM-OTX-003.

OTX-R3: task-class-conditioned estimates with Bayesian updating.

* ``NormalInverseGamma`` — conjugate posterior for an unknown Normal
  mean/variance; used for orchestration tax ratios and worker-execution
  seconds, both conditioned on (task_class, topology).
* ``BetaRate`` — Beta posterior for a Bernoulli rate; used for
  per-(task_class, topology) reliability (OTX-R7 quality adjustment).

Both estimators are deterministic, serialisable (for exact replay,
Gate C), and report predictive uncertainty rather than bare point
estimates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class NormalInverseGamma:
    """Conjugate NIG posterior for a Normal likelihood."""

    mu: float
    kappa: float
    alpha: float
    beta: float
    n: int = 0

    @classmethod
    def prior(cls, mu: float, kappa: float = 1.0, alpha: float = 2.0, beta: float = 1.0) -> "NormalInverseGamma":
        return cls(mu=float(mu), kappa=float(kappa), alpha=float(alpha), beta=float(beta), n=0)

    def update(self, x: float) -> None:
        """Standard sequential NIG update (deterministic)."""
        if not math.isfinite(x):
            raise ValueError("cannot update with non-finite observation")
        kappa_n = self.kappa + 1.0
        mu_n = (self.kappa * self.mu + x) / kappa_n
        alpha_n = self.alpha + 0.5
        beta_n = self.beta + (self.kappa * (x - self.mu) ** 2) / (2.0 * kappa_n)
        self.mu, self.kappa, self.alpha, self.beta = mu_n, kappa_n, alpha_n, beta_n
        self.n += 1

    @property
    def mean(self) -> float:
        return self.mu

    @property
    def mean_variance(self) -> float:
        """Posterior variance of the unknown mean (uncertainty-aware)."""
        if self.alpha <= 1.0:
            return float("inf")
        return self.beta / (self.kappa * (self.alpha - 1.0))

    @property
    def mean_std(self) -> float:
        v = self.mean_variance
        return math.sqrt(v) if math.isfinite(v) else float("inf")

    def snapshot(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, snap: Dict[str, float]) -> "NormalInverseGamma":
        return cls(mu=snap["mu"], kappa=snap["kappa"], alpha=snap["alpha"], beta=snap["beta"], n=snap["n"])


@dataclass
class BetaRate:
    """Beta posterior for a success probability."""

    alpha: float
    beta: float

    @classmethod
    def prior(cls, rate: float, strength: float = 4.0) -> "BetaRate":
        rate = min(max(rate, 1e-3), 1.0 - 1e-3)
        return cls(alpha=rate * strength, beta=(1.0 - rate) * strength)

    def update(self, success: bool) -> None:
        if success:
            self.alpha += 1.0
        else:
            self.beta += 1.0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def n(self) -> float:
        return self.alpha + self.beta

    @property
    def std(self) -> float:
        a, b = self.alpha, self.beta
        return math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1.0)))

    def snapshot(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, snap: Dict[str, float]) -> "BetaRate":
        return cls(alpha=snap["alpha"], beta=snap["beta"])


class TaxModel:
    """Task-class-conditioned tax/latency/reliability estimates (OTX-R2/R3/R7).

    Keyed by (task_class, topology). Priors are seeded from the topology
    descriptor so cold-start behaviour is structural, but every posterior
    is updated from observed data (never a fixed constant).
    """

    def __init__(self, topologies) -> None:
        self._topologies = topologies
        self.tax: Dict[str, NormalInverseGamma] = {}
        self.worker_s: Dict[str, NormalInverseGamma] = {}
        self.reliability: Dict[str, BetaRate] = {}

    def _key(self, task_class: str, topology: str) -> str:
        return f"{task_class}|{topology}"

    def _tax_est(self, task_class: str, topology: str) -> NormalInverseGamma:
        key = self._key(task_class, topology)
        est = self.tax.get(key)
        if est is None:
            topo = self._topologies[topology]
            # Structural prior: more complex topologies start with a higher
            # expected tax; data dominates after a few observations.
            est = NormalInverseGamma.prior(mu=0.05 + 0.15 * topo.complexity_rank, kappa=1.0, alpha=2.0, beta=0.05)
            self.tax[key] = est
        return est

    def _worker_est(self, task_class: str, topology: str) -> NormalInverseGamma:
        key = self._key(task_class, topology)
        est = self.worker_s.get(key)
        if est is None:
            est = NormalInverseGamma.prior(mu=1.0, kappa=1.0, alpha=2.0, beta=1.0)
            self.worker_s[key] = est
        return est

    def _rel_est(self, task_class: str, topology: str) -> BetaRate:
        key = self._key(task_class, topology)
        est = self.reliability.get(key)
        if est is None:
            est = BetaRate.prior(self._topologies[topology].reliability_prior)
            self.reliability[key] = est
        return est

    # -- queries ---------------------------------------------------------
    def predicted_tax(self, task_class: str, topology: str) -> float:
        return self._tax_est(task_class, topology).mean

    def tax_uncertainty(self, task_class: str, topology: str) -> float:
        return self._tax_est(task_class, topology).mean_std

    def predicted_worker_s(self, task_class: str, topology: str) -> float:
        return self._worker_est(task_class, topology).mean

    def predicted_total_s(self, task_class: str, topology: str) -> float:
        est = self._worker_est(task_class, topology)
        return est.mean * (1.0 + self._tax_est(task_class, topology).mean)

    def predicted_reliability(self, task_class: str, topology: str) -> float:
        return self._rel_est(task_class, topology).mean

    def sample_count(self, task_class: str, topology: str) -> int:
        return self._tax_est(task_class, topology).n

    # -- updates ----------------------------------------------------------
    def observe(self, task_class: str, topology: str, timing, success: bool) -> float:
        """Fold one experimental outcome into all posteriors (OTX-R3).

        Returns the observed tax for convenience.
        """
        tax = timing.observed_tax()
        if not math.isfinite(tax):
            tax = 10.0  # degenerate run: overhead with zero productive work
        self._tax_est(task_class, topology).update(tax)
        if timing.worker_execution_s > 0:
            self._worker_est(task_class, topology).update(timing.worker_execution_s)
        self._rel_est(task_class, topology).update(bool(success))
        return tax

    # -- serialisation (Gate C replay) ------------------------------------
    def snapshot(self) -> Dict[str, dict]:
        return {
            "tax": {k: v.snapshot() for k, v in sorted(self.tax.items())},
            "worker_s": {k: v.snapshot() for k, v in sorted(self.worker_s.items())},
            "reliability": {k: v.snapshot() for k, v in sorted(self.reliability.items())},
        }

    @classmethod
    def from_snapshot(cls, topologies, snap: Dict[str, dict]) -> "TaxModel":
        model = cls(topologies)
        model.tax = {k: NormalInverseGamma.from_snapshot(v) for k, v in snap.get("tax", {}).items()}
        model.worker_s = {k: NormalInverseGamma.from_snapshot(v) for k, v in snap.get("worker_s", {}).items()}
        model.reliability = {k: BetaRate.from_snapshot(v) for k, v in snap.get("reliability", {}).items()}
        return model
