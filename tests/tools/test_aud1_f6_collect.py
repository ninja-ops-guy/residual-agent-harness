from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("f6_collect", ROOT / "tools" / "aud1" / "f6_collect.py")
f6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f6)


class F6DiagnosticsTests(unittest.TestCase):
    def test_redactor_never_retains_token_or_credentials(self):
        value = {
            "session_token": "operator-secret",
            "worker_token": "worker-secret",
            "provider_credentials": {"openai": "provider-secret"},
            "safe": {"remote_workers_enabled": True},
        }
        clean = f6.redact(value)
        rendered = json.dumps(clean)
        self.assertNotIn("operator-secret", rendered)
        self.assertNotIn("worker-secret", rendered)
        self.assertNotIn("provider-secret", rendered)
        self.assertTrue(clean["safe"]["remote_workers_enabled"])

    def test_redactor_catches_secret_value_under_unexpected_key(self):
        value = {
            "mystery": "Authorization: Bearer this-is-a-secret-token-value",
            "opaque": "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0",
            "safe": "worker reconnect completed",
        }
        clean = f6.redact(value)
        rendered = json.dumps(clean)
        self.assertNotIn("this-is-a-secret-token-value", rendered)
        self.assertNotIn("A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0", rendered)
        self.assertEqual(clean["safe"], "worker reconnect completed")

    def test_read_only_snapshot_captures_task_and_event_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            db = pathlib.Path(temp) / "station.sqlite3"
            conn = sqlite3.connect(db)
            try:
                conn.executescript("""
                CREATE TABLE projects(id TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE tasks(project TEXT, id TEXT, value TEXT NOT NULL, PRIMARY KEY(project,id));
                CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT,project TEXT,value TEXT,prev_hash TEXT,hash TEXT);
                CREATE TABLE settings(id TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE submissions(id TEXT PRIMARY KEY,value TEXT);
                """)
                conn.execute("INSERT INTO projects VALUES(?,?)", ("p-test", '{"id":"p-test","name":"physical"}'))
                conn.execute("INSERT INTO tasks VALUES(?,?,?)", ("p-test", "OPS-101", '{"id":"OPS-101","state":"running","owner":"remote:Hammer","lease":"lease-a","lease_until":9999999999}'))
                conn.execute("INSERT INTO events(event_id,project,value,prev_hash,hash) VALUES(?,?,?,?,?)",
                             ("e-1", "p-test", '{"event_type":"task.claimed","actor":"remote:Hammer"}', "", "h1"))
                conn.execute("INSERT INTO settings VALUES(?,?)", ("worker_token", '"do-not-retain"'))
                conn.execute("INSERT INTO submissions VALUES(?,?)", ("s1", "{}"))
                conn.commit()
            finally:
                # Explicit close: on Windows an open SQLite handle locks the file and
                # blocks TemporaryDirectory teardown.
                conn.close()

            before = f6.sha256_file(db)
            snap = f6.station_snapshot(db, "p-test", "OPS-101")
            after = f6.sha256_file(db)
            self.assertEqual(before, after)
            self.assertEqual(snap["sqlite_integrity"], "ok")
            self.assertIsInstance(snap["captured_monotonic_ns"], int)
            self.assertGreater(snap["captured_monotonic_ns"], 0)
            self.assertEqual(snap["tasks"][0]["value"]["owner"], "remote:Hammer")
            self.assertNotIn("lease", snap["tasks"][0]["value"])
            self.assertTrue(snap["tasks"][0]["value"]["lease_present"])
            self.assertEqual(
                snap["tasks"][0]["value"]["lease_fingerprint"],
                "sha256:" + f6.sha256_bytes(b"lease-a"),
            )
            self.assertEqual(snap["event_count"], 1)
            self.assertEqual(snap["settings_redacted"]["worker_token"], "<redacted>")

    def test_attach_sanitizes_text_and_records_original_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            source = pathlib.Path(temp) / "remote-before.json"
            source.write_text(
                json.dumps({
                    "credential_present": True,
                    "unexpected": "Bearer this-is-a-secret-token-value",
                    "state": "connected",
                }) + "\n",
                encoding="utf-8",
            )
            case = "F6-A-inside-window"
            args = type("Args", (), {
                "output": temp,
                "case": case,
                "file": str(source),
                "name": "remote-before.json",
            })()
            original_hash = f6.sha256_file(source)
            self.assertEqual(f6.attach(args), 0)
            destination = pathlib.Path(temp) / case / "attachments" / "remote-before.json"
            meta = json.loads(destination.with_suffix(".json.meta.json").read_text(encoding="utf-8"))
            stored = destination.read_text(encoding="utf-8")
            self.assertNotIn("this-is-a-secret-token-value", stored)
            self.assertIn("<redacted>", stored)
            self.assertEqual(meta["source_sha256"], original_hash)
            self.assertTrue(meta["redacted_content"])
            self.assertEqual(meta["stored_sha256"], f6.sha256_file(destination))

    def test_manifest_freeze_and_verify_detect_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            case = "F6-A-inside-window"
            out = pathlib.Path(temp) / case
            out.mkdir()
            evidence = out / "fact.json"
            evidence.write_text('{"fact":true}\n', encoding="utf-8")

            args = type("Args", (), {"output": temp, "case": case})()
            self.assertEqual(f6.freeze(args), 0)
            self.assertEqual(f6.verify(args), 0)

            evidence.write_text('{"fact":false}\n', encoding="utf-8")
            self.assertEqual(f6.verify(args), 2)

    def test_candidate_identity_binds_head_and_tree(self):
        def fake_run(command, cwd=None, timeout=15):
            if command == ["git", "rev-parse", "HEAD"]:
                return {"stdout": f6.TARGET_SHA + "\n", "returncode": 0}
            if command == ["git", "rev-parse", "HEAD^{tree}"]:
                return {"stdout": f6.TARGET_TREE + "\n", "returncode": 0}
            if command == ["git", "status", "--porcelain=v1"]:
                return {"stdout": "", "returncode": 0}
            raise AssertionError(command)

        original = f6.run
        f6.run = fake_run
        try:
            identity = f6.candidate_identity(".")
        finally:
            f6.run = original
        self.assertEqual(identity["expected_sha"], f6.TARGET_SHA)
        self.assertEqual(identity["expected_tree"], f6.TARGET_TREE)
        self.assertTrue(identity["exact_head"])
        self.assertTrue(identity["exact_tree"])
        self.assertTrue(identity["clean_worktree"])

    def test_candidate_identity_flags_wrong_tree(self):
        def fake_run(command, cwd=None, timeout=15):
            if command == ["git", "rev-parse", "HEAD"]:
                return {"stdout": f6.TARGET_SHA + "\n", "returncode": 0}
            if command == ["git", "rev-parse", "HEAD^{tree}"]:
                return {"stdout": "f" * 40 + "\n", "returncode": 0}
            if command == ["git", "status", "--porcelain=v1"]:
                return {"stdout": "", "returncode": 0}
            raise AssertionError(command)

        original = f6.run
        f6.run = fake_run
        try:
            identity = f6.candidate_identity(".")
        finally:
            f6.run = original
        self.assertTrue(identity["exact_head"])
        self.assertFalse(identity["exact_tree"])

    def test_capture_refuses_tree_mismatch_before_station_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            def fake_identity(repo):
                return {
                    "path": str(repo),
                    "expected_sha": f6.TARGET_SHA,
                    "expected_tree": f6.TARGET_TREE,
                    "head_sha": f6.TARGET_SHA,
                    "tree_sha": "f" * 40,
                    "tracked_or_untracked_changes": [],
                    "exact_head": True,
                    "exact_tree": False,
                    "clean_worktree": True,
                    "git_errors": [],
                }

            def forbidden_snapshot(db, project, task):
                raise AssertionError("station_snapshot must not run after tree refusal")

            original_identity, original_snapshot = f6.candidate_identity, f6.station_snapshot
            f6.candidate_identity, f6.station_snapshot = fake_identity, forbidden_snapshot
            try:
                args = type("Args", (), {
                    "output": temp,
                    "case": "F6-A-inside-window",
                    "label": "00-preflight",
                    "candidate_repo": temp,
                    "db": str(pathlib.Path(temp) / "station.sqlite3"),
                    "project": "p-test",
                    "task": "OPS-101",
                    "station_url": None,
                })()
                with self.assertRaises(SystemExit) as raised:
                    f6.capture(args)
                self.assertIn("expected", str(raised.exception))
            finally:
                f6.candidate_identity, f6.station_snapshot = original_identity, original_snapshot


if __name__ == "__main__":
    unittest.main()
