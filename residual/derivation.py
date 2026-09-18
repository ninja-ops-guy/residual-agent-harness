"""Experimental proof-carrying derivation graph for M6.

The graph proves/checks only predicates that are explicitly encoded. It is not
a proof of natural-language scientific truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .core import ContractError, canonical, digest


class Author(str, Enum):
    HOST = "host"
    SCIENTIST = "scientist"
    PLANNER = "planner"
    REVIEWER = "reviewer"
    HUMAN = "human"


class NodeType(str, Enum):
    EVIDENCE_FACT = "evidence_fact"
    QUESTION = "question"
    FINDING = "finding"
    METRIC_DECISION = "metric_decision"
    METRIC_RESOLUTION = "metric_resolution"
    INVARIANT_VERDICT = "invariant_verdict"
    SEMANTIC_REVIEW = "semantic_review"
    ENVIRONMENT_VERDICT = "environment_verdict"
    IMPROVEMENT_SPEC = "improvement_spec"
    HUMAN_DECISION = "human_decision"
    CHALLENGE = "challenge"
    SUPERSESSION = "supersession"


class EdgeType(str, Enum):
    SUPPORTED_BY = "supported_by"
    SELECTED_TO_TEST = "selected_to_test"
    RESOLVES_TO = "resolves_to"
    REFINES = "refines"
    GENERALIZES = "generalizes"
    PRESERVES = "preserves"
    VIOLATES = "violates"
    CHALLENGES = "challenges"
    SUPERSEDES = "supersedes"
    REVIEWED_BY = "reviewed_by"
    QUALIFIED_UNDER = "qualified_under"
    AUTHORIZED_BY = "authorized_by"


class Validity(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    CHALLENGED = "challenged"
    UNKNOWN = "unknown"
    STALE_ENVIRONMENT = "stale_environment"
    SUPERSEDED = "superseded"


_REQUIRED_DEPENDENCY_EDGES = {
    EdgeType.SUPPORTED_BY,
    EdgeType.SELECTED_TO_TEST,
    EdgeType.RESOLVES_TO,
    EdgeType.PRESERVES,
    EdgeType.REVIEWED_BY,
    EdgeType.QUALIFIED_UNDER,
    EdgeType.AUTHORIZED_BY,
}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class DerivationNode:
    node_type: NodeType
    author: Author
    payload: Mapping[str, Any]
    schema_revision: str = "residual.derivation.node.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.node_type, NodeType):
            object.__setattr__(self, "node_type", NodeType(self.node_type))
        if not isinstance(self.author, Author):
            object.__setattr__(self, "author", Author(self.author))
        if not isinstance(self.payload, Mapping):
            raise ContractError("derivation node payload must be a mapping")
        if not isinstance(self.schema_revision, str) or not self.schema_revision.strip():
            raise ContractError("node schema_revision is required")
        object.__setattr__(self, "payload", _freeze(self.payload))

    def content(self) -> dict[str, Any]:
        return {
            "schema_revision": self.schema_revision,
            "node_type": self.node_type.value,
            "author": self.author.value,
            "payload": _thaw(self.payload),
        }

    @property
    def node_id(self) -> str:
        return digest(self.content())


@dataclass(frozen=True)
class DerivationEdge:
    edge_type: EdgeType
    source: str
    target: str
    predicate: Mapping[str, Any]
    schema_revision: str = "residual.derivation.edge.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.edge_type, EdgeType):
            object.__setattr__(self, "edge_type", EdgeType(self.edge_type))
        for name in ("source", "target", "schema_revision"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(f"edge {name} is required")
        if self.source == self.target:
            raise ContractError("self edges are forbidden")
        if not isinstance(self.predicate, Mapping):
            raise ContractError("edge predicate must be a mapping")
        object.__setattr__(self, "predicate", _freeze(self.predicate))

    def content(self) -> dict[str, Any]:
        return {
            "schema_revision": self.schema_revision,
            "edge_type": self.edge_type.value,
            "source": self.source,
            "target": self.target,
            "predicate": _thaw(self.predicate),
        }

    @property
    def edge_id(self) -> str:
        return digest(self.content())


_ALLOWED: dict[EdgeType, set[tuple[NodeType, NodeType]]] = {
    EdgeType.SUPPORTED_BY: {
        (NodeType.FINDING, NodeType.EVIDENCE_FACT),
        (NodeType.IMPROVEMENT_SPEC, NodeType.FINDING),
    },
    EdgeType.SELECTED_TO_TEST: {
        (NodeType.METRIC_DECISION, NodeType.FINDING),
        (NodeType.METRIC_DECISION, NodeType.QUESTION),
    },
    EdgeType.RESOLVES_TO: {
        (NodeType.METRIC_DECISION, NodeType.METRIC_RESOLUTION),
    },
    EdgeType.PRESERVES: {
        (NodeType.IMPROVEMENT_SPEC, NodeType.INVARIANT_VERDICT),
    },
    EdgeType.VIOLATES: {
        (NodeType.INVARIANT_VERDICT, NodeType.IMPROVEMENT_SPEC),
    },
    EdgeType.REVIEWED_BY: {
        (NodeType.FINDING, NodeType.SEMANTIC_REVIEW),
        (NodeType.METRIC_DECISION, NodeType.SEMANTIC_REVIEW),
        (NodeType.IMPROVEMENT_SPEC, NodeType.SEMANTIC_REVIEW),
    },
    EdgeType.QUALIFIED_UNDER: {
        (NodeType.IMPROVEMENT_SPEC, NodeType.ENVIRONMENT_VERDICT),
    },
    EdgeType.AUTHORIZED_BY: {
        (NodeType.IMPROVEMENT_SPEC, NodeType.HUMAN_DECISION),
    },
    EdgeType.CHALLENGES: {
        (NodeType.CHALLENGE, node_type) for node_type in NodeType
    },
    EdgeType.SUPERSEDES: {
        (NodeType.SUPERSESSION, node_type) for node_type in NodeType
    },
    EdgeType.REFINES: {
        (NodeType.METRIC_RESOLUTION, NodeType.METRIC_RESOLUTION),
    },
    EdgeType.GENERALIZES: {
        (NodeType.METRIC_RESOLUTION, NodeType.METRIC_RESOLUTION),
    },
}


class DerivationGraph:
    def __init__(
        self,
        nodes: Iterable[DerivationNode],
        edges: Iterable[DerivationEdge],
    ):
        node_items = tuple(nodes)
        edge_items = tuple(edges)
        by_id: dict[str, DerivationNode] = {}
        for node in node_items:
            if not isinstance(node, DerivationNode):
                raise ContractError("graph nodes must be typed")
            if node.node_id in by_id:
                raise ContractError(f"duplicate node: {node.node_id}")
            by_id[node.node_id] = node
        edge_by_id: dict[str, DerivationEdge] = {}
        for edge in edge_items:
            if not isinstance(edge, DerivationEdge):
                raise ContractError("graph edges must be typed")
            if edge.edge_id in edge_by_id:
                raise ContractError(f"duplicate edge: {edge.edge_id}")
            if edge.source not in by_id or edge.target not in by_id:
                raise ContractError("edge references unknown node")
            pair = (by_id[edge.source].node_type, by_id[edge.target].node_type)
            allowed = _ALLOWED.get(edge.edge_type, set())
            if pair not in allowed:
                raise ContractError(
                    f"edge type {edge.edge_type.value} invalid for "
                    f"{pair[0].value}->{pair[1].value}"
                )
            edge_by_id[edge.edge_id] = edge
        self._nodes = MappingProxyType(by_id)
        self._edges = MappingProxyType(edge_by_id)
        self._assert_acyclic()

    @property
    def nodes(self) -> Mapping[str, DerivationNode]:
        return self._nodes

    @property
    def edges(self) -> Mapping[str, DerivationEdge]:
        return self._edges

    def _assert_acyclic(self) -> None:
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in self._nodes}
        for edge in self._edges.values():
            if edge.edge_type in {EdgeType.CHALLENGES, EdgeType.SUPERSEDES}:
                # Meta-edges annotate historical nodes and are excluded from
                # justification-DAG dependency traversal.
                continue
            outgoing[edge.source].append(edge.target)
        state: dict[str, int] = {}

        def visit(node_id: str) -> None:
            mark = state.get(node_id, 0)
            if mark == 1:
                raise ContractError("derivation graph contains a cycle")
            if mark == 2:
                return
            state[node_id] = 1
            for target in outgoing[node_id]:
                visit(target)
            state[node_id] = 2

        for node_id in sorted(self._nodes):
            visit(node_id)

    @property
    def graph_root(self) -> str:
        # Deterministic set commitment: insertion order cannot change the root.
        return digest({
            "schema_version": "residual.derivation.graph.v1",
            "nodes": sorted(self._nodes),
            "edges": sorted(self._edges),
        })

    def content(self) -> dict[str, Any]:
        return {
            "schema_version": "residual.derivation.graph.v1",
            "graph_root": self.graph_root,
            "nodes": [
                {"node_id": node_id, **self._nodes[node_id].content()}
                for node_id in sorted(self._nodes)
            ],
            "edges": [
                {"edge_id": edge_id, **self._edges[edge_id].content()}
                for edge_id in sorted(self._edges)
            ],
        }

    def validity(self) -> dict[str, Validity]:
        result = {node_id: Validity.VALID for node_id in self._nodes}

        # Explicit semantic/host verdict payloads can fail closed.
        for node_id, node in self._nodes.items():
            verdict = str(node.payload.get("verdict", "")).lower()
            if verdict in {"fail", "invalid", "rejected"}:
                result[node_id] = Validity.INVALID
            elif verdict in {"unknown"}:
                result[node_id] = Validity.UNKNOWN
            elif node.node_type == NodeType.ENVIRONMENT_VERDICT and verdict in {
                "stale", "incompatible"
            }:
                result[node_id] = Validity.STALE_ENVIRONMENT

        # Append-only challenge/supersession annotations.
        for edge in self._edges.values():
            if edge.edge_type == EdgeType.CHALLENGES:
                result[edge.target] = Validity.CHALLENGED
            elif edge.edge_type == EdgeType.SUPERSEDES:
                result[edge.target] = Validity.SUPERSEDED

        # A source node is a conclusion that depends on its required edge target.
        changed = True
        while changed:
            changed = False
            for edge in self._edges.values():
                if edge.edge_type not in _REQUIRED_DEPENDENCY_EDGES:
                    continue
                target_state = result[edge.target]
                if target_state == Validity.VALID:
                    continue
                source_state = result[edge.source]
                if source_state in {Validity.INVALID, Validity.SUPERSEDED}:
                    continue
                desired = (
                    Validity.STALE_ENVIRONMENT
                    if target_state == Validity.STALE_ENVIRONMENT
                    else Validity.CHALLENGED
                )
                if source_state != desired:
                    result[edge.source] = desired
                    changed = True
        return result

    def improvement_admissible(self, spec_id: str) -> tuple[bool, tuple[str, ...]]:
        try:
            spec = self._nodes[spec_id]
        except KeyError:
            raise ContractError("unknown ImprovementSpec node") from None
        if spec.node_type != NodeType.IMPROVEMENT_SPEC:
            raise ContractError("admission target is not an ImprovementSpec")

        states = self.validity()
        findings: list[str] = []
        if states[spec_id] != Validity.VALID:
            findings.append(f"spec validity is {states[spec_id].value}")

        required = {
            EdgeType.SUPPORTED_BY: False,
            EdgeType.PRESERVES: False,
            EdgeType.REVIEWED_BY: False,
            EdgeType.QUALIFIED_UNDER: False,
            EdgeType.AUTHORIZED_BY: False,
        }
        for edge in self._edges.values():
            if edge.source != spec_id or edge.edge_type not in required:
                continue
            if states[edge.target] != Validity.VALID:
                findings.append(
                    f"{edge.edge_type.value} target is {states[edge.target].value}"
                )
                continue
            target = self._nodes[edge.target]
            if edge.edge_type == EdgeType.REVIEWED_BY:
                if str(target.payload.get("verdict", "")).lower() != "valid":
                    findings.append("semantic review is not VALID")
                    continue
            if edge.edge_type == EdgeType.QUALIFIED_UNDER:
                if str(target.payload.get("verdict", "")).lower() != "pass":
                    findings.append("environment verdict is not PASS")
                    continue
            if edge.edge_type == EdgeType.AUTHORIZED_BY:
                if str(target.payload.get("decision", "")).lower() != "cosign":
                    findings.append("human decision is not COSIGN")
                    continue
            if edge.edge_type == EdgeType.PRESERVES:
                if str(target.payload.get("verdict", "")).lower() != "pass":
                    findings.append("protected invariant verdict is not PASS")
                    continue
            required[edge.edge_type] = True

        for edge_type, present in required.items():
            if not present:
                findings.append(f"missing valid {edge_type.value} justification")

        payload_required = (
            "intent", "mechanism", "predicted_effects",
            "verification_plan", "preservation_criteria", "rollback_plan",
        )
        for field in payload_required:
            if field not in spec.payload:
                findings.append(f"ImprovementSpec missing {field}")

        return (not findings, tuple(findings))
