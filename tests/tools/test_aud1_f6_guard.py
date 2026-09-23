from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "f6_guard", ROOT / "tools" / "aud1" / "f6_case_guard.py"
)
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

    def remote_record(
        self,
        *,
        label,
        host="OLDHOST",
        pid=101,
        created="20260923170000.000000-000",
        found=True,
        connected=False,
        reachable=False,
        surrender=False,
    ):
        process = None
        if found:
            process = {
                "ProcessId": pid,
                "Name": "python.exe",
                "CreationDate": created,
                "IsResidualWorker": True,
            }
        log = None
        if surrender:
            log = {
                "Path": "runner.log",
                "Bytes": 100,
                "SHA256": "a" * 64,
                "Tail": [guard.SURRENDER_TEXT],
            }
        return {
            "schema": guard.REMOTE_SCHEMA,
            "captured_at": "2026-09-23T18:00:00+00:00",
            "label": label,
            "hostname": host,
            "station_host": "127.0.0.1",
            "station_port": 8765,
            "runner_pid_requested": pid,
            "runner_process": process,
            "runner_process_found": found,
            "runner_has_station_connection": connected,
            "worker_token_present": True,
            "runner_api_key_present": False,
            "tcp_probe": {"TcpTestSucceeded": reachable},
            "station_connections_for_runner": (
                [{"OwningProcess": pid}] if connected else []
            ),
            "runner_log": log,
        }

    def write_attachment(self, attachments, name, payload):
        (attachments / name).write_text(json.dumps(payload), encoding="utf-8")
        (attachments / (name + ".meta.json")).write_text(
            json.dumps({"stored_sha256": "b" * 64}),
            encoding="utf-8",
        )

    def make_case_a(self, root):
        out = pathlib.Path(root) / "F6-A-inside-window"
        out.mkdir(parents=True)
        for index, label in enumerate(guard.LABELS["F6-A-inside-window"], 1):
            payload = {
                "label": label,
                "candidate": {"exact_head": True, "clean_worktree": True},
                "station_process": {
                    "candidate_head": guard.TARGET_SHA,
                    "record_sha256": "b" * 64,
                },
                "public_probe": {
                    "status": 200,
                    "authority_key_names_present": False,
                },
                "station": {
                    "captured_at": "2026-09-23T18:00:00+00:00",
                    "project_id": "p-test",
                    "sqlite_integrity": "ok",
                    "tasks": [
                        {
                            "id": "OPS-101",
                            "value": {
                                "owner": "remote:runner-a",
                                "lease": "lease-a",
                            },
                        }
                    ],
                },
            }
            (out / f"snapshot-{index:03d}-{label}.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

        rows = [
            {"timestamp": "2026-09-23T18:00:00+00:00", "kind": "HITL"},
            {"timestamp": "2026-09-23T18:00:10+00:00", "kind": "TUNNEL_DOWN"},
            {"timestamp": "2026-09-23T18:01:10+00:00", "kind": "TUNNEL_UP"},
        ]
        (out / "operator-ledger.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

        attachments = out / "attachments"
        attachments.mkdir()
        remote = {
            "remote-01-owned-before.json": self.remote_record(
                label="owned-before", connected=True, reachable=True
            ),
            "remote-02-transport-down.json": self.remote_record(
                label="transport-down", connected=False, reachable=False
            ),
            "remote-03-reconnected.json": self.remote_record(
                label="reconnected", connected=True, reachable=True
            ),
            "remote-04-terminal.json": self.remote_record(
                label="terminal", found=False, connected=False, reachable=True
            ),
        }
        for name, payload in remote.items():
            self.write_attachment(attachments, name, payload)
        return out

    def make_case_b_remote(self, root):
        out = pathlib.Path(root) / "F6-B-outside-window"
        attachments = out / "attachments"
        attachments.mkdir(parents=True)
        remote = {
            "remote-01-owned-before.json": self.remote_record(
                label="owned-before", connected=True, reachable=True
            ),
            "remote-02-transport-down.json": self.remote_record(
                label="transport-down", connected=False, reachable=False
            ),
            "remote-03-after-grace.json": self.remote_record(
                label="after-grace",
                found=False,
                connected=False,
                reachable=False,
                surrender=True,
            ),
            "remote-04-reassigned.json": self.remote_record(
                label="reassigned",
                host="NEWHOST",
                pid=202,
                created="20260923171000.000000-000",
                connected=True,
                reachable=True,
            ),
            "remote-05-old-returned.json": self.remote_record(
                label="old-returned", found=False, connected=False, reachable=True
            ),
        }
        for name, payload in remote.items():
            self.write_attachment(attachments, name, payload)
        return out

    def test_remote_evidence_rejects_placeholder_json(self):
        with tempfile.TemporaryDirectory() as temp:
            out = pathlib.Path(temp) / "F6-A-inside-window"
            attachments = out / "attachments"
            attachments.mkdir(parents=True)
            for name in guard.ATTACH["F6-A-inside-window"]:
                self.write_attachment(attachments, name, {})
            errors = guard.validate_remote_evidence(out, "F6-A-inside-window")
            self.assertTrue(errors)
            self.assertTrue(any("schema mismatch" in error for error in errors), errors)

    def test_case_b_requires_surrender_and_different_live_runner(self):
        with tempfile.TemporaryDirectory() as temp:
            out = self.make_case_b_remote(temp)
            self.assertEqual(
                guard.validate_remote_evidence(out, "F6-B-outside-window"),
                [],
            )

            after = out / "attachments" / "remote-03-after-grace.json"
            record = json.loads(after.read_text(encoding="utf-8"))
            record["runner_log"]["Tail"] = ["generic disconnect"]
            after.write_text(json.dumps(record), encoding="utf-8")
            errors = guard.validate_remote_evidence(out, "F6-B-outside-window")
            self.assertTrue(
                any("WorkerAuthorityLost" in error for error in errors),
                errors,
            )

    def test_stale_probe_must_bind_original_task_lease_and_denial(self):
        before = {
            "station": {
                "project_id": "p-test",
                "tasks": [
                    {
                        "id": "OPS-101",
                        "value": {
                            "owner": "remote:old",
                            "lease": "lease-old",
                        },
                    }
                ],
            }
        }
        good = {
            "schema": guard.STALE_SCHEMA,
            "project_id": "p-test",
            "task_id": "OPS-101",
            "lease": "lease-old",
            "observed_status": 403,
            "rejected": True,
            "accepted": False,
            "credential_value_retained": False,
            "response_excerpt": json.dumps({"error": guard.STALE_REJECTION_TEXT}),
        }
        self.assertEqual(guard.validate_stale_probe(good, before), [])

        wrong = dict(good)
        wrong["task_id"] = "OPS-999"
        wrong["lease"] = "other-lease"
        wrong["response_excerpt"] = '{"error":"Remote workers are disabled"}'
        errors = guard.validate_stale_probe(wrong, before)
        self.assertTrue(any("task does not match" in error for error in errors), errors)
        self.assertTrue(any("lease does not match" in error for error in errors), errors)
        self.assertTrue(
            any("reassigned-authority denial" in error for error in errors),
            errors,
        )

    def test_closed_world_manifest_rejects_late_file(self):
        with tempfile.TemporaryDirectory() as temp:
            out = self.make_case_a(temp)
            args = type(
                "Args",
                (),
                {"output": temp, "case": "F6-A-inside-window"},
            )()
            self.assertEqual(guard.freeze(args), 0)
            self.assertEqual(guard.verify(args), 0)
            (out / "late-file.txt").write_text(
                "changed after freeze", encoding="utf-8"
            )
            self.assertEqual(guard.verify(args), 2)

    def test_incomplete_attempt_is_frozen_as_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            pathlib.Path(temp, "F6-A-inside-window").mkdir()
            args = type(
                "Args",
                (),
                {"output": temp, "case": "F6-A-inside-window"},
            )()
            self.assertEqual(guard.freeze(args), 2)
            manifest = json.loads(
                pathlib.Path(
                    temp,
                    "F6-A-inside-window",
                    "manifest.json",
                ).read_text()
            )
            self.assertFalse(manifest["validation"]["ok"])


if __name__ == "__main__":
    unittest.main()
