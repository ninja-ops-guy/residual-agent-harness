"""Validate science commitments and zero-observation paper scaffolding."""
from __future__ import annotations

import copy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paper_templates", ROOT / "scripts/paper_templates.py")
templates = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(templates)


class SciencePreparationTests(unittest.TestCase):
    def test_protocol_commitment_and_no_launch(self):
        protocol, sha = templates.load_protocol()
        self.assertEqual(sha, templates.digest(templates.PROTOCOL))
        self.assertFalse(protocol["confirmatory_launch_enabled"])
        self.assertTrue(all(g["status"] == "unresolved" for g in protocol["launch_gates"]))
        self.assertEqual(protocol["model_selection"]["selected_ids"], dict.fromkeys("SMWL"))

    def test_changed_protocol_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "protocol.v1.json"
            path.write_bytes(templates.PROTOCOL.read_bytes() + b" ")
            path.with_suffix(".sha256").write_bytes(templates.PROTOCOL.with_suffix(".sha256").read_bytes())
            with self.assertRaisesRegex(ValueError, "commitment mismatch"):
                templates.load_protocol(path)

    def test_boolean_flip_cannot_claim_launch(self):
        protocol, _ = templates.load_protocol()
        protocol["confirmatory_launch_enabled"] = True
        with self.assertRaisesRegex(ValueError, "launch must remain disabled"):
            templates.validate_protocol(protocol)

    def test_promotion_of_unresolved_gate_rejected(self):
        protocol, _ = templates.load_protocol()
        protocol["launch_gates"][0]["status"] = "passed"
        with self.assertRaisesRegex(ValueError, "cannot certify"):
            templates.validate_protocol(protocol)

    def test_holm_family_not_shrunk_for_missing_contrast(self):
        protocol, _ = templates.load_protocol()
        protocol["inference"]["holm_family"].pop()
        with self.assertRaisesRegex(ValueError, "Holm family"):
            templates.validate_protocol(protocol)

    def test_unknown_and_pairing_semantics_cannot_drift(self):
        protocol, _ = templates.load_protocol()
        changes = [
            ("pair_fields", ["task_id", "configuration"]),
            ("missingness", {**protocol["missingness"], "unknown_is_pass": True}),
            ("missingness", {**protocol["missingness"], "drop_scheduled_cells": True}),
        ]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(protocol)
                changed[field] = value
                with self.assertRaises(ValueError):
                    templates.validate_protocol(changed)

    def test_routes_cannot_gain_unrecorded_strong_workers(self):
        protocol, _ = templates.load_protocol()
        protocol["heterogeneous_routes"][2]["workers"][0] = "S"
        with self.assertRaisesRegex(ValueError, "route matrix"):
            templates.validate_protocol(protocol)

    def test_generated_tables_have_no_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "empty"
            manifest = templates.generate(out)
            self.assertEqual(manifest["row_count"], 0)
            csv_paths = list(out.glob("*.csv"))
            self.assertEqual(len(csv_paths), len(templates.PLOTS) + len(templates.TABLES))
            for path in csv_paths:
                with path.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.reader(handle))
                self.assertEqual(len(rows), 1, path.name)
                self.assertEqual(len(rows[0]), len(set(rows[0])), path.name)
                self.assertTrue(all(rows[0]), path.name)
            for name in templates.PLOTS:
                payload = json.loads((out / f"{name}.json").read_text())
                self.assertEqual(payload["data"], [])
                self.assertEqual(payload["evidence_level"], "empty_template")

    def test_generated_manifest_covers_actual_files(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "empty"
            manifest = templates.generate(out)
            self.assertEqual(set(manifest["files"]), {p.name for p in out.iterdir()} - {"manifest.json"})
            for name, sha in manifest["files"].items():
                self.assertEqual(templates.digest(out / name), sha)

    def test_default_generation_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "a", Path(temp) / "b"
            self.assertEqual(templates.generate(first), templates.generate(second))
            for p in first.iterdir():
                self.assertEqual(p.read_bytes(), (second / p.name).read_bytes(), p.name)

    def test_existing_results_directory_is_not_modified(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            sentinel = out / "results.csv"
            sentinel.write_text("retained\n")
            with self.assertRaises(FileExistsError):
                templates.generate(out)
            self.assertEqual(sentinel.read_text(), "retained\n")
            self.assertEqual([p.name for p in out.iterdir()], ["results.csv"])

    def test_verifier_templates_keep_execution_failures_separate(self):
        for name in ["verifier_roc", "verifier_calibration"]:
            columns = templates.PLOTS[name]["columns"]
            self.assertIn("unknown", columns)
            self.assertIn("execution_error", columns)
        self.assertIn("decision_coverage", templates.PLOTS["verifier_roc"]["columns"])

    def test_preparation_manifest_byte_commitments(self):
        manifest_path = ROOT / "experiments/preflight/science/preparation-manifest.v1.json"
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["status"], "preparation_frozen_launch_blocked")
        for name, sha in manifest["files"].items():
            path = ROOT / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(templates.digest(path), sha, name)
        expected = manifest_path.with_suffix(".sha256").read_text().split()
        self.assertEqual(expected, [templates.digest(manifest_path), manifest_path.name])

    def test_committed_templates_empty_and_hash_bound(self):
        out = ROOT / "experiments/preflight/science/templates"
        manifest = json.loads((out / "manifest.json").read_text())
        self.assertEqual(manifest["row_count"], 0)
        self.assertEqual(manifest["protocol_sha256"], templates.digest(templates.PROTOCOL))
        for name, sha in manifest["files"].items():
            self.assertEqual(templates.digest(out / name), sha, name)


if __name__ == "__main__":
    unittest.main()
