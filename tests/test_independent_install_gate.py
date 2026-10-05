"""Fail-closed tests for the bounded independent first-install gate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("independent_install_gate", ROOT / "tools/independent_install_gate.py")
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


class ClassificationTests(unittest.TestCase):
    def test_repository_ci_can_never_claim_external_verification(self):
        self.assertEqual(gate.classify("PASS", "repository_ci", True), gate.UNVERIFIED)

    def test_external_evaluator_must_attest_independence(self):
        self.assertEqual(gate.classify("PASS", "external", False), gate.UNVERIFIED)
        self.assertEqual(gate.classify("PASS", "external", True), gate.VERIFIED)

    def test_technical_failure_is_never_verified(self):
        self.assertEqual(gate.classify("FAIL", "external", True), gate.FAILED)


class HandoffTests(unittest.TestCase):
    def make_handoff(self, root: Path):
        files = {
            "candidate.whl": (b"candidate-wheel", "candidate-wheel"),
            "dependency.whl": (b"dependency-wheel", "dependency-wheel"),
            "evaluate.py": (b"# evaluator\n", "evaluator"),
            "TERMS.md": (b"terms\n", "evaluation-terms"),
        }
        members = []
        for name, (data, role) in files.items():
            path = root / name
            path.write_bytes(data)
            members.append({
                "name": name,
                "role": role,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            })
        manifest = {
            "schema": gate.SCHEMA_HANDOFF,
            "candidate": {"repository": "owner/repo", "commit": "a" * 40, "tree": "b" * 40},
            "artifact": {
                "package": gate.PACKAGE,
                "wheel": "candidate.whl",
                "sha256": hashlib.sha256(files["candidate.whl"][0]).hexdigest(),
            },
            "supported_configuration": {},
            "members": members,
            "claims": {"release_authority": False},
        }
        gate.write_json(root / "handoff.json", manifest)
        digest = gate.sha256_file(root / "handoff.json")
        (root / "handoff.sha256").write_text(f"{digest}  handoff.json\n", encoding="utf-8")
        return manifest

    def test_handoff_binds_candidate_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.make_handoff(root)
            observed, _ = gate.validate_handoff(root)
            self.assertEqual(observed["candidate"], manifest["candidate"])
            (root / "candidate.whl").write_bytes(b"tampered")
            with self.assertRaisesRegex(gate.GateError, "hash/size mismatch"):
                gate.validate_handoff(root)

    def test_negative_control_contains_package_and_example_tripwires(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gate.create_negative_control(root)
            self.assertIn("SOURCE_CHECKOUT_DEPENDENCY_TRIPWIRE", (root / "residual/__init__.py").read_text())
            poisoned = json.loads((root / "examples/onboarding/sample_project/inventory.json").read_text())
            self.assertEqual(poisoned["readings"]["fan_rpms"], [-999999])
            fixture = json.loads((root / "inventory.json").read_text())
            self.assertEqual(sum(fixture["readings"]["fan_rpms"]), 7230)
            self.assertEqual(sum(fixture["readings"]["temperatures_c"]), 65.25)


if __name__ == "__main__":
    unittest.main()
