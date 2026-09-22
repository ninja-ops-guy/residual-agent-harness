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

    def test_read_only_snapshot_captures_task_and_event_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            db = pathlib.Path(temp) / "station.sqlite3"
            with sqlite3.connect(db) as conn:
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

            before = f6.sha256_file(db)
            snap = f6.station_snapshot(db, "p-test", "OPS-101")
            after = f6.sha256_file(db)
            self.assertEqual(before, after)
            self.assertEqual(snap["sqlite_integrity"], "ok")
            self.assertEqual(snap["tasks"][0]["value"]["owner"], "remote:Hammer")
            self.assertEqual(snap["event_count"], 1)
            self.assertEqual(snap["settings_redacted"]["worker_token"], "<redacted>")

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


if __name__ == "__main__":
    unittest.main()
