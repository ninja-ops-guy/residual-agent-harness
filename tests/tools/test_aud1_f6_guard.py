from __future__ import annotations
import importlib.util, json, pathlib, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("f6_guard", ROOT / "tools" / "aud1" / "f6_case_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

class PhysicalEvidenceGuardTests(unittest.TestCase):
    def test_raw_git_identity_keeps_target_digest(self):
        def fake_git(repo, *args):
            if args == ("rev-parse", "HEAD"):
                return 0, guard.TARGET_SHA, ""
            if args == ("rev-parse", "HEAD^{tree}"):
                return 0, "a" * 40, ""
            if args == ("status", "--porcelain=v1"):
                return 0, "", ""
            raise AssertionError(args)
        with mock.patch.object(guard, "git", side_effect=fake_git):
            identity = guard.raw_identity(".")
        self.assertEqual(identity["head_sha"], guard.TARGET_SHA)
        self.assertTrue(identity["exact_head"])
        self.assertTrue(identity["clean_worktree"])

    def make_case_a(self, root):
        out = pathlib.Path(root) / "F6-A-inside-window"
        out.mkdir(parents=True)
        for i, label in enumerate(guard.LABELS["F6-A-inside-window"], 1):
            payload = {
                "label": label,
                "candidate": {"exact_head": True, "clean_worktree": True},
                "station_process": {"candidate_head": guard.TARGET_SHA, "record_sha256": "b" * 64},
                "public_probe": {"status": 200, "authority_key_names_present": False},
                "station": {
                    "captured_at": "2026-09-23T18:00:00+00:00",
                    "sqlite_integrity": "ok",
                    "tasks": [{"value": {"owner": "remote:runner-a", "lease": "lease-a"}}],
                },
            }
            (out / f"snapshot-{i:03d}-{label}.json").write_text(json.dumps(payload), encoding="utf-8")
        rows = [
            {"timestamp": "2026-09-23T18:00:00+00:00", "kind": "HITL"},
            {"timestamp": "2026-09-23T18:00:10+00:00", "kind": "TUNNEL_DOWN"},
            {"timestamp": "2026-09-23T18:01:10+00:00", "kind": "TUNNEL_UP"},
        ]
        (out / "operator-ledger.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        attachments = out / "attachments"
        attachments.mkdir()
        for name in guard.ATTACH["F6-A-inside-window"]:
            (attachments / name).write_text("{}", encoding="utf-8")
            (attachments / (name + ".meta.json")).write_text("{}", encoding="utf-8")
        return out

    def test_closed_world_manifest_rejects_late_file(self):
        with tempfile.TemporaryDirectory() as temp:
            out = self.make_case_a(temp)
            args = type("Args", (), {"output": temp, "case": "F6-A-inside-window"})()
            self.assertEqual(guard.freeze(args), 0)
            self.assertEqual(guard.verify(args), 0)
            (out / "late-file.txt").write_text("changed after freeze", encoding="utf-8")
            self.assertEqual(guard.verify(args), 2)

    def test_incomplete_attempt_is_frozen_as_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            pathlib.Path(temp, "F6-A-inside-window").mkdir()
            args = type("Args", (), {"output": temp, "case": "F6-A-inside-window"})()
            self.assertEqual(guard.freeze(args), 2)
            manifest = json.loads(pathlib.Path(temp, "F6-A-inside-window", "manifest.json").read_text())
            self.assertFalse(manifest["validation"]["ok"])

if __name__ == "__main__":
    unittest.main()
