from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("helper_retarget_preflight", ROOT / "tools/aud1/helper_retarget_preflight.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)
HELPER_HEAD = "a" * 40


class HelperReconciliationTests(unittest.TestCase):
    def make_helper(self, root):
        root = pathlib.Path(root)
        files = {
            "tools/aud1/f6_collect.py": f'TARGET_SHA = "{preflight.SELECTED_SHA}"\n',
            "tools/aud1/Run-F6-Physical.ps1": f'$Target = "{preflight.SELECTED_SHA}"\n',
            "tools/aud1/f6_bound_station.py": f'TARGET_SHA = "{preflight.SELECTED_SHA}"\n',
            "tools/aud1/f6_case_guard.py": "TARGET_SHA = base.TARGET_SHA\n",
            "tests/tools/test_aud1_f6_guard.py": "assert guard.TARGET_SHA\n",
            "tools/aud1/README.md": f"Selected candidate: {preflight.SELECTED_SHA}\n",
            "tools/aud1/STRICT-PHYSICAL-GATE.md": f"Selected candidate: {preflight.SELECTED_SHA}\n",
        }
        for relative, body in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return root

    def identity(self, head=HELPER_HEAD, tree="b" * 40, clean=True, ancestor=True):
        return {"path": "/fixture", "head_sha": head, "tree_sha": tree, "clean_worktree": clean, "frozen_403_ancestor": ancestor, "git_errors": []}

    def run_preflight(self, helper, candidate_temp, helper_identity=None, candidate_identity=None):
        helper_identity = helper_identity or self.identity()
        candidate_identity = candidate_identity or self.identity(preflight.SELECTED_SHA, preflight.SELECTED_TREE)
        with mock.patch.object(preflight, "repo_identity", side_effect=[helper_identity, candidate_identity]):
            return preflight.preflight(helper, candidate_temp, HELPER_HEAD)

    def test_all_known_pins_atomically_reconciled_passes_without_physical_execution(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            result = self.run_preflight(self.make_helper(helper_temp), candidate_temp)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["physical_f6_executed"])
        self.assertEqual({b["path"] for b in result["bindings"] if b["kind"] == "executable"}, set(preflight.CODE_BINDINGS))

    def test_wrong_selected_sha_fails(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            result = self.run_preflight(self.make_helper(helper_temp), candidate_temp, candidate_identity=self.identity("c" * 40, preflight.SELECTED_TREE))
        self.assertEqual(result["status"], "REFUSE")
        self.assertTrue(any("expected selected candidate" in e for e in result["errors"]))

    def test_stale_438_sha_fails(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            result = self.run_preflight(self.make_helper(helper_temp), candidate_temp, candidate_identity=self.identity(preflight.STALE_438_SHA, preflight.SELECTED_TREE))
        self.assertEqual(result["status"], "REFUSE")

    def test_frozen_403_left_executable_fails(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            (helper / "tools/aud1/f6_collect.py").write_text(f'TARGET_SHA = "{preflight.FROZEN_HELPER_SHA}"\n', encoding="utf-8")
            result = self.run_preflight(helper, candidate_temp)
        self.assertEqual(result["status"], "REFUSE")

    def test_unknown_literal_fails(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            (helper / "tools/aud1/future.py").write_text(f'PIN = "{"d" * 40}"\n', encoding="utf-8")
            result = self.run_preflight(helper, candidate_temp)
        self.assertEqual(result["status"], "REFUSE")
        self.assertTrue(any("unaccounted target-like literal" in e for e in result["errors"]))

    def test_document_executable_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            (helper / "tools/aud1/README.md").write_text("Selected candidate: omitted\n", encoding="utf-8")
            result = self.run_preflight(helper, candidate_temp)
        self.assertEqual(result["status"], "REFUSE")
        self.assertTrue(any("documentation pin is missing" in e for e in result["errors"]))

    def test_candidate_tree_and_helper_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            with mock.patch.object(preflight, "repo_identity", side_effect=[self.identity("e" * 40), self.identity(preflight.SELECTED_SHA, "f" * 40)]):
                result = preflight.preflight(helper, candidate_temp, HELPER_HEAD)
        self.assertEqual(result["status"], "REFUSE")
        self.assertTrue(any("expected helper identity" in e for e in result["errors"]))
        self.assertTrue(any("expected selected tree" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
