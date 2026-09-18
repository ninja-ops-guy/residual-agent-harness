import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from residual.core import ContractError
from residual.cli import main as cli_main
from residual.self_improvement import (
    build_station_spec,
    doctor_repository,
    execute_generation,
    load_candidates,
    mission_plan,
    originate_candidates,
    planning_station_spec,
    run_lineage,
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
            "docs/evaluator.md": "# frozen evaluator\n",
            "docs/self-improvement/MISSION.md": "# mission policy\n",
            "tests/test_self_improvement.py": "# frozen mission regression\n",
            "residual/goalspec.py": "GOAL = True\n",
            "residual/loop.py": "LOOP = True\n",
            "residual/station/service.py": "STATION = True\n",
            "residual/station/control.py": "CONTROL = True\n",
            "tests/frozen_eval.py": "EVALUATOR = True\n",
            "tests/factory_guard.py": "PROTECTED = True\n",
            "verifier/v3/factory_ownership_baseline.json": json.dumps({
                "pinned_at": "0" * 40,
                "files": {"tests/factory_guard.py": "1" * 40},
            }) + "\n",
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
            "# Roadmap\n\nCurrent " + chr(96) + "main" + chr(96) + " is **" + chr(96) + self.baseline + chr(96) + "**.\n\n"
            "## Current build order\n\n1. Repair health\n2. Improve throughput\n"
        )
        (self.repo / "docs/CURRENT_STATUS.md").write_text(
            "# Status\n\nCurrent " + chr(96) + "main" + chr(96) + " is **" + chr(96) + self.baseline + chr(96) + "**.\n"
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
        self.assertEqual(a["current_status_delta_commits"], 1)
        self.assertEqual(len(a["roadmap_items"]), 2)
        codes = {f["code"] for f in a["findings"]}
        self.assertIn("roadmap_status_lag", codes)
        self.assertIn("current_status_lag", codes)

    def test_doctor_detects_dirty_checkout(self):
        (self.repo / "scratch.txt").write_text("dirty")
        report = doctor_repository(self.repo)
        self.assertTrue(report["dirty"])
        self.assertIn("checkout_dirty", {f["code"] for f in report["findings"]})

    def test_plan_is_hierarchical_and_stable(self):
        report = doctor_repository(self.repo)
        self.assertEqual(mission_plan(report), mission_plan(report))
        self.assertIn("swarm_director", mission_plan(report)["hierarchy"]["mission_governor"])

    def test_planning_spec_has_parallel_scouts_and_dependent_composer(self):
        report = doctor_repository(self.repo)
        manifest = parse_spec(planning_station_spec(report, mission_plan(report), "local"))
        tasks = {task["id"]: task for task in manifest["tasks"]}
        self.assertEqual(set(tasks), {"SI_HEALTH_SCOUT", "SI_ROADMAP_SCOUT", "SI_COMPOSER"})
        self.assertEqual(tasks["SI_HEALTH_SCOUT"]["depends_on"], [])
        self.assertEqual(tasks["SI_ROADMAP_SCOUT"]["depends_on"], [])
        self.assertEqual(set(tasks["SI_COMPOSER"]["depends_on"]),
                         {"SI_HEALTH_SCOUT", "SI_ROADMAP_SCOUT"})

    def test_candidate_builds_existing_station_contract(self):
        report = doctor_repository(self.repo)
        spec = build_station_spec(report, mission_plan(report), self.candidate(), self.repo)
        manifest = parse_spec(spec)
        self.assertEqual(manifest["tasks"][0]["id"], "SI-001")

    def test_raw_status_input_changes_report_identity(self):
        status = self.repo / "docs/CURRENT_STATUS.md"
        original = status.read_text()
        status.write_text(original + "\nNote: one\n")
        before = doctor_repository(self.repo)
        status.write_text(original + "\nNote: two\n")
        after = doctor_repository(self.repo)
        self.assertEqual(before["head"], after["head"])
        self.assertEqual(before["dirty"], after["dirty"])
        self.assertEqual(before["findings"], after["findings"])
        self.assertNotEqual(before["inputs"]["current_status_sha256"], after["inputs"]["current_status_sha256"])
        self.assertNotEqual(before["report_sha256"], after["report_sha256"])

    def test_command_check_requires_external_evaluator(self):
        report = doctor_repository(self.repo)
        doc = self.candidate()
        doc["candidates"][0]["checks"] = [{"kind": "command", "argv": ["python", "-m", "pytest"]}]
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_unsafe_model_authored_command_is_rejected(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["residual/example.py"], ["tests/frozen_eval.py"])
        doc["candidates"][0]["checks"] = [
            {"kind": "command", "argv": ["{python}", "-c", "print('pass')"]}
        ]
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_code_candidate_can_bind_pytest_to_frozen_evaluator(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["residual/example.py"], ["tests/frozen_eval.py"])
        doc["candidates"][0]["checks"] = [
            {"kind": "command", "argv": ["{python}", "-m", "pytest", "tests/frozen_eval.py"]}
        ]
        manifest = parse_spec(build_station_spec(report, mission_plan(report), doc, self.repo))
        self.assertEqual(manifest["tasks"][0]["checks"][0]["argv"][-1], "tests/frozen_eval.py")

    def test_execution_config_candidate_requires_frozen_evaluator(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["pyproject.toml"], [])
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_code_candidate_requires_frozen_command_evaluator(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["residual/example.py"], [])
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_candidate_writable_scopes_cannot_overlap(self):
        report = doctor_repository(self.repo)
        a = self.candidate()["candidates"][0]
        b = dict(a)
        b["id"] = "SI-002"
        doc = {"schema_version": 1, "candidates": [a, b]}
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_generation_cannot_modify_another_candidates_evaluator(self):
        report = doctor_repository(self.repo)
        a = self.candidate(["docs/a.md"], ["docs/evaluator.md"])["candidates"][0]
        b = self.candidate(["docs/evaluator.md"], [])["candidates"][0]
        b["id"] = "SI-002"
        b["checks"] = [{"kind": "exists", "path": "docs/evaluator.md"}]
        doc = {"schema_version": 1, "candidates": [a, b]}
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_candidate_cannot_modify_its_evaluator(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["tests/frozen_eval.py"], ["tests/frozen_eval.py"])
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_factory_ownership_manifest_path_fails_closed(self):
        report = doctor_repository(self.repo)
        doc = self.candidate(["tests/factory_guard.py"], ["tests/frozen_eval.py"])
        doc["candidates"][0]["checks"] = [{"kind": "command", "argv": ["python", "tests/frozen_eval.py"]}]
        with self.assertRaises(ContractError):
            build_station_spec(report, mission_plan(report), doc, self.repo)

    def test_mission_policy_and_history_are_not_autonomous_writes(self):
        report = doctor_repository(self.repo)
        for path in ("docs/CURRENT_STATUS.md", "docs/roadmap/README.md",
                     "docs/self-improvement/MISSION.md",
                     "docs/self-improvement/generations/0002.json"):
            doc = self.candidate([path], [])
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

    def test_cli_dispatches_revision_doctor(self):
        with patch("residual.self_improvement.revision_main", return_value=7) as doctor:
            self.assertEqual(cli_main(["revision", "doctor"]), 7)
            doctor.assert_called_once_with(["doctor"])

    def test_origination_uses_station_and_admits_only_validated_proposal(self):
        proposal = self.candidate()
        calls = {}
        repo_path = str(self.repo.resolve())

        class FakeStore:
            def project(self, pid):
                return {"repo": repo_path}
            def add_artifact(self, pid, name, content, kind):
                calls["artifact"] = {"pid": pid, "name": name, "kind": kind}
                return {"id": "p-plan:abc", "sha256": "a" * 64, "name": name, "size": len(content), "kind": kind}
            def event(self, pid, event_type, data):
                calls.setdefault("events", []).append((event_type, data))

        class FakeStation:
            def __init__(self, root):
                self.store = FakeStore()
            def create(self, spec, source, allow_cloud, commands):
                manifest = parse_spec(spec)
                calls["planner_tasks"] = [task["id"] for task in manifest["tasks"]]
                calls["source"] = source
                self.pid = "p-plan"
                return {"project_id": self.pid}
            def batch(self, pid):
                target = self.repo / "docs/self-improvement/proposals/candidates.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(proposal))
                return {"integrated": 3, "total": 3, "control": {"outcome": "success"}}
            def export(self, pid):
                return {"id": "planner-export"}

        FakeStation.repo = self.repo
        with patch("residual.station.service.Station", FakeStation):
            result = originate_candidates(self.repo, self.repo / ".station", route="local")
        self.assertEqual(result["proposal"], proposal)
        self.assertEqual(result["planner_route"], "local")
        self.assertEqual(result["export"]["id"], "planner-export")
        self.assertEqual(set(calls["planner_tasks"]),
                         {"SI_HEALTH_SCOUT", "SI_ROADMAP_SCOUT", "SI_COMPOSER"})

    def test_lineage_advances_only_through_accepted_successors(self):
        next_repo = str((self.repo / ".station/successor").resolve())
        first = {
            "mission_id": "residual-self-improvement",
            "generation": "g1",
            "origin": {
                "source_head": "1" * 40,
                "source_report_sha256": "2" * 64,
                "plan_sha256": "3" * 64,
                "planner_project_id": "p1",
                "proposal_sha256": "4" * 64,
            },
            "execution": {
                "project_id": "e1",
                "accepted_successor": True,
                "successor_head": "5" * 40,
                "successor_tree": "6" * 40,
                "successor_repo": next_repo,
                "export": {"id": "x1"},
            },
        }
        second = {
            "mission_id": "residual-self-improvement",
            "generation": "g2",
            "origin": {
                "source_head": "5" * 40,
                "source_report_sha256": "7" * 64,
                "plan_sha256": "8" * 64,
                "planner_project_id": "p2",
                "proposal_sha256": None,
            },
            "execution": None,
        }
        with patch("residual.self_improvement.run_cycle", side_effect=[first, second]) as cycle:
            result = run_lineage(self.repo, self.repo / ".station", generations=3)
        self.assertEqual(result["attempted_generations"], 2)
        self.assertEqual(result["accepted_generations"], 1)
        self.assertEqual(result["stop_reason"], "origination_incomplete")
        self.assertEqual(cycle.call_args_list[1].args[0], next_repo)

    def test_revision_doctor_improve_dispatches_bounded_lineage(self):
        outcome = {
            "mission_id": "residual-self-improvement",
            "history": [{"accepted_successor": True}],
        }
        with patch("residual.self_improvement.run_lineage", return_value=outcome) as lineage:
            rc = cli_main([
                "revision", "doctor", "--improve", "--repo", str(self.repo),
                "--station-data", str(self.repo / ".station"), "--generations", "2",
            ])
        self.assertEqual(rc, 0)
        self.assertEqual(lineage.call_args.kwargs["generations"], 2)

    def test_execution_delegates_to_station_managed_clone_and_export(self):
        candidate = self.repo / "candidate.json"
        candidate.write_text(json.dumps(self.candidate()))
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "candidate"], cwd=self.repo, check=True, capture_output=True)

        calls = {}
        repo_path = str(self.repo.resolve())
        class FakeStore:
            def project(self, pid):
                return {"repo": repo_path}
            def event(self, pid, event_type, data):
                calls["event"] = {"event_type": event_type, "data": data}
        class FakeStation:
            repo = self.repo
            def __init__(self, root):
                calls["root"] = str(root)
                self.store = FakeStore()
            def create(self, spec, source, allow_cloud, commands):
                parse_spec(spec)
                calls["source"] = source
                return {"project_id": "p-test"}
            def batch(self, pid):
                target = self.repo / "docs/self-improvement/OPERATIONS.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("Generation promotion checklist\nexport\n")
                subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
                subprocess.run(["git", "commit", "-m", "candidate-output"], cwd=self.repo,
                               check=True, capture_output=True)
                return {"integrated": 1, "total": 1, "control": {"outcome": "success"}}
            def export(self, pid):
                return {"id": "export-test"}

        with patch("residual.station.service.Station", FakeStation):
            result = execute_generation(self.repo, candidate, self.repo / ".station")
        self.assertEqual(calls["source"], str(self.repo.resolve()))
        self.assertTrue(result["meaningful_delta"])
        self.assertTrue(result["accepted_successor"])
        self.assertEqual(result["export"]["id"], "export-test")


if __name__ == "__main__":
    unittest.main()
