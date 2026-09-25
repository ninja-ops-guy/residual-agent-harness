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
                    "captured_at": f"2026-09-23T18:00:{index:02d}+00:00",
                    "captured_monotonic_ns": index,
                    "project_id": "p-test",
                    "sqlite_integrity": "ok",
                    "tasks": [
                        {
                            "id": "OPS-101",
                            "value": {
                                "owner": "remote:runner-a",
                                "lease_present": True,
                                "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(b"lease-a"),
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
                self.write_attachment(attachments, name, {"placeholder": True})
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
                            "lease_present": True,
                            "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(b"abcdefghijklmnopqrstuvwxyzABCDEF"),
                            "lease_until": 1000.0,
                            "attempt": 1,
                        },
                    }
                ],
            }
        }
        good = {
            "schema": guard.STALE_SCHEMA,
            "project_id": "p-test",
            "task_id": "OPS-101",
            "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(
                b"abcdefghijklmnopqrstuvwxyzABCDEF"
            ),
            "attempt": 1,
            "owner": "remote:old",
            "observed_status": 403,
            "rejected": True,
            "accepted": False,
            "credential_value_retained": False,
            "response_excerpt": guard.STALE_REJECTION_TEXT,
        }
        self.assertEqual(guard.validate_stale_probe(good, before), [])

        wrong = dict(good)
        wrong["task_id"] = "OPS-999"
        wrong["lease_fingerprint"] = "sha256:" + ("0" * 64)
        wrong["response_excerpt"] = '{"error":"Remote workers are disabled"}'
        errors = guard.validate_stale_probe(wrong, before)
        self.assertTrue(any("task does not match" in error for error in errors), errors)
        self.assertTrue(any("lease does not match" in error for error in errors), errors)
        self.assertTrue(
            any("reassigned-authority denial" in error for error in errors),
            errors,
        )


    def test_stale_probe_requires_exact_false_and_original_authority_tuple(self):
        before = {
            "station": {
                "project_id": "p-test",
                "tasks": [{
                    "id": "OPS-101",
                    "value": {
                        "owner": "remote:old",
                        "lease_present": True,
                            "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(b"abcdefghijklmnopqrstuvwxyzABCDEF"),
                        "attempt": 3,
                    },
                }],
            },
        }
        good = {
            "schema": guard.STALE_SCHEMA,
            "project_id": "p-test",
            "task_id": "OPS-101",
            "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(
                b"abcdefghijklmnopqrstuvwxyzABCDEF"
            ),
            "attempt": 3,
            "owner": "remote:old",
            "observed_status": 403,
            "rejected": True,
            "accepted": False,
            "credential_value_retained": False,
            "response_excerpt": guard.STALE_REJECTION_TEXT,
        }
        self.assertEqual(guard.validate_stale_probe(good, before), [])

        for invalid in (None, 0, "false"):
            bad = dict(good)
            bad["accepted"] = invalid
            errors = guard.validate_stale_probe(bad, before)
            self.assertTrue(any("exactly false" in error for error in errors), errors)

        missing = dict(good)
        missing.pop("accepted")
        errors = guard.validate_stale_probe(missing, before)
        self.assertTrue(any("exactly false" in error for error in errors), errors)

        bad_attempt = dict(good)
        bad_attempt["attempt"] = 4
        self.assertTrue(any(
            "attempt does not match" in error
            for error in guard.validate_stale_probe(bad_attempt, before)
        ))

        bad_owner = dict(good)
        bad_owner["owner"] = "remote:new"
        self.assertTrue(any(
            "owner does not match" in error
            for error in guard.validate_stale_probe(bad_owner, before)
        ))

    def test_station_record_preserves_verified_public_identity_digests(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = pathlib.Path(temp) / "repo"
            data = pathlib.Path(temp) / "data"
            repo.mkdir()
            data.mkdir()
            module = repo / "server.py"
            module.write_text("pass\n", encoding="utf-8")
            record_path = pathlib.Path(temp) / "station-launch.json"
            record = {
                "schema": "residual.aud1.f6.station-launch.v1",
                "candidate_head": guard.TARGET_SHA,
                "candidate_tree": "b" * 40,
                "candidate_repo": str(repo),
                "server_module": str(module),
                "server_module_sha256": guard.base.sha256_file(module),
                "station_data": str(data),
                "station_url": "http://127.0.0.1:8766",
                "pid": 123,
            }
            record_path.write_text(json.dumps(record), encoding="utf-8")
            pathlib.Path(str(record_path) + ".sha256").write_text(
                guard.base.sha256_file(record_path) + "  station-launch.json\n",
                encoding="utf-8",
            )

            def fake_git(_repo, *args):
                if args == ("rev-parse", "HEAD^{tree}"):
                    return 0, "b" * 40, ""
                raise AssertionError(args)

            with mock.patch.object(guard, "git", side_effect=fake_git), \
                 mock.patch.object(guard, "alive", return_value=True):
                safe, errors = guard.station_record(
                    record_path, repo, data / "station.sqlite3", "http://127.0.0.1:8766"
                )
            self.assertEqual(errors, [])
            self.assertEqual(safe["candidate_head"], guard.TARGET_SHA)
            self.assertEqual(safe["candidate_tree"], "b" * 40)
            self.assertEqual(
                safe["server_module_sha256"], guard.base.sha256_file(module)
            )

    def test_event_chain_recomputes_hashes_and_rejects_mutation(self):
        previous = "0" * 64
        value = {
            "schema_version": 1,
            "event_id": "e-1",
            "event_type": "project.created",
            "timestamp": "2026-09-23T18:00:00+00:00",
            "project_id": "p-test",
            "task_id": None,
            "actor": "operator",
            "attempt": 0,
            "spec_hash": "a" * 64,
            "data": {"name": "fixture", "tasks": 1, "mode": "live"},
        }
        digest = guard.base.sha256_bytes(
            guard.base.canonical({"previous": previous, "event": value}).encode("utf-8")
        )
        snapshot = {
            "station": {
                "events": [{
                    "seq": 1,
                    "value": value,
                    "prev_hash": previous,
                    "hash": digest,
                }],
            },
        }
        self.assertEqual(guard.validate_event_chain(snapshot, "fixture"), [])

        snapshot["station"]["events"][0]["value"]["actor"] = "tampered"
        errors = guard.validate_event_chain(snapshot, "fixture")
        self.assertTrue(any("hash mismatch" in error for error in errors), errors)

    def test_snapshot_sequence_rejects_replay_or_regression(self):
        shots = {}
        for index, label in enumerate(guard.LABELS["F6-A-inside-window"], 1):
            shots[label] = {
                "station": {
                    "captured_at": f"2026-09-23T18:00:{index:02d}+00:00",
                    "captured_monotonic_ns": index,
                    "events": [{"seq": 1, "hash": "h1"}],
                },
            }
        self.assertEqual(
            guard.validate_snapshot_sequence(shots, "F6-A-inside-window"), []
        )
        shots["03-reconnected-inside-window"]["station"]["captured_monotonic_ns"] = 1
        errors = guard.validate_snapshot_sequence(shots, "F6-A-inside-window")
        self.assertTrue(any("monotonic capture order regressed" in error for error in errors), errors)

    def test_scope_identity_rejects_project_or_task_substitution(self):
        labels = guard.LABELS["F6-B-outside-window"]
        shots = {
            label: {
                "station": {
                    "project_id": "p-test",
                    "tasks": [{"id": "OPS-101", "value": {}}],
                },
            }
            for label in labels
        }
        self.assertEqual(
            guard.validate_scope_identity(shots, "F6-B-outside-window"), []
        )

        changed_project = json.loads(json.dumps(shots))
        changed_project["04-reassigned"]["station"]["project_id"] = "p-other"
        errors = guard.validate_scope_identity(
            changed_project, "F6-B-outside-window"
        )
        self.assertTrue(any("project identity differs" in error for error in errors), errors)

        changed_task = json.loads(json.dumps(shots))
        changed_task["04-reassigned"]["station"]["tasks"][0]["id"] = "OPS-999"
        errors = guard.validate_scope_identity(
            changed_task, "F6-B-outside-window"
        )
        self.assertTrue(any("task identity differs" in error for error in errors), errors)

    def test_case_b_requires_natural_expiry_before_reassignment(self):
        old_lease_until = 1_795_000_000.0
        tid = "OPS-101"
        old_owner = "remote:old"
        new_owner = "remote:new"

        def event(seq, event_type, actor, attempt, timestamp, data=None):
            value = {
                "schema_version": 1,
                "event_id": f"e-{seq}",
                "event_type": event_type,
                "timestamp": timestamp,
                "project_id": "p-test",
                "task_id": tid,
                "actor": actor,
                "attempt": attempt,
                "spec_hash": "spec",
                "data": data or {},
            }
            previous = "0" * 64 if seq == 1 else None
            return {"seq": seq, "value": value, "prev_hash": previous, "hash": "unused"}

        before_task = {
            "owner": old_owner,
            "lease_present": True,
                            "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(b"abcdefghijklmnopqrstuvwxyzABCDEF"),
            "lease_until": old_lease_until,
            "attempt": 1,
        }
        shots = {
            "01-owned-before-interrupt": {
                "station": {
                    "project_id": "p-test",
                    "tasks": [{"id": tid, "value": dict(before_task)}],
                    "events": [],
                },
            },
            "02-transport-down": {
                "station": {
                    "project_id": "p-test",
                    "tasks": [{"id": tid, "value": dict(before_task)}],
                    "events": [],
                },
            },
            "04-reassigned": {
                "station": {
                    "project_id": "p-test",
                    "tasks": [{
                        "id": tid,
                        "value": {
                            "owner": new_owner,
                            "lease_present": True,
                            "lease_fingerprint": "sha256:" + guard.base.sha256_bytes(b"new-lease"),
                            "lease_until": old_lease_until + 900,
                            "attempt": 2,
                        },
                    }],
                    "events": [
                        event(
                            1, "worker.expired", "coordinator", 1,
                            "2026-11-18T22:13:21+00:00", {"from": "running"}
                        ),
                        event(
                            2, "task.claimed", new_owner, 2,
                            "2026-11-18T22:13:22+00:00", {"route": "local", "lease_seconds": 900}
                        ),
                    ],
                },
            },
        }
        self.assertEqual(guard.validate_f6_b_authority_order(shots), [])

        regressed_deadline = json.loads(json.dumps(shots))
        regressed_deadline["01-owned-before-interrupt"]["station"]["tasks"][0]["value"]["lease_until"] = 1_795_000_100.0
        regressed_deadline["02-transport-down"]["station"]["tasks"][0]["value"]["lease_until"] = 1_795_000_000.0
        errors = guard.validate_f6_b_authority_order(regressed_deadline)
        self.assertTrue(any("lease deadline regressed" in error for error in errors), errors)

        expiry_before_original = json.loads(json.dumps(shots))
        expiry_before_original["01-owned-before-interrupt"]["station"]["tasks"][0]["value"]["lease_until"] = 1_795_000_100.0
        expiry_before_original["02-transport-down"]["station"]["tasks"][0]["value"]["lease_until"] = 1_795_000_200.0
        # 1_795_000_200 == 2026-11-18T11:10:00Z; choose an expiry
        # one minute earlier so the negative case is actually before authority expiry.
        expiry_before_original["04-reassigned"]["station"]["events"][0]["value"]["timestamp"] = "2026-11-18T11:09:00+00:00"
        errors = guard.validate_f6_b_authority_order(expiry_before_original)
        self.assertTrue(any("predates the authoritative lease deadline" in error for error in errors), errors)

        nan_deadline = json.loads(json.dumps(shots))
        nan_deadline["01-owned-before-interrupt"]["station"]["tasks"][0]["value"]["lease_until"] = "NaN"
        errors = guard.validate_f6_b_authority_order(nan_deadline)
        self.assertTrue(any("not machine-verifiable" in error for error in errors), errors)

        infinite_deadline = json.loads(json.dumps(shots))
        infinite_deadline["02-transport-down"]["station"]["tasks"][0]["value"]["lease_until"] = "Infinity"
        errors = guard.validate_f6_b_authority_order(infinite_deadline)
        self.assertTrue(any("not machine-verifiable" in error for error in errors), errors)

        missing_expiry = json.loads(json.dumps(shots))
        missing_expiry["04-reassigned"]["station"]["events"] = [
            missing_expiry["04-reassigned"]["station"]["events"][1]
        ]
        errors = guard.validate_f6_b_authority_order(missing_expiry)
        self.assertTrue(any("expiry/recovery" in error for error in errors), errors)

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
