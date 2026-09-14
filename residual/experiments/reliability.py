"""Canonical analysis for Residual Experimental Release 1.

The execution systems already produce evidence. This module deliberately does not
run models or modify accepted state. It consumes frozen trial observations and
turns them into hash-bound reliability results suitable for a paper or release.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..core import digest, strict_json


SCHEMA_VERSION = "residual.reliability-study.v1"
OBSERVATION_SCHEMA = "residual.reliability-observation.v1"
MANIFEST_SCHEMA = "residual.reliability-manifest.v1"


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _wilson(successes: int, total: int, z: float = 1.96) -> dict[str, float] | None:
    if total == 0:
        return None
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    radius = (z / denom) * math.sqrt((p * (1.0 - p) / total) + (z * z / (4.0 * total * total)))
    return {
        "lower": max(0.0, center - radius),
        "upper": min(1.0, center + radius),
        "confidence": 0.95,
    }


def _quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


@dataclass(frozen=True)
class ReliabilityManifest:
    study_id: str
    suite_sha256: str
    source_revision: str
    preregistered_at: str
    baseline_configuration: str
    configurations: tuple[str, ...]
    primary_metric: str = "accepted_error_rate"
    model_bindings: Mapping[str, Any] | None = None
    verifier_revisions: Mapping[str, Any] | None = None
    budget: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not all((self.study_id, self.suite_sha256, self.source_revision, self.preregistered_at)):
            raise ValueError("manifest identity fields are required")
        if not self.configurations:
            raise ValueError("at least one configuration is required")
        if len(self.configurations) != len(set(self.configurations)):
            raise ValueError("duplicate configuration")
        if self.baseline_configuration not in self.configurations:
            raise ValueError("baseline_configuration must be listed in configurations")
        if self.primary_metric != "accepted_error_rate":
            raise ValueError("v1 freezes accepted_error_rate as the primary metric")

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": MANIFEST_SCHEMA,
            "study_id": self.study_id,
            "suite_sha256": self.suite_sha256,
            "source_revision": self.source_revision,
            "preregistered_at": self.preregistered_at,
            "baseline_configuration": self.baseline_configuration,
            "configurations": list(self.configurations),
            "primary_metric": self.primary_metric,
            "model_bindings": dict(self.model_bindings or {}),
            "verifier_revisions": dict(self.verifier_revisions or {}),
            "budget": dict(self.budget or {}),
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class TrialObservation:
    case_id: str
    family: str
    trial: int
    configuration: str
    accepted: bool
    independently_correct: bool
    worker_correct: bool | None
    fault_injected: bool = False
    fault_contained: bool | None = None
    degradation_level: str = "nominal"
    cost_usd: float | None = None
    latency_ms: float | None = None
    evidence_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.case_id or not self.family or not self.configuration or not self.degradation_level:
            raise ValueError("observation identity fields are required")
        if type(self.trial) is not int or self.trial < 1:
            raise ValueError("trial must be a positive integer")
        if self.fault_contained is not None and not self.fault_injected:
            raise ValueError("fault_contained requires fault_injected")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise ValueError("cost_usd must be non-negative")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")

    @property
    def false_acceptance(self) -> bool:
        return self.accepted and not self.independently_correct

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": OBSERVATION_SCHEMA,
            "case_id": self.case_id,
            "family": self.family,
            "trial": self.trial,
            "configuration": self.configuration,
            "accepted": self.accepted,
            "independently_correct": self.independently_correct,
            "worker_correct": self.worker_correct,
            "fault_injected": self.fault_injected,
            "fault_contained": self.fault_contained,
            "degradation_level": self.degradation_level,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "evidence_hash": self.evidence_hash,
        }


def load_manifest(path: str | Path) -> ReliabilityManifest:
    raw = strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("invalid reliability manifest")
    allowed = {
        "schema_version", "study_id", "suite_sha256", "source_revision", "preregistered_at",
        "baseline_configuration", "configurations", "primary_metric", "model_bindings",
        "verifier_revisions", "budget",
    }
    if set(raw) - allowed:
        raise ValueError("unknown reliability manifest fields")
    return ReliabilityManifest(
        study_id=raw["study_id"],
        suite_sha256=raw["suite_sha256"],
        source_revision=raw["source_revision"],
        preregistered_at=raw["preregistered_at"],
        baseline_configuration=raw["baseline_configuration"],
        configurations=tuple(raw["configurations"]),
        primary_metric=raw.get("primary_metric", "accepted_error_rate"),
        model_bindings=raw.get("model_bindings") or {},
        verifier_revisions=raw.get("verifier_revisions") or {},
        budget=raw.get("budget") or {},
    )


def _observation_from_dict(raw: Mapping[str, Any]) -> TrialObservation:
    if raw.get("schema_version") != OBSERVATION_SCHEMA:
        raise ValueError("invalid reliability observation schema")
    required = {
        "schema_version", "case_id", "family", "trial", "configuration", "accepted",
        "independently_correct", "worker_correct", "fault_injected", "fault_contained",
        "degradation_level", "cost_usd", "latency_ms", "evidence_hash",
    }
    if set(raw) != required:
        raise ValueError("invalid reliability observation fields")
    for field in ("accepted", "independently_correct", "fault_injected"):
        if type(raw[field]) is not bool:
            raise ValueError(f"{field} must be boolean")
    if raw["worker_correct"] is not None and type(raw["worker_correct"]) is not bool:
        raise ValueError("worker_correct must be boolean or null")
    if raw["fault_contained"] is not None and type(raw["fault_contained"]) is not bool:
        raise ValueError("fault_contained must be boolean or null")
    return TrialObservation(
        case_id=raw["case_id"], family=raw["family"], trial=raw["trial"],
        configuration=raw["configuration"], accepted=raw["accepted"],
        independently_correct=raw["independently_correct"], worker_correct=raw["worker_correct"],
        fault_injected=raw["fault_injected"], fault_contained=raw["fault_contained"],
        degradation_level=raw["degradation_level"], cost_usd=raw["cost_usd"],
        latency_ms=raw["latency_ms"], evidence_hash=raw["evidence_hash"],
    )


def load_observations(path: str | Path) -> tuple[TrialObservation, ...]:
    observations: list[TrialObservation] = []
    seen: set[tuple[str, int, str, str]] = set()
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = strict_json(line)
        if not isinstance(raw, dict):
            raise ValueError(f"observation line {line_number} is not an object")
        obs = _observation_from_dict(raw)
        identity = (obs.case_id, obs.trial, obs.configuration, obs.degradation_level)
        if identity in seen:
            raise ValueError(f"duplicate observation identity at line {line_number}")
        seen.add(identity)
        observations.append(obs)
    if not observations:
        raise ValueError("reliability study requires observations")
    return tuple(observations)


def _metrics(rows: Sequence[TrialObservation]) -> dict[str, Any]:
    attempts = len(rows)
    accepted = sum(o.accepted for o in rows)
    false_acceptances = sum(o.false_acceptance for o in rows)
    independently_correct = sum(o.independently_correct for o in rows)
    accepted_correct = sum(o.accepted and o.independently_correct for o in rows)
    faults = [o for o in rows if o.fault_injected]
    contained = sum(o.fault_contained is True for o in faults)
    workers_known = [o for o in rows if o.worker_correct is not None]
    workers_correct = sum(o.worker_correct is True for o in workers_known)
    costs = [o.cost_usd for o in rows if o.cost_usd is not None]
    latencies = [o.latency_ms for o in rows if o.latency_ms is not None]
    total_cost = sum(costs) if len(costs) == attempts else None
    return {
        "attempts": attempts,
        "accepted": accepted,
        "accepted_correct": accepted_correct,
        "false_acceptances": false_acceptances,
        "accepted_error_rate": _rate(false_acceptances, accepted),
        "accepted_error_ci95": _wilson(false_acceptances, accepted),
        "accepted_correctness": _rate(accepted_correct, accepted),
        "acceptance_rate": _rate(accepted, attempts),
        "independent_success_rate": _rate(independently_correct, attempts),
        "worker_correctness_rate": _rate(workers_correct, len(workers_known)),
        "worker_correctness_known": len(workers_known),
        "faults_injected": len(faults),
        "faults_contained": contained,
        "failure_containment_rate": _rate(contained, len(faults)),
        "failure_containment_ci95": _wilson(contained, len(faults)),
        "cost_usd": total_cost,
        "cost_coverage": _rate(len(costs), attempts),
        "cost_per_accepted_correct": (total_cost / accepted_correct) if total_cost is not None and accepted_correct else None,
        "latency_coverage": _rate(len(latencies), attempts),
        "latency_median_ms": statistics.median(latencies) if latencies else None,
        "latency_p95_ms": _quantile(latencies, 0.95),
    }


def analyze_reliability(manifest: ReliabilityManifest, observations: Iterable[TrialObservation]) -> dict[str, Any]:
    rows = tuple(observations)
    unknown_configs = sorted({o.configuration for o in rows} - set(manifest.configurations))
    if unknown_configs:
        raise ValueError(f"observations include unregistered configurations: {unknown_configs}")
    missing = [c for c in manifest.configurations if not any(o.configuration == c for o in rows)]
    if missing:
        raise ValueError(f"manifest configurations have no observations: {missing}")

    by_config: dict[str, Any] = {}
    for config in manifest.configurations:
        selected = [o for o in rows if o.configuration == config]
        by_config[config] = _metrics(selected)

    baseline = by_config[manifest.baseline_configuration]
    baseline_aer = baseline["accepted_error_rate"]
    comparisons: dict[str, Any] = {}
    for config, metrics in by_config.items():
        aer = metrics["accepted_error_rate"]
        comparisons[config] = {
            "accepted_error_rate_delta_vs_baseline": (aer - baseline_aer) if aer is not None and baseline_aer is not None else None,
            "accepted_error_rate_relative_reduction_vs_baseline": (
                (baseline_aer - aer) / baseline_aer
                if aer is not None and baseline_aer not in (None, 0.0) else None
            ),
            "acceptance_rate_delta_vs_baseline": (
                metrics["acceptance_rate"] - baseline["acceptance_rate"]
                if metrics["acceptance_rate"] is not None and baseline["acceptance_rate"] is not None else None
            ),
            "cost_delta_vs_baseline": (
                metrics["cost_usd"] - baseline["cost_usd"]
                if metrics["cost_usd"] is not None and baseline["cost_usd"] is not None else None
            ),
        }

    levels = sorted({o.degradation_level for o in rows})
    degradation: dict[str, Any] = {}
    for level in levels:
        degradation[level] = {
            config: _metrics([o for o in rows if o.configuration == config and o.degradation_level == level])
            for config in manifest.configurations
            if any(o.configuration == config and o.degradation_level == level for o in rows)
        }

    families = sorted({o.family for o in rows})
    family_metrics = {
        family: {
            config: _metrics([o for o in rows if o.family == family and o.configuration == config])
            for config in manifest.configurations
            if any(o.family == family and o.configuration == config for o in rows)
        }
        for family in families
    }

    evidence_hashes = sorted({o.evidence_hash for o in rows if o.evidence_hash})
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "manifest": manifest.payload(),
        "manifest_sha256": manifest.sha256,
        "observation_count": len(rows),
        "observation_sha256": digest([o.payload() for o in sorted(rows, key=lambda x: (x.case_id, x.trial, x.configuration, x.degradation_level))]),
        "metrics_by_configuration": by_config,
        "comparisons_to_baseline": comparisons,
        "degradation_curves": degradation,
        "metrics_by_family": family_metrics,
        "evidence_hashes": evidence_hashes,
        "claim_scope": (
            "Results measure accepted error, containment, throughput proxies, cost and latency only for the frozen "
            "manifest and supplied observations. They do not establish universal model or verifier reliability."
        ),
    }
    result["sha256"] = digest(result)
    return result


def _pct(value: float | None) -> str:
    return "UNKNOWN" if value is None else f"{value * 100:.2f}%"


def _num(value: float | None, digits: int = 3) -> str:
    return "UNKNOWN" if value is None else f"{value:.{digits}f}"


def render_markdown(result: Mapping[str, Any]) -> str:
    manifest = result["manifest"]
    lines = [
        "# Residual Reliability Study",
        "",
        f"**Study:** `{manifest['study_id']}`  ",
        f"**Source revision:** `{manifest['source_revision']}`  ",
        f"**Suite SHA-256:** `{manifest['suite_sha256']}`  ",
        f"**Manifest SHA-256:** `{result['manifest_sha256']}`  ",
        f"**Result SHA-256:** `{result['sha256']}`",
        "",
        "## Primary results",
        "",
        "| Configuration | AER | Accepted correctness | Acceptance | FCR | Worker correctness | Cost USD | Cost / correct accepted | p95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for config in manifest["configurations"]:
        m = result["metrics_by_configuration"][config]
        lines.append(
            f"| `{config}` | {_pct(m['accepted_error_rate'])} | {_pct(m['accepted_correctness'])} | "
            f"{_pct(m['acceptance_rate'])} | {_pct(m['failure_containment_rate'])} | "
            f"{_pct(m['worker_correctness_rate'])} | {_num(m['cost_usd'])} | "
            f"{_num(m['cost_per_accepted_correct'])} | {_num(m['latency_p95_ms'], 1)} |"
        )
    lines.extend(["", "## Comparison to baseline", "", f"Baseline: `{manifest['baseline_configuration']}`", ""])
    for config in manifest["configurations"]:
        c = result["comparisons_to_baseline"][config]
        lines.append(
            f"- **{config}:** AER delta {_pct(c['accepted_error_rate_delta_vs_baseline'])}; "
            f"relative AER reduction {_pct(c['accepted_error_rate_relative_reduction_vs_baseline'])}; "
            f"acceptance delta {_pct(c['acceptance_rate_delta_vs_baseline'])}."
        )
    lines.extend(["", "## Model degradation", ""])
    for level, configs in result["degradation_curves"].items():
        lines.append(f"### {level}")
        lines.append("")
        lines.append("| Configuration | Worker correctness | AER | Accepted correctness | Acceptance |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for config, m in configs.items():
            lines.append(
                f"| `{config}` | {_pct(m['worker_correctness_rate'])} | {_pct(m['accepted_error_rate'])} | "
                f"{_pct(m['accepted_correctness'])} | {_pct(m['acceptance_rate'])} |"
            )
        lines.append("")
    lines.extend([
        "## Interpretation boundary",
        "",
        result["claim_scope"],
        "",
        "The headline metric is **Accepted Error Rate (AER)**: incorrect independently graded outputs divided by all accepted outputs. "
        "A low AER is not sufficient by itself; it must be interpreted together with acceptance rate, cost, latency, and failure containment so a system cannot appear reliable merely by rejecting nearly everything.",
        "",
    ])
    return "\n".join(lines)


def _svg_line_chart(result: Mapping[str, Any]) -> str:
    levels = list(result["degradation_curves"].keys())
    configs = list(result["manifest"]["configurations"])
    width, height = 900, 520
    left, top, plot_w, plot_h = 80, 50, 760, 380
    def x_at(index: int) -> float:
        return left + (plot_w * index / max(1, len(levels) - 1))
    def y_at(value: float) -> float:
        return top + plot_h * (1.0 - value)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="black"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="black"/>',
        '<text x="450" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">Accepted Error Rate under Worker Degradation</text>',
    ]
    for tick in range(0, 101, 20):
        value = tick / 100
        y = y_at(value)
        parts.append(f'<line x1="{left-5}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="black"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{tick}%</text>')
    for i, level in enumerate(levels):
        x = x_at(i)
        parts.append(f'<text x="{x:.1f}" y="{top+plot_h+24}" text-anchor="middle" font-family="sans-serif" font-size="11">{level}</text>')
    dash_patterns = ["", "6,4", "2,3", "10,4", "4,2,1,2", "12,3,2,3", "1,2"]
    for ci, config in enumerate(configs):
        points = []
        for i, level in enumerate(levels):
            m = result["degradation_curves"][level].get(config)
            if not m or m["accepted_error_rate"] is None:
                continue
            points.append((x_at(i), y_at(m["accepted_error_rate"])))
        if len(points) >= 2:
            coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            dash = dash_patterns[ci % len(dash_patterns)]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            parts.append(f'<polyline points="{coords}" fill="none" stroke="black" stroke-width="2"{dash_attr}/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="black"/>')
        legend_y = top + ci * 22
        parts.append(f'<text x="{left+plot_w+12}" y="{legend_y+4}" font-family="sans-serif" font-size="10">{config}</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def write_artifacts(result: Mapping[str, Any], output_dir: str | Path) -> None:
    out = Path(output_dir)
    figures = out / "figures"
    out.mkdir(parents=True, exist_ok=False)
    figures.mkdir()
    (out / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "report.md").write_text(render_markdown(result), encoding="utf-8")
    evidence_manifest = {
        "schema_version": "residual.reliability-evidence-manifest.v1",
        "study_id": result["manifest"]["study_id"],
        "source_revision": result["manifest"]["source_revision"],
        "suite_sha256": result["manifest"]["suite_sha256"],
        "study_manifest_sha256": result["manifest_sha256"],
        "observation_sha256": result["observation_sha256"],
        "result_sha256": result["sha256"],
        "evidence_hashes": result["evidence_hashes"],
    }
    evidence_manifest["sha256"] = digest(evidence_manifest)
    (out / "evidence-manifest.json").write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (figures / "degradation-aer.svg").write_text(_svg_line_chart(result), encoding="utf-8")
    with (out / "plot-data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["degradation_level", "configuration", "worker_correctness_rate", "accepted_error_rate", "accepted_correctness", "acceptance_rate"])
        for level, configs in result["degradation_curves"].items():
            for config, metrics in configs.items():
                writer.writerow([
                    level, config, metrics["worker_correctness_rate"], metrics["accepted_error_rate"],
                    metrics["accepted_correctness"], metrics["acceptance_rate"],
                ])
