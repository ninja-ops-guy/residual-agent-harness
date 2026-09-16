from __future__ import annotations

import inspect
import time
import unittest
from unittest import mock

from residual.workbench import browser_mailbox, browser_poll, browser_worker


class WebVMPollClockTests(unittest.TestCase):
    def test_relative_pause_does_not_use_time_sleep(self):
        with mock.patch.object(time, "sleep", side_effect=OverflowError("timestamp too large")):
            with mock.patch.object(browser_poll.select, "select", return_value=([], [], [])) as wait:
                browser_poll.pause(0.05)
        wait.assert_called_once_with([], [], [], 0.05)

    def test_browser_poll_interval_is_bounded(self):
        for value in (-0.01, 1.01, True, "0.05"):
            with self.assertRaises(ValueError):
                browser_poll.pause(value)

    def test_public_worker_and_mailbox_do_not_call_time_sleep(self):
        self.assertNotIn("time.sleep(", inspect.getsource(browser_worker))
        self.assertNotIn("time.sleep(", inspect.getsource(browser_mailbox))
        self.assertIn("pause()", inspect.getsource(browser_worker))
        self.assertIn("pause()", inspect.getsource(browser_mailbox))


if __name__ == "__main__":
    unittest.main()
