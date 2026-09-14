"""Evaluation report: stats pipeline output serialized to JSON.

T10-R1: mean/median/stddev + significance per configuration.
T10-R3: all raw evaluation data preserved (``raw_runs`` per config).
T10-R4: report records the FrozenWorkload manifest hash so reviewers
can verify they ran the identical workload.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from .stats import compare_samples
from .workload import FrozenWorkload

SCHEMA_VERSION = "residual.eval.report.v1"
METRICS = ("elapsed_ms", "tokens_used", "success")


class EvaluationReport:
    """Aggregates per-configuration run results into a signed-off report."""

    def __init__(self, workload: FrozenWorkload, config_results: Sequence[Dict[str, Any]],
                 test: str = "mann_whitney_u", alpha: float = 0.05):
        if not workload.verify():
            raise ValueError("workload failed manifest verification")
        self.workload = workload
        self.config_results = list(config_results)
        self.test = test
        self.alpha = alpha

    # -- per-configuration metric samples -------------------------------
    @staticmethod
    def _samples(runs: Sequence[Dict[str, Any]], metric: str) -> List[float]:
        if metric == "success":
            return [1.0 if r["success"] else 0.0 for r in runs]
        return [float(r[metric]) for r in runs]

    def summarize(self) -> Dict[str, Any]:
        from .stats import summary_stats

        configs = []
        for cfg in self.config_results:
            runs = cfg["runs"]
            metrics = {m: summary_stats(self._samples(runs, m)) for m in METRICS}
            clean = [r for r in runs if r.get("fault") is None]
            metrics["clean_success_rate"] = (
                sum(1 for r in clean if r["success"]) / len(clean) if clean else None
            )
            configs.append({
                "configuration": cfg["configuration"],
                "backend_kind": cfg["backend_kind"],
                "backend_name": cfg["backend_name"],
                "ablation": cfg["ablation"],
                "repeats": cfg["repeats"],
                "metrics": metrics,
            })

        comparisons = []
        base = self.config_results[0] if self.config_results else None
        if base is not None:
            for other in self.config_results[1:]:
                for metric in ("elapsed_ms", "tokens_used"):
                    comp = compare_samples(
                        metric,
                        base["configuration"], self._samples(base["runs"], metric),
                        other["configuration"], self._samples(other["runs"], metric),
                        test=self.test, alpha=self.alpha,
                    )
                    comparisons.append(comp.to_dict())

        return {
            "schema_version": SCHEMA_VERSION,
            "workload": self.workload.manifest(),
            "significance_test": self.test,
            "alpha": self.alpha,
            "configurations": configs,
            "comparisons_vs_baseline": comparisons,
            # T10-R3: raw data preserved in full as supplementary material.
            "raw_runs": {
                cfg["configuration"]: cfg["runs"] for cfg in self.config_results
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.summarize(), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> Dict[str, Any]:
        data = json.loads(text)
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported report schema: {data.get('schema_version')}")
        return data
