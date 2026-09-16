"""Real-file and driver regressions for release evidence integrity."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "release"))
import blank_vm_install_check as bvic
import soak_run


class InstallIntegrityTests(unittest.TestCase):
    def test_log_verification_requires_external_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            log = bvic.CheckLog(Path(d) / "checks.jsonl")
            log.emit("first", "PASS")
            log.emit("last", "FAIL")
            self.assertFalse(bvic.verify_chain(log.path)[0])

    def test_retained_endpoint_rejects_truncated_and_changed_tail(self):
        with tempfile.TemporaryDirectory() as d:
            log = bvic.CheckLog(Path(d) / "checks.jsonl")
            log.emit("first", "PASS")
            log.emit("last", "FAIL")
            endpoint = dict(expected_head=log.chain_head, expected_count=2)
            original = log.path.read_text()
            self.assertTrue(bvic.verify_chain(log.path, **endpoint)[0])
            log.path.write_text(original.splitlines()[0] + "\n")
            self.assertFalse(bvic.verify_chain(log.path, **endpoint)[0])
            lines = original.splitlines()
            last = json.loads(lines[-1]); last["status"] = "PASS"
            lines[-1] = json.dumps(last, sort_keys=True)
            log.path.write_text("\n".join(lines) + "\n")
            self.assertFalse(bvic.verify_chain(log.path, **endpoint)[0])

    def test_existing_install_evidence_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "checks.jsonl"
            log = bvic.CheckLog(path); log.emit("old", "FAIL")
            before = path.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "existing|fresh"):
                bvic.CheckLog(path)
            self.assertEqual(before, path.read_bytes())

    def test_missing_or_malformed_digest_never_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); artifact = root / "artifact.whl"; artifact.write_bytes(b"wheel")
            for index, digest in enumerate(["", None, "x" * 64, "a" * 63, " a" * 32]):
                with self.subTest(digest=digest):
                    log = bvic.CheckLog(root / f"{index}.jsonl")
                    self.assertFalse(bvic.check_hash(log, root / "logs", artifact, digest))
                    self.assertEqual(log.records[-1]["status"], "FAIL")

    def test_freeze_failure_is_not_install_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); log = bvic.CheckLog(root / "checks.jsonl")
            results = [subprocess.CompletedProcess([], 0),
                       subprocess.CompletedProcess([], 0),
                       subprocess.CompletedProcess([], 1)]
            with patch.object(bvic, "run_logged", side_effect=results):
                self.assertFalse(bvic.check_install(log, root / "logs", root / "venv", root / "wheel"))
            self.assertEqual(log.records[-1]["status"], "FAIL")
            self.assertIn("freeze", log.records[-1]["detail"])


class SoakPolicyIntegrityTests(unittest.TestCase):
    def run_driver(self, root, **overrides):
        args = dict(out_dir=root, days=2, tasks_per_day=40, seed=1,
                    station_key=b"a" * 32, max_exceptions=0,
                    brake_fn_limit=1.0, min_free_mb=1, allow_below_minimum=True)
        args.update(overrides)
        return soak_run.run_soak(**args)

    def test_resume_cannot_change_stop_policy(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.run_driver(root, max_days=1)
            before = (root / "soak-journal.jsonl").read_bytes()
            with self.assertRaisesRegex(RuntimeError, "configuration|policy"):
                self.run_driver(root, max_exceptions=100)
            self.assertEqual(before, (root / "soak-journal.jsonl").read_bytes())

    def test_machine_readable_report_cannot_claim_elapsed_soak(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); result = self.run_driver(root)
            self.assertEqual(result["execution_mode"], "simulation")
            manifest = json.loads((root / "retention-manifest.json").read_text())
            report = json.loads((root / "report.json").read_text())
            checkpoint = json.loads((root / "soak-checkpoint.json").read_text())
            for record in [manifest, report["payload"], checkpoint["payload"]]:
                self.assertEqual(record["execution_mode"], "simulation")
                self.assertFalse(record["qualifies_elapsed_soak"])

    @unittest.skipUnless(os.name == "posix", "directory fsync contract is POSIX-specific")
    def test_stable_soak_boundaries_fsync_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            real_fsync = os.fsync
            calls = []

            def recording_fsync(fd):
                calls.append(fd)
                return real_fsync(fd)

            with patch.object(soak_run.os, "fsync", side_effect=recording_fsync):
                result = self.run_driver(root, max_days=1)

            self.assertEqual(result["status"], "PAUSED")
            self.assertGreaterEqual(len(calls), 6)
            self.assertTrue((root / "soak-journal.jsonl").is_file())
            self.assertTrue((root / "soak-state.json").is_file())
            self.assertTrue((root / "soak-checkpoint.json").is_file())
            self.assertTrue((root / "retention-manifest.json").is_file())

    def test_station_key_file_supplies_secret_without_literal_cli_key(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "station-key.hex"
            expected = bytes.fromhex("11" * 32)
            path.write_text(expected.hex() + "\n", encoding="utf-8")
            if os.name == "posix":
                path.chmod(0o600)
            self.assertEqual(soak_run._station_key_file(path), expected)

    @unittest.skipUnless(os.name == "posix", "permission check is POSIX-specific")
    def test_station_key_file_rejects_group_or_other_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "station-key.hex"
            path.write_text("22" * 32, encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(argparse.ArgumentTypeError, "permissions"):
                soak_run._station_key_file(path)


if __name__ == "__main__":
    unittest.main()
