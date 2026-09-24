from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "helper_retarget_preflight",
    ROOT / "tools" / "aud1" / "helper_retarget_preflight.py",
)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


PROPOSED = "e815f33484352f100e11b8d075bb954a815244cc"


class HelperRetargetPreflightTests(unittest.TestCase):
    def make_helper(self, root):
        root = pathlib.Path(root)
        files = {
            "tools/aud1/f6_collect.py":
                f'TARGET_SHA = "{preflight.FROZEN_TARGET_SHA}"\n',
            "tools/aud1/Run-F6-Physical.ps1":
                f'$Target = "{preflight.FROZEN_TARGET_SHA}"\n',
            "tools/aud1/f6_bound_station.py":
                f'TARGET_SHA = "{preflight.FROZEN_TARGET_SHA}"\n',
            "tools/aud1/f6_case_guard.py":
                "TARGET_SHA = base.TARGET_SHA\n",
            "tests/tools/test_aud1_f6_guard.py":
                "self.assertEqual(identity['head_sha'], guard.TARGET_SHA)\n",
            "tools/aud1/README.md":
                f"Qualified candidate under test: {preflight.FROZEN_TARGET_SHA}\n",
            "tools/aud1/STRICT-PHYSICAL-GATE.md":
                f"Qualified Station candidate under test: {preflight.FROZEN_TARGET_SHA}\n",
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def identity(self, head, clean=True):
        return {
            "path": "/fixture",
            "head_sha": head,
            "tree_sha": "a" * 40,
            "clean_worktree": clean,
            "git_errors": [],
        }

    def run_preflight(self, helper, candidate_temp, helper_identity=None, candidate_identity=None):
        helper_identity = helper_identity or self.identity(preflight.FROZEN_HELPER_SHA)
        candidate_identity = candidate_identity or self.identity(PROPOSED)
        with mock.patch.object(
            preflight,
            "repo_identity",
            side_effect=[helper_identity, candidate_identity],
        ):
            return preflight.preflight(helper, candidate_temp, PROPOSED)

    def test_preflight_reports_atomic_plan_without_mutating_helper(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            before = {
                p.relative_to(helper).as_posix(): preflight.sha256_file(p)
                for p in helper.rglob("*") if p.is_file()
            }
            result = self.run_preflight(helper, candidate_temp)
            after = {
                p.relative_to(helper).as_posix(): preflight.sha256_file(p)
                for p in helper.rglob("*") if p.is_file()
            }
            self.assertEqual(result["status"], "PREPARED_NOT_AUTHORIZED")
            self.assertFalse(result["mutated"])
            self.assertEqual(before, after)
            direct = [b for b in result["bindings"] if b["kind"] == "direct-code"]
            self.assertEqual({b["path"] for b in direct}, set(preflight.CODE_BINDINGS))
            self.assertTrue(all(b["change_required_after_selection"] for b in direct))
            self.assertEqual(
                {x["path"] for x in result["literal_target_locations"]},
                set(preflight.CODE_BINDINGS) | set(preflight.DOCUMENT_BINDINGS),
            )

    def test_refuses_wrong_or_dirty_helper(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            result = self.run_preflight(
                helper,
                candidate_temp,
                helper_identity=self.identity("b" * 40, clean=False),
            )
            self.assertEqual(result["status"], "REFUSE")
            self.assertTrue(any("expected frozen #403 head" in e for e in result["errors"]))
            self.assertIn("helper checkout is dirty", result["errors"])

    def test_refuses_candidate_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            result = self.run_preflight(
                helper,
                candidate_temp,
                candidate_identity=self.identity("c" * 40),
            )
            self.assertEqual(result["status"], "REFUSE")
            self.assertTrue(any("expected proposed target" in e for e in result["errors"]))

    def test_refuses_missing_direct_target_binding(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            (helper / "tools/aud1/Run-F6-Physical.ps1").write_text(
                '$Target = "deadbeef"\n',
                encoding="utf-8",
            )
            result = self.run_preflight(helper, candidate_temp)
            self.assertEqual(result["status"], "REFUSE")
            self.assertTrue(any("expected exactly one frozen target binding" in e for e in result["errors"]))

    def test_refuses_unaccounted_literal_target_binding(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            unexpected = helper / "tools/aud1/future_helper.py"
            unexpected.write_text(
                f'PIN = "{preflight.FROZEN_TARGET_SHA}"\n',
                encoding="utf-8",
            )
            result = self.run_preflight(helper, candidate_temp)
            self.assertEqual(result["status"], "REFUSE")
            self.assertTrue(any("unaccounted frozen target literal" in e for e in result["errors"]))

    def test_current_frozen_target_is_not_misreported_as_retarget(self):
        with tempfile.TemporaryDirectory() as helper_temp, tempfile.TemporaryDirectory() as candidate_temp:
            helper = self.make_helper(helper_temp)
            with mock.patch.object(
                preflight,
                "repo_identity",
                side_effect=[
                    self.identity(preflight.FROZEN_HELPER_SHA),
                    self.identity(preflight.FROZEN_TARGET_SHA),
                ],
            ):
                result = preflight.preflight(
                    helper, candidate_temp, preflight.FROZEN_TARGET_SHA
                )
            self.assertEqual(result["status"], "CURRENT_TARGET_MATCH")


if __name__ == "__main__":
    unittest.main()
