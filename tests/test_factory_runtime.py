"""Real Linux worker/process/Git tests, plus durable journal and broker invariants."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from observation_layer import verify_chain
from residual.factory import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.runtime import FactoryRuntime, RuntimeUnavailable
from residual.factory.runtime_journal import JournalError, RuntimeJournal
from residual.factory.runtime_workspace import ManagedWorktree, SafeFileBroker, git
from residual.factory.worker_contract import AttemptGuard, ContractViolation, WorkerContract, WorkerContractError

ROOT = Path(__file__).resolve().parents[1]


class Fixture(unittest.TestCase):
    def setUp(self):
        if sys.platform != 'linux':
            self.skipTest('Linux runtime only')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init')
        (self.repo / 'input.txt').write_text('hello')
        (self.repo / 'secret.txt').write_text('never disclose')
        (self.repo / 'obsolete.txt').write_text('remove me')
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=fixture', '-c', 'user.email=fixture@localhost', 'commit', '-m', 'base')
        self.commit = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        self.plan = ExecutionPlan('write output', (Requirement('R1', 'create output', ('unit',)),),
                                  (FactoryTask('task1', 'write output', ('R1',), swarm='swarm1'),))
        self.approval = FrozenPlan.approve(self.plan, 'local-test-operator')
        self.journal = RuntimeJournal(self.root / 'state' / 'run.db', trace_id='test-run')
        self.runtime = FactoryRuntime(self.repo, self.root / 'work', self.journal, allow_local_worker_code=True)
        self.counter = 0

    def contract(self, **overrides):
        self.counter += 1
        i = self.counter
        data = dict(task_id='task1', worker_id=f'worker{i}', swarm_id='swarm1',
                    execution_plan_hash=self.plan.graph_hash, attempt_id=f'attempt{i}',
                    lease_id=f'lease{i}', lease_generation=i, input_commit=self.commit,
                    workspace_root=str(self.root / 'work' / 'swarm1' / f'attempt{i}'),
                    inputs=('input.txt', 'obsolete.txt'), allowed_outputs=('output.txt', 'obsolete.txt'),
                    forbidden=('secret.txt',), requirements=('R1',), acceptance=('unit',), dependencies=(),
                    allowed_tools=('read_file', 'write_file', 'delete_file'), forbidden_tools=('shell',),
                    token_budget=0, wall_clock_budget_s=5, max_tool_calls=10, max_file_writes=5, memory_limit_mb=128)
        data.update(overrides)
        return WorkerContract(**data)

    def run_source(self, source, **overrides):
        contract = self.contract(**overrides)
        return contract, self.runtime.run(self.plan, self.approval, contract, source)

    def events(self):
        return [dict(obs.payload) for obs in self.journal.observations()]

    def wait_active(self):
        end = time.monotonic() + 15  # condition-based; generous margin only
        while time.monotonic() < end:
            if any(x['event'] == 'RuntimeSandboxReady' for x in self.events()):
                return
            time.sleep(0.01)
        self.fail('worker did not become ready')


class JournalTests(Fixture):
    def test_event_chain_survives_reopen_and_export(self):
        self.journal.observe({'event': 'first'})
        reopened = RuntimeJournal(self.journal.path, trace_id='test-run')
        reopened.observe({'event': 'second'})
        self.assertTrue(verify_chain(reopened.observations(), expected_count=2))
        output = self.root / 'events.jsonl'
        reopened.export_jsonl(output)
        self.assertEqual(len(output.read_text().splitlines()), 2)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            reopened.export_jsonl(output)

    def test_event_update_and_delete_are_rejected(self):
        self.journal.observe({'event': 'first'})
        with sqlite3.connect(self.journal.path) as db:
            for sql in ('UPDATE events SET record=\'{}\'', 'DELETE FROM events'):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)

    def test_other_run_is_rejected(self):
        with self.assertRaises(JournalError):
            RuntimeJournal(self.journal.path, trace_id='other-run')

    def test_journal_symlink_rejected(self):
        link = self.journal.path.parent / 'linked.db'
        link.symlink_to(self.journal.path)
        with self.assertRaises(OSError):
            RuntimeJournal(link, trace_id='test-run')

    def test_journal_world_readable_rejected(self):
        os.chmod(self.journal.path, 0o644)
        with self.assertRaises(JournalError):
            RuntimeJournal(self.journal.path, trace_id='test-run')

    def test_concurrent_observations_are_one_valid_chain(self):
        def emit(index):
            for count in range(8):
                self.journal.observe({'event': 'parallel', 'writer': index, 'number': count})
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(emit, range(4)))
        self.assertTrue(verify_chain(self.journal.observations(), expected_count=32))

    def test_claim_exclusive_and_terminal_generation_persists(self):
        c = self.contract()
        self.journal.claim(c, source_hash='a' * 64, approval=self.approval.to_dict())
        with self.assertRaises(JournalError):
            self.journal.claim(c, source_hash='a' * 64, approval=self.approval.to_dict())
        with self.assertRaises(JournalError):
            self.journal.claim(self.contract(), source_hash='a' * 64, approval=self.approval.to_dict())
        self.journal.finish(c, 'FAILED')
        reopened = RuntimeJournal(self.journal.path, trace_id='test-run')
        with self.assertRaises(JournalError):
            reopened.claim(c, source_hash='a' * 64, approval=self.approval.to_dict())
        newer = self.contract()
        reopened.claim(newer, source_hash='a' * 64, approval=self.approval.to_dict())
        self.assertTrue(reopened.lease_is_current(newer))

    def test_revocation_fences_candidate_commit(self):
        c = self.contract()
        self.journal.claim(c, source_hash='a' * 64, approval=self.approval.to_dict())
        self.journal.revoke(c.attempt_id)
        self.assertFalse(self.journal.lease_is_current(c))
        with self.assertRaises(JournalError):
            self.journal.finish(c, 'CANDIDATE')
        self.journal.finish(c, 'VIOLATED')


class WorkspaceTests(Fixture):
    def open_broker(self, c):
        worktree = ManagedWorktree(self.repo, self.root / 'work', c)
        worktree.create()
        self.addCleanup(worktree.discard)
        guard = AttemptGuard(c, observe=self.journal.observe, terminate=lambda: None)
        guard.start()
        broker = SafeFileBroker(worktree, guard)
        self.addCleanup(broker.close)
        return worktree, broker, guard

    def test_worktree_path_must_match_attempt(self):
        c = self.contract(workspace_root=str(self.repo))
        with self.assertRaises(WorkerContractError):
            ManagedWorktree(self.repo, self.root / 'work', c)

    def test_runtime_and_repository_must_be_disjoint(self):
        with self.assertRaises(WorkerContractError):
            ManagedWorktree(self.repo, self.repo / 'work', self.contract())

    def test_symlink_input_never_exposes_target(self):
        c = self.contract(inputs=('linked.txt',))
        wt, broker, guard = self.open_broker(c)
        (wt.path / 'linked.txt').symlink_to(self.repo / 'secret.txt')
        with self.assertRaises(ContractViolation):
            broker.dispatch('read_file', {'path': 'linked.txt'})
        self.assertEqual(guard.state, 'VIOLATED')
        self.assertNotIn('never disclose', json.dumps(self.events()))

    def test_symlink_write_does_not_truncate_target(self):
        c = self.contract()
        wt, broker, _ = self.open_broker(c)
        (wt.path / 'output.txt').symlink_to(self.repo / 'secret.txt')
        with self.assertRaises(ContractViolation):
            broker.dispatch('write_file', {'path': 'output.txt', 'content': 'bad'})
        self.assertEqual((self.repo / 'secret.txt').read_text(), 'never disclose')

    def test_symlink_parent_cannot_escape(self):
        c = self.contract(allowed_outputs=('nested/',))
        wt, broker, _ = self.open_broker(c)
        (wt.path / 'nested').symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(ContractViolation):
            broker.dispatch('write_file', {'path': 'nested/secret.txt', 'content': 'bad'})
        self.assertEqual((self.repo / 'secret.txt').read_text(), 'never disclose')

    def test_hardlink_write_does_not_truncate_target(self):
        wt, broker, _ = self.open_broker(self.contract())
        os.link(self.repo / 'secret.txt', wt.path / 'output.txt')
        with self.assertRaises(ContractViolation):
            broker.dispatch('write_file', {'path': 'output.txt', 'content': 'bad'})
        self.assertEqual((self.repo / 'secret.txt').read_text(), 'never disclose')

    def test_fifo_read_is_nonblocking_and_rejected(self):
        c = self.contract(inputs=('pipe',))
        wt, broker, _ = self.open_broker(c)
        os.mkfifo(wt.path / 'pipe')
        with self.assertRaises(ContractViolation):
            broker.dispatch('read_file', {'path': 'pipe'})

    def test_git_metadata_is_always_denied(self):
        c = self.contract(inputs=('.git',), allowed_outputs=('.git',))
        _, broker, _ = self.open_broker(c)
        with self.assertRaises(ContractViolation):
            broker.dispatch('read_file', {'path': '.git'})

    def test_large_project_file_rejected(self):
        c = self.contract(inputs=('large',))
        wt, broker, _ = self.open_broker(c)
        (wt.path / 'large').write_bytes(b'x' * (1024 * 1024 + 1))
        with self.assertRaises(ContractViolation):
            broker.dispatch('read_file', {'path': 'large'})


class ExecutionTests(Fixture):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'linux':
            raise unittest.SkipTest('Linux kernel required')
        source = json.dumps({'source': 'pass'}) + '\n' + '{"sequence":1,"ok":true}\n'
        probe = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'residual/factory/_sandbox_child.py'),
                                '128', '3', str(os.getpid())], input=source.encode(),
                               capture_output=True, timeout=5, env={'PATH': '/usr/bin:/bin'})
        if probe.returncode != 0 or b'SandboxReady' not in probe.stdout:
            if os.environ.get('RESIDUAL_REQUIRE_SECCOMP') == '1':
                raise AssertionError('required real seccomp backend is unavailable')
            raise unittest.SkipTest('libseccomp/kernel backend unavailable (no fallback)')

    def test_complete_candidate_preserves_source_and_is_not_receipt(self):
        c, result = self.run_source("write_file('output.txt', read_file('input.txt') + ' world')")
        self.assertEqual(result.status, 'CANDIDATE', result)
        self.assertTrue(result.process_reaped)
        self.assertEqual(result.candidate.status, 'UNTRUSTED_CANDIDATE')
        self.assertEqual(result.usage['tool_calls'], 2)
        self.assertEqual(result.usage['file_writes'], 1)
        self.assertEqual(result.usage['tokens'], 0)
        self.assertEqual((Path(c.workspace_root) / 'output.txt').read_text(), 'hello world')
        self.assertFalse((self.repo / 'output.txt').exists())
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD').decode().strip(), self.commit)
        with self.assertRaises(WorkerContractError):
            git(self.repo, 'cat-file', '-e', result.candidate.output_commit)
        output_blob = git(self.repo, 'hash-object', '--stdin', data=b'hello world').decode().strip()
        with self.assertRaises(WorkerContractError):
            git(self.repo, 'cat-file', '-e', output_blob)
        object_root = Path(c.workspace_root).parent / f'.{c.attempt_id}.objects'
        self.assertEqual(git(self.repo, 'cat-file', '-p', output_blob,
                             extra_env={'GIT_OBJECT_DIRECTORY': str(object_root)}), b'hello world')
        events = self.events()
        names = [e['event'] for e in events]
        self.assertLess(names.index('WorkerContractRecorded'), names.index('RuntimeProcessSpawned'))
        self.assertLess(names.index('RuntimeSandboxReady'), names.index('ToolAuthorized'))
        self.assertFalse(any('Receipt' in name for name in names))
        self.assertTrue(verify_chain(self.journal.observations()))
        self.runtime.purge(c)
        self.assertFalse(Path(c.workspace_root).exists())
        self.assertFalse((Path(c.workspace_root).parent / f'.{c.attempt_id}.objects').exists())

    def test_cli_runs_the_same_real_backend(self):
        c = self.contract()
        for name, value in [('plan', self.plan.to_dict()), ('approval', self.approval.to_dict()), ('contract', c.to_dict())]:
            (self.root / (name + '.json')).write_text(json.dumps(value))
        source = self.root / 'controller.py'
        source.write_text("write_file('output.txt','cli')")
        result = subprocess.run([sys.executable, '-m', 'residual.factory.runtime',
                                 '--repo', str(self.repo), '--runtime-root', str(self.root / 'work'),
                                 '--journal', str(self.journal.path), '--run-id', 'test-run',
                                 '--plan', str(self.root / 'plan.json'), '--approval', str(self.root / 'approval.json'),
                                 '--contract', str(self.root / 'contract.json'), '--source', str(source),
                                 '--allow-local-worker-code'], cwd=ROOT, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['status'], 'CANDIDATE')
        self.assertTrue(value['process_reaped'])
        self.assertEqual((Path(c.workspace_root) / 'output.txt').read_text(), 'cli')

    def test_delete_produces_tombstone_not_source_mutation(self):
        _, result = self.run_source("delete_file('obsolete.txt')")
        self.assertEqual(result.status, 'CANDIDATE', result)
        self.assertEqual(result.candidate.artifacts, (('obsolete.txt', None),))
        self.assertTrue((self.repo / 'obsolete.txt').exists())

    def test_execution_requires_opt_in(self):
        runtime = FactoryRuntime(self.repo, self.root / 'work', self.journal)
        with self.assertRaises(RuntimeUnavailable):
            runtime.run(self.plan, self.approval, self.contract(), 'pass')
        self.assertEqual(self.journal.attempts(), [])

    def test_wrong_approval_rejected_before_launch(self):
        approval = dataclasses.replace(self.approval, graph_hash='a' * 64)
        with self.assertRaises(ValueError):
            self.runtime.run(self.plan, approval, self.contract(), 'pass')
        self.assertEqual(self.journal.attempts(), [])

    def test_invalid_approval_identity_rejected(self):
        approval = dataclasses.replace(self.approval, approved_by='')
        with self.assertRaises(WorkerContractError):
            self.runtime.run(self.plan, approval, self.contract(), 'pass')

    def test_dependency_execution_is_fail_closed_without_receipt_admission(self):
        self.plan = ExecutionPlan('two', (Requirement('R1', 'one', ('unit',)),), (
            FactoryTask('parent', 'first', ('R1',)),
            FactoryTask('task1', 'second', ('R1',), depends_on=('parent',), swarm='swarm1')))
        self.approval = FrozenPlan.approve(self.plan, 'operator')
        with self.assertRaises(RuntimeUnavailable):
            self.runtime.run(self.plan, self.approval, self.contract(dependencies=('parent',)), 'pass')
        self.assertEqual(self.journal.attempts(), [])

    def test_cloud_only_placement_is_not_silently_local(self):
        with self.assertRaises(RuntimeUnavailable):
            self.runtime.run(self.plan, self.approval, self.contract(engine_class='cloud'), 'pass')

    def test_worker_does_not_inherit_provider_credentials(self):
        with patch.dict(os.environ, {'RESIDUAL_TEST_SECRET': 'DO-NOT-LEAK'}):
            c, result = self.run_source("import os\nwrite_file('output.txt', str(dict(os.environ)))")
        self.assertEqual(result.status, 'CANDIDATE', result)
        self.assertNotIn('DO-NOT-LEAK', (Path(c.workspace_root) / 'output.txt').read_text())

    def test_unauthorized_broker_read_terminates_and_discards(self):
        c, result = self.run_source("read_file('secret.txt')")
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'inputs'))
        self.assertTrue(result.process_reaped)
        self.assertFalse(Path(c.workspace_root).exists())
        self.assertNotIn('never disclose', json.dumps(self.events()))

    def test_unauthorized_broker_write_terminates_and_preserves_source(self):
        _, result = self.run_source("write_file('secret.txt', 'bad')")
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'allowed_outputs'))
        self.assertEqual((self.repo / 'secret.txt').read_text(), 'never disclose')

    def test_tool_limit_enforced_before_dispatch(self):
        _, result = self.run_source("write_file('output.txt','x')", max_tool_calls=0)
        self.assertEqual(result.reason, 'max_tool_calls')
        self.assertEqual(result.status, 'VIOLATED')

    def test_write_limit_enforced_before_mutation(self):
        _, result = self.run_source("write_file('output.txt','x')", max_file_writes=0)
        self.assertEqual(result.reason, 'max_file_writes')
        self.assertEqual(result.status, 'VIOLATED')

    def test_raw_file_syscall_is_kernel_killed(self):
        c, result = self.run_source("open('/etc/passwd').read()")
        self.assertEqual(result.returncode, -signal.SIGSYS)
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'os_syscall_allowlist'))
        self.assertEqual(result.termination['classification'], 'kernel_sigsys')
        self.assertIsNone(result.termination['requested_by'])
        self.assertEqual(result.termination['correlation_id'], c.attempt_id)
        self.assertEqual(result.termination['observed_signal'], signal.SIGSYS)
        self.assertFalse(Path(c.workspace_root).exists())

    def test_raw_network_syscall_is_kernel_killed(self):
        _, result = self.run_source("import ctypes\nctypes.CDLL(None).socket(2, 1, 0)")
        self.assertEqual(result.returncode, -signal.SIGSYS)
        self.assertEqual(result.status, 'VIOLATED')

    def test_process_creation_is_kernel_killed(self):
        _, result = self.run_source("import os\nos.fork()")
        self.assertEqual(result.returncode, -signal.SIGSYS)
        self.assertTrue(result.process_reaped)

    def test_exec_is_kernel_killed(self):
        _, result = self.run_source("import os\nos.execv('/bin/true', ['true'])")
        self.assertEqual(result.returncode, -signal.SIGSYS)

    def test_ptrace_is_kernel_killed(self):
        _, result = self.run_source("import ctypes\nctypes.CDLL(None).ptrace(0,0,0,0)")
        self.assertEqual(result.returncode, -signal.SIGSYS)

    def test_thread_creation_is_kernel_killed(self):
        _, result = self.run_source("import _thread\n_thread.start_new_thread(lambda: None, ())")
        self.assertEqual(result.returncode, -signal.SIGSYS)

    def test_forbidden_tool_protocol_is_terminal(self):
        message = json.dumps({'sequence': 1, 'operation': 'shell', 'arguments': {}}).encode() + b'\n'
        _, result = self.run_source(f"import os,time\nos.write(1,{message!r})\ntime.sleep(2)")
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'allowed_tools'))

    def test_replayed_request_is_terminal(self):
        message = json.dumps({'sequence': 1, 'operation': 'read_file', 'arguments': {'path': 'input.txt'}}).encode() + b'\n'
        _, result = self.run_source(f"import os,time\nos.write(1,{message * 2!r})\ntime.sleep(2)")
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'broker_protocol'))

    def test_early_exit_cannot_claim_candidate(self):
        _, result = self.run_source('import os\nos._exit(0)')
        self.assertEqual(result.status, 'FAILED')
        self.assertIsNone(result.candidate)

    def test_wall_clock_kills_noncooperative_worker(self):
        c, result = self.run_source('while True: pass', wall_clock_budget_s=0.2)
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'wall_clock_budget_s'))
        self.assertTrue(result.process_reaped)
        self.assertEqual(result.returncode, -signal.SIGKILL)
        self.assertEqual(result.termination['classification'], 'watchdog_wall_clock')
        self.assertEqual(result.termination['requested_by'], 'watchdog')
        self.assertEqual(result.termination['observed_signal'], signal.SIGKILL)
        self.assertFalse(Path(c.workspace_root).exists())

    def test_external_sigkill_remains_unknown(self):
        c = self.contract(wall_clock_budget_s=30)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.runtime.run, self.plan, self.approval, c, 'while True: pass')
            self.wait_active()
            with self.runtime._lock:
                control = self.runtime._active[c.attempt_id]
            signal.pidfd_send_signal(control.pidfd, signal.SIGKILL)
            result = future.result(timeout=5)
        self.assertEqual(result.returncode, -signal.SIGKILL)
        self.assertTrue(result.termination['classification'].startswith('unknown_sigkill'))
        self.assertIsNone(result.termination['requested_by'])
        self.assertEqual(result.termination['observed_signal'], signal.SIGKILL)

    def test_virtual_memory_limit_prevents_large_allocation(self):
        _, result = self.run_source("x=bytearray(256*1024*1024)", memory_limit_mb=64)
        self.assertNotEqual(result.status, 'CANDIDATE')
        self.assertTrue(result.process_reaped)
        self.assertIsNone(result.candidate)

    def test_oversized_protocol_frame_terminates(self):
        _, result = self.run_source("import os\nos.write(1,b'x'*(3*1024*1024))")
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'protocol_frame_bytes'))

    def test_cancellation_reaps_real_process(self):
        c = self.contract()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.runtime.run, self.plan, self.approval, c, 'while True: pass')
            self.wait_active()
            self.assertTrue(self.runtime.cancel(c.attempt_id))
            result = future.result(timeout=5)
        self.assertEqual(result.status, 'CANCELLED', result)
        self.assertTrue(result.process_reaped)
        self.assertFalse(Path(c.workspace_root).exists())

    def test_durable_revocation_reaps_real_process(self):
        c = self.contract()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.runtime.run, self.plan, self.approval, c, 'while True: pass')
            self.wait_active()
            second = RuntimeJournal(self.journal.path, trace_id='test-run')
            second.revoke(c.attempt_id)
            result = future.result(timeout=5)
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'lease_generation'))
        self.assertTrue(result.process_reaped)

    def test_lease_revocation_kills_with_lease_generation(self):
        # A durably revoked lease must terminate the worker with the typed
        # primary reason ('lease', 'lease_generation') — never retyped.
        c = self.contract()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.runtime.run, self.plan, self.approval, c, 'while True: pass')
            self.wait_active()
            second = RuntimeJournal(self.journal.path, trace_id='test-run')
            second.revoke(c.attempt_id)
            result = future.result(timeout=15)
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'lease_generation'))
        violations = [e for e in self.events() if e['event'] == 'ContractViolation']
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]['boundary'], 'lease')
        self.assertEqual(violations[0]['field'], 'lease_generation')
        self.assertTrue(result.process_reaped)

    def test_audit_error_prevents_launch(self):
        original = self.journal.observe
        def refuse(payload):
            if payload['event'] == 'WorkerContractRecorded':
                raise OSError('test disk error')
            original(payload)
        with patch.object(self.journal, 'observe', side_effect=refuse):
            _, result = self.run_source("write_file('output.txt','no')")
        self.assertEqual(result.status, 'AUDIT_FAILED')
        self.assertIsNone(result.returncode)
        self.assertFalse(any(x['event'] == 'RuntimeProcessSpawned' for x in self.events()))

    def test_missing_seccomp_never_receives_worker_source(self):
        bootstrap_dir = self.root / 'unavailable'
        bootstrap_dir.mkdir()
        child = (ROOT / 'residual/factory/_sandbox_child.py').read_text()
        (bootstrap_dir / '_sandbox_child.py').write_text(child.replace('libseccomp.so.2', 'lib-not-installed.so'))
        with patch('residual.factory.runtime.__file__', str(bootstrap_dir / 'runtime.py')):
            _, result = self.run_source("write_file('output.txt', 'must-not-run')")
        self.assertEqual(result.status, 'FAILED')
        self.assertIsNone(result.candidate)
        self.assertFalse(any(e['event'] == 'RuntimeSandboxReady' for e in self.events()))
        self.assertFalse(any(e['event'] == 'ToolAuthorized' for e in self.events()))

    def test_watchdog_termination_is_independent_of_blocked_audit_callback(self):
        entered, release = threading.Event(), threading.Event()
        original = self.journal.observe

        def blocked(payload):
            if payload['event'] == 'PathAuthorized':
                entered.set()
                release.wait(3)
            original(payload)

        def deterministic_clock_ns():
            return 31_000_000_000 if entered.is_set() else 0

        runtime = FactoryRuntime(self.repo, self.root / 'work', self.journal,
                                 allow_local_worker_code=True,
                                 monotonic_ns=deterministic_clock_ns,
                                 clock=lambda: 31.0 if entered.is_set() else 0.0)
        c = self.contract(wall_clock_budget_s=30)
        with patch.object(self.journal, 'observe', side_effect=blocked), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(runtime.run, self.plan, self.approval, c, "write_file('output.txt','no')")
            self.assertTrue(entered.wait(10), 'worker never reached deterministic PathAuthorized barrier')
            try:
                control = None
                for _ in range(200):
                    with runtime._lock:
                        control = runtime._active.get(c.attempt_id)
                    if control is not None and control.stopped.wait(.01):
                        break
                self.assertIsNotNone(control)
                self.assertTrue(control.stopped.is_set())
                self.assertFalse((Path(c.workspace_root) / 'output.txt').exists())
            finally:
                release.set()
            result = future.result(timeout=5)
        self.assertEqual((result.status, result.reason), ('VIOLATED', 'wall_clock_budget_s'), result)
        self.assertTrue(result.process_reaped)
        self.assertEqual(result.termination['classification'], 'watchdog_wall_clock')
        self.assertEqual(result.termination['requested_by'], 'watchdog')

    def test_purge_expired_uses_configured_retention(self):
        c, result = self.run_source('pass')
        self.assertEqual(result.status, 'CANDIDATE')
        updated = self.journal.attempts()[0]['updated_ns']
        self.assertEqual(self.runtime.purge_expired(now_ns=updated + 100), [])
        self.assertEqual(self.runtime.purge_expired(now_ns=updated + 3600 * 10**9 + 1), [c.attempt_id])
        self.assertFalse(Path(c.workspace_root).exists())

    def test_two_swarms_have_distinct_workers_and_worktrees(self):
        self.plan = ExecutionPlan('parallel', (Requirement('R1', 'one', ('unit',)), Requirement('R2', 'two', ('unit',))),
                                  (FactoryTask('task1', 'one', ('R1',), swarm='swarm1'),
                                   FactoryTask('task2', 'two', ('R2',), swarm='swarm2')))
        self.approval = FrozenPlan.approve(self.plan, 'operator')
        c1 = self.contract()
        c2 = self.contract(task_id='task2', swarm_id='swarm2', requirements=('R2',),
                           workspace_root=str(self.root / 'work' / 'swarm2' / 'attempt2'))
        workers = [(c1, "import time\ntime.sleep(.2)\nwrite_file('output.txt','one')"),
                   (c2, "import time\ntime.sleep(.2)\nwrite_file('output.txt','two')")]
        results = self.runtime.run_many(self.plan, self.approval, workers, capacity=2)
        self.assertEqual([x.status for x in results], ['CANDIDATE', 'CANDIDATE'], results)
        self.assertEqual((Path(c1.workspace_root) / 'output.txt').read_text(), 'one')
        self.assertEqual((Path(c2.workspace_root) / 'output.txt').read_text(), 'two')
        self.assertEqual(len({r['pid'] for r in self.journal.attempts()}), 2)


if __name__ == '__main__':
    unittest.main()
