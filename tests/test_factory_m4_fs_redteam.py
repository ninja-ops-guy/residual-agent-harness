"""Issue #63 M4-2 red team: adversarial candidate-path writes never mutate
outside the worktree and never follow or honour links/special files."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from residual.factory.m4_safety import M4SafetyError, apply_artifact, snapshot


class FilesystemRedTeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "worktree"
        self.work.mkdir(mode=0o700)
        self.sentinel = self.root / "external-sentinel"
        self.sentinel.write_bytes(b"intact")

    def tearDown(self):
        self.assertEqual(self.sentinel.read_bytes(), b"intact")

    def test_dotdot_traversal_rejected(self):
        for path in ("../external-sentinel", "a/../../external-sentinel", ".."):
            with self.subTest(path=path), self.assertRaises(M4SafetyError):
                apply_artifact(self.work, path, b"evil")

    def test_absolute_and_backslash_paths_rejected(self):
        for path in ("/etc/passwd", "a\\..\\external-sentinel", "", "a//b"):
            with self.subTest(path=path), self.assertRaises(M4SafetyError):
                apply_artifact(self.work, path, b"evil")

    def test_git_metadata_paths_rejected(self):
        for path in (".git", ".GIT/config", "a/.git/hooks/x"):
            with self.subTest(path=path), self.assertRaises(M4SafetyError):
                apply_artifact(self.work, path, b"evil")

    def test_fifo_target_rejected_and_preserved(self):
        os.mkfifo(self.work / "pipe")
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, "pipe", b"evil")
        self.assertTrue((self.work / "pipe").is_fifo())

    def test_unix_socket_rejected_by_snapshot(self):
        sock = socket.socket(socket.AF_UNIX)
        try:
            sock.bind(str(self.work / "sock"))
            with self.assertRaises(M4SafetyError):
                snapshot(self.work)
        finally:
            sock.close()

    def test_hardlink_to_external_sentinel_rejected(self):
        target = self.work / "linked"
        os.link(self.sentinel, target)
        self.assertEqual(os.stat(target).st_nlink, 2)
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, "linked", b"evil")
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, "linked", None)  # deletion too

    def test_symlink_parent_swap_race_rejected_or_contained(self):
        # Parent directory atomically swapped for an external symlink between
        # validation and write: the descriptor-relative walk either fails closed
        # or (if the swap lands before traversal) writes into a directory it
        # legitimately opened - never through a symlink to the sentinel dir.
        external = self.root / "external"
        external.mkdir()
        (self.work / "sub").mkdir()
        stop = threading.Event()
        races = []

        def swapper():
            while not stop.is_set():
                try:
                    os.rename(self.work / "sub", self.root / "hold")
                    (self.work / "sub").symlink_to(external)
                    races.append("swapped")
                    os.unlink(self.work / "sub")
                    os.rename(self.root / "hold", self.work / "sub")
                except OSError:
                    pass

        thread = threading.Thread(target=swapper, daemon=True)
        thread.start()
        try:
            for _ in range(200):
                try:
                    apply_artifact(self.work, "sub/file.txt", b"data")
                except M4SafetyError:
                    pass
                self.assertFalse((external / "file.txt").exists())
        finally:
            stop.set()
            thread.join(timeout=5)

    def test_dangling_symlink_target_and_parent(self):
        (self.work / "dangling").symlink_to(self.root / "does-not-exist")
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, "dangling", b"evil")
        (self.work / "dir-link").symlink_to(self.root / "no-such-dir")
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, "dir-link/file.txt", b"evil")

    def test_file_type_change_to_symlink_between_calls_rejected(self):
        apply_artifact(self.work, "target.txt", b"first")
        os.unlink(self.work / "target.txt")
        (self.work / "target.txt").symlink_to(self.sentinel)
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, "target.txt", b"evil")

    def test_snapshot_detects_directory_only_pollution(self):
        before = snapshot(self.work)
        (self.work / ".hidden-cache").mkdir()
        self.assertNotEqual(snapshot(self.work), before)


if __name__ == "__main__":
    unittest.main()
