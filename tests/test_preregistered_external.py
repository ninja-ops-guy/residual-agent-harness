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
    projected_declared_cost_usd,
    projected_provider_calls,
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
            maximum_budget_usd=1.0, runner_revision="git:deadbeef", trials=3, notes="frozen",
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            write_preregistration(path, manifest)
            loaded = load_preregistration(path)
            self.assertEqual(loaded, manifest)
            self.assertEqual(loaded.sha256, manifest.sha256)
            self.assertEqual(loaded.trials, 3)

    def test_v1_manifest_remains_hash_stable_and_defaults_to_one_trial(self):
        payload = {
            "schema_version": "residual.external-preregistration.v1",
            "study_id": "legacy", "registered_at": "t", "suite_sha256": "a" * 64,
            "engine_config_sha256": "b" * 64, "hypotheses": ["h"],
            "primary_metric": "market_success_rate", "secondary_metrics": [],
            "stopping_rule": {"kind": "fixed_evaluation_cases", "value": 1},
            "maximum_budget_usd": 1.0, "runner_revision": "git:old", "notes": "",
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "legacy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            manifest = load_preregistration(path)
            self.assertEqual(manifest.trials, 1)
            self.assertEqual(manifest.payload(), payload)

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
                maximum_budget_usd=2.0, runner_revision="git:abc", trials=2,
            )
            report = {"suite_sha256": suite.sha256, "trials": 2, "market": {"success_rate": 0.5}, "sha256": "c" * 64}
            bundle = build_evidence_bundle(
                manifest=manifest, suite=suite, engines_path=engines_path, report=report
            )
            self.assertEqual(bundle["preregistration_sha256"], manifest.sha256)
            self.assertEqual(bundle["suite_sha256"], suite.sha256)
            self.assertEqual(bundle["trials"], 2)
            self.assertAlmostEqual(bundle["projected_declared_cost_usd"], 0.04)
            self.assertEqual(bundle["projected_provider_calls"], 8)
            self.assertEqual(len(bundle["sha256"]), 64)

    def test_budget_and_call_ceiling_scale_with_trials(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            suite_path = self.write_suite(root)
            engines_path = self.write_engines(root)
            suite = load_external_suite(suite_path)
            self.assertAlmostEqual(projected_declared_cost_usd(suite, engines_path, 3), 0.06)
            self.assertEqual(projected_provider_calls(suite, engines_path, 3), 12)

            with self.assertRaisesRegex(ValueError, "preregistered budget"):
                preregister_from_files(
                    study_id="too-cheap", registered_at="now", suite_path=suite_path,
                    engines_path=engines_path, hypotheses=("h",),
                    primary_metric="market_success_rate", secondary_metrics=(),
                    maximum_budget_usd=0.059, runner_revision="git:abc", trials=3,
                )

            manifest = ExternalPreregistration(
                study_id="calls", registered_at="now", suite_sha256=suite.sha256,
                engine_config_sha256=engine_config_sha256(engines_path), hypotheses=("h",),
                primary_metric="market_success_rate", secondary_metrics=(),
                stopping_rule={"kind": "maximum_provider_calls", "value": 11},
                maximum_budget_usd=1.0, runner_revision="git:abc", trials=3,
            )
            with self.assertRaisesRegex(ValueError, "provider calls"):
                verify_preregistration(manifest, suite, engines_path)

    def test_bundle_rejects_report_with_wrong_trial_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            suite_path = self.write_suite(root)
            engines_path = self.write_engines(root)
            suite = load_external_suite(suite_path)
            manifest = preregister_from_files(
                study_id="study-trials", registered_at="now", suite_path=suite_path,
                engines_path=engines_path, hypotheses=("h",),
                primary_metric="market_success_rate", secondary_metrics=(),
                maximum_budget_usd=1.0, runner_revision="git:abc", trials=2,
            )
            with self.assertRaisesRegex(ValueError, "trial count"):
                build_evidence_bundle(
                    manifest=manifest, suite=suite, engines_path=engines_path,
                    report={"suite_sha256": suite.sha256, "trials": 1},
                )

    def test_engine_config_rejects_secret_and_unknown_fields(self):
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

            path.write_text(json.dumps({
                "schema_version": "residual.external-engines.v1",
                "engines": [
                    {"provider": "openai", "model": "a", "mystery": "value"},
                    {"provider": "ollama", "model": "b"},
                ],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid engine entry"):
                engine_config_sha256(path)


if __name__ == "__main__":
    unittest.main()
