"""Issue #63 M4-1: hash(verified_tree) == hash(accepted_tree) under adversarial
verification commands, in both execution boundaries (isolated + dev fixture).
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import sys
import unittest

from residual.factory import m4_integrator as m4
from residual.factory.m4_integrator import ProjectVerificationPolicy, VerificationCommand
from residual.factory.m4_sandbox import SANDBOX_PROFILE, probe_isolation
from residual.factory.runtime_workspace import git
from residual.factory.worker_contract import WorkerContractError
from tests import test_factory_m4_integrator as fixtures

ISOLATED = probe_isolation()[0]
SANDBOX_PYTHON = "/usr/bin/python3"


class TreeBindingBase(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.M4IntegratorTests(methodName="runTest")
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.receipt = self.f.issue("task1", "R1", artifacts={"one.txt": b"one\n"}, index=1)
        self.plan = self.f.m4.integration_plan((self.receipt.receipt_hash,))

    def isolated_policy(self, first_code: str, *, last_code: str = "raise SystemExit(0)"):
        return ProjectVerificationPolicy((
            VerificationCommand("tests", "full_test_suite", (SANDBOX_PYTHON, "-c", first_code)),
            VerificationCommand("types", "type_check", (SANDBOX_PYTHON, "-c", "raise SystemExit(0)")),
            VerificationCommand("contracts", "contract_validation", (SANDBOX_PYTHON, "-c", last_code)),
        ))

    def fixture_policy(self, first_code: str, *, last_code: str = "raise SystemExit(0)"):
        original = self.f.policy()
        first = replace(original.commands[0], argv=(sys.executable, "-c", first_code))
        last = replace(original.commands[-1], argv=(sys.executable, "-c", last_code))
        return replace(original, commands=(first,) + original.commands[1:-1] + (last,))

    def integrate(self, policy):
        return self.f.integrator.integrate(self.plan, policy=policy,
                                           station_identity=self.f.identity)


@unittest.skipUnless(ISOLATED, "kernel namespace isolation unavailable on this platform")
class IsolatedTreeBindingTests(TreeBindingBase):
    def test_isolated_verification_issues_receipt_bound_to_verified_tree(self):
        outcome = self.integrate(self.isolated_policy("raise SystemExit(0)"))
        receipt = outcome.receipt
        self.assertTrue(receipt.verify_signature(self.f.identity.public_bytes()))
        self.assertEqual(receipt.evidence_level, "isolated_candidate_verification")
        self.assertEqual(receipt.verification_results[0].execution_boundary, SANDBOX_PROFILE)
        resolved = git(self.f.repo, "rev-parse", f"{receipt.output_commit}^{{tree}}").decode().strip()
        self.assertEqual(resolved, outcome.output_tree)  # verified tree == accepted tree
        blob = git(self.f.repo, "show", f"{receipt.output_commit}:one.txt")
        self.assertEqual(blob, b"one\n")

    def test_extra_file_creation_fails_and_nothing_is_accepted(self):
        with self.assertRaises(WorkerContractError):
            self.integrate(self.isolated_policy("open('sneaky.txt','w').write('x')"))
        self.assertFalse(any(e["event"] == "IntegrationReceiptIssued" for e in self.f.events))
        head = git(self.f.repo, "rev-parse", "HEAD").decode().strip()
        self.assertEqual(head, self.f.base)

    def test_candidate_artifact_modification_fails(self):
        with self.assertRaises(WorkerContractError):
            self.integrate(self.isolated_policy("open('one.txt','w').write('evil')"))
        self.assertFalse(any(e["event"] == "IntegrationReceiptIssued" for e in self.f.events))

    def test_network_exfiltration_attempt_fails_verification(self):
        code = ("import socket; socket.create_connection(('203.0.113.1', 443), 2)")
        with self.assertRaises(m4.ProjectVerificationError):
            self.integrate(self.isolated_policy(code))

    def test_post_check_mutation_before_commit_rejected(self):
        # Mutation in the final command is caught by the post-loop snapshot even
        # though every individual check "passed" (write fails on RO bind; on a
        # writable boundary the tree-freeze rejects it instead).
        with self.assertRaises(WorkerContractError):
            self.integrate(self.isolated_policy("raise SystemExit(0)",
                                                last_code="open('late.txt','w').write('x')"))
        self.assertFalse(any(e["event"] == "IntegrationReceiptIssued" for e in self.f.events))


class FixtureTreeBindingTests(TreeBindingBase):
    """The trusted-fixture boundary is writable, so the tree-freeze itself must
    catch every mutation class here."""

    def test_post_check_mutation_before_commit_rejected(self):
        with self.assertRaisesRegex(m4.M4IntegrationError, "modified the frozen"):
            self.integrate(self.fixture_policy("raise SystemExit(0)",
                                               last_code="open('late.txt','w').write('x')"))
        self.assertFalse(any(e["event"] == "IntegrationReceiptIssued" for e in self.f.events))

    def test_git_add_staging_unreceipted_state_rejected(self):
        code = (
            "import subprocess, os\n"
            "open('junk.txt','w').write('x')\n"
            "subprocess.run(['git','add','-A'], check=False)\n"
        )
        with self.assertRaisesRegex(m4.M4IntegrationError, "modified the frozen"):
            self.integrate(self.fixture_policy(code))
        head = git(self.f.repo, "rev-parse", "HEAD").decode().strip()
        self.assertEqual(head, self.f.base)

    def test_verified_tree_hash_equals_accepted_tree_hash(self):
        outcome = self.integrate(self.fixture_policy("raise SystemExit(0)"))
        receipt = outcome.receipt
        self.assertEqual(receipt.evidence_level, "development_fixture")
        resolved = git(self.f.repo, "rev-parse", f"{receipt.output_commit}^{{tree}}").decode().strip()
        self.assertEqual(resolved, outcome.output_tree)
        # The accepted tree contains exactly the receipted bytes, no more.
        names = git(self.f.repo, "ls-tree", "-r", "--name-only", receipt.output_commit).decode().split()
        self.assertIn("one.txt", names)
        self.assertEqual(git(self.f.repo, "show", f"{receipt.output_commit}:one.txt"), b"one\n")

    def test_generated_cache_directories_rejected(self):
        code = (
            "import os\n"
            "os.makedirs('.cache/pytest', exist_ok=True)\n"
            "open('.cache/pytest/v','w').write('x')\n"
        )
        with self.assertRaisesRegex(m4.M4IntegrationError, "modified the frozen"):
            self.integrate(self.fixture_policy(code))


if __name__ == "__main__":
    unittest.main()
