"""Restricted formal refinement rules for composite metric expressions.

This checker is intentionally conservative. UNKNOWN is preferred over
natural-language inference or pairwise heuristics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .core import ContractError


class Refinement(str, Enum):
    EXACTLY_EQUIVALENT = "exactly_equivalent"
    STRICT_REFINEMENT = "strict_refinement"
    COARSENING = "coarsening"
    INCOMPARABLE = "incomparable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Atomic:
    metric_id: str
    unit_dimension: str


@dataclass(frozen=True)
class Compare:
    expr: "MetricExpr"
    operator: str
    threshold: float


@dataclass(frozen=True)
class And:
    children: tuple["MetricExpr", ...]


@dataclass(frozen=True)
class Or:
    children: tuple["MetricExpr", ...]


@dataclass(frozen=True)
class Not:
    child: "MetricExpr"


MetricExpr = Atomic | Compare | And | Or | Not


def _combine_same_topology(relations: list[Refinement]) -> Refinement:
    if not relations:
        return Refinement.UNKNOWN
    if any(r in {Refinement.UNKNOWN, Refinement.INCOMPARABLE} for r in relations):
        return Refinement.UNKNOWN
    if any(r == Refinement.COARSENING for r in relations):
        # A mixed refine/coarsen composite cannot be reduced safely without a
        # stronger expression-level proof rule.
        return Refinement.UNKNOWN
    if all(r == Refinement.EXACTLY_EQUIVALENT for r in relations):
        return Refinement.EXACTLY_EQUIVALENT
    if all(r in {Refinement.EXACTLY_EQUIVALENT, Refinement.STRICT_REFINEMENT} for r in relations):
        return Refinement.STRICT_REFINEMENT
    return Refinement.UNKNOWN


def _threshold_relation(operator: str, candidate: float, base: float) -> Refinement:
    if candidate == base:
        return Refinement.EXACTLY_EQUIVALENT
    if operator in {"<", "<="}:
        return Refinement.STRICT_REFINEMENT if candidate < base else Refinement.COARSENING
    if operator in {">", ">="}:
        return Refinement.STRICT_REFINEMENT if candidate > base else Refinement.COARSENING
    if operator == "==":
        return Refinement.INCOMPARABLE
    return Refinement.UNKNOWN


def expression_refinement(
    candidate: MetricExpr,
    base: MetricExpr,
    *,
    atomic_relations: Mapping[tuple[str, str], Refinement],
) -> Refinement:
    """Return whether candidate is a conservative refinement of base."""
    if type(candidate) is not type(base):
        return Refinement.UNKNOWN

    if isinstance(candidate, Atomic) and isinstance(base, Atomic):
        if candidate.unit_dimension != base.unit_dimension:
            return Refinement.INCOMPARABLE
        if candidate.metric_id == base.metric_id:
            return Refinement.EXACTLY_EQUIVALENT
        return atomic_relations.get(
            (candidate.metric_id, base.metric_id),
            Refinement.UNKNOWN,
        )

    if isinstance(candidate, Compare) and isinstance(base, Compare):
        if candidate.operator != base.operator:
            return Refinement.UNKNOWN
        child=expression_refinement(
            candidate.expr,base.expr,atomic_relations=atomic_relations
        )
        if child in {Refinement.UNKNOWN, Refinement.INCOMPARABLE, Refinement.COARSENING}:
            return Refinement.UNKNOWN
        threshold=_threshold_relation(
            candidate.operator,candidate.threshold,base.threshold
        )
        return _combine_same_topology([child,threshold])

    if isinstance(candidate, And) and isinstance(base, And):
        if len(candidate.children) != len(base.children):
            return Refinement.UNKNOWN
        return _combine_same_topology([
            expression_refinement(c,b,atomic_relations=atomic_relations)
            for c,b in zip(candidate.children,base.children)
        ])

    if isinstance(candidate, Or) and isinstance(base, Or):
        if len(candidate.children) != len(base.children):
            return Refinement.UNKNOWN
        return _combine_same_topology([
            expression_refinement(c,b,atomic_relations=atomic_relations)
            for c,b in zip(candidate.children,base.children)
        ])

    if isinstance(candidate, Not) and isinstance(base, Not):
        child=expression_refinement(
            candidate.child,base.child,atomic_relations=atomic_relations
        )
        if child == Refinement.STRICT_REFINEMENT:
            return Refinement.COARSENING
        if child == Refinement.COARSENING:
            return Refinement.STRICT_REFINEMENT
        return child

    raise ContractError("unsupported metric expression")
