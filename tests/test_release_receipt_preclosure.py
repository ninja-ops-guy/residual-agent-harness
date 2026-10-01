"""Receipt boundary regressions. All receipt/tag/approval data are synthetic.

These tests exercise source-bound structural validation, not actual release
approval, tag signatures, remote artifacts, native providers, or physical F6.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "release_binding_fixture", ROOT / "tests" / "test_release_receipt_binding.py"
)
assert SPEC and SPEC.loader
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
mod = fixture.mod


class ReleasePreclosureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.ReleaseReceiptBindingTests()
        self.fixture.setUp()
        self.doc = copy.deepcopy(self.fixture.doc)

    def expectations(self):
        return {
            "expected_rc_source": self.doc["candidate"]["commit"],
            "expected_rc_tree": self.doc["candidate"]["tree"],
            "expected_artifacts": self.fixture.artifact_map(self.doc),
        }

    def cases(self):
        yield "PRE_CLOSURE", copy.deepcopy(self.doc)
        rolled_back = copy.deepcopy(self.doc)
        rolled_back["closure"]["state"] = "ROLLED_BACK"
        yield "ROLLED_BACK_WITHOUT_TAG", rolled_back
        closed = copy.deepcopy(self.doc)
        self.fixture.close(closed)
        yield "V1_CLOSED", closed
        rolled_back = copy.deepcopy(closed)
        rolled_back["closure"]["state"] = "ROLLED_BACK"
        yield "ROLLED_BACK_WITH_TAG", rolled_back

    def cli(self, raw, *args):
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / "fixture.json"
            receipt.write_bytes(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
            return subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts" / "validate_release_receipt.py"),
                 str(receipt), *args],
                capture_output=True, text=True, timeout=10, check=False,
            )

    def test_matching_expectations_remain_valid_in_every_phase(self):
        for state, doc in self.cases():
            with self.subTest(state=state):
                mod.validate_binding(doc, **self.expectations())

    def test_expected_rc_source_is_enforced_before_closure_and_after_rollback(self):
        for state, doc in self.cases():
            args = self.expectations()
            args["expected_rc_source"] = "4" * 40
            with self.subTest(state=state), self.assertRaisesRegex(
                mod.ReceiptBindingError, "externally selected RC source"
            ):
                mod.validate_binding(doc, **args)

    def test_expected_rc_tree_is_enforced_in_every_phase(self):
        for state, doc in self.cases():
            args = self.expectations()
            args["expected_rc_tree"] = "4" * 40
            with self.subTest(state=state), self.assertRaisesRegex(
                mod.ReceiptBindingError, "externally selected RC tree"
            ):
                mod.validate_binding(doc, **args)

    def test_expected_artifact_set_is_enforced_in_every_phase(self):
        for state, doc in self.cases():
            args = self.expectations()
            args["expected_artifacts"] = {"residual.whl": "4" * 64}
            with self.subTest(state=state), self.assertRaisesRegex(
                mod.ReceiptBindingError, "externally selected qualified artifact set"
            ):
                mod.validate_binding(doc, **args)

    def test_partial_explicit_expectation_is_never_ignored(self):
        for key, value in [("expected_rc_source", "4" * 40),
                           ("expected_rc_tree", "4" * 40),
                           ("expected_artifacts", {"other.whl": "4" * 64})]:
            with self.subTest(key=key), self.assertRaises(mod.ReceiptBindingError):
                mod.validate_binding(self.doc, **{key: value})

    def test_supplied_malformed_expectations_are_typed_errors(self):
        for key, value in [("expected_rc_source", "main"), ("expected_rc_tree", []),
                           ("expected_artifacts", []), ("expected_artifacts", {}),
                           ("expected_artifacts", {" ": "4" * 64}),
                           ("expected_artifacts", {"residual.whl": "not-a-digest"})]:
            with self.subTest(key=key, value=value), self.assertRaises(mod.ReceiptBindingError):
                mod.validate_binding(self.doc, **{key: value})

    def test_cli_rejects_wrong_selected_rc_in_preclosure(self):
        result = self.cli(json.dumps(self.doc), "--expected-rc-source", "4" * 40)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("externally selected RC source", result.stdout)
        self.assertNotIn("PASS:", result.stdout)

    def test_cli_rejects_duplicate_authority_keys_at_every_depth(self):
        raw = json.dumps(self.doc)
        for description, ambiguous in [
            ("root", raw.replace('"release": "v1.0.0"',
                                 '"release": "not-v1", "release": "v1.0.0"', 1)),
            ("candidate", raw.replace('"commit": "' + "1" * 40 + '"',
                  '"commit": "' + "4" * 40 + '", "commit": "' + "1" * 40 + '"', 1)),
            ("decision", raw.replace('"state": "GO"', '"state": "NO_GO", "state": "GO"', 1)),
            ("identical", raw.replace('"release": "v1.0.0"',
                                 '"release": "v1.0.0", "release": "v1.0.0"', 1)),
        ]:
            with self.subTest(description=description):
                result = self.cli(ambiguous)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("duplicate JSON object key", result.stdout)
                self.assertNotIn("PASS:", result.stdout)

    def test_cli_rejects_nonfinite_numbers_anywhere(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            doc = copy.deepcopy(self.doc)
            doc["artifact"][0]["size"] = value
            with self.subTest(value=value):
                result = self.cli(json.dumps(doc))
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("non-finite JSON number", result.stdout)

    def test_cli_rejects_overflowing_finite_syntax(self):
        raw = json.dumps(self.doc)
        result = self.cli(raw.replace('"size": 1', '"size": 1e9999', 1))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("non-finite JSON number", result.stdout)

    def test_cli_reports_overlong_integer_without_traceback(self):
        raw = json.dumps(self.doc)
        result = self.cli(raw.replace('"size": 1', '"size": ' + "9" * 20000, 1))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_rejects_oversized_document_before_parsing(self):
        # Independent fixed boundary: do not import a runtime constant to weaken the test.
        result = self.cli(b" " * (4 * 1024 * 1024 + 1))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("receipt exceeds 4194304 bytes", result.stdout)

    def test_cli_reports_invalid_encoding_without_traceback(self):
        result = self.cli(b"\xff\xfe\x00")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_reports_excessive_nesting_without_traceback(self):
        result = self.cli("[" * 2000 + "0" + "]" * 2000)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_authority_types_raise_receipt_error(self):
        for state, doc in self.cases():
            if state == "V1_CLOSED":
                doc["decisions"][0]["gate_id"] = []
                with self.subTest(field="gate_id"), self.assertRaises(mod.ReceiptBindingError):
                    mod.validate_binding(doc, **self.expectations())
        doc = copy.deepcopy(self.doc)
        doc["closure"]["state"] = []
        with self.subTest(field="closure.state"), self.assertRaises(mod.ReceiptBindingError):
            mod.validate_binding(doc)
        with self.subTest(field="root"), self.assertRaises(mod.ReceiptBindingError):
            mod.validate_binding([])

    def test_valid_cli_does_not_claim_release_authority(self):
        result = self.cli(json.dumps(self.doc))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("binding verified", result.stdout)
        self.assertIn("not release authorization", result.stdout)


if __name__ == "__main__":
    unittest.main()
