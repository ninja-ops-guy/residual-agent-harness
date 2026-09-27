"""Binding-constants regression tests for the proposed-V1 F6 helper successor.

These tests pin the helper's atomic product binding to the feature-frozen
proposed-V1 candidate (coordination/DEVELOPMENT_FREEZE.md) and prove that a
checkout of ANY other identity — including the superseded #469 tree — is
REFUSED. Any future rebind must update these pins deliberately.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
AUD1 = ROOT / "tools" / "aud1"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


f6 = _load("f6_collect_under_test", AUD1 / "f6_collect.py")
bound = _load("f6_bound_station_under_test", AUD1 / "f6_bound_station.py")
guard = _load("f6_guard_under_test", AUD1 / "f6_case_guard.py")

PROPOSED_V1_HEAD = "05e01731208957e85cf72cf02a925b0660fca144"
PROPOSED_V1_TREE = "92276b7d9883a57fd061c749e319ec10b527d586"
SUPERSEDED_PR469_HEAD = "935498ecd42982bc682d7ed69b562c642b74a8fe"
SUPERSEDED_PR469_TREE = "8d8ecb2970d3dc2cf304ba8c8c6997a05b45370b"


class BindingPinTests(unittest.TestCase):
    def test_collect_pins_proposed_v1_identity(self):
        self.assertEqual(f6.TARGET_SHA, PROPOSED_V1_HEAD)
        self.assertEqual(f6.TARGET_TREE, PROPOSED_V1_TREE)

    def test_bound_station_pins_proposed_v1_identity(self):
        self.assertEqual(bound.TARGET_SHA, PROPOSED_V1_HEAD)
        self.assertEqual(bound.TARGET_TREE, PROPOSED_V1_TREE)

    def test_guard_imports_same_constants(self):
        # f6_case_guard imports TARGET_SHA/TARGET_TREE from f6_collect.
        self.assertEqual(guard.TARGET_SHA, f6.TARGET_SHA)
        self.assertEqual(guard.TARGET_TREE, f6.TARGET_TREE)

    def test_superseded_pr469_identity_is_refused(self):
        # The old #469 binding must no longer satisfy the guard.
        self.assertNotEqual(f6.TARGET_SHA, SUPERSEDED_PR469_HEAD)
        self.assertNotEqual(f6.TARGET_TREE, SUPERSEDED_PR469_TREE)

        def fake_git(repo, *args):
            if args == ("rev-parse", "HEAD"):
                return 0, SUPERSEDED_PR469_HEAD, ""
            if args == ("rev-parse", "HEAD^{tree}"):
                return 0, SUPERSEDED_PR469_TREE, ""
            if args == ("status", "--porcelain=v1"):
                return 0, "", ""
            raise AssertionError(args)

        with unittest.mock.patch.object(guard, "git", side_effect=fake_git):
            identity = guard.raw_identity(".")
        self.assertFalse(identity["exact_head"])
        self.assertFalse(identity["exact_tree"])

    def test_powershell_runner_carries_same_binding(self):
        script = (AUD1 / "Run-F6-Physical.ps1").read_text(encoding="utf-8")
        self.assertIn(f'$Target = "{PROPOSED_V1_HEAD}"', script)
        self.assertIn(f'$TargetTree = "{PROPOSED_V1_TREE}"', script)
        self.assertNotIn(SUPERSEDED_PR469_HEAD, script)
        self.assertNotIn(SUPERSEDED_PR469_TREE, script)

    def test_docs_carry_same_binding(self):
        for name in ("README.md", "STRICT-PHYSICAL-GATE.md"):
            text = (AUD1 / name).read_text(encoding="utf-8")
            self.assertIn(PROPOSED_V1_HEAD, text, name)
            self.assertIn(PROPOSED_V1_TREE, text, name)
            self.assertNotIn(SUPERSEDED_PR469_HEAD, text, name)
            self.assertNotIn(SUPERSEDED_PR469_TREE, text, name)


if __name__ == "__main__":
    unittest.main()
