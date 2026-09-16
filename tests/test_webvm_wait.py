from __future__ import annotations

from pathlib import Path
import unittest

from residual.workbench import browser_mailbox, browser_worker
from residual.workbench.webvm_wait import wait


class WebVMWaitTests(unittest.TestCase):
    def test_zero_and_small_positive_wait_return(self):
        wait(0)
        wait(0.001)

    def test_invalid_waits_fail_closed(self):
        for value in (-0.001, float('inf'), float('nan'), 5.001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                wait(value)
        with self.assertRaises(TypeError):
            wait(True)

    def test_long_lived_browser_paths_do_not_call_python_time_sleep(self):
        for module in (browser_worker, browser_mailbox):
            with self.subTest(module=module.__name__):
                source = Path(module.__file__).read_text(encoding='utf-8')
                self.assertNotIn('time.sleep(', source)
                self.assertIn('browser_wait(0.05)', source)


if __name__ == '__main__':
    unittest.main()
