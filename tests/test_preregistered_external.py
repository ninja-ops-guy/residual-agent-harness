import json
import tempfile
import unittest
from pathlib import Path

from residual.assurance.preregistered import (
    ExternalPreregistration,
    build_evidence_bundle,
    engine_config_sha256,
    load_preregistration,
    preregister_from_files,
    verify_preregistration,
    write_preregistration,
)
from residual.assurance.external import load_external_suite


class PreregisteredExternalTests(unittest.TestCase):
    def write_suite(self, root: Path) -> Path:
        path = root / "suite.json"
        payload = {
            "schema_version": "residual.external-suite.v1",
            "name": "public-mini",
            "provenance": {
                "evidence_level": "externally_authored",
                "author": "independent-evaluator",
                "source_uri": "https://example.invalid/frozen",
                "authored_at": "2026-09-14T00:00:00Z",
            },
            "cases": [
                {
                    "id": "train-1", "split": "train", "capability": "text",
                    "assurance": "routine", "required_pass_rate": 0.5,
                    "prompt": "2+2?", "grader": {"kind": "exact_text", "expected": "4"},
                },
                {
                    "id": "eval-1", "split": "evaluation", "capability": "text",
                    "assurance": "routine", "required_pass_rate": 0.5,
                    "prompt": "3+3?", "grader": {"kind": "exact_text", "expected": "6"},
                },
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_engines(self, root: Path) -> Path:
        path = root / "engines.json"
        payload = {
            "schema_version": "residual.external-engines.v1",
            "engines": [
                {"provider": "openai", "model": "model-a", "capabilities": ["text"], "cost_per_task": 0.01},
                {"provider": "ollama", "model": "model-b", "capabilities": ["text"], "cost_per_task": 0.0},
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_manifest_binds_suite_and_engine_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            suite_path = self.write_suite(root)
            engines_path = self.write_engines(root)
            manifest = preregister_from_files(
                study_id="study-1",
                registered_at="2026-09-14T03:30:00-04:00",
                suite_path=suite_path,
                engines_path=engines_path,
                hypotheses=("VCM beats the cheaper-engine baseline.",),
                primary_metric="market_success_rate",
                secondary_metrics=("oracle_gap",),
                maximum_budget_usd=5.0,
                runner_revision="git:abc123",
            )
            suite = load_external_suite(suite_path)
            verify_preregistration(manifest, suite, engines_path)
            self.assertEqual(manifest.suite_sha256, suite.sha256)
            self.assertEqual(manifest.engine_config_sha256, engine_config_sha256(engines_path))

            raw = json.loads(engines_path.read_text())
            raw["engines"][0]["model"] = "changed-model"
            engines_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "engine config hash"):
                verify_preregistration(manifest, suite, engines_path)

    def test_manifest_round_trip_and_hash(self):
        manifest = ExternalPreregistration(
            study_id="s", registered_at="t", suite_sha256="a" * 64,
            engine_config_sha256="b" * 64, hypotheses=("h",),
            primary_metric="market_success_rate", secondary_metrics=("oracle_gap",),
            stopping_rule={"kind": "fixed_evaluation_cases", "value": 1},
            maximum_budget_usd=1.0, runner_revision="git:deadbeef", notes="frozen",
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            write_preregistration(path, manifest)
            loaded = load_preregistration(path)
            self.assertEqual(loaded, manifest)
            self.assertEqual(loaded.sha256, manifest.sha256)

    def test_bundle_binds_report_to_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            suite_path = self.write_suite(root)
            engines_path = self.write_engines(root)
            suite = load_external_suite(suite_path)
            manifest = preregister_from_files(
                study_id="study-2", registered_at="now", suite_path=suite_path,
                engines_path=engines_path, hypotheses=("h",),
                primary_metric="market_success_rate", secondary_metrics=(),
                maximum_budget_usd=2.0, runner_revision="git:abc",
            )
            report = {"suite_sha256": suite.sha256, "market": {"success_rate": 0.5}, "sha256": "c" * 64}
            bundle = build_evidence_bundle(
                manifest=manifest, suite=suite, engines_path=engines_path, report=report
            )
            self.assertEqual(bundle["preregistration_sha256"], manifest.sha256)
            self.assertEqual(bundle["suite_sha256"], suite.sha256)
            self.assertEqual(len(bundle["sha256"]), 64)

    def test_engine_config_rejects_secret_fields(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "engines.json"
            path.write_text(json.dumps({
                "schema_version": "residual.external-engines.v1",
                "engines": [
                    {"provider": "openai", "model": "a", "api_key": "secret"},
                    {"provider": "ollama", "model": "b"},
                ],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "credentials or endpoints"):
                engine_config_sha256(path)


if __name__ == "__main__":
    unittest.main()
