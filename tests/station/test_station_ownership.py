from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

from residual.station.ownership import StationDataDirOwnership, StationOwnershipError


class OwnershipTests(unittest.TestCase):
    def test_second_owner_same_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            first = StationDataDirOwnership(td)
            self.addCleanup(first.close)
            with self.assertRaises(StationOwnershipError):
                StationDataDirOwnership(td)

    def test_separate_directories_are_independent(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = StationDataDirOwnership(a)
            second = StationDataDirOwnership(b)
            first.close(); second.close()

    def test_release_allows_reacquire(self):
        with tempfile.TemporaryDirectory() as td:
            first = StationDataDirOwnership(td)
            first.close()
            second = StationDataDirOwnership(td)
            second.close()

    @unittest.skipUnless(os.name == "posix", "POSIX symlink semantics")
    def test_path_alias_resolves_to_same_owner(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real = base / "real"
            real.mkdir()
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            first = StationDataDirOwnership(real)
            self.addCleanup(first.close)
            with self.assertRaises(StationOwnershipError):
                StationDataDirOwnership(alias)

    @unittest.skipUnless(os.name == "posix", "POSIX cross-process lock")
    def test_other_process_is_rejected_and_restart_after_release_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            first = StationDataDirOwnership(td)
            script = textwrap.dedent('''
                import sys
                from residual.station.ownership import StationDataDirOwnership, StationOwnershipError
                try:
                    x=StationDataDirOwnership(sys.argv[1])
                except StationOwnershipError:
                    print("BLOCKED")
                    raise SystemExit(23)
                else:
                    print("ACQUIRED")
                    x.close()
            ''')
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[2]))
            p = subprocess.run([sys.executable, "-c", script, td], text=True,
                               capture_output=True, env=env, timeout=5)
            self.assertEqual(p.returncode, 23, p.stdout + p.stderr)
            self.assertEqual(p.stdout.strip(), "BLOCKED")
            first.close()
            p = subprocess.run([sys.executable, "-c", script, td], text=True,
                               capture_output=True, env=env, timeout=5)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(p.stdout.strip(), "ACQUIRED")

    @unittest.skipUnless(os.name == "posix", "POSIX crash-release semantics")
    def test_process_death_releases_lock(self):
        with tempfile.TemporaryDirectory() as td:
            script = textwrap.dedent('''
                import sys, time
                from residual.station.ownership import StationDataDirOwnership
                x=StationDataDirOwnership(sys.argv[1])
                print("READY", flush=True)
                time.sleep(30)
            ''')
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[2]))
            p = subprocess.Popen([sys.executable, "-c", script, td], text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            try:
                self.assertEqual(p.stdout.readline().strip(), "READY")
                with self.assertRaises(StationOwnershipError):
                    StationDataDirOwnership(td)
                p.kill(); p.wait(timeout=5)
                owner = StationDataDirOwnership(td)
                owner.close()
            finally:
                if p.poll() is None:
                    p.kill(); p.wait(timeout=5)
                if p.stdout:
                    p.stdout.close()
                if p.stderr:
                    p.stderr.close()

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "POSIX no-follow")
    def test_lockfile_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            outside=root.parent / (root.name + "-outside-lock")
            outside.write_text("x")
            (root / ".residual-station-owner.lock").symlink_to(outside)
            try:
                with self.assertRaises(StationOwnershipError):
                    StationDataDirOwnership(root)
            finally:
                outside.unlink(missing_ok=True)

    def test_unsupported_platform_fails_closed(self):
        candidate = StationDataDirOwnership.__new__(StationDataDirOwnership)
        with self.assertRaisesRegex(StationOwnershipError, "unavailable"):
            candidate._acquire_os_lock(platform="unsupported")

    def test_failed_os_acquisition_releases_local_guard(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(StationDataDirOwnership, "_acquire_os_lock",
                                   side_effect=StationOwnershipError("unavailable")):
                with self.assertRaisesRegex(StationOwnershipError, "unavailable"):
                    StationDataDirOwnership(td)
            owner=StationDataDirOwnership(td)
            owner.close()

    @unittest.skipUnless(os.name == "posix", "POSIX startup race")
    def test_simultaneous_startup_has_one_owner(self):
        with tempfile.TemporaryDirectory() as td:
            start = Path(td).parent / (Path(td).name + "-go")
            script = textwrap.dedent("""
                import pathlib, sys, time
                from residual.station.ownership import StationDataDirOwnership, StationOwnershipError
                start=pathlib.Path(sys.argv[2])
                deadline=time.time()+5
                while not start.exists():
                    if time.time() > deadline: raise SystemExit(91)
                    time.sleep(0.005)
                try:
                    x=StationDataDirOwnership(sys.argv[1])
                except StationOwnershipError:
                    print("BLOCKED", flush=True)
                    raise SystemExit(23)
                print("ACQUIRED", flush=True)
                time.sleep(1.5)
                x.close()
            """)
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[2]))
            ps = [subprocess.Popen([sys.executable, "-c", script, td, str(start)],
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                  for _ in range(4)]
            start.touch()
            outputs=[]
            try:
                for proc in ps:
                    out, err = proc.communicate(timeout=5)
                    outputs.append((proc.returncode, out.strip(), err))
            finally:
                for proc in ps:
                    if proc.poll() is None:
                        proc.kill(); proc.wait(timeout=5)
                start.unlink(missing_ok=True)
            self.assertEqual(sum(out == "ACQUIRED" for _, out, _ in outputs), 1, outputs)
            self.assertEqual(sum(out == "BLOCKED" for _, out, _ in outputs), 3, outputs)


if __name__ == "__main__":
    unittest.main()
