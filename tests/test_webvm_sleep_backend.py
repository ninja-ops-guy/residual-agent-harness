from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest import mock

from residual.workbench import webvm_wait


ROOT = Path(__file__).resolve().parents[1]


class WebVMSleepBackendTests(unittest.TestCase):
    def test_default_backend_preserves_python_sleep(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(webvm_wait.time, "sleep") as standard:
            webvm_wait.sleep(0.05)
        standard.assert_called_once_with(0.05)

    def test_explicit_webvm_backend_uses_legacy_nanosleep(self):
        with mock.patch.dict(os.environ, {webvm_wait.BACKEND_ENV: webvm_wait.LEGACY_NANOSLEEP}, clear=False), mock.patch.object(webvm_wait, "_legacy_nanosleep") as legacy:
            webvm_wait.sleep(0.05)
        legacy.assert_called_once_with(0.05)

    def test_unknown_backend_fails_closed(self):
        with mock.patch.dict(os.environ, {webvm_wait.BACKEND_ENV: "unknown"}, clear=False):
            with self.assertRaises(RuntimeError):
                webvm_wait.sleep(0.05)

    def test_duration_conversion_is_bounded(self):
        spec = webvm_wait._timespec(0.05)
        self.assertEqual((spec.tv_sec, spec.tv_nsec), (0, 50_000_000))
        with self.assertRaises(ValueError):
            webvm_wait._timespec(-0.01)
        with self.assertRaises(ValueError):
            webvm_wait._timespec(float("inf"))

    def test_persistent_browser_paths_do_not_call_python_sleep_directly(self):
        for relative in (
            "residual/workbench/browser_worker.py",
            "residual/workbench/browser_mailbox.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("from .webvm_wait import sleep as webvm_sleep", source)
            self.assertNotIn("time.sleep(", source)

    def test_webvm_image_and_browser_proof_activate_and_cross_boundary(self):
        dockerfile = (ROOT / "demo/vm/Dockerfile").read_text(encoding="utf-8")
        smoke = (ROOT / "demo/vm/browser_smoke.py").read_text(encoding="utf-8")
        self.assertIn("RESIDUAL_WEBVM_SLEEP_BACKEND=legacy-nanosleep", dockerfile)
        self.assertIn("webvm_sleep_backend_crosses_time64_boundary", smoke)
        self.assertIn("range(300)", smoke)


if __name__ == "__main__":
    unittest.main()
