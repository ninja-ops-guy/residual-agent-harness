"""Tests for results_store.py (toy data only)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import results_store


def toy_record(condition="F", seed_index=0):
    return {
        "model_hash": "sha256:" + "cd" * 32,
        "benchmark_hash": "sha256:" + "ef" * 32,
        "harness_condition": condition,
        "seed": results_store.FROZEN_SEEDS[seed_index],
        "seed_index": seed_index,
        "hardware": {"sku": "toy-cpu-node", "memory_gb": 8},
        "metrics": {"vmsr": 0.9, "fner": 0.0, "avr": 0.0, "ece": 0.05,
                    "brier": 0.1},
        "raw_outputs": [{"item_id": "toy-1", "output": "ok"}],
    }


class TestResultsStore(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.store = os.path.join(self.td.name, "runs.jsonl")
        results_store.init_store(self.store)

    def tearDown(self):
        self.td.cleanup()

    def test_init_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            results_store.init_store(self.store)

    def test_append_and_verify_chain(self):
        r1 = results_store.append_record(self.store, toy_record("A", 0))
        r2 = results_store.append_record(self.store, toy_record("F", 1))
        self.assertEqual(r1["seq"], 0)
        self.assertEqual(r2["seq"], 1)
        self.assertEqual(r2["prev_digest"], r1["digest"])
        self.assertTrue(r1["run_id"].startswith("slm-run-"))
        self.assertEqual(results_store.verify_chain(self.store), [])

    def test_tamper_detected(self):
        results_store.append_record(self.store, toy_record())
        with open(self.store, "r", encoding="utf-8") as fh:
            rec = json.loads(fh.readline())
        rec["metrics"]["vmsr"] = 0.99  # tamper
        with open(self.store, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        self.assertTrue(results_store.verify_chain(self.store))

    def test_unknown_metric_rejected(self):
        bad = toy_record()
        bad["metrics"]["made_up_metric"] = 1.0
        with self.assertRaises(ValueError):
            results_store.append_record(self.store, bad)

    def test_non_frozen_seed_rejected(self):
        bad = toy_record()
        bad["seed"] = 12345
        with self.assertRaises(ValueError):
            results_store.append_record(self.store, bad)

    def test_bad_condition_rejected(self):
        bad = toy_record(condition="G")
        with self.assertRaises(ValueError):
            results_store.append_record(self.store, bad)

    def test_list_filter_by_condition(self):
        results_store.append_record(self.store, toy_record("A", 0))
        results_store.append_record(self.store, toy_record("F", 1))
        self.assertEqual(len(list(results_store.iter_records(self.store))), 2)
        self.assertEqual(
            len(list(results_store.iter_records(self.store, "F"))), 1)

    def test_cli(self):
        rec_path = os.path.join(self.td.name, "rec.json")
        with open(rec_path, "w", encoding="utf-8") as fh:
            json.dump(toy_record(), fh)
        self.assertEqual(
            results_store.main(["--store", self.store, "append",
                                "--record", rec_path]), 0)
        self.assertEqual(
            results_store.main(["--store", self.store, "verify"]), 0)
        with self.assertRaises(SystemExit) as ctx:
            results_store.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
