#!/usr/bin/env python3
"""Feature-addressable harness machinery switches for SLM-05 ablation.

Maps the five harness machinery features (contracts, epistemic memory,
deterministic verification, failure/repair history, full station
context) onto the frozen SLM-05 conditions A-F as a pure configuration
matrix, so the future ablation is configuration, not refactor:

    A structured state only
    B + contracts
    C + epistemic memory
    D + deterministic verification
    E + failure/repair history
    F full Station

This is a PURE CONFIG/SPEC MODULE. It does not modify, import, or call
any RESIDUAL runtime code; it only describes which machinery would be
enabled under each condition. Consumption of this matrix by the harness
is a separate, later change.

Per SLM-00: ablations MUST remove information/capability explicitly;
prompt wording changes alone do not constitute a harness ablation.

CLI:
  python feature_flags.py --help
  python feature_flags.py matrix            # full config matrix as JSON
  python feature_flags.py condition F       # one condition's config
  python feature_flags.py diff A F          # feature delta between conditions
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Sequence, Tuple

FEATURES: Tuple[str, ...] = (
    "contracts",
    "epistemic_memory",
    "deterministic_verification",
    "repair_history",
    "full_station_context",
)

CONDITIONS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

# Frozen condition ladder (SLM-05). Each lettered condition is strictly
# additive over the previous one, ending at full Station (F).
_CONDITION_FEATURES: Dict[str, Tuple[str, ...]] = {
    "A": (),
    "B": ("contracts",),
    "C": ("contracts", "epistemic_memory"),
    "D": ("contracts", "epistemic_memory", "deterministic_verification"),
    "E": (
        "contracts",
        "epistemic_memory",
        "deterministic_verification",
        "repair_history",
    ),
    "F": (
        "contracts",
        "epistemic_memory",
        "deterministic_verification",
        "repair_history",
        "full_station_context",
    ),
}


@dataclass(frozen=True)
class ConditionConfig:
    """Feature-addressable config for one SLM-05 harness condition."""

    condition: str
    description: str
    flags: Dict[str, bool]

    def enabled(self, feature: str) -> bool:
        if feature not in FEATURES:
            raise KeyError("unknown feature: %r" % feature)
        return self.flags[feature]


_DESCRIPTIONS = {
    "A": "structured state only",
    "B": "A + contracts",
    "C": "B + epistemic memory",
    "D": "C + deterministic verification",
    "E": "D + failure/repair history",
    "F": "full Station",
}


def condition_config(condition: str) -> ConditionConfig:
    """Return the frozen config for one SLM-05 condition."""
    if condition not in CONDITIONS:
        raise ValueError(
            "condition must be one of %s, got %r" % (CONDITIONS, condition)
        )
    enabled = set(_CONDITION_FEATURES[condition])
    return ConditionConfig(
        condition=condition,
        description=_DESCRIPTIONS[condition],
        flags={feature: feature in enabled for feature in FEATURES},
    )


def config_matrix() -> Dict[str, Dict[str, object]]:
    """The full SLM-05 condition x feature config matrix."""
    return {c: asdict(condition_config(c)) for c in CONDITIONS}


def diff_conditions(a: str, b: str) -> Dict[str, Dict[str, bool]]:
    """Feature delta between two conditions (explicit removals/additions)."""
    ca, cb = condition_config(a), condition_config(b)
    return {
        feature: {"from_%s" % a: ca.flags[feature], "from_%s" % b: cb.flags[feature]}
        for feature in FEATURES
        if ca.flags[feature] != cb.flags[feature]
    }


def validate_ladder() -> None:
    """Assert the ladder is strictly additive (freeze self-check)."""
    prev: Optional[set] = None
    for c in CONDITIONS:
        current = set(_CONDITION_FEATURES[c])
        if prev is not None and not prev < current:
            raise AssertionError(
                "condition %s is not strictly additive over the ladder" % c
            )
        prev = current


validate_ladder()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("matrix", help="print the full config matrix as JSON")
    cond = sub.add_parser("condition", help="print one condition's config")
    cond.add_argument("name", choices=CONDITIONS)
    diff = sub.add_parser("diff", help="feature delta between two conditions")
    diff.add_argument("from_condition", choices=CONDITIONS)
    diff.add_argument("to_condition", choices=CONDITIONS)
    args = parser.parse_args(argv)

    if args.command == "matrix":
        print(json.dumps(config_matrix(), indent=2, sort_keys=True))
    elif args.command == "condition":
        print(json.dumps(asdict(condition_config(args.name)), indent=2,
                         sort_keys=True))
    else:
        print(json.dumps(diff_conditions(args.from_condition,
                                         args.to_condition),
                         indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
