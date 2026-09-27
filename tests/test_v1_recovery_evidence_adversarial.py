"""Disposable recovery-validator boundary controls; never operational evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

_BASE_SPEC = importlib.util.spec_from_file_location(
    "recovery_boundary_fixture", Path(__file__).with_name("test_v1_recovery_evidence.py")
)
assert _BASE_SPEC and _BASE_SPEC.loader
_BASE = importlib.util.module_from_spec(_BASE_SPEC)
_BASE_SPEC.loader.exec_module(_BASE)
mod, sample, SCRIPT = _BASE.mod, _BASE.sample, _BASE.SCRIPT
FIELDS = (
    ("objectives", "rpo_seconds"),
    ("objectives", "rto_seconds"),
    ("restore", "observed_rpo_seconds"),
    ("restore", "observed_rto_seconds"),
)


class RecoveryEvidenceBoundaryTests(unittest.TestCase):
    def cli(self, raw: str | bytes) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-evidence.json"
            path.write_bytes(raw.encode("utf-8") if isinstance(raw, str) else raw)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                capture_output=True, text=True, timeout=10, check=False,
            )
        self.assertEqual(result.stderr, "", "typed failure must not print a traceback")
        output = json.loads(result.stdout)
        self.assertEqual(output["execution_claim"], "VALIDATION_ONLY")
        return result.returncode, output

    def blocked(self, raw: str | bytes) -> None:
        code, output = self.cli(raw)
        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "BLOCKED")

    def test_api_nan_is_rejected_for_each_metric(self):
        for section, field in FIELDS:
            with self.subTest(section=section, field=field):
                evidence = sample()
                evidence[section][field] = float("nan")
                with self.assertRaises(mod.EvidenceError):
                    mod.validate_evidence(evidence)

    def test_api_infinities_are_rejected_for_each_metric(self):
        for section, field in FIELDS:
            for value in (float("inf"), float("-inf")):
                with self.subTest(section=section, field=field, value=value):
                    evidence = sample()
                    evidence[section][field] = value
                    with self.assertRaises(mod.EvidenceError):
                        mod.validate_evidence(evidence)

    def test_api_invalid_numeric_types_remain_rejected(self):
        for section, field in FIELDS:
            for value in (True, False, None, "300", -1):
                with self.subTest(section=section, field=field, value=value):
                    evidence = sample()
                    evidence[section][field] = value
                    with self.assertRaises(mod.EvidenceError):
                        mod.validate_evidence(evidence)

    def test_api_missing_metric_remains_rejected(self):
        for section, field in FIELDS:
            with self.subTest(section=section, field=field):
                evidence = sample()
                del evidence[section][field]
                with self.assertRaises(mod.EvidenceError):
                    mod.validate_evidence(evidence)

    def test_api_preserves_integer_comparison_precision(self):
        for objective, observed in (("rpo_seconds", "observed_rpo_seconds"),
                                    ("rto_seconds", "observed_rto_seconds")):
            with self.subTest(objective=objective):
                evidence = sample()
                evidence["objectives"][objective] = 2**53
                evidence["restore"][observed] = 2**53 + 1
                self.assertEqual(mod.validate_evidence(evidence)["status"], "FAIL")

    def test_api_large_integer_breach_is_fail_not_exception(self):
        evidence = sample()
        evidence["restore"]["observed_rpo_seconds"] = 10**400
        self.assertEqual(mod.validate_evidence(evidence)["status"], "FAIL")

    def test_api_finite_fraction_and_zero_positive_controls(self):
        for value in (0, 0.0, 0.25, 60):
            with self.subTest(value=value):
                evidence = sample()
                evidence["objectives"]["rpo_seconds"] = value
                evidence["restore"]["observed_rpo_seconds"] = value
                self.assertEqual(mod.validate_evidence(evidence)["status"], "PASS")

    def test_api_non_object_roots_are_typed_failures(self):
        for value in (None, [], 0, True, "text"):
            with self.subTest(value=value):
                with self.assertRaises(mod.EvidenceError):
                    mod.validate_evidence(value)

    def test_cli_nonstandard_constants_are_blocked(self):
        for section, field in FIELDS:
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(section=section, field=field, value=value):
                    evidence = sample()
                    evidence[section][field] = value
                    self.blocked(json.dumps(evidence))

    def test_cli_finite_syntax_overflow_is_blocked(self):
        raw = json.dumps(sample()).replace('"rpo_seconds": 300', '"rpo_seconds": 1e400')
        self.blocked(raw)

    def test_cli_extra_nonfinite_values_are_blocked(self):
        for literal in ("NaN", "Infinity", "-Infinity", "1e400"):
            with self.subTest(literal=literal):
                raw = json.dumps(sample())[:-1] + ',"extra":[{"measurement":' + literal + '}]}'
                self.blocked(raw)

    def test_cli_duplicate_approval_cannot_replace_false_with_true(self):
        raw = json.dumps(sample()).replace('"approved": true', '"approved": false, "approved": true')
        self.blocked(raw)

    def test_cli_duplicate_root_cannot_replace_unobserved_claim(self):
        raw = json.dumps(sample()).replace(
            '"execution_claim": "OBSERVED"',
            '"execution_claim": "NONE", "execution_claim": "OBSERVED"',
        )
        self.blocked(raw)

    def test_cli_duplicate_metric_cannot_hide_invalid_value(self):
        self.blocked(json.dumps(sample()).replace(
            '"rpo_seconds": 300', '"rpo_seconds": null, "rpo_seconds": 300'
        ))

    def test_cli_duplicate_escaped_key_is_rejected(self):
        self.blocked(json.dumps(sample()).replace(
            '"approved": true', '"approved": false, "\\u0061pproved": true'
        ))

    def test_cli_duplicate_equal_values_are_rejected(self):
        self.blocked(json.dumps(sample()).replace(
            '"approved": true', '"approved": true, "approved": true'
        ))

    def test_cli_duplicate_deep_extra_key_is_rejected(self):
        raw = json.dumps(sample())[:-1] + ',"extra":[{"a":{"b":1,"b":2}}]}'
        self.blocked(raw)

    def test_cli_invalid_utf8_is_typed_blocked(self):
        self.blocked(b"\xff")

    def test_cli_invalid_json_remains_blocked(self):
        self.blocked('{"broken":')

    def test_cli_non_object_roots_remain_blocked(self):
        for value in (None, [], 0, True, "text"):
            with self.subTest(value=value):
                self.blocked(json.dumps(value))

    def test_cli_valid_fixture_remains_validation_only_pass(self):
        code, output = self.cli(json.dumps(sample(), allow_nan=False))
        self.assertEqual((code, output["status"]), (0, "PASS"))

    def test_cli_finite_breach_remains_fail(self):
        evidence = sample()
        evidence["restore"]["observed_rto_seconds"] = 901
        code, output = self.cli(json.dumps(evidence))
        self.assertEqual((code, output["status"]), (1, "FAIL"))

    def test_cli_large_integer_breach_preserves_precision(self):
        evidence = sample()
        evidence["objectives"]["rpo_seconds"] = 2**53
        evidence["restore"]["observed_rpo_seconds"] = 2**53 + 1
        code, output = self.cli(json.dumps(evidence))
        self.assertEqual((code, output["status"]), (1, "FAIL"))


if __name__ == "__main__":
    unittest.main()
