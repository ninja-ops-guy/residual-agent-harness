"""Issue #63 M4-3: adversarial tests for the OS-isolated verification runner.

These tests run real namespace sandboxes when the platform supports them; the
fail-closed contract (UNKNOWN/ERROR, never unsandboxed fallback) is tested by
simulating platform absence.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from residual.factory import m4_sandbox
from residual.factory.m4_sandbox import (
    M4SandboxError, probe_isolation, require_isolation, run_isolated,
)

PYTHON = "/usr/bin/python3"  # Path inside the sandbox root.
ISOLATED = probe_isolation()[0]


@unittest.skipUnless(ISOLATED, "kernel namespace isolation unavailable on this platform")
class IsolatedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.worktree = Path(self.temp.name) / "worktree"
        self.worktree.mkdir()
        (self.worktree / "candidate.txt").write_text("candidate-bytes")
        self.sentinel = Path(self.temp.name) / "host-sentinel"
        self.sentinel.write_text("must-not-change")

    def check(self, code: str, **kwargs):
        options = {"timeout_s": 20, "output_limit": 1 << 20}
        options.update(kwargs)
        return run_isolated((PYTHON, "-c", code), self.worktree, **options)

    def test_pass_and_fail_and_hashes(self):
        ok = self.check("import sys; sys.stdout.write('out'); sys.stderr.write('err')")
        self.assertEqual(ok.status, "pass")
        self.assertEqual(ok.returncode, 0)
        import hashlib
        self.assertEqual(ok.stdout_sha256, hashlib.sha256(b"out").hexdigest())
        self.assertEqual(ok.stderr_sha256, hashlib.sha256(b"err").hexdigest())
        bad = self.check("import sys; sys.exit(3)")
        self.assertEqual((bad.status, bad.returncode), ("fail", 3))

    def test_worktree_readable_but_read_only(self):
        read = self.check("import pathlib; assert pathlib.Path('candidate.txt').read_text() == 'candidate-bytes'")
        self.assertEqual(read.status, "pass")
        write = self.check("open('candidate.txt', 'w').write('mutated')")
        self.assertEqual(write.status, "fail")
        self.assertEqual((self.worktree / "candidate.txt").read_text(), "candidate-bytes")

    def test_network_attempt_fails(self):
        result = self.check(
            "import socket; socket.create_connection(('203.0.113.1', 80), timeout=3)"
        )
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.reason, "exit")

    def test_external_filesystem_write_attempt_fails(self):
        code = (
            "import os, sys\n"
            f"targets = ['/etc/hostname', {str(self.sentinel)!r}, '/root/x', '/usr/local/x']\n"
            "for t in targets:\n"
            "    if not os.path.exists(t):\n"
            "        continue\n"
            "    try:\n"
            "        open(t, 'a').write('evil')\n"
            "    except OSError:\n"
            "        continue\n"
            "    sys.exit(42)\n"
            "sys.exit(0)\n"
        )
        result = self.check(code)
        self.assertEqual(result.status, "pass")  # every target was unreachable/unwritable
        self.assertEqual(self.sentinel.read_text(), "must-not-change")

    def test_host_paths_not_visible(self):
        result = self.check(
            "import os, sys; sys.exit(0 if not os.path.exists('/etc/hostname') "
            "and not os.path.exists(os.path.expanduser('~/.ssh')) else 1)"
        )
        self.assertEqual(result.status, "pass")

    def test_infinite_loop_hits_deterministic_timeout(self):
        import time
        start = time.monotonic()
        result = self.check("while True: pass", timeout_s=3)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.reason, "timeout")
        self.assertLess(time.monotonic() - start, 15)

    def test_infinite_output_is_bounded_and_killed(self):
        result = self.check(
            "import sys\nwhile True: sys.stdout.write('x' * 65536)",
            timeout_s=30, output_limit=1 << 16,
        )
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.reason, "output_limit")

    def test_fork_descendants_do_not_escape(self):
        code = (
            "import os, time\n"
            "if os.fork() == 0:\n"
            "    if os.fork() == 0:\n"
            "        time.sleep(300)\n"
            "        os._exit(0)\n"
            "print('leader exits')"
        )
        result = self.check(code)
        self.assertEqual(result.status, "pass")
        time_sleeping = subprocess.run(
            ["sh", "-c", "ps -eo args | grep -c '[t]ime.sleep' || true"],
            capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(time_sleeping, "0")

    def test_child_surviving_timeout_is_killed(self):
        code = (
            "import os, time\n"
            "if os.fork() == 0:\n"
            "    time.sleep(300)\n"
            "    os._exit(0)\n"
            "while True: pass\n"
        )
        result = self.check(code, timeout_s=3)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.reason, "timeout")
        time_sleeping = subprocess.run(
            ["sh", "-c", "ps -eo args | grep -c '[t]ime.sleep' || true"],
            capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(time_sleeping, "0")

    def test_verifier_crash_is_fail_not_error(self):
        result = self.check("import ctypes; ctypes.string_at(0)")
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.reason, "exit")
        self.assertLess(result.returncode, 0)  # terminated by a signal

    def test_memory_limit_fails_runaway_allocation(self):
        result = self.check("x = bytearray(10 * 1024**3)", memory_mb=64)
        self.assertEqual(result.status, "fail")


class FailClosedTests(unittest.TestCase):
    def setUp(self):
        m4_sandbox._probe_cache = None
        self.addCleanup(setattr, m4_sandbox, "_probe_cache", None)

    def test_non_linux_platform_fails_closed(self):
        with patch.object(m4_sandbox.sys, "platform", "darwin"):
            ok, reason = probe_isolation()
            self.assertFalse(ok)
            self.assertEqual(reason, "platform_not_linux")
            with self.assertRaises(M4SandboxError):
                require_isolation()

    def test_missing_unshare_binary_fails_closed(self):
        with patch.object(m4_sandbox.shutil, "which", return_value=None):
            ok, reason = probe_isolation()
            self.assertFalse(ok)
            self.assertEqual(reason, "unshare_binary_missing")
            with tempfile.TemporaryDirectory() as tmp:
                result = run_isolated(("true",), Path(tmp), timeout_s=5, output_limit=1024)
            self.assertEqual(result.status, "unknown")
            self.assertIn("isolation_unavailable", result.reason)

    def test_failed_namespace_probe_fails_closed(self):
        real_run = subprocess.run

        def fake_run(argv, **kwargs):
            if argv and "unshare" in str(argv[0]):
                return subprocess.CompletedProcess(argv, 1, b"", b"operation not permitted")
            return real_run(argv, **kwargs)

        with patch.object(m4_sandbox.subprocess, "run", side_effect=fake_run):
            ok, reason = probe_isolation()
            self.assertFalse(ok)
            self.assertEqual(reason, "namespace_probe_failed")

    def test_invalid_requests_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(M4SandboxError):
                run_isolated((), Path(tmp), timeout_s=5, output_limit=1024)
            with self.assertRaises(M4SandboxError):
                run_isolated(("true",), Path(tmp), timeout_s=0, output_limit=1024)
            with self.assertRaises(M4SandboxError):
                run_isolated(("true",), Path(tmp), timeout_s=5, output_limit=0)
            with self.assertRaises(M4SandboxError):
                run_isolated(("true",), Path(tmp), timeout_s=5, output_limit=1024, memory_mb=1)


if __name__ == "__main__":
    unittest.main()
