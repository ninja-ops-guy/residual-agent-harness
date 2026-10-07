"""VQ-R5: deterministic verifier ensembles with explicit aggregation policy.

Aggregation is pure: same member verdicts + same policy => same ensemble
verdict, with no wall-clock, ordering, or RNG dependence. Ties are
resolved by an explicit, declared tie-break rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from residual.core import ContractError


class AggregationPolicy(str, Enum):
    UNANIMOUS = "unanimous"        # accept iff all members accept
    MAJORITY = "majority"          # accept iff accepts > rejects (tie => tie_break)
    ANY = "any"                    # accept iff at least one member accepts


@dataclass(frozen=True)
class EnsembleVerdict:
    verdict: bool
    accepts: int
    rejects: int
    policy: str
    tie: bool
    tie_break: Optional[str]

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "accepts": self.accepts,
            "rejects": self.rejects,
            "policy": self.policy,
            "tie": self.tie,
            "tie_break": self.tie_break,
        }


class VerifierEnsemble:
    """Deterministic ensemble of member verifier callables.

    Members are stored sorted by name so aggregation never depends on
    registration order. tie_break applies only to MAJORITY ties and must
    be declared explicitly ("accept" or "reject"); default is fail-closed
    "reject".
    """

    def __init__(self, members: dict[str, Callable[[object], bool]],
                 policy: AggregationPolicy = AggregationPolicy.MAJORITY,
                 tie_break: str = "reject"):
        if not members:
            raise ContractError("ensemble requires at least one member")
        self.policy = AggregationPolicy(policy)
        if tie_break not in ("accept", "reject"):
            raise ContractError("tie_break must be 'accept' or 'reject'")
        if self.policy != AggregationPolicy.MAJORITY and tie_break != "reject":
            raise ContractError("tie_break is only meaningful for MAJORITY policy")
        self.tie_break = tie_break
        # sorted by name: deterministic member order (VQ-R5)
        self._members = dict(sorted(members.items()))

    @property
    def member_names(self) -> tuple[str, ...]:
        return tuple(self._members)

    def aggregate(self, candidate: object) -> EnsembleVerdict:
        verdicts = {name: bool(fn(candidate))
                    for name, fn in self._members.items()}
        accepts = sum(verdicts.values())
        rejects = len(verdicts) - accepts
        tie = False
        tie_break_used: Optional[str] = None

        if self.policy == AggregationPolicy.UNANIMOUS:
            verdict = rejects == 0
        elif self.policy == AggregationPolicy.ANY:
            verdict = accepts > 0
        else:  # MAJORITY
            if accepts > rejects:
                verdict = True
            elif rejects > accepts:
                verdict = False
            else:
                tie = True
                tie_break_used = self.tie_break
                verdict = self.tie_break == "accept"
        return EnsembleVerdict(verdict, accepts, rejects,
                               self.policy.value, tie, tie_break_used)
