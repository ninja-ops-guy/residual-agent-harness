"""Fail-closed Factory ownership gate regressions using real temp Git repos."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "verifier/v3/check_factory_ownership.py"
spec = importlib.util.spec_from_file_location("factory_ownership_gate", MODULE)
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

EXPECTED_CORE = frozenset({
    "residual/factory/__init__.py",
    "residual/factory/_isolated_child.py",
    "residual/factory/_sandbox_child.py",
    "residual/factory/evidence_bus.py",
    "residual/factory/evidence_receipts.py",
    "residual/factory/m4_evidence.py",
    "residual/factory/m4_git_evidence.py",
    "residual/factory/m4_integrator.py",
    "residual/factory/m4_safety.py",
    "residual/factory/m4_sandbox.py",
    "residual/factory/m4_scheduler.py",
    "residual/factory/runtime.py",
    "residual/factory/runtime_journal.py",
    "residual/factory/runtime_workspace.py",
    "residual/factory/station_issuer.py",
    "residual/factory/termination_provenance.py",
    "residual/factory/worker_contract.py",
})


class FactoryOwnershipGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Ownership gate test")
        self.git("config", "user.email", "ownership-test@example.invalid")
        for path in sorted(EXPECTED_CORE):
            self.write(path, f"# fixture content for {path}\n")
        self.write("README.md", "unprotected\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")
        self.manifest_path = Path(self.temp.name) / "baseline.json"
        self.write_manifest()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def write_manifest(self, drop=(), extra=None, justification="fixture pin"):
        files = {}
        for path in sorted(EXPECTED_CORE):
            if path in drop:
                continue
            files[path] = self.git("rev-parse", f"HEAD:{path}")
        if extra:
            files.update(extra)
        data = {
            "pinned_at": self.git("rev-parse", "HEAD"),
            "justification": justification,
            "files": files,
        }
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")

    def evaluate(self):
        return gate.evaluate_ownership(self.root, self.manifest_path)

    def test_core_set_matches_expected_trust_surface(self):
        self.assertEqual(gate.CORE_PROTECTED, EXPECTED_CORE)
        self.assertEqual(len(gate.CORE_PROTECTED), 17)

    def test_repo_manifest_covers_core_set(self):
        repo_manifest = json.loads(
            (Path(__file__).resolve().parents[1]
             / "verifier/v3/factory_ownership_baseline.json").read_text())
        self.assertTrue(EXPECTED_CORE <= repo_manifest["files"].keys())
        self.assertTrue(repo_manifest["justification"].strip())
        self.assertEqual(len(repo_manifest["pinned_at"]), 40)

    def test_repo_manifest_matches_committed_tree(self):
        repo_root = Path(__file__).resolve().parents[1]
        manifest = repo_root / "verifier/v3/factory_ownership_baseline.json"
        report, failures = gate.evaluate_ownership(repo_root, manifest)
        self.assertEqual(failures, [], report)
        self.assertEqual(report["checked"], len(json.loads(manifest.read_text())["files"]))

    def test_unchanged_tree_passes(self):
        report, failures = self.evaluate()
        self.assertEqual(failures, [])
        self.assertEqual(report["checked"], len(EXPECTED_CORE))

    def test_unprotected_edit_allowed(self):
        self.write("README.md", "allowed\n")
        self.commit()
        _, failures = self.evaluate()
        self.assertEqual(failures, [])

    def test_protected_edit_rejected(self):
        self.write("residual/factory/runtime.py", "# tampered\n")
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("residual/factory/runtime.py", " ".join(failures))

    def test_each_core_file_edit_rejected(self):
        for path in sorted(EXPECTED_CORE):
            with self.subTest(path=path):
                self.git("checkout", "-q", "--", ".")
                self.write(path, "# unauthorized edit\n")
                self.commit()
                _, failures = self.evaluate()
                self.assertIn(path, " ".join(failures))
                self.git("reset", "--hard", "-q", "HEAD~1")

    def test_protected_deletion_rejected(self):
        (self.root / "residual/factory/m4_safety.py").unlink()
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("residual/factory/m4_safety.py", " ".join(failures))

    def test_missing_manifest_fails_closed(self):
        self.manifest_path.unlink()
        _, failures = self.evaluate()
        self.assertTrue(any("manifest missing" in f for f in failures))

    def test_invalid_manifest_fails_closed(self):
        self.manifest_path.write_text("{not json", encoding="utf-8")
        _, failures = self.evaluate()
        self.assertTrue(failures)

    def test_missing_justification_fails_closed(self):
        self.write_manifest(justification="  ")
        _, failures = self.evaluate()
        self.assertTrue(any("justification" in f for f in failures))

    def test_missing_core_entry_fails_closed(self):
        self.write_manifest(drop=("residual/factory/m4_sandbox.py",))
        _, failures = self.evaluate()
        self.assertTrue(any("missing from baseline manifest" in f
                            for f in failures))

    def test_extra_protected_path_also_checked(self):
        self.write("scripts/status_check.py", "# pinned tool\n")
        self.commit()
        sha = self.git("rev-parse", "HEAD:scripts/status_check.py")
        self.write_manifest(extra={"scripts/status_check.py": sha})
        _, failures = self.evaluate()
        self.assertEqual(failures, [])
        self.write("scripts/status_check.py", "# tampered tool\n")
        self.commit()
        _, failures = self.evaluate()
        self.assertIn("scripts/status_check.py", " ".join(failures))

    def test_git_error_fails_closed(self):
        with patch.object(gate.subprocess, "run",
                          side_effect=FileNotFoundError("git missing")):
            _, failures = self.evaluate()
        self.assertTrue(failures)


if __name__ == "__main__":
    unittest.main()
