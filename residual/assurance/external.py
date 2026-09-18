"""Externally authored assurance workload support and live heterogeneous-engine evaluation."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Mapping

from ..core import canonical, digest, strict_json
from ..engines.protocol import ContextAssembly, TaskSpec
from ..engines.provider_bridge import ProviderExecutionEngine
from .market import MarketProfile, MarketRequest, VerifiedComputeMarket
from .quality import AssuranceClass


_ALLOWED_SPLITS = {"train", "evaluation"}
_ALLOWED_GRADERS = {"exact_text", "contains_all", "json_exact", "regex"}


class EvidenceBudgetExceeded(RuntimeError):
    """Declared spend would exceed the frozen ceiling before provider dispatch."""


def wilson_interval(successes: int, total: int, z: float = 1.96) -> dict[str, float]:
    """Return a Wilson score interval for a Bernoulli success proportion."""
    if type(successes) is not int or type(total) is not int or total < 0 or successes < 0 or successes > total:
        raise ValueError("invalid successes/total")
    if total == 0:
        return {"lower": 0.0, "upper": 0.0, "confidence": 0.95}
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    radius = (z / denom) * math.sqrt((p * (1.0 - p) / total) + ((z * z) / (4.0 * total * total)))
    return {"lower": max(0.0, center - radius), "upper": min(1.0, center + radius), "confidence": 0.95}


@dataclass(frozen=True)
class ExternalCase:
    case_id: str
    split: str
    capability: str
    assurance: AssuranceClass
    required_pass_rate: float
    prompt: str
    grader: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.case_id or not self.capability or not self.prompt:
            raise ValueError("case id, capability and prompt are required")
        if self.split not in _ALLOWED_SPLITS:
            raise ValueError("invalid split")
        if not 0 <= self.required_pass_rate <= 1:
            raise ValueError("required_pass_rate must be in [0,1]")
        kind = self.grader.get("kind") if isinstance(self.grader, Mapping) else None
        if kind not in _ALLOWED_GRADERS:
            raise ValueError("unsupported grader")

    def payload(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "split": self.split,
            "capability": self.capability,
            "assurance": self.assurance.value,
            "required_pass_rate": self.required_pass_rate,
            "prompt": self.prompt,
            "grader": dict(self.grader),
        }


@dataclass(frozen=True)
class ExternalSuite:
    name: str
    author: str
    source_uri: str
    authored_at: str
    cases: tuple[ExternalCase, ...]

    def __post_init__(self) -> None:
        if not all((self.name, self.author, self.source_uri, self.authored_at)):
            raise ValueError("external provenance fields are required")
        if not self.cases:
            raise ValueError("external suite requires cases")
        ids = [c.case_id for c in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate external case id")
        if not any(c.split == "train" for c in self.cases) or not any(c.split == "evaluation" for c in self.cases):
            raise ValueError("external suite requires train and evaluation cases")

    @property
    def sha256(self) -> str:
        return digest({
            "schema_version": "residual.external-suite.v1",
            "name": self.name,
            "author": self.author,
            "source_uri": self.source_uri,
            "authored_at": self.authored_at,
            "cases": [c.payload() for c in self.cases],
        })


def load_external_suite(path: str | Path) -> ExternalSuite:
    raw = strict_json(Path(path).read_text(encoding="utf-8"))
    required = {"schema_version", "name", "provenance", "cases"}
    if not isinstance(raw, dict) or set(raw) != required or raw["schema_version"] != "residual.external-suite.v1":
        raise ValueError("invalid external suite")
    provenance = raw["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"evidence_level", "author", "source_uri", "authored_at"}:
        raise ValueError("invalid external provenance")
    if provenance["evidence_level"] != "externally_authored":
        raise ValueError("external suite must declare externally_authored evidence")
    cases = []
    for item in raw["cases"]:
        if not isinstance(item, dict) or set(item) != {"id", "split", "capability", "assurance", "required_pass_rate", "prompt", "grader"}:
            raise ValueError("invalid external case")
        cases.append(ExternalCase(
            case_id=item["id"], split=item["split"], capability=item["capability"],
            assurance=AssuranceClass(item["assurance"]), required_pass_rate=item["required_pass_rate"],
            prompt=item["prompt"], grader=item["grader"],
        ))
    return ExternalSuite(raw["name"], provenance["author"], provenance["source_uri"], provenance["authored_at"], tuple(cases))


def grade_external(candidate: Any, grader: Mapping[str, Any]) -> bool:
    kind = grader["kind"]
    text = candidate if isinstance(candidate, str) else canonical(candidate)
    if kind == "exact_text":
        return text.strip() == str(grader.get("expected", "")).strip()
    if kind == "contains_all":
        values = grader.get("values")
        return isinstance(values, list) and all(str(v).lower() in text.lower() for v in values)
    if kind == "regex":
        pattern = grader.get("pattern")
        return isinstance(pattern, str) and re.fullmatch(pattern, text.strip()) is not None
    if kind == "json_exact":
        try:
            parsed = strict_json(text)
        except Exception:
            return False
        return parsed == grader.get("expected")
    raise ValueError("unsupported grader")


@dataclass(frozen=True)
class LiveEngineSpec:
    engine: ProviderExecutionEngine
    cost_per_task: float
    privacy_class: int = 0
    location: str = "unknown"


class ExternalEvidenceRunner:
    """Run repeated train/evaluation trials across heterogeneous engines.

    Each trial starts with a fresh compute market trained only on that trial's
    train outcomes. Evaluation outcomes are applied only after the corresponding
    market decision has been recorded. Fixed baselines reuse the same observed
    engine outputs, so policy comparisons do not make additional provider calls.
    The optional budget reserves declared cost before every attempted dispatch,
    across all trials and repeated runs on this instance. Failed calls remain
    charged. This bounds declared accounting, not actual provider billing.
    """

    def __init__(self, suite: ExternalSuite, engines: Iterable[LiveEngineSpec], trials: int = 1,
                 *, maximum_budget_usd: float | None = None):
        self.suite = suite
        self.engines = tuple(engines)
        if len(self.engines) < 2:
            raise ValueError("heterogeneous evidence requires at least two engines")
        if type(trials) is not int or trials < 1:
            raise ValueError("trials must be a positive integer")
        self.trials = trials
        ids = [e.engine.engine_id for e in self.engines]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate engine id")
        for spec in self.engines:
            if not math.isfinite(spec.cost_per_task) or spec.cost_per_task < 0:
                raise ValueError("cost_per_task must be finite and non-negative")
        if maximum_budget_usd is not None:
            if not math.isfinite(maximum_budget_usd) or maximum_budget_usd < 0:
                raise ValueError("maximum_budget_usd must be finite and non-negative")
        self.maximum_budget_usd = maximum_budget_usd
        # Exact decimal input values avoid an epsilon that authorizes overspend.
        self._budget_limit = (None if maximum_budget_usd is None
                              else Fraction(str(maximum_budget_usd)))
        self._declared_costs = {spec.engine.engine_id: Fraction(str(spec.cost_per_task))
                                for spec in self.engines}
        self._reserved_cost_usd = Fraction(0)
        self._reservation_lock = Lock()

    def _reserve_provider_call(self, spec: LiveEngineSpec) -> None:
        with self._reservation_lock:
            next_total = self._reserved_cost_usd + self._declared_costs[spec.engine.engine_id]
            if self._budget_limit is not None and next_total > self._budget_limit:
                raise EvidenceBudgetExceeded("provider dispatch refused: declared budget exhausted")
            self._reserved_cost_usd = next_total

    def _new_market(self) -> VerifiedComputeMarket:
        market = VerifiedComputeMarket(exploration_strength=0.0)
        for spec in self.engines:
            market.register(MarketProfile(
                engine_id=spec.engine.engine_id,
                capabilities=frozenset(spec.engine.config.capabilities),
                cost_per_task=spec.cost_per_task,
                latency_ms=0.0,
                privacy_class=spec.privacy_class,
                location=spec.location,
            ))
        return market

    def _cheapest_engine(self, capability: str) -> LiveEngineSpec:
        eligible = [spec for spec in self.engines if capability in spec.engine.config.capabilities]
        if not eligible:
            raise ValueError(f"no engine supports capability {capability}")
        return min(eligible, key=lambda spec: (spec.cost_per_task, spec.engine.engine_id))

    def run(self) -> dict[str, Any]:
        observations: dict[tuple[int, str, str], dict[str, Any]] = {}
        for trial in range(1, self.trials + 1):
            for case in self.suite.cases:
                for spec in self.engines:
                    task = TaskSpec(
                        f"{case.case_id}:trial-{trial}", case.capability, case.prompt,
                        {"assurance": case.assurance.value, "trial": trial},
                    )
                    self._reserve_provider_call(spec)
                    try:
                        result = spec.engine.execute(task, ContextAssembly())
                        passed = grade_external(result.candidate, case.grader)
                        observations[(trial, case.case_id, spec.engine.engine_id)] = {
                            "passed": passed,
                            "latency_ms": result.wall_clock_ms,
                            "token_usage": result.token_usage,
                            "error": None,
                        }
                    except EvidenceBudgetExceeded:
                        raise
                    except Exception as exc:
                        observations[(trial, case.case_id, spec.engine.engine_id)] = {
                            "passed": False,
                            "latency_ms": None,
                            "token_usage": None,
                            "error": exc.__class__.__name__,
                        }

        evaluation = [c for c in self.suite.cases if c.split == "evaluation"]
        train = [c for c in self.suite.cases if c.split == "train"]
        eval_rows: list[dict[str, Any]] = []
        market_successes = 0
        oracle_successes = 0
        cheapest_successes = 0
        market_declared_cost = 0.0
        cheapest_declared_cost = 0.0

        for trial in range(1, self.trials + 1):
            market = self._new_market()
            for case in train:
                for spec in self.engines:
                    obs = observations[(trial, case.case_id, spec.engine.engine_id)]
                    market.update(spec.engine.engine_id, verifier_passed=bool(obs["passed"]), verifier_reliability=1.0)

            for case in evaluation:
                decision = market.select(MarketRequest(
                    capability=case.capability,
                    required_pass_rate=case.required_pass_rate,
                    allow_exploration=False,
                ))
                chosen = observations[(trial, case.case_id, decision.engine_id)]
                passed = bool(chosen["passed"])
                market_successes += int(passed)
                chosen_spec = next(spec for spec in self.engines if spec.engine.engine_id == decision.engine_id)
                market_declared_cost += chosen_spec.cost_per_task

                cheapest = self._cheapest_engine(case.capability)
                cheapest_obs = observations[(trial, case.case_id, cheapest.engine.engine_id)]
                cheapest_passed = bool(cheapest_obs["passed"])
                cheapest_successes += int(cheapest_passed)
                cheapest_declared_cost += cheapest.cost_per_task

                oracle_successes += int(any(
                    observations[(trial, case.case_id, spec.engine.engine_id)]["passed"]
                    for spec in self.engines
                ))
                eval_rows.append({
                    "trial": trial,
                    "case_id": case.case_id,
                    "engine_id": decision.engine_id,
                    "market_reason": decision.reason,
                    "passed": passed,
                    "latency_ms": chosen["latency_ms"],
                    "token_usage": chosen["token_usage"],
                    "cheapest_engine_id": cheapest.engine.engine_id,
                    "cheapest_passed": cheapest_passed,
                })
                market.update(decision.engine_id, verifier_passed=passed, verifier_reliability=1.0)

        eval_attempts = len(evaluation) * self.trials
        per_engine: dict[str, Any] = {}
        for spec in self.engines:
            engine_id = spec.engine.engine_id
            train_successes = sum(
                int(observations[(trial, case.case_id, engine_id)]["passed"])
                for trial in range(1, self.trials + 1) for case in train
            )
            eval_successes = sum(
                int(observations[(trial, case.case_id, engine_id)]["passed"])
                for trial in range(1, self.trials + 1) for case in evaluation
            )
            train_total = len(train) * self.trials
            per_engine[engine_id] = {
                "provider": spec.engine.config.provider,
                "model": spec.engine.config.model,
                "train_successes": train_successes,
                "train_total": train_total,
                "evaluation_successes": eval_successes,
                "evaluation_total": eval_attempts,
                "evaluation_success_rate": eval_successes / eval_attempts if eval_attempts else 0.0,
                "evaluation_success_ci95": wilson_interval(eval_successes, eval_attempts),
                "cost_per_task": spec.cost_per_task,
                "evaluation_declared_cost_usd": spec.cost_per_task * eval_attempts,
            }

        market_rate = market_successes / eval_attempts if eval_attempts else 0.0
        cheapest_rate = cheapest_successes / eval_attempts if eval_attempts else 0.0
        oracle_rate = oracle_successes / eval_attempts if eval_attempts else 0.0
        report = {
            "schema_version": "residual.external-evidence.v2",
            "suite_name": self.suite.name,
            "suite_sha256": self.suite.sha256,
            "provenance": {"author": self.suite.author, "source_uri": self.suite.source_uri, "authored_at": self.suite.authored_at},
            "engine_count": len(self.engines),
            "trials": self.trials,
            "evaluation_cases_per_trial": len(evaluation),
            "evaluation_attempts": eval_attempts,
            "budget": {
                "maximum_budget_usd": self.maximum_budget_usd,
                "reserved_declared_cost_usd": float(self._reserved_cost_usd),
                "accounting": "declared_per_task_not_provider_billing",
            },
            "per_engine": per_engine,
            "market": {
                "evaluation_successes": market_successes,
                "evaluation_total": eval_attempts,
                "success_rate": market_rate,
                "success_ci95": wilson_interval(market_successes, eval_attempts),
                "declared_cost_usd": market_declared_cost,
                "oracle_successes": oracle_successes,
                "oracle_success_rate": oracle_rate,
                "oracle_success_ci95": wilson_interval(oracle_successes, eval_attempts),
                "oracle_gap": oracle_rate - market_rate,
            },
            "baselines": {
                "cheapest_eligible": {
                    "evaluation_successes": cheapest_successes,
                    "evaluation_total": eval_attempts,
                    "success_rate": cheapest_rate,
                    "success_ci95": wilson_interval(cheapest_successes, eval_attempts),
                    "declared_cost_usd": cheapest_declared_cost,
                    "market_success_delta": market_rate - cheapest_rate,
                },
                "fixed_engine": {
                    engine_id: {
                        "success_rate": data["evaluation_success_rate"],
                        "success_ci95": data["evaluation_success_ci95"],
                        "declared_cost_usd": data["evaluation_declared_cost_usd"],
                    }
                    for engine_id, data in per_engine.items()
                },
            },
            "evaluation_rows": eval_rows,
            "claim_scope": "Repeated live externally-authored workload evidence; conclusions remain scoped to the supplied suite, trial count, engines, models, declared prices, and execution environment.",
        }
        report["sha256"] = digest(report)
        return report
