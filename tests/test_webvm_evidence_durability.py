from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from residual.workbench import browser_worker


@unittest.skipUnless(hasattr(os, "sync"), "guest durability boundary requires os.sync")
class WebVMEvidenceDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mailbox = self.root / "mailbox"
        self.mailbox.mkdir()
        self.output = self.root / "runs"
        self.output.mkdir()
        self.control = self.root / "control"
        self.pid = self.root / "worker.pid"
        self.busy = self.root / "worker.busy"
        self.poison = self.root / "worker.poison"
        self.mid = "m-" + "a" * 32

    def serve(self):
        return browser_worker.serve(
            control_file=self.control,
            pid_file=self.pid,
            mailbox=self.mailbox,
            root=self.root,
            output_root=self.output,
            poison_file=self.poison,
            busy_file=self.busy,
        )

    def test_completion_marker_is_published_only_after_filesystem_sync(self):
        events: list[str] = []
        evidence = self.output / "evidence.txt"

        def dispatch(*args, **kwargs):
            evidence.write_text("complete", encoding="utf-8")
            events.append("dispatch")
            return 0

        def sync():
            self.assertEqual(evidence.read_text(encoding="utf-8"), "complete")
            events.append("sync")

        def capture_print(value, *args, **kwargs):
            events.append(str(value))

        with (
            mock.patch.object(
                browser_worker,
                "_consume_control",
                side_effect=[(self.mid, "audit"), browser_worker.SHUTDOWN],
            ),
            mock.patch.object(browser_worker, "_dispatch_admitted", side_effect=dispatch),
            mock.patch.object(browser_worker.os, "sync", side_effect=sync),
            mock.patch("builtins.print", side_effect=capture_print),
        ):
            self.assertEqual(self.serve(), 0)

        marker = f"{browser_worker.RUN_PREFIX}{self.mid}:0"
        self.assertLess(events.index("dispatch"), events.index("sync"))
        self.assertLess(events.index("sync"), events.index(marker))
        self.assertIn(browser_worker.STOPPED, events)
        self.assertFalse(self.poison.exists())

    def test_sync_failure_poison_fences_worker_and_never_publishes_run_marker(self):
        printed: list[str] = []

        with (
            mock.patch.object(
                browser_worker,
                "_consume_control",
                return_value=(self.mid, "audit"),
            ),
            mock.patch.object(browser_worker, "_dispatch_admitted", return_value=0),
            mock.patch.object(browser_worker.os, "sync", side_effect=OSError("sync failed")),
            mock.patch("builtins.print", side_effect=lambda value, *a, **k: printed.append(str(value))),
        ):
            self.assertEqual(self.serve(), 70)

        self.assertEqual(self.poison.read_text(encoding="ascii"), self.mid + "\n")
        self.assertIn(f"{browser_worker.FATAL_PREFIX}{self.mid}:70", printed)
        self.assertNotIn(f"{browser_worker.RUN_PREFIX}{self.mid}:0", printed)


if __name__ == "__main__":
    unittest.main()
