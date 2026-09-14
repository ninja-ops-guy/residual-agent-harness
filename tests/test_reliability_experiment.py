from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from residual.experiments.reliability import (
    MANIFEST_SCHEMA,
    OBSERVATION_SCHEMA,
    ReliabilityManifest,
    TrialObservation,
    analyze_reliability,
    load_manifest,
    load_observations,
    write_artifacts,
)


class ReliabilityExperimentTests(unittest.TestCase):
    def manifest(self) -> ReliabilityManifest:
        return ReliabilityManifest(
            study_id="fixture-study",
            suite_sha256="suite-abc",
            source_revision="git:deadbeef",
            preregistered_at="2026-09-14T08:00:00-04:00",
            baseline_configuration="raw",
            configurations=("raw", "covd"),
            model_bindings={"raw": "fixture@1", "covd": "fixture@1"},
            verifier_revisions={"grader": "fixture-v1"},
            budget={"maximum_calls": 100},
        )

    def observations(self):
        return (
            TrialObservation("a", "repair", 1, "raw", True, False, False, degradation_level="weak", cost_usd=1, latency_ms=100),
            TrialObservation("b", "repair", 1, "raw", True, True, True, fault_injected=True, fault_contained=False, degradation_level="weak", cost_usd=1, latency_ms=120),
            TrialObservation("a", "repair", 1, "covd", False, False, False, fault_injected=True, fault_contained=True, degradation_level="weak", cost_usd=2, latency_ms=150),
            TrialObservation("b", "repair", 1, "covd", True, True, True, degradation_level="weak", cost_usd=2, latency_ms=160),
        )

    def test_aer_and_containment_measure_acceptance_boundary(self):
        result = analyze_reliability(self.manifest(), self.observations())
        raw = result["metrics_by_configuration"]["raw"]
        covd = result["metrics_by_configuration"]["covd"]
        self.assertEqual(raw["accepted_error_rate"], 0.5)
        self.assertEqual(covd["accepted_error_rate"], 0.0)
        self.assertEqual(covd["failure_containment_rate"], 1.0)
        self.assertEqual(result["comparisons_to_baseline"]["covd"]["accepted_error_rate_delta_vs_baseline"], -0.5)
        self.assertEqual(result["comparisons_to_baseline"]["covd"]["accepted_error_rate_relative_reduction_vs_baseline"], 1.0)

    def test_zero_acceptance_stays_unknown_not_zero_error(self):
        rows = (
            TrialObservation("a", "x", 1, "raw", True, True, True),
            TrialObservation("a", "x", 1, "covd", False, False, False),
        )
        result = analyze_reliability(self.manifest(), rows)
        self.assertIsNone(result["metrics_by_configuration"]["covd"]["accepted_error_rate"])
        self.assertEqual(result["metrics_by_configuration"]["covd"]["acceptance_rate"], 0.0)

    def test_unknown_configuration_fails_closed(self):
        rows = self.observations() + (TrialObservation("z", "x", 1, "surprise", True, True, True),)
        with self.assertRaises(ValueError):
            analyze_reliability(self.manifest(), rows)

    def test_round_trip_files_and_release_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            obs_path = root / "observations.jsonl"
            manifest_path.write_text(json.dumps(self.manifest().payload()), encoding="utf-8")
            obs_path.write_text("\n".join(json.dumps(o.payload()) for o in self.observations()) + "\n", encoding="utf-8")
            manifest = load_manifest(manifest_path)
            observations = load_observations(obs_path)
            result = analyze_reliability(manifest, observations)
            output = root / "release"
            write_artifacts(result, output)
            self.assertTrue((output / "results.json").exists())
            self.assertTrue((output / "report.md").exists())
            self.assertTrue((output / "evidence-manifest.json").exists())
            self.assertTrue((output / "plot-data.csv").exists())
            self.assertTrue((output / "figures" / "degradation-aer.svg").exists())
            evidence = json.loads((output / "evidence-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["result_sha256"], result["sha256"])

    def test_loaders_reject_schema_drift_and_duplicate_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_manifest = self.manifest().payload()
            bad_manifest["schema_version"] = "wrong"
            path = root / "manifest.json"
            path.write_text(json.dumps(bad_manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(path)

            payload = self.observations()[0].payload()
            self.assertEqual(payload["schema_version"], OBSERVATION_SCHEMA)
            obs_path = root / "obs.jsonl"
            obs_path.write_text(json.dumps(payload) + "\n" + json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_observations(obs_path)


if __name__ == "__main__":
    unittest.main()
