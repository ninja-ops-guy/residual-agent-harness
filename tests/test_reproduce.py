"""Retained-evidence adversarial tests; no model execution or live study."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from residual.reproduce import CORE_PATHS, ReproductionError, canonical_bytes, main, reproduce

FIXTURE = Path(__file__).resolve().parents[1] / "examples/reproduction/synthetic-demo"


class ReproduceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runs = Path(self.temp.name)
        self.bundle = self.runs / "synthetic-demo"
        shutil.copytree(FIXTURE, self.bundle)

    def replay(self, **kwargs):
        return reproduce("synthetic-demo", runs_dir=self.runs, **kwargs)

    def read_manifest(self):
        return json.loads((self.bundle / "manifest.json").read_text())

    def write_manifest(self, manifest):
        (self.bundle / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")

    def replace(self, role, data):
        path = CORE_PATHS[role]
        if isinstance(data, list):
            raw = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in data)
        elif isinstance(data, dict):
            raw = (json.dumps(data, sort_keys=True) + "\n").encode()
        else:
            raw = data
        (self.bundle / path).write_bytes(raw)
        manifest = self.read_manifest()
        for entry in manifest["artifacts"]:
            if entry["path"] == path:
                entry["sha256"] = hashlib.sha256(raw).hexdigest()
                entry["bytes"] = len(raw)
        self.write_manifest(manifest)

    def rows(self, role):
        return [json.loads(line) for line in (self.bundle / CORE_PATHS[role]).read_text().splitlines()]

    def test_demo_keeps_missing_and_unknown_separate(self):
        report = self.replay()
        metrics = report["metrics"]
        self.assertEqual(metrics["scheduled_cells"], 6)
        self.assertEqual(metrics["recorded_cells"], 5)
        self.assertEqual(metrics["accepted_count"], 3)
        self.assertEqual(metrics["correct_accepted_count"], 2)
        self.assertEqual(metrics["incorrect_accepted_count"], 1)
        self.assertEqual(metrics["verified_goodput"], 2 / 6)
        self.assertIsNone(metrics["accepted_error_rate"])
        self.assertEqual(metrics["accepted_error_rate_bounds"], [1 / 4, 2 / 4])
        self.assertEqual(metrics["execution_counts"]["MISSING"], 1)
        self.assertEqual(metrics["verifier_counts"]["UNKNOWN"], 3)
        self.assertIsNone(metrics["total_cost_usd"])
        self.assertFalse(report["publication_ready"])
        self.assertEqual(report["evidence_mode"], "synthetic")

    def test_deterministic_and_network_free_without_mutating_bundle(self):
        before = {str(p): p.read_bytes() for p in self.bundle.rglob("*") if p.is_file()}
        with patch.object(socket, "socket", side_effect=AssertionError("network")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("process")):
            first = canonical_bytes(self.replay())
            second = canonical_bytes(self.replay())
        self.assertEqual(first, second)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.bundle.rglob("*") if p.is_file()})

    def test_byte_tampering_rejected(self):
        with (self.bundle / CORE_PATHS["cells"]).open("ab") as out:
            out.write(b"{}\n")
        with self.assertRaisesRegex(ReproductionError, "hash/size"):
            self.replay()

    def test_external_pin_detects_rewritten_manifest(self):
        pin = hashlib.sha256((self.bundle / "manifest.json").read_bytes()).hexdigest()
        self.assertTrue(self.replay(manifest_sha256=pin)["manifest_pin_checked"])
        rows = self.rows("cells")
        rows[0]["correctness_status"] = "INCORRECT"
        self.replace("cells", rows)
        # Internal hashes alone cannot establish truthful authorship or authenticity.
        self.assertEqual(self.replay()["metrics"]["correct_accepted_count"], 1)
        with self.assertRaisesRegex(ReproductionError, "pin mismatch"):
            self.replay(manifest_sha256=pin)

    def test_missing_required_artifact_fails_instead_of_zero_filling(self):
        (self.bundle / CORE_PATHS["usage"]).unlink()
        with self.assertRaises(ReproductionError):
            self.replay()

    def test_missing_record_keeps_scheduled_denominator(self):
        rows = self.rows("cells")
        self.replace("cells", rows[1:])
        metrics = self.replay()["metrics"]
        self.assertEqual(metrics["scheduled_cells"], 6)
        self.assertEqual(metrics["recorded_cells"], 4)
        self.assertEqual(metrics["verified_goodput"], 1 / 6)
        self.assertEqual(metrics["unknown_acceptance_count"], 2)

    def test_duplicate_or_unscheduled_records_rejected(self):
        rows = self.rows("cells")
        self.replace("cells", rows + [rows[0]])
        with self.assertRaisesRegex(ReproductionError, "duplicate"):
            self.replay()
        rows[0]["cell_id"] = "unscheduled"
        self.replace("cells", rows)
        with self.assertRaisesRegex(ReproductionError, "unscheduled"):
            self.replay()

    def test_unknown_ground_truth_is_not_inferred_from_pass(self):
        rows = self.rows("cells")
        rows[0]["correctness_status"] = "UNKNOWN"
        self.replace("cells", rows)
        metrics = self.replay()["metrics"]
        self.assertEqual(metrics["correct_accepted_count"], 1)
        self.assertEqual(metrics["unknown_accepted_correctness_count"], 1)
        self.assertIsNone(metrics["accepted_error_rate"])

    def test_bad_acceptance_is_reported_as_violation_not_hidden(self):
        rows = self.rows("cells")
        rows[0]["verifier_status"] = "UNKNOWN"
        self.replace("cells", rows)
        report = self.replay()
        self.assertIn(rows[0]["cell_id"], report["invariant_violations"])
        self.assertIsNone(report["system_metrics_by_cell"][rows[0]["cell_id"]]["verifier_rejection_rate_pct"])

    def test_zero_acceptances_and_zero_test_denominator_are_null(self):
        rows = self.rows("cells")
        # Add the previously missing cell so acceptance itself is fully known.
        extra = {**rows[0], "cell_id": "R0-task3"}
        rows.append(extra)
        for row in rows:
            row.update(accepted=False, tests_passed=0, tests_total=0)
        self.replace("cells", rows)
        report = self.replay()
        metrics = report["metrics"]
        self.assertEqual(metrics["accepted_count"], 0)
        self.assertIsNone(metrics["accepted_error_rate"])
        self.assertEqual(metrics["accepted_error_rate_bounds"], [None, None])
        self.assertIsNone(metrics["cost_per_correct_acceptance_usd"])
        self.assertTrue(all(m["final_test_pass_rate_pct"] is None for m in report["system_metrics_by_cell"].values()))

    def test_system_metrics_match_existing_complete_run_semantics(self):
        from residual.eval.spec_eval import RunCounters, SystemMetrics
        counters = RunCounters(elapsed_seconds=3, accepted_tasks=1, total_tasks=1,
                               tokens_used=15, gpu_seconds=0, coordination_seconds=1,
                               rework_tasks=0, merge_conflicts=0, verifier_rejections=0,
                               verifier_outputs=1, tests_passed=1, tests_total=1)
        self.assertEqual(self.replay()["system_metrics_by_cell"]["R0-task1"], SystemMetrics.from_counters(counters).to_dict())

    def test_failed_calls_still_cost_money_and_incomplete_cost_is_null(self):
        rows = self.rows("usage")
        failure = next(r for r in rows if r["status"] == "TIMEOUT")
        failure["cost_usd"] = 4
        self.replace("usage", rows)
        report = self.replay()
        self.assertAlmostEqual(report["metrics"]["known_cost_usd_subtotal"], 4.045)
        self.assertAlmostEqual(report["by_configuration"]["R5"]["total_cost_usd"], 4.023)
        failure["cost_usd"] = None
        self.replace("usage", rows)
        self.assertIsNone(self.replay()["by_configuration"]["R5"]["total_cost_usd"])

    def test_reserved_call_cannot_look_like_complete_zero_cost(self):
        rows = self.rows("usage")
        rows[-1].update(status="RESERVED", cost_usd=0, input_tokens=0, output_tokens=0)
        self.replace("usage", rows)
        metrics = self.replay()["by_configuration"]["R5"]
        self.assertFalse(metrics["cost_complete"])
        self.assertFalse(metrics["tokens_complete"])

    def test_source_refs_cannot_reference_unretained_files(self):
        rows = self.rows("cells")
        rows[0]["source_refs"] = ["attachments/missing.json"]
        self.replace("cells", rows)
        with self.assertRaisesRegex(ReproductionError, "unretained"):
            self.replay()

    def test_path_traversal_absolute_and_noncanonical_paths_rejected(self):
        original = self.read_manifest()
        for path in ("../outside", "/etc/passwd", "attachments/../x", "attachments//x", "attachments/./x", "attachments\\x"):
            with self.subTest(path=path):
                manifest = json.loads(json.dumps(original))
                manifest["artifacts"][0]["path"] = path
                self.write_manifest(manifest)
                with self.assertRaises(ReproductionError):
                    self.replay()
        for run_id in ("../synthetic-demo", "/tmp", ".", ".."):
            with self.subTest(run_id=run_id), self.assertRaises(ReproductionError):
                reproduce(run_id, runs_dir=self.runs)

    def test_symlink_file_directory_and_hardlink_rejected(self):
        target = self.bundle / CORE_PATHS["stdout"]
        outside = self.runs / "outside"
        outside.write_bytes(b"")
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaises(ReproductionError):
            self.replay()
        target.unlink()
        os.link(outside, target)
        with self.assertRaises(ReproductionError):
            self.replay()
        target.unlink()
        target.write_bytes(b"")
        renamed = self.runs / "moved-streams"
        (self.bundle / "streams").rename(renamed)
        (self.bundle / "streams").symlink_to(renamed, target_is_directory=True)
        with self.assertRaises(ReproductionError):
            self.replay()

    def test_fifo_and_oversized_sparse_file_rejected_without_reading(self):
        target = self.bundle / CORE_PATHS["stdout"]
        target.unlink()
        os.mkfifo(target)
        with self.assertRaises(ReproductionError):
            self.replay()
        target.unlink()
        with target.open("wb") as stream:
            stream.truncate(33 * 1024 * 1024)
        with self.assertRaises(ReproductionError):
            self.replay()

    def test_torn_duplicate_key_nonfinite_unknown_field_rejected(self):
        original = self.rows("cells")
        for data in (b'{"cell_id":"x"}', b'{"cell_id":"x","cell_id":"y"}\n',
                     b'{"cell_id":NaN}\n', b'{"cell_id":1e400}\n', [{**original[0], "unexpected": True}]):
            with self.subTest(data=data):
                self.replace("cells", data)
                with self.assertRaises(ReproductionError):
                    self.replay()

    def test_malformed_unhashable_and_huge_integer_have_controlled_errors(self):
        rows = self.rows("cells")
        for value in ([{}], [[1]], [None]):
            rows[0]["source_refs"] = value
            self.replace("cells", rows)
            with self.assertRaises(ReproductionError):
                self.replay()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["synthetic-demo", "--runs-dir", str(self.runs)]), 2)
            self.assertNotIn("Traceback", stderr.getvalue())
        rows[0]["source_refs"] = []
        rows[0]["merge_conflicts"] = 10 ** 400
        self.replace("cells", rows)
        with self.assertRaises(ReproductionError):
            self.replay()

    def test_workload_schedule_and_prompt_hash_mismatch_rejected(self):
        workload = json.loads((self.bundle / CORE_PATHS["workload"]).read_text())
        workload["expected_cells"].pop()
        self.replace("workload", workload)
        with self.assertRaisesRegex(ReproductionError, "schedule differs"):
            self.replay()
        workload["expected_cells"] = self.read_manifest()["expected_cells"]
        self.replace("workload", workload)
        prompts = json.loads((self.bundle / CORE_PATHS["prompts"]).read_text())
        prompts["prompts"][0]["sha256"] = "a" * 64
        self.replace("prompts", prompts)
        with self.assertRaisesRegex(ReproductionError, "prompt content"):
            self.replay()

    def test_measured_and_frozen_labels_do_not_self_certify_publication(self):
        manifest = self.read_manifest()
        manifest["evidence_mode"] = "measured"
        self.write_manifest(manifest)
        protocol = json.loads((self.bundle / CORE_PATHS["protocol"]).read_text())
        protocol["status"] = "frozen"
        self.replace("protocol", protocol)
        self.assertFalse(self.replay()["publication_ready"])

    def complete_demo(self):
        """Retain the missing R0 row and its all-attempt cost for Pareto tests."""
        rows = self.rows("cells")
        rows.append({**rows[-1], "cell_id": "R0-task3", "execution_status": "COMPLETED"})
        self.replace("cells", rows)
        timing = self.rows("timing")
        timing.append({**timing[-1], "cell_id": "R0-task3"})
        self.replace("timing", timing)
        usage = self.rows("usage")
        usage.append({**usage[-1], "cell_id": "R0-task3", "call_id": "call-R0-task3", "status": "COMPLETED"})
        self.replace("usage", usage)

    def test_pareto_dominance_uses_all_three_dimensions(self):
        self.complete_demo()
        pareto = self.replay()["pareto"]
        self.assertEqual(pareto["status"], "complete")
        self.assertEqual(pareto["frontier"], ["R5"])
        self.assertEqual(pareto["points"]["R0"]["dominated_by"], ["R5"])
        # Cheaper R0 trades off worse accepted error: neither now dominates.
        usage = self.rows("usage")
        for row in usage:
            if row["cell_id"].startswith("R0-"):
                row["cost_usd"] = 0
        self.replace("usage", usage)
        self.assertEqual(self.replay()["pareto"]["frontier"], ["R0", "R5"])

    def test_pareto_equal_points_are_both_retained(self):
        self.complete_demo()
        rows = self.rows("cells")
        next(row for row in rows if row["cell_id"] == "R0-task2")["accepted"] = False
        self.replace("cells", rows)
        pareto = self.replay()["pareto"]
        self.assertEqual(pareto["frontier"], ["R0", "R5"])
        self.assertTrue(all(not point["dominated_by"] for point in pareto["points"].values()))

    def test_pareto_unknown_cost_and_acceptance_make_global_frontier_indeterminate(self):
        pareto = self.replay()["pareto"]
        self.assertEqual(pareto["status"], "indeterminate")
        self.assertIsNone(pareto["frontier"])
        self.assertEqual(pareto["frontier_among_complete_points"], ["R5"])
        self.assertIn("unknown_acceptance", pareto["points"]["R0"]["indeterminate_reasons"])
        self.complete_demo()
        usage = self.rows("usage")
        usage[0]["cost_usd"] = None
        self.replace("usage", usage)
        pareto = self.replay()["pareto"]
        self.assertIsNone(pareto["frontier"])
        self.assertEqual(pareto["points"]["R0"]["indeterminate_reasons"], ["incomplete_cost"])

    def test_pareto_unknown_accepted_grade_or_zero_acceptance_is_indeterminate(self):
        self.complete_demo()
        rows = self.rows("cells")
        rows[0]["correctness_status"] = "UNKNOWN"
        self.replace("cells", rows)
        pareto = self.replay()["pareto"]
        self.assertIsNone(pareto["frontier"])
        self.assertIn("unknown_accepted_correctness", pareto["points"]["R0"]["indeterminate_reasons"])
        for row in rows:
            row["accepted"] = False
        self.replace("cells", rows)
        pareto = self.replay()["pareto"]
        self.assertIsNone(pareto["frontier"])
        self.assertEqual(pareto["frontier_among_complete_points"], [])
        self.assertTrue(all("zero_acceptance" in point["indeterminate_reasons"] for point in pareto["points"].values()))

    def test_cli_new_output_and_refuse_existing_or_symlink(self):
        output = self.runs / "report.json"
        args = ["synthetic-demo", "--runs-dir", str(self.runs), "--output", str(output)]
        self.assertEqual(main(args), 0)
        self.assertEqual(output.read_bytes(), canonical_bytes(self.replay()))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main(args), 2)
        output.unlink()
        output.symlink_to(self.bundle / "manifest.json")
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(main(args), 2)
        self.assertEqual(self.replay()["run_id"], "synthetic-demo")


if __name__ == "__main__":
    unittest.main()
