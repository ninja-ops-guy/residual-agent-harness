import unittest
from unittest.mock import patch

from residual.workbench.__main__ import main


class WorkbenchCliDurabilityTests(unittest.TestCase):
    @patch("residual.workbench.__main__.os.sync", create=True)
    @patch("residual.workbench.runner.main", return_value=0)
    def test_successful_runner_command_syncs_before_return(self, runner_main, sync):
        self.assertEqual(main(["audit"]), 0)
        runner_main.assert_called_once_with(["audit"])
        sync.assert_called_once_with()

    @patch("residual.workbench.__main__.os.sync", create=True)
    @patch("residual.workbench.runner.main", return_value=1)
    def test_failed_runner_command_does_not_publish_durability(self, runner_main, sync):
        self.assertEqual(main(["audit"]), 1)
        runner_main.assert_called_once_with(["audit"])
        sync.assert_not_called()

    @patch("residual.workbench.__main__.os.sync", create=True)
    @patch("residual.workbench.build.main", return_value=0)
    def test_successful_build_command_syncs_and_strips_subcommand(self, build_main, sync):
        self.assertEqual(main(["build", "--request", "mission.json"]), 0)
        build_main.assert_called_once_with(["--request", "mission.json"])
        sync.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
