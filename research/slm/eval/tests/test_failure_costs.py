"""Tests for failure_costs.py (toy data only)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import failure_costs

MATRIX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "failure-cost-matrix.yaml",
)


class TestFailureCosts(unittest.TestCase):
    def test_frozen_asymmetry_10_to_1(self):
        matrix = failure_costs.FailureCostMatrix()
        weights = matrix.effective_weights()
        self.assertEqual(weights["false_non_escalation"], 10.0)
        self.assertEqual(weights["unnecessary_escalation"], 1.0)
        self.assertEqual(
            weights["false_non_escalation"] / weights["unnecessary_escalation"],
            failure_costs.FROZEN_WEIGHTS["false_non_escalation"],
        )

    def test_weighted_cost_per_run(self):
        matrix = failure_costs.FailureCostMatrix()
        result = matrix.weighted_cost(
            {"false_non_escalation": 1, "unnecessary_escalation": 3}
        )
        self.assertEqual(result["total_weighted_cost"], 10.0 + 3.0)
        self.assertIn("decision-analysis", result["label"])

    def test_unknown_category_rejected(self):
        matrix = failure_costs.FailureCostMatrix()
        with self.assertRaises(ValueError):
            matrix.weighted_cost({"surprise": 1})
        with self.assertRaises(ValueError):
            failure_costs.FailureCostMatrix(weights={"surprise": 1.0})

    def test_overrides_explicit_per_category(self):
        matrix = failure_costs.FailureCostMatrix(
            overrides={"wrong_routing": 5.0}
        )
        self.assertEqual(matrix.effective_weights()["wrong_routing"], 5.0)
        # frozen asymmetry untouched by unrelated overrides
        self.assertEqual(
            matrix.effective_weights()["false_non_escalation"], 10.0)

    def test_yaml_matrix_loads(self):
        matrix = failure_costs.matrix_from_yaml(MATRIX_PATH)
        self.assertEqual(matrix.protocol, "eval-protocol-v1.0.0")
        self.assertEqual(matrix.effective_weights(),
                         failure_costs.FROZEN_WEIGHTS)

    def test_yaml_roundtrip_cost(self):
        matrix = failure_costs.matrix_from_yaml(MATRIX_PATH)
        result = matrix.weighted_cost({"authority_violation": 2})
        self.assertEqual(result["total_weighted_cost"], 20.0)

    def test_cli_help(self):
        with self.assertRaises(SystemExit) as ctx:
            failure_costs.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_cost(self):
        self.assertEqual(
            failure_costs.main(
                ["cost", "--counts", '{"false_non_escalation": 1}']
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
