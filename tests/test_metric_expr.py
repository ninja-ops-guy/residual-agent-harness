from __future__ import annotations

import unittest

from residual.metric_expr import (
    And, Atomic, Compare, Refinement, expression_refinement,
)


def tail(p99_id="latency_p99_ms", latency_threshold=250, throughput_floor=1000, error_ceiling=0.01):
    return And((
        Compare(Atomic(p99_id,"time"),"<",latency_threshold),
        Compare(Atomic("throughput_rps","rate"),">=",throughput_floor),
        Compare(Atomic("error_rate","ratio"),"<=",error_ceiling),
    ))


class MetricExpressionTests(unittest.TestCase):
    def test_mx001_valid_conjunction_refinement(self):
        base=tail(latency_threshold=250,throughput_floor=1000,error_ceiling=0.01)
        candidate=tail(latency_threshold=220,throughput_floor=1100,error_ceiling=0.008)
        self.assertEqual(
            expression_refinement(candidate,base,atomic_relations={}),
            Refinement.STRICT_REFINEMENT,
        )

    def test_mx001_child_coarsening_makes_composite_unknown(self):
        base=tail(latency_threshold=250)
        candidate=tail(latency_threshold=300)
        self.assertEqual(
            expression_refinement(candidate,base,atomic_relations={}),
            Refinement.UNKNOWN,
        )

    def test_mx001_incompatible_topology_is_unknown(self):
        base=tail()
        candidate=Compare(Atomic("latency_p99_ms","time"),"<",250)
        self.assertEqual(
            expression_refinement(candidate,base,atomic_relations={}),
            Refinement.UNKNOWN,
        )

    def test_mx001_unit_incompatible_atomic_relation_is_not_admitted(self):
        base=Compare(Atomic("latency_p99_ms","time"),"<",250)
        candidate=Compare(Atomic("latency_p99_bytes","bytes"),"<",250)
        self.assertEqual(
            expression_refinement(
                candidate,base,
                atomic_relations={
                    ("latency_p99_bytes","latency_p99_ms"):Refinement.STRICT_REFINEMENT
                },
            ),
            Refinement.UNKNOWN,
        )


if __name__=="__main__":
    unittest.main()
