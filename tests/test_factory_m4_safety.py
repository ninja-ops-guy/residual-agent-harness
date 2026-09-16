"""Issue #63: real temporary Git/receipts, safe filesystem sentinels, no models."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import math
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from residual.factory import m4_integrator as m4
from residual.factory.m4_safety import (
    M4SafetyError, apply_artifact, artifact_parts, run_trusted_fixture, snapshot,
)
from residual.factory.runtime_workspace import git
from residual.factory.worker_contract import WorkerContractError
from tests import test_factory_m4_integrator as fixtures


class PathBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'workspace'
        self.work.mkdir(mode=0o700)
        self.outside = self.root / 'sentinel'
        self.outside.write_bytes(b'unchanged')

    def test_regular_creation_and_replacement_preserve_executable_mode(self):
        apply_artifact(self.work, 'src/app.py', b'first')
        target = self.work / 'src/app.py'
        target.chmod(0o755)
        apply_artifact(self.work, 'src/app.py', b'second')
        self.assertEqual(target.read_bytes(), b'second')
        self.assertEqual(target.stat().st_mode & 0o777, 0o755)

    def test_regular_delete_and_absent_parent_delete(self):
        apply_artifact(self.work, 'one', b'one')
        apply_artifact(self.work, 'one', None)
        apply_artifact(self.work, 'missing/one', None)
        self.assertFalse((self.work / 'one').exists())

    def test_dangling_target_cannot_create_external_file(self):
        outside = self.root / 'absent'
        (self.work / 'target').symlink_to(outside)
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, 'target', b'bad')
        self.assertFalse(outside.exists())

    def test_symlink_target_cannot_overwrite_external_file(self):
        (self.work / 'target').symlink_to(self.outside)
        with self.assertRaises(M4SafetyError):
            apply_artifact(self.work, 'target', b'bad')
        self.assertEqual(self.outside.read_bytes(), b'unchanged')

    def test_symlink_parents_live_and_dangling_rejected(self):
        for outside in (self.root, self.root / 'missing'):
            link = self.work / 'parent'
            link.symlink_to(outside, target_is_directory=True)
            try:
                with self.assertRaises(M4SafetyError):
                    apply_artifact(self.work, 'parent/sentinel', b'bad')
            finally:
                link.unlink()
        self.assertEqual(self.outside.read_bytes(), b'unchanged')

    def test_hardlink_rejected_before_overwrite_or_delete(self):
        os.link(self.outside, self.work / 'linked')
        for data in (b'bad', None):
            with self.subTest(data=data), self.assertRaises(M4SafetyError):
                apply_artifact(self.work, 'linked', data)
        self.assertEqual(self.outside.read_bytes(), b'unchanged')

    def test_directory_is_not_a_file_target(self):
        (self.work / 'directory').mkdir()
        for data in (b'bad', None):
            with self.subTest(data=data), self.assertRaises(M4SafetyError):
                apply_artifact(self.work, 'directory', data)

    def test_target_symlink_substitution_race_never_follows_link(self):
        target = self.work / 'target'
        target.write_bytes(b'old')
        real_replace = os.replace

        def substitute(src, dst, **kwargs):
            target.unlink()
            target.symlink_to(self.outside)
            return real_replace(src, dst, **kwargs)

        with patch('residual.factory.m4_safety.os.replace', side_effect=substitute):
            apply_artifact(self.work, 'target', b'new')
        self.assertEqual(self.outside.read_bytes(), b'unchanged')
        self.assertEqual(target.read_bytes(), b'new')
        self.assertFalse(target.is_symlink())

    def test_parent_substitution_race_rejected_at_descriptor_open(self):
        parent = self.work / 'parent'
        parent.mkdir()
        real_open = os.open

        def substitute(path, flags, *args, **kwargs):
            if path == 'parent' and kwargs.get('dir_fd') is not None:
                parent.rmdir()
                parent.symlink_to(self.root, target_is_directory=True)
            return real_open(path, flags, *args, **kwargs)

        with patch('residual.factory.m4_safety.os.open', side_effect=substitute):
            with self.assertRaises(M4SafetyError):
                apply_artifact(self.work, 'parent/sentinel', b'bad')
        self.assertEqual(self.outside.read_bytes(), b'unchanged')

    def test_noncanonical_and_git_metadata_paths_rejected(self):
        for path in ('', '.', '../sentinel', '/tmp/x', 'a//b', 'a/./b', '.git',
                     'a/.GiT/config', 'a/../b', 'a\\b', 'a\x00b'):
            with self.subTest(path=path), self.assertRaises(M4SafetyError):
                artifact_parts(path)

    def test_whitespace_paths_remain_literal(self):
        name = 'dir/a b\nc.txt'
        apply_artifact(self.work, name, b'good')
        self.assertEqual((self.work / name).read_bytes(), b'good')

    def test_snapshot_includes_ignored_files_directories_and_git_marker(self):
        (self.work / '.git').write_text('gitdir: trusted')
        (self.work / '.gitignore').write_text('cache/\n')
        before = snapshot(self.work)
        (self.work / 'cache').mkdir()
        after = snapshot(self.work)
        self.assertIn('.git', before)
        self.assertNotEqual(before, after)
        self.assertIn('cache', after)

    def test_snapshot_rejects_dangling_link_and_fifo(self):
        (self.work / 'bad').symlink_to(self.root / 'missing')
        with self.assertRaises(M4SafetyError):
            snapshot(self.work)
        (self.work / 'bad').unlink()
        os.mkfifo(self.work / 'fifo')
        with self.assertRaises(M4SafetyError):
            snapshot(self.work)


class VerificationInputTests(unittest.TestCase):
    def test_deadline_requires_finite_typed_bounded_value(self):
        for value in (True, False, 0, -1, math.nan, math.inf, -math.inf, '1', 901):
            with self.subTest(value=value), self.assertRaises(m4.M4IntegrationError):
                m4.VerificationCommand('tests', 'full_test_suite', ('python',), value)

    def test_output_cap_requires_positive_bounded_integer(self):
        for value in (True, False, 0, -1, 1.5, '1', 16 * 1024 * 1024 + 1):
            with self.subTest(value=value), self.assertRaises(m4.M4IntegrationError):
                m4.VerificationCommand('tests', 'full_test_suite', ('python',), max_output_bytes=value)

    def test_argv_must_be_immutable_and_nul_free(self):
        for value in ([], ['python'], (), ('py\x00thon',)):
            with self.subTest(value=value), self.assertRaises(m4.M4IntegrationError):
                m4.VerificationCommand('tests', 'full_test_suite', value)

    def test_fixture_consent_is_boolean_not_truthy_string(self):
        command = m4.VerificationCommand('tests', 'full_test_suite', ('python',))
        with self.assertRaises(m4.M4IntegrationError):
            m4.ProjectVerificationPolicy((command,), trusted_fixture_mode='false')


class M4AcceptanceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.M4IntegratorTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.receipt = self.f.issue('task1', 'R1', artifacts={'one.txt': b'one\n'}, index=1)
        self.plan = self.f.m4.integration_plan((self.receipt.receipt_hash,))

    def integrate(self, policy=None):
        return self.f.integrator.integrate(self.plan, policy=policy or self.f.policy(),
                                          station_identity=self.f.identity)

    def policy(self, code, **kwargs):
        original = self.f.policy()
        first = replace(original.commands[0], argv=(fixtures.sys.executable, '-c', code), **kwargs)
        return replace(original, commands=(first,) + original.commands[1:])

    def test_default_refuses_unsandboxed_execution_before_worktree_creation(self):
        # Without trusted_fixture_mode the OS-isolated runner is mandatory;
        # when the platform cannot provide it the integrator fails closed.
        with patch('residual.factory.m4_sandbox.probe_isolation',
                   return_value=(False, 'namespace_probe_failed')):
            with patch.object(self.f.integrator, '_worktree') as worktree:
                with patch('residual.factory.m4_integrator.run_trusted_fixture') as runner:
                    with self.assertRaisesRegex(WorkerContractError, 'isolated project verification is unavailable'):
                        self.integrate(replace(self.f.policy(), trusted_fixture_mode=False))
        runner.assert_not_called()
        worktree.assert_not_called()

    def test_extra_unreceipted_file_never_gets_signed(self):
        with self.assertRaisesRegex(m4.M4IntegrationError, 'modified the frozen'):
            self.integrate(self.policy("from pathlib import Path; Path('extra.txt').write_text('bad')"))
        self.assertFalse(any(e['event'] == 'IntegrationReceiptIssued' for e in self.f.events))
        self.assertEqual(git(self.f.repo, 'rev-parse', 'HEAD').decode().strip(), self.f.base)

    def test_artifact_mutation_never_gets_signed(self):
        with self.assertRaisesRegex(m4.M4IntegrationError, 'modified the frozen'):
            self.integrate(self.policy("from pathlib import Path; Path('one.txt').write_text('bad')"))
        self.assertFalse(any(e['event'] == 'IntegrationReceiptIssued' for e in self.f.events))

    def test_cache_output_and_permission_changes_rejected(self):
        for code in (
            "from pathlib import Path; Path('.cache').mkdir(); Path('.cache/data').write_text('bad')",
            "from pathlib import Path; Path('one.txt').chmod(0o755)",
        ):
            with self.subTest(code=code), self.assertRaises(m4.M4IntegrationError):
                self.integrate(self.policy(code))

    def test_mutation_is_checked_after_each_command(self):
        policy = self.policy("from pathlib import Path; Path('one.txt').write_text('bad')")
        restore = replace(policy.commands[1], argv=(fixtures.sys.executable, '-c',
                          "from pathlib import Path; Path('one.txt').write_text('one\\n')"))
        policy = replace(policy, commands=(policy.commands[0], restore, policy.commands[2]))
        with self.assertRaises(m4.M4IntegrationError):
            self.integrate(policy)

    def test_acceptance_uses_frozen_tree_not_later_worktree_contents(self):
        original = self.f.integrator._run_verification
        def after_checks(worktree, policy):
            results = original(worktree, policy)
            (worktree / 'not-receipted.txt').write_text('never sign this')
            (worktree / 'one.txt').write_text('never sign this either')
            return results
        # Trusted test seam deliberately mutates after final verification snapshot.
        # The signed tree must still use only the previously frozen artifact bytes.
        with patch.object(self.f.integrator, '_run_verification', side_effect=after_checks):
            output = self.integrate()
        self.assertEqual(git(self.f.repo, 'show', f'{output.receipt.output_commit}:one.txt'), b'one\n')
        paths = git(self.f.repo, 'ls-tree', '-r', '--name-only', output.receipt.output_commit)
        self.assertNotIn(b'not-receipted.txt', paths)

    def test_receipt_labels_unsandboxed_fixture_and_binds_policy(self):
        first = self.integrate()
        second = self.integrate()
        self.assertEqual(first.output_tree, second.output_tree)
        receipt = first.receipt
        self.assertEqual(receipt.schema_version, 'factory-integration-receipt-v2')
        self.assertEqual(receipt.evidence_level, 'development_fixture')
        self.assertEqual(receipt.verification_results[0].execution_boundary, 'trusted_fixture_unsandboxed')
        self.assertTrue(receipt.verify_signature(self.f.identity.public_bytes()))
        self.assertFalse(replace(receipt, evidence_level='measured').verify_signature(self.f.identity.public_bytes()))
        self.assertFalse(replace(receipt, verification_policy_hash='0' * 64).verify_signature(self.f.identity.public_bytes()))

    def test_output_limit_failure_publishes_no_integration_receipt(self):
        with self.assertRaises(m4.ProjectVerificationError):
            self.integrate(self.policy("import sys; sys.stdout.write('x' * 10000)", max_output_bytes=128))
        checks = [e for e in self.f.events if e['event'] == 'M4ProjectVerification'][-1]['checks']
        self.assertEqual(checks[0]['termination_reason'], 'output_limit')
        self.assertEqual(checks[0]['status'], 'fail')
        self.assertFalse(any(e['event'] == 'IntegrationReceiptIssued' for e in self.f.events))

    def test_unavailable_executable_is_unknown_not_pass(self):
        policy = self.f.policy()
        first = replace(policy.commands[0], argv=('/residual-no-such-executable',))
        with self.assertRaises(m4.ProjectVerificationError):
            self.integrate(replace(policy, commands=(first,) + policy.commands[1:]))
        checks = [e for e in self.f.events if e['event'] == 'M4ProjectVerification'][-1]['checks']
        self.assertEqual(checks[0]['status'], 'unknown')

    def test_git_absence_is_distinct_from_empty_file(self):
        self.assertIsNone(self.f.integrator._git_blob(self.f.base, 'absent'))
        (self.f.repo / 'empty').write_bytes(b'')
        git(self.f.repo, 'add', 'empty')
        git(self.f.repo, '-c', 'user.name=test', '-c', 'user.email=test@localhost', 'commit', '-m', 'empty')
        commit = git(self.f.repo, 'rev-parse', 'HEAD').decode().strip()
        self.assertEqual(self.f.integrator._git_blob(commit, 'empty'), b'')

    def test_missing_commit_is_an_error_not_absence(self):
        with self.assertRaises(WorkerContractError):
            self.f.integrator._git_blob('0' * 40, 'absent')

    def test_failed_tree_lookup_is_an_error_not_absence(self):
        from residual.factory.m4_git_evidence import GitBlobEvidence, GitEvidenceState
        unavailable = GitBlobEvidence(GitEvidenceState.ERROR, None, 'git_command_failed')
        with patch.object(m4, 'read_base_blob', return_value=unavailable):
            with self.assertRaises(WorkerContractError):
                self.f.integrator._git_blob(self.f.base, 'absent')

    def test_missing_base_blob_is_an_error_not_absence(self):
        oid = git(self.f.repo, 'rev-parse', f'{self.f.base}:shared.txt').decode().strip()
        (self.f.repo / '.git' / 'objects' / oid[:2] / oid[2:]).unlink()
        with self.assertRaises(WorkerContractError):
            self.f.integrator._git_blob(self.f.base, 'shared.txt')

    def test_different_incomparable_base_states_cannot_auto_resolve(self):
        r2 = self.f.issue('task2', 'R2', artifacts={'one.txt': b'different'}, index=2)
        with patch.object(self.f.integrator, '_git_blob', side_effect=(b'base-a', b'base-b')):
            with self.assertRaisesRegex(m4.M4IntegrationError, 'different base file states'):
                self.f.integrator._classify_overlaps((self.receipt, r2))

    def test_duplicate_receipts_fail_closed(self):
        forged = replace(self.plan, ordered_receipt_hashes=(self.receipt.receipt_hash,) * 2,
                         ordered_task_ids=('task1',) * 2)
        with self.assertRaisesRegex(m4.M4IntegrationError, 'duplicate'):
            self.f.integrator._receipts(forged)


class FixtureSupervisorTests(unittest.TestCase):
    def test_direct_supervisor_rejects_unbounded_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            for deadline, cap in ((math.nan, 128), (1, True), (math.inf, 128)):
                with self.subTest(deadline=deadline, cap=cap), self.assertRaises(M4SafetyError):
                    run_trusted_fixture(('python',), Path(directory), timeout_s=deadline, output_limit=cap)

    def test_output_capture_cap_does_not_depend_on_communicate_buffer(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_trusted_fixture((fixtures.sys.executable, '-c',
                "import sys; sys.stdout.write('x'*1000000)"), Path(directory), timeout_s=5, output_limit=64)
        self.assertEqual(result.reason, 'output_limit')
        self.assertEqual(result.stdout_sha256, hashlib.sha256(b'x' * 64).hexdigest())
        self.assertEqual(result.status, 'fail')

    def test_timeout_kills_process_group_not_only_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pidfile = root / 'child.pid'
            child_code = f"from pathlib import Path; import os,time; Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)"
            parent_code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child_code!r}]); time.sleep(30)"
            result = run_trusted_fixture((fixtures.sys.executable, '-c', parent_code), root,
                                        timeout_s=2, output_limit=1024)
            self.assertEqual(result.reason, 'timeout')
            self.assertTrue(pidfile.exists(), 'child fixture did not start before deadline')
            pid = int(pidfile.read_text())
            for _ in range(100):
                status = Path(f'/proc/{pid}/status')
                try:
                    status_text = status.read_text()
                except FileNotFoundError:
                    break
                if '\nState:\tZ' in status_text:
                    break
                time.sleep(0.01)
            else:
                self.fail('child remained running after process-group termination')


if __name__ == '__main__':
    unittest.main()
