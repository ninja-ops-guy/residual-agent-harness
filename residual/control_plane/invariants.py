"""Invariant dependency graph for SPEC-GATEWAY/CONTROL-PLANE-001 maintenance.

`requires` captures prerequisites for the invariant to be meaningful.
`implies` captures deliberate specialization/derivation relationships.
`conflicts` is explicit even when empty so reviews can detect future tension.
"""

INVARIANT_GRAPH = {
    1: {"requires": (), "implies": (), "conflicts": ()},
    2: {"requires": (), "implies": (3,), "conflicts": ()},
    3: {"requires": (2,), "implies": (16, 18), "conflicts": ()},
    4: {"requires": (3,), "implies": (16,), "conflicts": ()},
    5: {"requires": (), "implies": (13,), "conflicts": ()},
    6: {"requires": (), "implies": (20,), "conflicts": ()},
    7: {"requires": (), "implies": (15,), "conflicts": ()},
    8: {"requires": (), "implies": (), "conflicts": ()},
    9: {"requires": (), "implies": (19,), "conflicts": ()},
    10: {"requires": (9,), "implies": (), "conflicts": ()},
    11: {"requires": (7,), "implies": (), "conflicts": ()},
    12: {"requires": (7,), "implies": (), "conflicts": ()},
    13: {"requires": (3, 5), "implies": (), "conflicts": ()},
    14: {"requires": (7,), "implies": (), "conflicts": ()},
    15: {"requires": (7, 14), "implies": (), "conflicts": ()},
    16: {"requires": (3, 4), "implies": (), "conflicts": ()},
    17: {"requires": (6, 14, 16), "implies": (), "conflicts": ()},
    18: {"requires": (3, 11), "implies": (), "conflicts": ()},
    19: {"requires": (9, 10), "implies": (), "conflicts": ()},
    20: {"requires": (6,), "implies": (), "conflicts": ()},
}


def validate_invariant_graph(graph=INVARIANT_GRAPH):
    expected = set(range(1, 21))
    if set(graph) != expected:
        raise ValueError("invariant graph must contain exactly invariants 1..20")
    for invariant, edges in graph.items():
        if set(edges) != {"requires", "implies", "conflicts"}:
            raise ValueError(f"invariant {invariant} has malformed dependency metadata")
        for relation, targets in edges.items():
            unknown = set(targets) - expected
            if unknown:
                raise ValueError(f"invariant {invariant} {relation} unknown invariants {sorted(unknown)}")
            if invariant in targets:
                raise ValueError(f"invariant {invariant} cannot {relation} itself")
    return True


validate_invariant_graph()
