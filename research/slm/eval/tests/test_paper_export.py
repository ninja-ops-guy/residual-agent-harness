"""Tests for paper_export.py (toy data only)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paper_export
import results_store


def toy_record(condition="F", seed_index=0):
    return {
        "model_hash": "sha256:" + "cd" * 32,
        "benchmark_hash": "sha256:" + "ef" * 32,
        "harness_condition": condition,
        "seed": results_store.FROZEN_SEEDS[seed_index],
        "seed_index": seed_index,
        "hardware": {"sku": "toy-cpu-node"},
        "metrics": {"vmsr": 0.9, "fner": 0.0, "brier": 0.1},
    }


class TestPaperExport(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.store = os.path.join(self.td.name, "runs.jsonl")
        results_store.init_store(self.store)
        results_store.append_record(self.store, toy_record("A", 0))
        results_store.append_record(self.store, toy_record("F", 1))
        self.records = list(results_store.iter_records(self.store))

    def tearDown(self):
        self.td.cleanup()

    def test_markdown_table(self):
        table = paper_export.result_table(self.records, "markdown")
        self.assertIn("run_id", table)
        self.assertIn("vmsr", table)
        self.assertIn("harness_condition", table)
        self.assertEqual(table.count("slm-run-"), 2)

    def test_csv_table(self):
        table = paper_export.result_table(self.records, "csv")
        header = table.splitlines()[0]
        self.assertTrue(header.startswith("run_id,harness_condition"))
        self.assertEqual(len(table.splitlines()), 3)

    def test_manifests_content_addressed(self):
        paths = paper_export.export_manifests(
            self.records, os.path.join(self.td.name, "m"))
        self.assertEqual(len(paths), 2)
        for p in paths:
            with open(p, encoding="utf-8") as fh:
                rec = json.load(fh)
            self.assertIn("run_id", rec)
            self.assertIn("manifest-slm-run-", os.path.basename(p))

    def test_repro_metadata(self):
        meta = paper_export.reproducibility_metadata(self.records)
        self.assertEqual(meta["record_count"], 2)
        self.assertEqual(meta["head_digest"], self.records[-1]["digest"])
        self.assertEqual(meta["conditions_present"], ["A", "F"])
        self.assertEqual(meta["evaluation_protocol"], "eval-protocol-v1.0.0")

    def test_refuses_tampered_store(self):
        with open(self.store, "a", encoding="utf-8") as fh:
            rec = dict(self.records[-1])
            rec["seq"] = 2
            rec["metrics"] = dict(rec["metrics"], vmsr=1.0)  # tampered
            fh.write(json.dumps(rec) + "\n")
        with self.assertRaises(ValueError):
            paper_export._load_verified(self.store)

    def test_cli(self):
        self.assertEqual(
            paper_export.main(["--store", self.store, "table",
                               "--format", "csv"]), 0)
        self.assertEqual(
            paper_export.main(["--store", self.store, "repro"]), 0)
        self.assertEqual(
            paper_export.main(["--store", self.store, "manifest",
                               "--outdir", os.path.join(self.td.name, "x")]), 0)
        with self.assertRaises(SystemExit) as ctx:
            paper_export.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
