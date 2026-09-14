"""Machine-verifiable preregistration and evidence bundles for live external assurance runs."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..core import canonical, digest, strict_json
from .external import ExternalSuite, load_external_suite


_MANIFEST_SCHEMA = "residual.external-preregistration.v1"
_BUNDLE_SCHEMA = "residual.external-evidence-bundle.v1"
_ALLOWED_METRICS = {
    "market_success_rate",
    "oracle_success_rate",
    "oracle_gap",
    "per_engine_success_rate",
}
_ALLOWED_ENGINE_FIELDS = {
    "provider", "model", "capabilities", "locality", "max_tokens", "temperature",
    "system_prompt", "cost_per_task", "privacy_class", "location",
}
_FORBIDDEN_ENGINE_FIELDS = {
    "api_key", "token", "secret", "password", "headers", "endpoint", "base_url",
}


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"invalid {label}: expected keys {sorted(expected)}")


def load_engine_config_payload(path: str | Path) -> dict[str, Any]:
    raw = strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid engine config")
    _require_keys(raw, {"schema_version", "engines"}, "engine config")
    if raw["schema_version"] != "residual.external-engines.v1":
        raise ValueError("invalid engine config schema")
    if not isinstance(raw["engines"], list) or len(raw["engines"]) < 2:
        raise ValueError("at least two engines are required")
    for item in raw["engines"]:
        if not isinstance(item, dict):
            raise ValueError("invalid engine entry")
        if _FORBIDDEN_ENGINE_FIELDS.intersection(item):
            raise ValueError("engine config must not contain credentials or endpoints")
        if set(item) - _ALLOWED_ENGINE_FIELDS:
            raise ValueError("invalid engine entry")
        for required in ("provider", "model"):
            if not isinstance(item.get(required), str) or not item[required].strip():
                raise ValueError(f"engine {required} is required")
        capabilities = item.get("capabilities", ["text"])
        if not isinstance(capabilities, list) or not capabilities or any(not isinstance(v, str) or not v for v in capabilities):
            raise ValueError("engine capabilities must be a non-empty string list")
        cost = item.get("cost_per_task", 0.0)
        if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
            raise ValueError("cost_per_task must be a finite non-negative number")
        privacy = item.get("privacy_class", 0)
        if type(privacy) is not int or privacy < 0:
            raise ValueError("privacy_class must be a non-negative integer")
    return raw


def engine_config_sha256(path: str | Path) -> str:
    return digest(load_engine_config_payload(path))


def projected_declared_cost_usd(suite: ExternalSuite, engines_path: str | Path) -> float:
    raw = load_engine_config_payload(engines_path)
    per_case = sum(float(item.get("cost_per_task", 0.0)) for item in raw["engines"])
    return per_case * len(suite.cases)


def projected_provider_calls(suite: ExternalSuite, engines_path: str | Path) -> int:
    raw = load_engine_config_payload(engines_path)
    return len(suite.cases) * len(raw["engines"])


@dataclass(frozen=True)
class ExternalPreregistration:
    study_id: str
    registered_at: str
    suite_sha256: str
    engine_config_sha256: str
    hypotheses: tuple[str, ...]
    primary_metric: str
    secondary_metrics: tuple[str, ...]
    stopping_rule: Mapping[str, Any]
    maximum_budget_usd: float
    runner_revision: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.study_id or not self.registered_at or not self.runner_revision:
            raise ValueError("study_id, registered_at and runner_revision are required")
        for value, label in ((self.suite_sha256, "suite"), (self.engine_config_sha256, "engine config")):
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"invalid {label} sha256")
        if not self.hypotheses or any(not isinstance(h, str) or not h.strip() for h in self.hypotheses):
            raise ValueError("at least one non-empty hypothesis is required")
        if self.primary_metric not in _ALLOWED_METRICS:
            raise ValueError("unsupported primary metric")
        if any(m not in _ALLOWED_METRICS for m in self.secondary_metrics):
            raise ValueError("unsupported secondary metric")
        if self.primary_metric in self.secondary_metrics:
            raise ValueError("primary metric must not be duplicated in secondary metrics")
        if not isinstance(self.stopping_rule, Mapping) or set(self.stopping_rule) != {"kind", "value"}:
            raise ValueError("invalid stopping rule")
        if self.stopping_rule["kind"] not in {"fixed_evaluation_cases", "maximum_provider_calls"}:
            raise ValueError("unsupported stopping rule")
        if type(self.stopping_rule["value"]) is not int or self.stopping_rule["value"] < 1:
            raise ValueError("stopping rule value must be a positive integer")
        if type(self.maximum_budget_usd) not in (int, float) or not math.isfinite(self.maximum_budget_usd) or self.maximum_budget_usd < 0:
            raise ValueError("maximum_budget_usd must be finite and non-negative")

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": _MANIFEST_SCHEMA,
            "study_id": self.study_id,
            "registered_at": self.registered_at,
            "suite_sha256": self.suite_sha256,
            "engine_config_sha256": self.engine_config_sha256,
            "hypotheses": list(self.hypotheses),
            "primary_metric": self.primary_metric,
            "secondary_metrics": list(self.secondary_metrics),
            "stopping_rule": dict(self.stopping_rule),
            "maximum_budget_usd": float(self.maximum_budget_usd),
            "runner_revision": self.runner_revision,
            "notes": self.notes,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


def load_preregistration(path: str | Path) -> ExternalPreregistration:
    raw = strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid preregistration")
    _require_keys(raw, {
        "schema_version", "study_id", "registered_at", "suite_sha256",
        "engine_config_sha256", "hypotheses", "primary_metric",
        "secondary_metrics", "stopping_rule", "maximum_budget_usd",
        "runner_revision", "notes",
    }, "preregistration")
    if raw["schema_version"] != _MANIFEST_SCHEMA:
        raise ValueError("invalid preregistration schema")
    if not isinstance(raw["hypotheses"], list) or not isinstance(raw["secondary_metrics"], list):
        raise ValueError("invalid preregistration list fields")
    return ExternalPreregistration(
        study_id=raw["study_id"],
        registered_at=raw["registered_at"],
        suite_sha256=raw["suite_sha256"],
        engine_config_sha256=raw["engine_config_sha256"],
        hypotheses=tuple(raw["hypotheses"]),
        primary_metric=raw["primary_metric"],
        secondary_metrics=tuple(raw["secondary_metrics"]),
        stopping_rule=raw["stopping_rule"],
        maximum_budget_usd=raw["maximum_budget_usd"],
        runner_revision=raw["runner_revision"],
        notes=raw["notes"],
    )


def verify_preregistration(
    manifest: ExternalPreregistration,
    suite: ExternalSuite,
    engines_path: str | Path,
) -> None:
    if manifest.suite_sha256 != suite.sha256:
        raise ValueError("suite hash does not match preregistration")
    if manifest.engine_config_sha256 != engine_config_sha256(engines_path):
        raise ValueError("engine config hash does not match preregistration")
    evaluation_cases = sum(1 for case in suite.cases if case.split == "evaluation")
    if manifest.stopping_rule["kind"] == "fixed_evaluation_cases":
        if manifest.stopping_rule["value"] != evaluation_cases:
            raise ValueError("fixed evaluation stopping rule does not match suite")
    elif projected_provider_calls(suite, engines_path) > manifest.stopping_rule["value"]:
        raise ValueError("planned provider calls exceed preregistered stopping rule")
    projected_cost = projected_declared_cost_usd(suite, engines_path)
    if projected_cost > manifest.maximum_budget_usd + 1e-12:
        raise ValueError("projected declared cost exceeds preregistered budget")


def build_evidence_bundle(
    *,
    manifest: ExternalPreregistration,
    suite: ExternalSuite,
    engines_path: str | Path,
    report: Mapping[str, Any],
) -> dict[str, Any]:
    verify_preregistration(manifest, suite, engines_path)
    if report.get("suite_sha256") != suite.sha256:
        raise ValueError("report suite hash does not match preregistered suite")
    payload = {
        "schema_version": _BUNDLE_SCHEMA,
        "study_id": manifest.study_id,
        "preregistration": manifest.payload(),
        "preregistration_sha256": manifest.sha256,
        "suite_sha256": suite.sha256,
        "engine_config_sha256": engine_config_sha256(engines_path),
        "projected_declared_cost_usd": projected_declared_cost_usd(suite, engines_path),
        "projected_provider_calls": projected_provider_calls(suite, engines_path),
        "report": dict(report),
    }
    payload["sha256"] = digest(payload)
    return payload


def write_preregistration(path: str | Path, manifest: ExternalPreregistration) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical(manifest.payload()) + "\n", encoding="utf-8")


def preregister_from_files(
    *,
    study_id: str,
    registered_at: str,
    suite_path: str | Path,
    engines_path: str | Path,
    hypotheses: tuple[str, ...],
    primary_metric: str,
    secondary_metrics: tuple[str, ...],
    maximum_budget_usd: float,
    runner_revision: str,
    notes: str = "",
) -> ExternalPreregistration:
    suite = load_external_suite(suite_path)
    eval_count = sum(1 for case in suite.cases if case.split == "evaluation")
    manifest = ExternalPreregistration(
        study_id=study_id,
        registered_at=registered_at,
        suite_sha256=suite.sha256,
        engine_config_sha256=engine_config_sha256(engines_path),
        hypotheses=hypotheses,
        primary_metric=primary_metric,
        secondary_metrics=secondary_metrics,
        stopping_rule={"kind": "fixed_evaluation_cases", "value": eval_count},
        maximum_budget_usd=maximum_budget_usd,
        runner_revision=runner_revision,
        notes=notes,
    )
    verify_preregistration(manifest, suite, engines_path)
    return manifest
