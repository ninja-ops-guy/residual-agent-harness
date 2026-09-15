from pathlib import Path
import tempfile
import unittest

import yaml

from scripts.check_current_status import (
    DOCUMENTS, FAMILIES, ROOT, check, check_document, manifest_summary,
)


class CurrentStatusTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"families": [
            {"family": family, "status": "implemented"} for family in FAMILIES
        ]}
        self.summary = manifest_summary(self.manifest)
        self.valid = self.summary + "\n`residual/eval_frozen/`\n"

    def test_checked_in_current_summaries(self):
        self.assertEqual(check(ROOT), [])

    def test_explicit_historical_references_allowed(self):
        self.assertEqual(check_document(self.valid + (
            "The code from closed issue #63 landed.\n"
            "The basic reconciliation in closed issue #48 landed.\n"
            "#103 replaced the path intended by closed PR #71.\n"
        ), self.summary), [])

    def test_old_blocker_claims_rejected_including_wrapped_markdown(self):
        claims = (
            "close **#63** — harden M4", "Close issue\n#48 and regenerate",
            "Issue #63 tracks remaining hardening", "PR #71 still needs correction",
            "### M4 hardening — issue #63", "Close closed issue #63",
            "closed issue #63 still tracks missing isolation",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertTrue(check_document(self.valid + claim, self.summary))

    def test_longer_issue_numbers_and_unrelated_open_issues_not_misclassified(self):
        self.assertEqual(check_document(
            self.valid + "Issue #630 and PR #710 remain open; issue #35 tracks science.",
            self.summary), [])

    def test_manifest_drift_and_duplicate_summary_rejected(self):
        for text in (self.valid.replace("M4=implemented", "M4=partial"),
                     self.valid + self.summary + "\n"):
            with self.subTest(text=text):
                self.assertTrue(check_document(text, self.summary))

    def test_manifest_summary_uses_actual_states(self):
        self.manifest["families"][2]["status"] = "implemented_unverified"
        self.assertIn("M4=implemented_unverified", manifest_summary(self.manifest))

    def test_obsolete_not_started_paragraph_rejected(self):
        self.assertTrue(check_document(
            self.valid + "M2, M3, M4 and EVAL are still marked `not_started`.", self.summary))

    def test_frozen_path_required_without_banning_legacy_utilities(self):
        self.assertTrue(check_document(self.summary, self.summary))
        self.assertEqual(check_document(self.valid + "Utilities in `residual/eval/`.", self.summary), [])

    def test_missing_or_ambiguous_family_fails_closed(self):
        for rows in ([], self.manifest["families"] * 2):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                manifest_summary({"families": rows})

    def test_missing_invalid_manifest_or_document_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(check(root))
            (root / "implementation-status.yaml").write_text("[invalid", encoding="utf-8")
            self.assertTrue(check(root))
            (root / "implementation-status.yaml").write_text(yaml.safe_dump(self.manifest), encoding="utf-8")
            self.assertEqual(len(check(root)), len(DOCUMENTS))
            for path in DOCUMENTS:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(self.valid, encoding="utf-8")
            self.assertEqual(check(root), [])
