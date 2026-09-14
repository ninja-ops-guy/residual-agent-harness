from __future__ import annotations

import hashlib
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from residual.core import ContractError
from residual.inspector import (
    PX0_UPSTREAM_COMMIT,
    PX0_VERSION,
    Px0Inspector,
    _safe_env,
    snapshot,
    snapshot_is_current,
    validate_receipt_path,
)


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(self.root)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Inspector Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "inspector@example.invalid"], check=True)
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "a.py"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-m", "baseline"], check=True, stdout=subprocess.DEVNULL)
        self.fake_px0 = self.base / "px0-fake"
        self.fake_px0.write_text(
            "#!/bin/sh\nif [ \"$1\" = \"-version\" ]; then echo 'px0 0.1.2 (linux/amd64)'; exit 0; fi\nexit 0\n",
            encoding="utf-8",
        )
        self.fake_px0.chmod(self.fake_px0.stat().st_mode | stat.S_IXUSR)
        self.fake_digest = hashlib.sha256(self.fake_px0.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def inspector(self):
        return Px0Inspector(self.fake_px0, expected_binary_sha256=self.fake_digest)

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

    def test_px0_version_and_release_commit_are_pinned(self):
        self.inspector()
        self.assertEqual(PX0_VERSION, "0.1.2")
        self.assertEqual(PX0_UPSTREAM_COMMIT, "343c14a705b3021bd18ee521c82f7d7227c4ee88")

    def test_actual_v012_cli_contract_uses_supported_flags(self):
        inspector = self.inspector()
        command, backend = inspector.build_command(self.root, port=0, lsp=False, sandbox=False)
        self.assertEqual(backend, "none")
        self.assertIn("-host", command)
        self.assertIn("127.0.0.1", command)
        self.assertIn("-port", command)
        self.assertIn("0", command)
        self.assertIn("-no-lsp", command)
        self.assertIn("-no-open", command)
        self.assertIn("-no-color", command)
        # px0 v0.1.2 does not have a -no-telemetry CLI flag.
        self.assertNotIn("-no-telemetry", command)

    def test_wrong_px0_version_is_rejected(self):
        self.fake_px0.write_text("#!/bin/sh\necho 'px0 9.9.9 (linux/amd64)'\n", encoding="utf-8")
        self.fake_px0.chmod(self.fake_px0.stat().st_mode | stat.S_IXUSR)
        digest = hashlib.sha256(self.fake_px0.read_bytes()).hexdigest()
        with self.assertRaises(ContractError):
            Px0Inspector(self.fake_px0, expected_binary_sha256=digest)

    def test_unqualified_binary_digest_is_rejected(self):
        with self.assertRaises(ContractError):
            Px0Inspector(self.fake_px0, expected_binary_sha256="0" * 64)

    def test_safe_environment_does_not_inherit_operator_secrets(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "secret", "AWS_SECRET_ACCESS_KEY": "secret"}, clear=False):
            env = _safe_env()
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertEqual(env["PX0_UPDATE_URL"], "http://127.0.0.1:9")
        self.assertEqual(env["DO_NOT_TRACK"], "1")

    def test_receipt_must_live_outside_reviewed_workspace(self):
        outside = validate_receipt_path(self.base / "receipt.json", self.root)
        self.assertEqual(outside, (self.base / "receipt.json").resolve())
        with self.assertRaises(ContractError):
            validate_receipt_path(self.root / "runs" / "inspection.json", self.root)

    def test_secure_launch_fails_closed_without_bubblewrap(self):
        inspector = self.inspector()
        with patch("residual.inspector.platform.system", return_value="Linux"), patch("residual.inspector.shutil.which", return_value=None):
            with self.assertRaises(ContractError):
                inspector.build_command(self.root, port=0, sandbox=True)

    def test_launch_receipt_uses_actual_px0_bound_url(self):
        inspector = self.inspector()
        fake_process = Mock()
        actual_url = "http://127.0.0.1:49152"
        with patch("residual.inspector._spawn", return_value=fake_process) as spawn, patch(
            "residual.inspector._wait_for_url", return_value=actual_url
        ):
            process, receipt, bound = inspector.launch(
                self.root,
                port=0,
                lsp=False,
                open_browser=False,
                sandbox=False,
            )
        self.assertIs(process, fake_process)
        self.assertEqual(receipt.head_commit, bound.head_commit)
        self.assertEqual(receipt.tree_hash, bound.tree_hash)
        self.assertEqual(receipt.url, actual_url)
        self.assertTrue(receipt.binary_qualified)
        self.assertFalse(receipt.telemetry_enabled)
        self.assertFalse(receipt.lsp_enabled)
        self.assertFalse(receipt.sandboxed)
        argv = spawn.call_args.args[0]
        self.assertEqual(argv[-1], str(self.root.resolve()))
        self.assertEqual(argv[argv.index("-port") + 1], "0")
        env = spawn.call_args.kwargs["env"]
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertEqual(env["PX0_UPDATE_URL"], "http://127.0.0.1:9")


if __name__ == "__main__":
    unittest.main()
