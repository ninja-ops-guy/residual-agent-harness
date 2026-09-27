"""Tests for feature_flags.py (toy data only)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feature_flags


class TestFeatureFlags(unittest.TestCase):
    def test_condition_a_is_structured_state_only(self):
        cfg = feature_flags.condition_config("A")
        self.assertTrue(all(not v for v in cfg.flags.values()))

    def test_condition_f_is_full_station(self):
        cfg = feature_flags.condition_config("F")
        self.assertTrue(all(v for v in cfg.flags.values()))

    def test_ladder_strictly_additive(self):
        prev = 0
        for c in feature_flags.CONDITIONS:
            cfg = feature_flags.condition_config(c)
            enabled = sum(cfg.flags.values())
            self.assertGreater(enabled, prev - 1)
            prev = enabled
        feature_flags.validate_ladder()

    def test_each_letter_adds_expected_feature(self):
        additions = {
            "B": "contracts",
            "C": "epistemic_memory",
            "D": "deterministic_verification",
            "E": "repair_history",
            "F": "full_station_context",
        }
        letters = feature_flags.CONDITIONS
        for i, letter in enumerate(letters[1:], start=1):
            delta = feature_flags.diff_conditions(letters[i - 1], letter)
            self.assertEqual(set(delta), {additions[letter]})
            self.assertFalse(delta[additions[letter]]["from_%s" % letters[i - 1]])
            self.assertTrue(delta[additions[letter]]["from_%s" % letter])

    def test_unknown_condition_and_feature(self):
        with self.assertRaises(ValueError):
            feature_flags.condition_config("G")
        with self.assertRaises(KeyError):
            feature_flags.condition_config("F").enabled("nope")

    def test_matrix_shape(self):
        matrix = feature_flags.config_matrix()
        self.assertEqual(set(matrix), set(feature_flags.CONDITIONS))
        for cfg in matrix.values():
            self.assertEqual(set(cfg["flags"]), set(feature_flags.FEATURES))

    def test_cli(self):
        self.assertEqual(feature_flags.main(["matrix"]), 0)
        self.assertEqual(feature_flags.main(["condition", "F"]), 0)
        self.assertEqual(feature_flags.main(["diff", "A", "F"]), 0)
        with self.assertRaises(SystemExit) as ctx:
            feature_flags.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
