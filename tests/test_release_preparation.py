"""Regression tests for the release-preparation procedures (Lane 6).

Covers scripts/release/blank_vm_install_check.py (typed checks, hash chain,
fail-closed behavior), scripts/release/recovery_check.py (scenario
detection), and scripts/release/soak_run.py (journal chain, signed resume
checkpoint, stop criteria, retention manifest). Real venv/pip scenarios are
exercised where the sandbox allows.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "release"))

import blank_vm_install_check as bvic  # noqa: E402
import recovery_check  # noqa: E402
import soak_run  # noqa: E402

STATION_KEY = bytes.fromhex("00" * 32)


class CheckLogTests(unittest.TestCase):
    def test_chain_verifies_and_tamper_detected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            log = bvic.CheckLog(Path(d) / "checks.jsonl")
            log.emit("a", "PASS", "ok")
            log.emit("b", "FAIL", "bad")
            ok, records, error = bvic.verify_chain(
                log.path, expected_head=log.chain_head, expected_count=len(log.records))
            self.assertTrue(ok, error)
            self.assertEqual([r["check_id"] for r in records], ["a", "b"])
            lines = log.path.read_text().splitlines()
            first = json.loads(lines[0])
            first["status"] = "FAIL"
            lines[0] = json.dumps(first, sort_keys=True)
            log.path.write_text("\n".join(lines) + "\n")
            ok, _, error = bvic.verify_chain(
                log.path, expected_head=log.chain_head, expected_count=len(log.records))
            self.assertFalse(ok)
            self.assertIn("chain break", error)

    def test_invalid_status_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            log = bvic.CheckLog(Path(d) / "c.jsonl")
            with self.assertRaises(ValueError):
                log.emit("x", "MEH")


class MissingPythonTests(unittest.TestCase):
    def test_missing_interpreter_detected_and_skips(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            wheel = recovery_check.make_trivial_wheel(Path(d) / "f.whl")
            out = Path(d) / "evidence"
            summary = bvic.run_procedure(
                artifact_url=wheel.as_uri(),
                expected_sha256=bvic.sha256_file(wheel),
                out_dir=out, work_dir=out / "work",
                python_override="/nonexistent/python3")
            self.assertEqual(summary["status"], "FAIL")
            self.assertEqual(summary["checks"]["python_probe"], "FAIL")
            self.assertEqual(summary["checks"]["fetch_artifact"], "SKIP")
            self.assertEqual(summary["checks"]["install_artifact"], "SKIP")
            ok, _, error = bvic.verify_chain(
                out / "checks.jsonl", expected_head=summary["chain_head"],
                expected_count=summary["record_count"])
            self.assertTrue(ok, error)

    def test_real_interpreter_probe_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            log = bvic.CheckLog(Path(d) / "c.jsonl")
            exe = bvic.check_python(log, Path(d) / "logs")
            self.assertEqual(exe, sys.executable)
            self.assertEqual(log.records[0]["status"], "PASS")


class HashGateTests(unittest.TestCase):
    def test_wrong_hash_blocks_install(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            wheel = recovery_check.make_trivial_wheel(Path(d) / "f.whl")
            out = Path(d) / "evidence"
            summary = bvic.run_procedure(
                artifact_url=wheel.as_uri(),
                expected_sha256="0" * 64,
                out_dir=out, work_dir=out / "work")
            self.assertEqual(summary["status"], "FAIL")
            self.assertEqual(summary["checks"]["verify_hash"], "FAIL")
            self.assertEqual(summary["checks"]["create_venv"], "SKIP")
            self.assertFalse((out / "work" / "install-venv").exists())

    def test_correct_hash_passes_gate(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            wheel = recovery_check.make_trivial_wheel(Path(d) / "f.whl")
            out = Path(d) / "evidence"
            log = bvic.CheckLog(out / "c.jsonl")
            fetched = bvic.check_fetch(log, out / "logs", out / "work", wheel.as_uri())
            self.assertIsNotNone(fetched)
            self.assertTrue(bvic.check_hash(
                log, out / "logs", fetched, bvic.sha256_file(wheel)))


class VenvRecoveryTests(unittest.TestCase):
    def test_dirty_venv_wiped_and_recorded(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / "work"
            dirty = work / "install-venv"
            dirty.mkdir(parents=True)
            (dirty / "STALE").write_text("x")
            log = bvic.CheckLog(Path(d) / "c.jsonl")
            venv = bvic.check_venv(log, Path(d) / "logs", sys.executable, work)
            self.assertIsNotNone(venv)
            self.assertFalse((dirty / "STALE").exists())
            self.assertTrue(bvic.venv_python(venv).is_file())
            self.assertIn("partial prior install", log.records[0]["recovery"])


class RecoveryScenarioTests(unittest.TestCase):
    def test_all_offline_scenarios_pass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            rc = recovery_check.main(["--out", d])
            self.assertEqual(rc, 0)
            report = json.loads((Path(d) / "recovery-checks.json").read_text())
            self.assertEqual(report["status"], "PASS")
            names = {s["scenario"] for s in report["scenarios"]}
            self.assertEqual(
                names, {"corrupt-download", "missing-python",
                        "partial-prior-install", "dependency-resolution",
                        "interrupted-install"})
            for scenario in report["scenarios"]:
                self.assertEqual(scenario["status"], "PASS", scenario)

    def test_trivial_wheel_is_installable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            wheel = recovery_check.make_trivial_wheel(Path(d) / "f.whl")
            self.assertTrue(wheel.name.endswith("-py3-none-any.whl"))
            log = bvic.CheckLog(Path(d) / "c.jsonl")
            venv = bvic.check_venv(log, Path(d) / "logs", sys.executable,
                                   Path(d) / "work")
            result = bvic.run_logged(
                [str(bvic.venv_python(venv)), "-m", "pip", "install",
                 "--no-index", str(wheel)],
                Path(d) / "logs" / "i.log", env=bvic.clean_env(), timeout=180)
            self.assertEqual(result.returncode, 0)


class SoakDriverTests(unittest.TestCase):
    def _run(self, out, **overrides):
        kwargs = dict(out_dir=out, days=2, tasks_per_day=40, seed=1,
                      station_key=STATION_KEY, max_exceptions=0,
                      brake_fn_limit=1.0, min_free_mb=1,
                      allow_below_minimum=True)
        kwargs.update(overrides)
        return soak_run.run_soak(**kwargs)

    def test_complete_run_chains_signs_and_checkpoints(self):
        import tempfile
        from residual.soak import verify_report
        with tempfile.TemporaryDirectory() as d:
            result = self._run(Path(d))
            self.assertEqual(result["status"], "COMPLETE")
            journal = soak_run.Journal(Path(d) / "soak-journal.jsonl")
            ok, records, error = journal.verify()
            self.assertTrue(ok, error)
            self.assertEqual([r["type"] for r in records],
                             ["START", "DAY", "DAY", "COMPLETE"])
            report = json.loads((Path(d) / "report.json").read_text())
            self.assertTrue(verify_report(report, STATION_KEY))
            manifest = json.loads((Path(d) / "retention-manifest.json").read_text())
            self.assertEqual(manifest["status"], "COMPLETE")
            self.assertEqual(manifest["journal_chain_head"], journal.head)
            self.assertEqual(manifest["journal_record_count"], len(records))
            self.assertIn("soak-journal.jsonl", manifest["retained_files_sha256"])
            checkpoint = soak_run.verify_checkpoint(Path(d), journal, STATION_KEY)
            self.assertEqual(checkpoint["status"], "COMPLETE")

    def test_determinism_same_seed_same_metrics(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            self._run(Path(d1))
            self._run(Path(d2))
            m1 = json.loads((Path(d1) / "report.json").read_text())["payload"]["totals"]
            m2 = json.loads((Path(d2) / "report.json").read_text())["payload"]["totals"]
            self.assertEqual(m1, m2)

    def test_resume_after_rehearsal_pause(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            first = self._run(Path(d), days=3, max_days=1)
            self.assertEqual(first["status"], "PAUSED")
            self.assertEqual(first["days_completed"], 1)
            self.assertFalse((Path(d) / "report.json").exists())
            second = self._run(Path(d), days=3)
            self.assertEqual(second["status"], "COMPLETE")
            self.assertEqual(second["days_completed"], 3)
            journal = soak_run.Journal(Path(d) / "soak-journal.jsonl")
            ok, records, error = journal.verify()
            self.assertTrue(ok, error)
            self.assertEqual(sum(1 for r in records if r["type"] == "DAY"), 3)
            self.assertIn("PAUSED", [r["type"] for r in records])
            self.assertIn("RESUME", [r["type"] for r in records])
            self.assertEqual(records[-1]["type"], "COMPLETE")

    def test_truncated_journal_is_rejected_before_resume(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(self._run(out, days=3, max_days=1)["status"], "PAUSED")
            journal_path = out / "soak-journal.jsonl"
            lines = journal_path.read_text().splitlines()
            journal_path.write_text("\n".join(lines[:-1]) + "\n")
            with self.assertRaisesRegex(RuntimeError, "checkpoint|manifest"):
                self._run(out, days=3)

    def test_checkpoint_hmac_rejects_tamper(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self._run(out, days=3, max_days=1)
            path = out / "soak-checkpoint.json"
            envelope = json.loads(path.read_text())
            envelope["payload"]["state"]["next_day"] = 2
            path.write_text(json.dumps(envelope))
            with self.assertRaisesRegex(RuntimeError, "HMAC"):
                self._run(out, days=3)

    def test_resume_configuration_mismatch_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self._run(out, days=3, max_days=1)
            with self.assertRaisesRegex(RuntimeError, "configuration mismatch"):
                self._run(out, days=4)

    def test_resource_stop_criterion(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            result = self._run(Path(d), min_free_mb=10**12)
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(result["criterion"], "resource_exhaustion")
            journal = soak_run.Journal(Path(d) / "soak-journal.jsonl")
            ok, records, _ = journal.verify()
            self.assertTrue(ok)
            self.assertEqual(records[-1]["type"], "STOP")
            self.assertTrue((Path(d) / "retention-manifest.json").is_file())
            checkpoint = soak_run.verify_checkpoint(Path(d), journal, STATION_KEY)
            self.assertEqual(checkpoint["status"], "STOPPED")

    def test_load_minimum_enforced_by_default(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                soak_run.run_soak(
                    out_dir=Path(d), days=1, tasks_per_day=10, seed=1,
                    station_key=STATION_KEY, max_exceptions=0,
                    brake_fn_limit=1.0, min_free_mb=1,
                    allow_below_minimum=False)


if __name__ == "__main__":
    unittest.main()
