import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from residual.core import ContractError
from residual.self_improvement import (
    build_station_spec,
    doctor_repository,
    execute_generation,
    load_candidates,
    mission_plan,
)
from residual.station.contracts import parse_spec


class RecursiveImprovementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        required = {
            "docs/CURRENT_STATUS.md": "# status\n",
            "residual/goalspec.py": "GOAL = True\n",
            "residual/loop.py": "LOOP = True\n",
            "residual/station/service.py": "STATION = True\n",
            "residual/station/control.py": "CONTROL = True\n",
            "tests/frozen_eval.py": "EVALUATOR = True\n",
        }
        for name, content in required.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        roadmap = self.repo / "docs/roadmap/README.md"
        roadmap.parent.mkdir(parents=True, exist_ok=True)
        roadmap.write_text("# Roadmap\n\n## Current build order\n\n1. Repair health\n2. Improve throughput\n")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=self.repo, check=True, capture_output=True)
        self.baseline = self.git("rev-parse", "HEAD")
        roadmap.write_text(
            "# Roadmap\n\nCurrent main is **" + chr(96) + self.baseline + chr(96) + "**.\n\n"
            "## Current build order\n\n1. Repair health\n2. Improve throughput\n"
        )
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "status"], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def candidate(self, files=None, evaluators=None):
        return {
            "schema_version": 1,
            "candidates": [{
                "id": "SI-001",
                "title": "Document operation",
                "instruction": "Create an operations note.",
                "files": files or ["docs/self-improvement/OPERATIONS.md"],
                "context": ["docs/CURRENT_STATUS.md"],
                "depends_on": [],
                "checks": [{"kind": "exists", "path": (files or ["docs/self-improvement/OPERATIONS.md"])[0]}],
                "route": "local",
                "evaluator_files": evaluators or [],
            }],
        }

    def test_doctor_is_content_addressed_and_detects_roadmap_lag(self):
        a = doctor_repository(self.repo)
        b = doctor_repository(self.repo)
        self.assertEqual(a["report_sha256"], b["report_sha256"])
        self.assertEqual(a["roadmap_delta_commits"], 1)
        self.assertEqual(len(a["roadmap_items"]), 2)
        self.assertIn("roadmap_status_lag", {f["code"] for f in a["findings"]})

    def test_doctor_detects_dirty_checkout(self):
        (self.repo / "scratch.txt").write_text("dirty")
        report = doctor_repository(self.repo)
        self.assertTrue(report["dirty"])
        self.assertIn("checkout_dirty", {f["code"] for f in report["findings"]})

    def test_plan_is_hierarchical_and_stable(self):
        report = doctor_repository(self.repo)
        self.assertEqual(mission_plan(report), mission_plan(report))
        self.assertIn("swarm_director", mission_plan(report)["hierarchy"]["mission_governor"])

    def test_candidate_builds_existing_station_contract(self):
        report = doctor_repository(self.repo)
        spec = build_station_spec(report, mission_plan(report), self.candidate(), self.repo)
        manifest = parse_spec(spec)
        self.assertEqual(manifest["tasks"][0]["id"], "SI-001")

    def test_candidate_cannot_modify_its_evaluator(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["tests/frozen_eval.py"], ["tests/frozen_eval.py"])
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_protected_path_fails_closed(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["residual/station/service.py"], [])
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_unknown_candidate_fields_fail_closed(self):
        path = self.repo / "candidate.json"
        value = self.candidate()
        value["extra"] = True
        path.write_text(json.dumps(value))
        with self.assertRaises(ContractError):
            load_candidates(path)

    def test_execution_delegates_to_station_managed_clone_and_export(self):
        candidate = self.repo / "candidate.json"
        candidate.write_text(json.dumps(self.candidate()))
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "candidate"], cwd=self.repo, check=True, capture_output=True)

        calls = {}
        class FakeStation:
            def __init__(self, root):
                calls["root"] = str(root)
            def create(self, spec, source, allow_cloud, commands):
                parse_spec(spec)
                calls["source"] = source
                return {"project_id": "p-test"}
            def batch(self, pid):
                return {"integrated": 1, "total": 1, "control": {"outcome": "success"}}
            def export(self, pid):
                return {"id": "export-test"}

        with patch("residual.station.service.Station", FakeStation):
            result = execute_generation(self.repo, candidate, self.repo / ".station")
        self.assertEqual(calls["source"], str(self.repo.resolve()))
        self.assertEqual(result["export"]["id"], "export-test")


if __name__ == "__main__":
    unittest.main()
