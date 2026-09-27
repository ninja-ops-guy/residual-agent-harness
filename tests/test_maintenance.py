from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from residual.core import ContractError
from residual.maintenance import Installation, doctor_report, perform_update, update_status
from residual.version import current_version


class MaintenanceTests(unittest.TestCase):
    def test_runtime_version_comes_from_package_metadata(self):
        from importlib.metadata import version
        self.assertEqual(current_version(), version("residual-agent-harness"))

    def test_doctor_reports_state_without_mutating_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            data = repo / "station-state"
            data.mkdir()
            install = Installation("editable", str(repo / "residual"), str(repo), True)
            facts = {
                "source_head": "1" * 40,
                "source_branch": "main",
                "working_tree_clean": True,
                "origin": "origin-url",
            }
            with patch("residual.maintenance.inspect_installation", return_value=install), \
                 patch("residual.maintenance._git_facts", return_value=facts), \
                 patch("residual.maintenance.shutil.which", return_value="/usr/bin/git"), \
                 patch.dict("os.environ", {"RESIDUAL_DATA": str(data)}, clear=False):
                report = doctor_report()
            self.assertEqual(report["update_readiness"], "READY")
            self.assertEqual(report["data_directory"], str(data))
            self.assertTrue(data.exists())

    def test_dirty_source_checkout_refuses_without_running_update_commands(self):
        install = Installation("editable", "/repo/residual", "/repo", True)
        facts = {
            "source_head": "1" * 40,
            "source_branch": "main",
            "working_tree_clean": False,
            "origin": "origin",
        }
        with patch("residual.maintenance.inspect_installation", return_value=install), \
             patch("residual.maintenance._git_facts", return_value=facts), \
             patch("residual.maintenance._run") as run:
            with self.assertRaisesRegex(ContractError, "not clean"):
                perform_update()
        run.assert_not_called()

    def test_source_update_is_fast_forward_only_and_never_resets_or_stashes(self):
        install = Installation("editable", "/repo/residual", "/repo", True)
        before = "1" * 40
        target = "2" * 40
        facts = {
            "source_head": before,
            "source_branch": "main",
            "working_tree_clean": True,
            "origin": "origin",
        }
        calls = []

        def record(argv, **kwargs):
            calls.append(argv)
            class Result:
                stdout = ""
                stderr = ""
            return Result()

        with patch("residual.maintenance.inspect_installation", return_value=install), \
             patch("residual.maintenance._git_facts", return_value=facts), \
             patch("residual.maintenance._remote_target", return_value=target), \
             patch("residual.maintenance._git", return_value=target), \
             patch("residual.maintenance._run", side_effect=record):
            result = perform_update()

        flat = " ".join(" ".join(call) for call in calls)
        self.assertTrue(result["updated"])
        self.assertIn("merge --ff-only FETCH_HEAD", flat)
        self.assertNotIn("reset", flat)
        self.assertNotIn("stash", flat)

    def test_update_check_resolves_remote_without_source_mutation(self):
        install = Installation("source-checkout", "/repo/residual", "/repo", False)
        facts = {
            "source_head": "1" * 40,
            "source_branch": "main",
            "working_tree_clean": True,
            "origin": "origin",
        }
        with patch("residual.maintenance.inspect_installation", return_value=install), \
             patch("residual.maintenance._git_facts", return_value=facts), \
             patch("residual.maintenance._remote_target", return_value="2" * 40):
            result = update_status()
        self.assertTrue(result["update_available"])
        self.assertEqual(result["target"], "main")


if __name__ == "__main__":
    unittest.main()
