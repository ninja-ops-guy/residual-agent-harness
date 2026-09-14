"""Externally authored assurance workload support and live heterogeneous-engine evaluation."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..core import canonical, digest, strict_json
from ..engines.protocol import ContextAssembly, TaskSpec
from ..engines.provider_bridge import ProviderExecutionEngine
from .market import MarketProfile, MarketRequest, VerifiedComputeMarket
from .quality import AssuranceClass


_ALLOWED_SPLITS = {"train", "evaluation"}
_ALLOWED_GRADERS = {"exact_text", "contains_all", "json_exact", "regex"}


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
    """Run every engine on train/eval cases, then evaluate VCM only on eval cases.

    The market is trained from independently graded train outcomes. Evaluation
    decisions never update profiles until after the decision is recorded.
    """

    def __init__(self, suite: ExternalSuite, engines: Iterable[LiveEngineSpec]):
        self.suite = suite
        self.engines = tuple(engines)
        if len(self.engines) < 2:
            raise ValueError("heterogeneous evidence requires at least two engines")
        ids = [e.engine.engine_id for e in self.engines]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate engine id")

    def run(self) -> dict[str, Any]:
        observations: dict[tuple[str, str], dict[str, Any]] = {}
        for case in self.suite.cases:
            for spec in self.engines:
                task = TaskSpec(case.case_id, case.capability, case.prompt, {"assurance": case.assurance.value})
                try:
                    result = spec.engine.execute(task, ContextAssembly())
                    passed = grade_external(result.candidate, case.grader)
                    observations[(case.case_id, spec.engine.engine_id)] = {
                        "passed": passed,
                        "latency_ms": result.wall_clock_ms,
                        "token_usage": result.token_usage,
                        "error": None,
                    }
                except Exception as exc:
                    observations[(case.case_id, spec.engine.engine_id)] = {
                        "passed": False,
                        "latency_ms": None,
                        "token_usage": None,
                        "error": exc.__class__.__name__,
                    }

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
        for case in self.suite.cases:
            if case.split != "train":
                continue
            for spec in self.engines:
                obs = observations[(case.case_id, spec.engine.engine_id)]
                market.update(spec.engine.engine_id, verifier_passed=bool(obs["passed"]), verifier_reliability=1.0)

        eval_rows = []
        market_successes = 0
        oracle_successes = 0
        for case in self.suite.cases:
            if case.split != "evaluation":
                continue
            decision = market.select(MarketRequest(
                capability=case.capability,
                required_pass_rate=case.required_pass_rate,
                allow_exploration=False,
            ))
            chosen = observations[(case.case_id, decision.engine_id)]
            passed = bool(chosen["passed"])
            market_successes += int(passed)
            oracle_successes += int(any(observations[(case.case_id, spec.engine.engine_id)]["passed"] for spec in self.engines))
            eval_rows.append({
                "case_id": case.case_id,
                "engine_id": decision.engine_id,
                "market_reason": decision.reason,
                "passed": passed,
                "latency_ms": chosen["latency_ms"],
                "token_usage": chosen["token_usage"],
            })
            market.update(decision.engine_id, verifier_passed=passed, verifier_reliability=1.0)

        eval_count = len(eval_rows)
        per_engine = {}
        for spec in self.engines:
            engine_id = spec.engine.engine_id
            train = [c for c in self.suite.cases if c.split == "train"]
            evaluation = [c for c in self.suite.cases if c.split == "evaluation"]
            per_engine[engine_id] = {
                "provider": spec.engine.config.provider,
                "model": spec.engine.config.model,
                "train_successes": sum(observations[(c.case_id, engine_id)]["passed"] for c in train),
                "train_total": len(train),
                "evaluation_successes": sum(observations[(c.case_id, engine_id)]["passed"] for c in evaluation),
                "evaluation_total": len(evaluation),
                "cost_per_task": spec.cost_per_task,
            }
        report = {
            "schema_version": "residual.external-evidence.v1",
            "suite_name": self.suite.name,
            "suite_sha256": self.suite.sha256,
            "provenance": {"author": self.suite.author, "source_uri": self.suite.source_uri, "authored_at": self.suite.authored_at},
            "engine_count": len(self.engines),
            "per_engine": per_engine,
            "market": {
                "evaluation_successes": market_successes,
                "evaluation_total": eval_count,
                "success_rate": market_successes / eval_count if eval_count else 0.0,
                "oracle_successes": oracle_successes,
                "oracle_success_rate": oracle_successes / eval_count if eval_count else 0.0,
            },
            "evaluation_rows": eval_rows,
            "claim_scope": "Live externally-authored workload evidence; conclusions remain scoped to the supplied suite, engines, models, prices, and execution environment.",
        }
        report["sha256"] = digest(report)
        return report
