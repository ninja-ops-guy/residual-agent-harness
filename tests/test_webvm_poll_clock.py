from __future__ import annotations

import inspect
import time
import unittest
from unittest import mock

from residual.workbench import browser_mailbox, browser_poll, browser_worker


class WebVMPollClockTests(unittest.TestCase):
    def test_relative_pause_bypasses_python_timeout_wrappers(self):
        with mock.patch.object(time, "sleep", side_effect=OverflowError("timestamp too large")):
            with mock.patch.object(browser_poll, "_usleep", return_value=0) as wait:
                browser_poll.pause(0.05)
        wait.assert_called_once_with(50_000)
        self.assertFalse(hasattr(browser_poll, "select"))
        pause_source = inspect.getsource(browser_poll.pause)
        self.assertNotIn("select", pause_source)
        self.assertNotIn("time.sleep", pause_source)

    def test_browser_poll_interval_is_bounded(self):
        for value in (-0.01, 1.01, True, "0.05"):
            with self.assertRaises(ValueError):
                browser_poll.pause(value)

    def test_interrupted_libc_wait_is_retried_without_changing_contract(self):
        with mock.patch.object(browser_poll, "_usleep", side_effect=[-1, 0]) as wait:
            with mock.patch.object(browser_poll.ctypes, "get_errno", return_value=browser_poll.errno.EINTR):
                browser_poll.pause(0.05)
        self.assertEqual(wait.call_count, 2)

    def test_public_worker_and_mailbox_do_not_call_python_sleep(self):
        self.assertNotIn("time.sleep(", inspect.getsource(browser_worker))
        self.assertNotIn("time.sleep(", inspect.getsource(browser_mailbox))
        self.assertIn("pause()", inspect.getsource(browser_worker))
        self.assertIn("pause()", inspect.getsource(browser_mailbox))


if __name__ == "__main__":
    unittest.main()
