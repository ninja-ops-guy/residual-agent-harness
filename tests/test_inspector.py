from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from residual.core import ContractError
from residual.inspector import PX0_UPSTREAM_COMMIT, PX0_VERSION, Px0Inspector, snapshot, snapshot_is_current


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-b", "main", str(self.root)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Inspector Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "inspector@example.invalid"], check=True)
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "a.py"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-m", "baseline"], check=True, stdout=subprocess.DEVNULL)
        self.fake_px0 = self.root / "px0-fake"
        self.fake_px0.write_text("#!/bin/sh\nif [ \"$1\" = \"-version\" ]; then echo 'px0 0.1.2 (linux/amd64)'; exit 0; fi\nexit 0\n", encoding="utf-8")
        self.fake_px0.chmod(self.fake_px0.stat().st_mode | stat.S_IXUSR)

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_binds_head_tree_and_clean_state(self):
        value = snapshot(self.root)
        self.assertTrue(value.clean)
        self.assertEqual(len(value.head_commit), 40)
        self.assertEqual(len(value.tree_hash), 40)
        self.assertTrue(snapshot_is_current(value))
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        self.assertFalse(snapshot_is_current(value))
        with self.assertRaises(ContractError):
            snapshot(self.root)

    def test_px0_version_is_pinned_and_safe_flags_are_default(self):
        inspector = Px0Inspector(self.fake_px0)
        command = inspector.build_command(self.root, port=7777, lsp=False, open_browser=False)
        self.assertIn("-host", command)
        self.assertIn("127.0.0.1", command)
        self.assertIn("-no-telemetry", command)
        self.assertIn("-no-lsp", command)
        self.assertIn("-no-open", command)
        self.assertEqual(PX0_VERSION, "0.1.2")
        self.assertEqual(PX0_UPSTREAM_COMMIT, "57539720bad363980ef6dd80febbc925ffab214f")

    def test_wrong_px0_version_is_rejected(self):
        self.fake_px0.write_text("#!/bin/sh\necho 'px0 9.9.9 (linux/amd64)'\n", encoding="utf-8")
        self.fake_px0.chmod(self.fake_px0.stat().st_mode | stat.S_IXUSR)
        with self.assertRaises(ContractError):
            Px0Inspector(self.fake_px0)

    def test_launch_receipt_binds_binary_and_git_snapshot(self):
        inspector = Px0Inspector(self.fake_px0)
        fake_process = unittest.mock.Mock()
        with patch("residual.inspector.subprocess.Popen", return_value=fake_process) as popen:
            process, receipt, bound = inspector.launch(self.root, port=7788, lsp=False, open_browser=False)
        self.assertIs(process, fake_process)
        self.assertEqual(receipt.head_commit, bound.head_commit)
        self.assertEqual(receipt.tree_hash, bound.tree_hash)
        self.assertEqual(receipt.url, "http://127.0.0.1:7788")
        self.assertFalse(receipt.telemetry_enabled)
        self.assertFalse(receipt.lsp_enabled)
        argv = popen.call_args.args[0]
        self.assertEqual(argv[-1], str(self.root.resolve()))
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["DO_NOT_TRACK"], "1")
        self.assertEqual(env["PX0_TELEMETRY"], "0")


if __name__ == "__main__":
    unittest.main()
