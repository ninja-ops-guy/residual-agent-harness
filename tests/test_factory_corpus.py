from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from residual.core import canonical
from residual.factory.evidence_receipts import StationIdentity
from residual.factory.eval_framework import EVAL_DOMAIN, FrozenEvalTask, FrozenWorkload

ROOT = Path(__file__).resolve().parents[1]
COMMON_PATH = ROOT / "benchmarks" / "factory" / "corpus" / "common.py"
spec = importlib.util.spec_from_file_location("factory_corpus_common", COMMON_PATH)
corpus = importlib.util.module_from_spec(spec); spec.loader.exec_module(corpus)


def _host():
    value = {"system": "Linux", "release": "test", "machine": "x86_64", "python": "3.12.0",
             "cpu_model": "fixture", "logical_cpus": 8, "gpu": "fixture-gpu"}
    value["fingerprint"] = corpus._sha(value)
    return value


def _entries(version="digest-a"):
    return tuple(corpus.CorpusEntry(name, (str(i + 1) * 64)[:64], (str(i + 5) * 64)[:64],
                                    False, "ollama:model", version)
                 for i, name in enumerate(corpus.BENCHMARKS))


class CorpusTests(unittest.TestCase):
    def test_manifest_roundtrip_signature_and_tamper(self):
        identity = StationIdentity.generate()
        manifest = corpus.CorpusManifest.issue(source_commit="a" * 40, model_name="ollama:model",
                                               model_version="digest-a", host=_host(), runs=3,
                                               entries=_entries(), identity=identity)
        self.assertTrue(manifest.verify(identity.public_bytes()))
        rebuilt = corpus.CorpusManifest.from_dict(manifest.to_dict())
        self.assertEqual(rebuilt.manifest_hash, manifest.manifest_hash)
        self.assertTrue(rebuilt.verify(identity.public_bytes()))
        tampered = manifest.to_dict(); tampered["runs"] = 4
        with self.assertRaises(ValueError):
            corpus.CorpusManifest.from_dict(tampered)

    def test_mixed_model_corpus_rejected(self):
        identity = StationIdentity.generate()
        entries = list(_entries()); last = entries[-1]
        entries[-1] = corpus.CorpusEntry(last.benchmark, last.workload_hash, last.report_hash,
                                         False, last.engine_name, "different")
        with self.assertRaises(ValueError):
            corpus.CorpusManifest.issue(source_commit="b" * 40, model_name="ollama:model",
                                        model_version="digest-a", host=_host(), runs=3,
                                        entries=tuple(entries), identity=identity)

    def test_report_entry_checks_workload_hash_and_signature(self):
        identity = StationIdentity.generate()
        workload = FrozenWorkload("fixture", ("R1",),
                                  (FrozenEvalTask("t1", ("R1",), (), ("check",)),),
                                  "1" * 40, "2" * 40, "ollama:model", "digest-a", 0, 7)
        unsigned = {"schema_version": "factory-comparison-report-v1",
                    "workload_hash": workload.workload_hash, "run_count": 3,
                    "configurations": {}, "significance": {}, "observation_root": "3" * 64,
                    "simulation": False, "generated_at_ns": 1,
                    "station_key_id": identity.key_id}
        report_hash = corpus._sha(unsigned)
        report = {**unsigned, "report_hash": report_hash,
                  "station_signature": identity.sign_hash(report_hash, domain=EVAL_DOMAIN)}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); wp = root / "workload.json"; rp = root / "report.json"
            wp.write_text(json.dumps(workload.to_dict()) + "\n", encoding="utf-8")
            rp.write_text(json.dumps(report) + "\n", encoding="utf-8")
            entry = corpus.report_entry("fb001", wp, rp, identity.public_bytes())
            self.assertEqual(entry.workload_hash, workload.workload_hash)
            bad = dict(report); bad["generated_at_ns"] = 2
            rp.write_text(json.dumps(bad) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                corpus.report_entry("fb001", wp, rp, identity.public_bytes())

    def test_host_fingerprint_is_bound(self):
        identity = StationIdentity.generate()
        bad = _host(); bad["logical_cpus"] = 9
        with self.assertRaises(ValueError):
            corpus.CorpusManifest.issue(source_commit="c" * 40, model_name="ollama:model",
                                        model_version="digest-a", host=bad, runs=3,
                                        entries=_entries(), identity=identity)


if __name__ == "__main__":
    unittest.main()
