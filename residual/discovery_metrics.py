"""Versioned semantic metric identities for bounded M6 discovery.

A metric name/value pair is not enough to establish semantic identity.
This module is host-owned trust infrastructure: models may reference or
propose metrics, but they cannot mutate the active registry.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .core import ContractError, canonical, digest


_METRIC_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIRECTIONS = {"lower_is_better", "higher_is_better", "target", "contextual"}
_AMBIGUOUS_POPULATION = (
    "normal conditions",
    "normal operating conditions",
    "typical conditions",
    "usual conditions",
    "representative conditions",
)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _text(value, name)
    if _SHA256.fullmatch(value) is None:
        raise ContractError(f"{name} must be a lowercase SHA-256 digest")
    return value


def metric_id(value: Any) -> str:
    value = _text(value, "metric_id")
    if _METRIC_ID.fullmatch(value) is None:
        raise ContractError("metric_id must be canonical lowercase snake_case")
    return value


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    description: str
    unit: str
    aggregation: str
    population: str
    valid_domain: str
    directionality: str
    collection_method: str
    implementation_ref: str
    revision: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", metric_id(self.metric_id))
        for name in (
            "description", "unit", "aggregation", "population", "valid_domain",
            "collection_method", "implementation_ref", "revision",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        direction = _text(self.directionality, "directionality")
        if direction not in _DIRECTIONS:
            raise ContractError("invalid metric directionality")
        object.__setattr__(self, "directionality", direction)

    def content(self) -> dict[str, str]:
        return {
            "metric_id": self.metric_id,
            "description": self.description,
            "unit": self.unit,
            "aggregation": self.aggregation,
            "population": self.population,
            "valid_domain": self.valid_domain,
            "directionality": self.directionality,
            "collection_method": self.collection_method,
            "implementation_ref": self.implementation_ref,
            "revision": self.revision,
        }

    @property
    def definition_sha256(self) -> str:
        return digest(self.content())

    def to_dict(self) -> dict[str, str]:
        return {**self.content(), "definition_sha256": self.definition_sha256}

    def exact_semantic_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.unit,
            self.aggregation,
            self.population,
            self.valid_domain,
            self.collection_method,
        )


@dataclass(frozen=True)
class MetricDefinitionProposal:
    definition: MetricDefinition
    evidence_snapshot_hash: str
    observed_metric: str
    observed_value: float
    reason_existing_registry_insufficient: str
    preserve_invariants: tuple[str, ...]
    human_approval_required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.definition, MetricDefinition):
            raise ContractError("definition must be MetricDefinition")
        object.__setattr__(
            self, "evidence_snapshot_hash",
            _sha256(self.evidence_snapshot_hash, "evidence_snapshot_hash"),
        )
        object.__setattr__(self, "observed_metric", metric_id(self.observed_metric))
        if type(self.observed_value) not in (int, float):
            raise ContractError("observed_value must be numeric")
        object.__setattr__(
            self, "reason_existing_registry_insufficient",
            _text(
                self.reason_existing_registry_insufficient,
                "reason_existing_registry_insufficient",
            ),
        )
        if (
            not isinstance(self.preserve_invariants, (tuple, list))
            or not self.preserve_invariants
            or any(not isinstance(v, str) or not v.strip() for v in self.preserve_invariants)
        ):
            raise ContractError("preserve_invariants must contain nonempty IDs")
        object.__setattr__(self, "preserve_invariants", tuple(self.preserve_invariants))
        if self.human_approval_required is not True:
            raise ContractError("metric proposals must retain human approval")

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": self.definition.to_dict(),
            "evidence_snapshot_hash": self.evidence_snapshot_hash,
            "observed_metric": self.observed_metric,
            "observed_value": self.observed_value,
            "reason_existing_registry_insufficient": self.reason_existing_registry_insufficient,
            "preserve_invariants": list(self.preserve_invariants),
            "human_approval_required": True,
        }


class ProposalDisposition(str, Enum):
    REJECT = "reject"
    UNKNOWN = "unknown"
    SEMANTIC_REVIEW = "semantic_review"


@dataclass(frozen=True)
class ProposalAssessment:
    disposition: ProposalDisposition
    findings: tuple[str, ...]
    similar_metric_ids: tuple[str, ...] = ()

    @property
    def mechanically_admissible(self) -> bool:
        return self.disposition == ProposalDisposition.SEMANTIC_REVIEW


class MetricRegistry:
    """Immutable semantic registry.

    Construction validates identity and exact semantic uniqueness. No mutation
    API is exposed; a new registry revision is constructed between runs.
    """

    def __init__(self, revision: str, definitions: Iterable[MetricDefinition]):
        self._revision = _text(revision, "registry revision")
        items = tuple(definitions)
        if not items:
            raise ContractError("metric registry must not be empty")
        by_id: dict[str, MetricDefinition] = {}
        semantic: dict[tuple[str, str, str, str, str], str] = {}
        for definition in items:
            if not isinstance(definition, MetricDefinition):
                raise ContractError("registry definitions must be typed")
            if definition.metric_id in by_id:
                raise ContractError(f"duplicate metric_id: {definition.metric_id}")
            key = definition.exact_semantic_key()
            if key in semantic:
                raise ContractError(
                    f"exact semantic duplicate: {definition.metric_id} and {semantic[key]}"
                )
            by_id[definition.metric_id] = definition
            semantic[key] = definition.metric_id
        self._definitions = tuple(sorted(items, key=lambda d: d.metric_id))
        self._by_id: Mapping[str, MetricDefinition] = MappingProxyType(by_id)

    @property
    def revision(self) -> str:
        return self._revision

    @property
    def definitions(self) -> tuple[MetricDefinition, ...]:
        return self._definitions

    @property
    def registry_sha256(self) -> str:
        return digest(self.content())

    def content(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.discovery.metric-registry.v1",
            "revision": self.revision,
            "definitions": [d.to_dict() for d in self.definitions],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.content(), "registry_sha256": self.registry_sha256}

    def resolve(self, name: str) -> MetricDefinition:
        name = metric_id(name)
        try:
            return self._by_id[name]
        except KeyError:
            raise ContractError(f"unregistered discovery metric: {name}") from None

    def bind_snapshot(self, metrics: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(metrics, Mapping) or not metrics:
            raise ContractError("snapshot metrics must be a nonempty mapping")
        normalized: dict[str, int | float] = {}
        for name, value in metrics.items():
            definition = self.resolve(name)
            if type(value) not in (int, float):
                raise ContractError(f"metric {name} value must be numeric")
            normalized[definition.metric_id] = value
        return {
            "metric_registry_revision": self.revision,
            "metric_registry_sha256": self.registry_sha256,
            "metrics": normalized,
        }

    def validate_snapshot_binding(self, snapshot: Mapping[str, Any]) -> None:
        if not isinstance(snapshot, Mapping):
            raise ContractError("snapshot must be a mapping")
        if snapshot.get("metric_registry_revision") != self.revision:
            raise ContractError("metric registry revision mismatch")
        if snapshot.get("metric_registry_sha256") != self.registry_sha256:
            raise ContractError("metric registry hash mismatch")
        metrics = snapshot.get("metrics")
        if not isinstance(metrics, Mapping) or not metrics:
            raise ContractError("snapshot metrics missing")
        for name, value in metrics.items():
            self.resolve(name)
            if type(value) not in (int, float):
                raise ContractError(f"metric {name} value must be numeric")

    def validate_observation(self, name: str, value: Any, unit: str) -> None:
        definition = self.resolve(name)
        if _text(unit, "unit") != definition.unit:
            raise ContractError(
                f"metric unit mismatch for {definition.metric_id}: "
                f"expected {definition.unit}, got {unit}"
            )
        if type(value) not in (int, float):
            raise ContractError("observation value must be numeric")

    def assess_proposal(self, proposal: MetricDefinitionProposal) -> ProposalAssessment:
        if not isinstance(proposal, MetricDefinitionProposal):
            raise ContractError("proposal must be MetricDefinitionProposal")
        if proposal.observed_metric not in self._by_id:
            return ProposalAssessment(
                ProposalDisposition.REJECT,
                ("observed anomaly metric is not registered",),
            )

        candidate = proposal.definition
        if candidate.metric_id in self._by_id:
            return ProposalAssessment(
                ProposalDisposition.REJECT,
                (f"metric_id already registered: {candidate.metric_id}",),
                (candidate.metric_id,),
            )

        semantic_matches = tuple(
            d.metric_id
            for d in self.definitions
            if d.exact_semantic_key() == candidate.exact_semantic_key()
        )
        if semantic_matches:
            return ProposalAssessment(
                ProposalDisposition.REJECT,
                ("exact semantic duplicate under a different metric_id",),
                semantic_matches,
            )

        findings: list[str] = []
        similar: set[str] = set()
        candidate_tokens = set(candidate.metric_id.split("_"))
        for existing in self.definitions:
            ratio = SequenceMatcher(None, candidate.metric_id, existing.metric_id).ratio()
            existing_tokens = set(existing.metric_id.split("_"))
            token_overlap = (
                len(candidate_tokens & existing_tokens)
                / max(1, min(len(candidate_tokens), len(existing_tokens)))
            )
            if ratio >= 0.78 or token_overlap >= 0.8:
                similar.add(existing.metric_id)

        population = candidate.population.lower()
        if any(term in population for term in _AMBIGUOUS_POPULATION):
            findings.append(
                "population uses an ambiguous condition without a deterministic inclusion rule"
            )
        if similar:
            findings.append("metric identity has likely spelling/semantic overlap with registered metrics")

        if findings:
            return ProposalAssessment(
                ProposalDisposition.UNKNOWN,
                tuple(findings),
                tuple(sorted(similar)),
            )
        return ProposalAssessment(
            ProposalDisposition.SEMANTIC_REVIEW,
            ("mechanical registry checks passed; independent semantic review required",),
        )


def load_metric_registry(path: str | Path) -> MetricRegistry:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("invalid metric registry document") from exc
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "revision", "definitions"}:
        raise ContractError("invalid metric registry document shape")
    if raw["schema_version"] != "residual.discovery.metric-registry.v1":
        raise ContractError("unsupported metric registry schema")
    if not isinstance(raw["definitions"], list):
        raise ContractError("registry definitions must be a list")
    definitions: list[MetricDefinition] = []
    expected = {
        "metric_id", "description", "unit", "aggregation", "population",
        "valid_domain", "directionality", "collection_method",
        "implementation_ref", "revision", "definition_sha256",
    }
    for item in raw["definitions"]:
        if not isinstance(item, dict) or set(item) != expected:
            raise ContractError("invalid metric definition shape")
        wire_hash = item["definition_sha256"]
        definition = MetricDefinition(**{k: item[k] for k in expected if k != "definition_sha256"})
        if wire_hash != definition.definition_sha256:
            raise ContractError(f"metric definition hash mismatch: {definition.metric_id}")
        definitions.append(definition)
    return MetricRegistry(raw["revision"], definitions)


def admission_binding(
    *,
    evidence_snapshot_hash: str,
    registry: MetricRegistry,
    verifier_rules: Mapping[str, Any],
) -> dict[str, str]:
    """Return explicit hashes to bind into an existing StationReceipt.

    StationReceipt v2 stays unchanged. Callers bind this context through the
    receipt cache_key and verifier_revision rather than weakening/changing the
    protected receipt schema.
    """
    snapshot_hash = _sha256(evidence_snapshot_hash, "evidence_snapshot_hash")
    if not isinstance(verifier_rules, Mapping) or not verifier_rules:
        raise ContractError("verifier_rules must be a nonempty mapping")
    context = {
        "evidence_snapshot_hash": snapshot_hash,
        "metric_registry_revision": registry.revision,
        "metric_registry_sha256": registry.registry_sha256,
    }
    return {
        "cache_key": digest({"discovery_context": context}),
        "verifier_revision": digest(
            {"metric_registry": context, "verifier_rules": dict(verifier_rules)}
        ),
    }
