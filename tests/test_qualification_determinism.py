"""Fail-closed tests for the D0-D4 determinism bundle validator.

Proves the validator refuses malformed, cross-revision, cross-referenced
(inconsistent), and incomplete bundles, and accepts the fixture-valid bundle.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.qualification_determinism import (
    BUNDLE_JSON_SCHEMA,
    BUNDLE_SCHEMA,
    BundleValidationError,
    load_bundle,
    validate_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "qualification" / "d2-valid.bundle.json"
SCHEMA_FILE = (
    ROOT / "docs" / "qualification" / "schemas" / "residual.determinism.bundle.v1.schema.json"
)


def valid_bundle() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def rejected(bundle) -> list[str]:
    with unittest.TestCase().assertRaises(BundleValidationError) as ctx:
        validate_bundle(bundle)
    return ctx.exception.reasons


class FixtureValidityTests(unittest.TestCase):
    def test_fixture_valid_bundle_is_accepted(self):
        bundle = load_bundle(FIXTURE)
        self.assertEqual(bundle["class_attempted"], "D2")
        self.assertEqual(bundle["result"], "PASS")

    def test_shipped_schema_matches_embedded_schema_byte_for_byte(self):
        expected = json.dumps(BUNDLE_JSON_SCHEMA, indent=2, sort_keys=True) + "\n"
        self.assertEqual(SCHEMA_FILE.read_text(encoding="utf-8"), expected)

    def test_validator_module_is_stdlib_only(self):
        import ast

        tree = ast.parse(
            (ROOT / "scripts" / "qualification_determinism.py").read_text(encoding="utf-8")
        )
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertLessEqual(
            imported,
            {"argparse", "json", "re", "sys", "pathlib", "typing", "residual", "__future__"},
        )


class MalformedBundleTests(unittest.TestCase):
    def test_non_object_bundle_rejected(self):
        for bad in ([], "bundle", 42, None):
            with self.assertRaises(BundleValidationError):
                validate_bundle(bad)

    def test_missing_required_key_rejected(self):
        for key in ("backend", "class_attempted", "envelope", "suite", "runs",
                    "canonicalization", "equivalence", "result", "non_claims",
                    "bundle_id", "predecessor_id"):
            bundle = valid_bundle()
            del bundle[key]
            reasons = rejected(bundle)
            self.assertTrue(any("missing required keys" in r for r in reasons), key)

    def test_unexpected_top_level_key_rejected(self):
        bundle = valid_bundle()
        bundle["surprise"] = True
        self.assertTrue(any("unexpected keys" in r for r in rejected(bundle)))

    def test_bad_bundle_id_rejected(self):
        bundle = valid_bundle()
        bundle["bundle_id"] = "not-a-uuid"
        self.assertTrue(any("bundle_id" in r for r in rejected(bundle)))

    def test_malformed_hash_rejected(self):
        bundle = valid_bundle()
        bundle["runs"][0]["canonical_output_sha256"] = "zz" * 32
        self.assertTrue(any("canonical_output_sha256" in r for r in rejected(bundle)))

    def test_unreadable_file_rejected(self):
        with self.assertRaises(BundleValidationError):
            load_bundle(ROOT / "tests" / "fixtures" / "qualification" / "does-not-exist.json")


class CrossRevisionTests(unittest.TestCase):
    def test_wrong_bundle_schema_revision_rejected(self):
        bundle = valid_bundle()
        bundle["schema"] = "residual.determinism.bundle.v2"
        reasons = rejected(bundle)
        self.assertTrue(any("unknown revisions are rejected" in r for r in reasons))

    def test_wrong_envelope_schema_revision_rejected(self):
        bundle = valid_bundle()
        bundle["envelope"]["schema"] = "residual.qualification.evidence.v2"
        reasons = rejected(bundle)
        self.assertTrue(any("cross-revision" in r for r in reasons))

    def test_missing_envelope_schema_rejected(self):
        bundle = valid_bundle()
        del bundle["envelope"]["schema"]
        self.assertTrue(any("envelope.schema" in r for r in rejected(bundle)))


class CrossReferenceTests(unittest.TestCase):
    def test_envelope_result_must_match_bundle_result(self):
        bundle = valid_bundle()
        bundle["envelope"]["result"] = "FAIL"
        self.assertTrue(any("cross-reference mismatch" in r for r in rejected(bundle)))

    def test_gate_id_must_encode_class_and_backend(self):
        bundle = valid_bundle()
        bundle["envelope"]["gate_id"] = "determinism-d2-other-backend"
        self.assertTrue(any("envelope.gate_id" in r for r in rejected(bundle)))

    def test_pass_requires_zero_skip_and_unknown(self):
        for key in ("skip_count", "unknown_count"):
            bundle = valid_bundle()
            bundle["envelope"][key] = 1
            reasons = rejected(bundle)
            self.assertTrue(any(key in r for r in reasons), key)

    def test_pass_requires_clean_tree(self):
        for dirty in (True, None):
            bundle = valid_bundle()
            bundle["envelope"]["source"]["tracked_source_dirty"] = dirty
            self.assertTrue(
                any("tracked_source_dirty" in r for r in rejected(bundle)), dirty
            )

    def test_pass_requires_full_revision_binding(self):
        bundle = valid_bundle()
        bundle["envelope"]["source"]["commit"] = "abc123"
        self.assertTrue(any("40-hex" in r for r in rejected(bundle)))


class IncompleteEvidenceTests(unittest.TestCase):
    def test_d1_requires_three_runs(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D1"
        bundle["envelope"]["gate_id"] = "determinism-d1-fixture-echo"
        bundle["runs"] = bundle["runs"][:1] * 1  # single run only
        self.assertTrue(any(">= 3 repeat runs" in r for r in rejected(bundle)))

    def test_d2_requires_seed(self):
        bundle = valid_bundle()
        bundle["suite"]["seed"] = None
        self.assertTrue(any("recorded seed" in r for r in rejected(bundle)))

    def test_d2_rejects_float_tolerance(self):
        bundle = valid_bundle()
        bundle["equivalence"]["relation"] = "canonical_with_float_tolerance"
        bundle["canonicalization"]["float_policy"] = "tolerance"
        bundle["canonicalization"]["float_tolerance"] = 1e-6
        reasons = rejected(bundle)
        self.assertTrue(any("D1 property" in r for r in reasons))

    def test_d2_rejects_diverging_canonical_outputs(self):
        bundle = valid_bundle()
        bundle["runs"][1]["canonical_output_sha256"] = "0" * 64
        bundle["equivalence"]["all_pairwise_equal"] = False
        reasons = rejected(bundle)
        self.assertTrue(any("identical canonical_output_sha256" in r for r in reasons))

    def test_d3_requires_environment_matrix_and_restart(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D3"
        bundle["envelope"]["gate_id"] = "determinism-d3-fixture-echo"
        reasons = rejected(bundle)
        self.assertTrue(any("distinct (platform, machine)" in r for r in reasons))
        self.assertTrue(any("restart_generation" in r for r in reasons))

    def test_d3_fixture_variant_accepted_when_matrix_and_restart_present(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D3"
        bundle["envelope"]["gate_id"] = "determinism-d3-fixture-echo"
        second = copy.deepcopy(bundle["runs"][1])
        second["environment"]["platform"] = "Darwin-24.0-arm64"
        second["environment"]["machine"] = "arm64"
        second["restart_generation"] = 1
        second["run_index"] = 2
        bundle["runs"].append(second)
        validate_bundle(bundle)  # must not raise

    def test_d4_requires_negative_control_and_airgap(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D4"
        bundle["envelope"]["gate_id"] = "determinism-d4-fixture-echo"
        reasons = rejected(bundle)
        self.assertTrue(any("negative_control" in r for r in reasons))
        self.assertTrue(any("network-disabled" in r for r in reasons))

    def test_d4_rejects_blind_negative_control(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D4"
        bundle["envelope"]["gate_id"] = "determinism-d4-fixture-echo"
        second = copy.deepcopy(bundle["runs"][1])
        second["environment"]["platform"] = "Darwin-24.0-arm64"
        second["environment"]["machine"] = "arm64"
        second["restart_generation"] = 1
        second["run_index"] = 2
        second["network_disabled"] = True
        bundle["runs"].append(second)
        bundle["negative_control"] = {
            "performed": True, "tamper_detected": False, "evidence_sha256": "f" * 64
        }
        self.assertTrue(any("tamper_detected" in r for r in rejected(bundle)))

    def test_d4_full_fixture_variant_accepted(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D4"
        bundle["envelope"]["gate_id"] = "determinism-d4-fixture-echo"
        second = copy.deepcopy(bundle["runs"][1])
        second["environment"]["platform"] = "Darwin-24.0-arm64"
        second["environment"]["machine"] = "arm64"
        second["restart_generation"] = 1
        second["run_index"] = 2
        second["network_disabled"] = True
        bundle["runs"].append(second)
        bundle["negative_control"] = {
            "performed": True, "tamper_detected": True, "evidence_sha256": "f" * 64
        }
        validate_bundle(bundle)  # must not raise

    def test_d0_cannot_pass(self):
        bundle = valid_bundle()
        bundle["class_attempted"] = "D0"
        bundle["envelope"]["gate_id"] = "determinism-d0-fixture-echo"
        self.assertTrue(any("D0" in r for r in rejected(bundle)))


class RetainedObservationTests(unittest.TestCase):
    """UNKNOWN/FAIL/SKIP bundles are valid retained observations, never PASS."""

    def test_unknown_bundle_validates_as_observation(self):
        for result in ("UNKNOWN", "FAIL", "SKIP"):
            bundle = valid_bundle()
            bundle["result"] = result
            bundle["envelope"]["result"] = result
            if result == "UNKNOWN":
                bundle["envelope"]["unknown_count"] = 1
            if result == "SKIP":
                bundle["envelope"]["skip_count"] = 1
            validate_bundle(bundle)  # must not raise: retained, not qualifying


if __name__ == "__main__":
    unittest.main()
