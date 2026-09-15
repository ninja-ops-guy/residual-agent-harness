"""Opt-in, local Linux execution for independent Factory worker contracts.

This backend runs brokered Python worker controllers, not arbitrary shells or
SDK agents. It produces quarantined CANDIDATES only: no Station receipt, merge,
network inference, or dependency acceptance is implied by successful execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import selectors
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from residual.core import canonical, strict_json
from .models import ExecutionPlan, FrozenPlan
from .runtime_journal import JournalError, RuntimeJournal
from .runtime_workspace import CandidateTree, ManagedWorktree, SafeFileBroker
from .termination_provenance import ProcessControl
from .worker_contract import AttemptGuard, ContractViolation, WorkerContract, WorkerContractError

PROFILE = 'linux-seccomp-broker-v1'
MAX_FRAME = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 256 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class RuntimeUnavailable(WorkerContractError):
    pass


@dataclass(frozen=True)
class RuntimeResult:
    attempt_id: str
    status: str
    contract_hash: str
    execution_plan_hash: str
    returncode: int | None
    process_reaped: bool
    usage: dict[str, int]
    candidate: CandidateTree | None
    reason: str
    termination: dict[str, Any] | None = None
    engine_name: str = 'brokered-python'
    engine_version: str = PROFILE

    def to_dict(self) -> dict[str, Any]:
        return {**vars(self), 'candidate': self.candidate.to_dict() if self.candidate else None}


class FactoryRuntime:
    def __init__(self, repository: str | Path, runtime_root: str | Path,
                 journal: RuntimeJournal, *, allow_local_worker_code: bool = False,
                 monotonic_ns=time.monotonic_ns):
        if sys.platform != 'linux':
            raise RuntimeUnavailable('the brokered execution backend requires Linux')
        self.repository, self.root = Path(repository).absolute(), Path(runtime_root).absolute()
        self.journal = journal
        self.enabled = allow_local_worker_code is True
        self._monotonic_ns = monotonic_ns
        self._lock = threading.Lock()
        self._active: dict[str, ProcessControl] = {}

    def cancel(self, attempt_id: str) -> bool:
        with self._lock:
            control = self._active.get(attempt_id)
        if control is None:
            return False
        control.kill(('cancellation', 'operator_cancel', {'reason': 'local_operator'}), requester='operator')
        try:
            self.journal.revoke(attempt_id)  # serialize cancellation against candidate publication
        except JournalError:
            return False  # already terminal; do not claim a completed candidate was cancelled
        return True

    def _watch(self, control: ProcessControl, contract: WorkerContract,
               started_ns: int, done: threading.Event) -> None:
        memory_at_ns = lease_at_ns = 0
        while not done.wait(0.02):
            if control.termination_requested.is_set() or control.exited():
                return
            now_ns = self._monotonic_ns()
            reason = None
            elapsed_s = (now_ns - started_ns) / 1_000_000_000
            if elapsed_s >= contract.wall_clock_budget_s:
                reason = ('resource', 'wall_clock_budget_s', {'elapsed_s': elapsed_s})
            elif now_ns >= memory_at_ns:
                memory_at_ns = now_ns + 1_000_000_000
                try:
                    fields = Path(f'/proc/{control.process.pid}/statm').read_text().split()
                    resident = int(fields[1]) * os.sysconf('SC_PAGE_SIZE')
                    if resident > contract.memory_limit_mb * 1024 * 1024:
                        reason = ('resource', 'memory_limit_mb', {'resident_bytes': resident})
                except (OSError, ValueError, IndexError):
                    if not control.exited():
                        reason = ('resource', 'memory_limit_mb', {'reason': 'rss_meter_unavailable'})
            if reason is None and now_ns >= lease_at_ns:
                lease_at_ns = now_ns + 200_000_000
                # A broker/guard path may have started killing the worker after the
                # top-of-loop check. Do not perform a secondary lease read in that
                # window and accidentally overwrite the primary violation reason.
                if control.termination_requested.is_set():
                    return
                try:
                    current = self.journal.lease_is_current(contract)
                except Exception:
                    current = False
                if not current:
                    reason = ('lease', 'lease_generation', {'reason': 'revoked_or_unavailable'})
            if reason is not None:
                control.kill(reason, requester='watchdog')
                return

    def run(self, plan: ExecutionPlan, approval: FrozenPlan,
            contract: WorkerContract, source: str) -> RuntimeResult:
        if not self.enabled:
            raise RuntimeUnavailable('local worker execution requires explicit opt-in')
        if not isinstance(plan, ExecutionPlan) or not isinstance(approval, FrozenPlan):
            raise WorkerContractError('existing ExecutionPlan and FrozenPlan are required')
        # Detach caller-owned mutable structures before binding and execution.
        plan = ExecutionPlan.from_dict(strict_json(canonical(plan.to_dict())))
        approval.assert_matches(plan)
        if approval.schema_version != 'factory-approval-v1' or not isinstance(approval.approved_by, str) or not approval.approved_by.strip():
            raise WorkerContractError('invalid local approval record')
        stamp = datetime.fromisoformat(approval.approved_at)
        if stamp.tzinfo is None:
            raise WorkerContractError('approval timestamp requires a timezone')
        contract.assert_matches_plan(plan)
        if contract.dependencies:
            raise RuntimeUnavailable('dependent tasks require the forthcoming Station receipt admission gate')
        if contract.engine_class == 'cloud':
            raise RuntimeUnavailable('this backend is local and cannot satisfy cloud-only placement')
        if contract.memory_limit_mb < 64:
            raise RuntimeUnavailable('brokered CPython needs at least a 64 MiB address-space ceiling')
        if not isinstance(source, str) or len(source.encode('utf-8')) > MAX_SOURCE_BYTES:
            raise WorkerContractError('worker source must be text within the source byte limit')
        workspace = ManagedWorktree(self.repository, self.root, contract)
        source_hash = hashlib.sha256(source.encode()).hexdigest()
        self.journal.claim(contract, source_hash=source_hash, approval=approval.to_dict())

        process = control = broker = watcher = None
        done = threading.Event()
        guard = AttemptGuard(
            contract,
            observe=self.journal.observe,
            terminate=lambda: control.kill(
                ('guard', 'contract_violation', {'reason': 'guard_stop_hook'}), requester='guard'
            ) if control is not None else None,
        )
        state, reason, candidate = 'FAILED', 'launch_failed', None
        reaped = False
        termination = None
        journal_finished = False
        try:
            workspace.create()
            self.journal.observe({'event': 'RuntimeWorktreeCreated', 'attempt_id': contract.attempt_id,
                                  'correlation_id': contract.attempt_id,
                                  'monotonic_ns': self._monotonic_ns(),
                                  'input_commit': contract.input_commit, 'contract_hash': contract.contract_hash})
            guard.start()  # durable contract acknowledgement BEFORE Popen
            def before_io():
                guard.check_deadline()
                if control is not None and control.reason is not None:
                    guard.fail(*control.reason)
                if not self.journal.lease_is_current(contract):
                    guard.fail('lease', 'lease_generation', {'reason': 'fenced_before_io'})
            broker = SafeFileBroker(workspace, guard, before_io=before_io)
            started_ns = self._monotonic_ns()
            bootstrap = Path(__file__).with_name('_sandbox_child.py').resolve()
            process = subprocess.Popen(
                [sys.executable, '-I', '-S', str(bootstrap), str(contract.memory_limit_mb),
                 str(contract.wall_clock_budget_s), str(os.getpid())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'},
                cwd='/', close_fds=True, start_new_session=True, bufsize=0)
            control = ProcessControl(process, correlation_id=contract.attempt_id,
                                     clock_ns=self._monotonic_ns)
            # Start the watchdog before persistence/dispatch, not in the worker.
            watcher = threading.Thread(target=self._watch, args=(control, contract, started_ns, done), daemon=True)
            watcher.start()
            with self._lock:
                self._active[contract.attempt_id] = control
            self.journal.started(contract, process.pid)
            self.journal.observe({'event': 'RuntimeProcessIdentity',
                                  'attempt_id': contract.attempt_id,
                                  'correlation_id': contract.attempt_id,
                                  'monotonic_ns': self._monotonic_ns(),
                                  'identity': control.identity.to_dict()})
            complete = self._exchange(process, control, guard, broker, contract, source)
            control.reap(timeout=2)
            reaped = True
            termination = control.termination_record().to_dict()
            done.set()
            watcher.join(timeout=2)
            if watcher.is_alive():
                raise WorkerContractError('watchdog did not stop')
            if control.reason is not None:
                boundary, field, action = control.reason
                if boundary == 'cancellation':
                    guard.cancel()
                    state, reason = 'CANCELLED', field
                else:
                    guard.fail(boundary, field, action)
            elif process.returncode == -signal.SIGSYS:
                guard.fail('tool', 'os_syscall_allowlist',
                           {'reason': 'kernel_seccomp_kill', 'signal': signal.SIGSYS,
                            'syscall_attribution': 'unavailable', 'profile': PROFILE})
            elif process.returncode != 0 or not complete:
                reason = 'worker_failed_or_incomplete'
                guard.cancel()
            else:
                if not self.journal.lease_is_current(contract):
                    guard.fail('lease', 'lease_generation', {'reason': 'stale_before_capture'})
                candidate = workspace.capture(broker)
                guard.finish()
                state, reason = 'CANDIDATE', 'awaiting_station_verification'
            self.journal.finish(contract, state, reason=reason, process_reaped=reaped,
                                returncode=process.returncode, usage=guard.usage,
                                termination=termination,
                                candidate=candidate.to_dict() if candidate else None)
            journal_finished = True
        except ContractViolation as exc:
            state, reason, candidate = 'VIOLATED', exc.observation['field'], None
        except Exception as exc:
            # Audit failures never publish candidates. Expose an error class, not
            # exception text that may contain operator paths or untrusted content.
            state = 'AUDIT_FAILED' if guard.state == 'AUDIT_FAILED' else 'FAILED'
            reason, candidate = type(exc).__name__, None
            if control is not None and control.reason is not None and control.reason[0] == 'cancellation':
                state, reason = 'CANCELLED', 'operator_cancel'
        finally:
            if control is not None:
                if not control.reaped:
                    if control.exited():
                        control.reap(timeout=2)
                    else:
                        control.kill(('runtime', 'finalizer', {'reason': 'ensure_reaped'}), requester='runtime')
                reaped = control.reaped
                termination = control.termination_record().to_dict()
            elif process is not None:
                # A failure before ProcessControl ownership is established is the
                # only fallback path allowed to consume this PID directly.
                process.kill()
                process.wait(timeout=2)
                reaped = True
            done.set()
            if watcher is not None:
                watcher.join(timeout=2)
            with self._lock:
                self._active.pop(contract.attempt_id, None)
            if control is not None:
                control.close()
            if broker is not None:
                broker.close()
            if process is not None:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
            if state != 'CANDIDATE':
                workspace.discard()
            if not journal_finished:
                # If the durable store is unavailable this raises instead of
                # falsely claiming a persisted terminal record.
                self.journal.finish(contract, state, reason=reason, process_reaped=reaped,
                                    returncode=process.returncode if process else None,
                                    usage=guard.usage, termination=termination)
        return RuntimeResult(contract.attempt_id, state, contract.contract_hash, plan.graph_hash,
                             process.returncode if process else None, reaped, guard.usage,
                             candidate, reason, termination)

    def _exchange(self, process, control, guard, broker, contract, source) -> bool:
        incoming, outgoing = bytearray(), bytearray()
        ready = completed = False
        expected, total = 1, 0
        with selectors.DefaultSelector() as selector:
            for stream, label in ((process.stdout, 'out'), (process.stderr, 'err')):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, label)
            os.set_blocking(process.stdin.fileno(), False)

            def queue(value):
                frame = canonical(value).encode() + b'\n'
                if len(frame) > MAX_FRAME or len(outgoing) + len(frame) > MAX_FRAME:
                    guard.fail('resource', 'protocol_frame_bytes', {'reason': 'reply_limit'})
                outgoing.extend(frame)
                try:
                    selector.register(process.stdin, selectors.EVENT_WRITE, 'in')
                except KeyError:
                    pass

            while selector.get_map():
                if control.reason is not None:
                    return False
                for key, _ in selector.select(timeout=0.02):
                    if key.data == 'in':
                        try:
                            count = os.write(key.fd, outgoing)
                        except BrokenPipeError:
                            selector.unregister(key.fileobj)
                            outgoing.clear()
                            continue
                        del outgoing[:count]
                        if not outgoing:
                            selector.unregister(key.fileobj)
                        continue
                    data = os.read(key.fd, 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(data)
                    if total > MAX_OUTPUT_BYTES:
                        guard.fail('resource', 'protocol_output_bytes', {'bytes': total})
                    if key.data == 'err':
                        continue  # never copy untrusted stderr into the observation ledger
                    incoming.extend(data)
                    if len(incoming) > MAX_FRAME:
                        guard.fail('resource', 'protocol_frame_bytes', {'bytes': len(incoming)})
                    while b'\n' in incoming:
                        line, _, remainder = incoming.partition(b'\n')
                        incoming[:] = remainder
                        try:
                            value = strict_json(line.decode('utf-8'))
                            if not isinstance(value, dict):
                                raise ValueError('not an object')
                        except (ValueError, UnicodeError):
                            guard.fail('tool', 'broker_protocol', {'reason': 'invalid_json'})
                        if not ready:
                            if value != {'event': 'SandboxReady', 'profile': PROFILE}:
                                guard.fail('tool', 'sandbox_handshake', {'reason': 'not_ready'})
                            ready = True
                            self.journal.observe({'event': 'RuntimeSandboxReady',
                                                  'attempt_id': contract.attempt_id,
                                                  'correlation_id': contract.attempt_id,
                                                  'monotonic_ns': self._monotonic_ns(),
                                                  'profile': PROFILE,
                                                  'contract_hash': contract.contract_hash})
                            queue({'source': source})
                            continue
                        if completed or set(value) != {'sequence', 'operation', 'arguments'} or \
                                type(value.get('sequence')) is not int or value['sequence'] != expected or \
                                not isinstance(value.get('operation'), str) or not isinstance(value.get('arguments'), dict):
                            guard.fail('tool', 'broker_protocol', {'reason': 'invalid_or_replayed_request'})
                        expected += 1
                        if not self.journal.lease_is_current(contract):
                            guard.fail('lease', 'lease_generation', {'reason': 'revoked_before_dispatch'})
                        if value['operation'] == '__complete__':
                            if value['arguments']:
                                guard.fail('tool', 'broker_protocol', {'reason': 'invalid_completion'})
                            completed, result = True, None
                        else:
                            result = broker.dispatch(value['operation'], value['arguments'])
                        queue({'sequence': value['sequence'], 'ok': True, 'result': result})
                if control.exited() and all(key.data == 'in' for key in selector.get_map().values()):
                    break
        if incoming:
            guard.fail('tool', 'broker_protocol', {'reason': 'unterminated_frame'})
        return ready and completed

    def run_many(self, plan: ExecutionPlan, approval: FrozenPlan,
                 workers: list[tuple[WorkerContract, str]], *, capacity: int = 2) -> list[RuntimeResult]:
        if type(capacity) is not int or not 1 <= capacity <= 32:
            raise WorkerContractError('capacity must be between 1 and 32')
        self.journal.observe({'event': 'RuntimeCapacitySelected', 'execution_plan_hash': plan.graph_hash,
                              'capacity': capacity, 'policy': 'fixed-local-root-tasks-v1'})
        with ThreadPoolExecutor(max_workers=capacity) as pool:
            futures = [pool.submit(self.run, plan, approval, contract, source) for contract, source in workers]
            return [future.result() for future in futures]

    def purge(self, contract: WorkerContract) -> None:
        rows = [row for row in self.journal.attempts() if row['attempt_id'] == contract.attempt_id]
        if len(rows) != 1 or rows[0]['contract_hash'] != contract.contract_hash or rows[0]['state'] != 'CANDIDATE':
            raise WorkerContractError('only an exact quarantined candidate can be purged')
        workspace = ManagedWorktree(self.repository, self.root, contract)
        workspace.created = True
        workspace.discard()
        self.journal.mark_purged(contract.attempt_id)

    def purge_expired(self, *, retention_s: float = 3600, now_ns: int | None = None) -> list[str]:
        if type(retention_s) not in (int, float) or not math.isfinite(retention_s) or retention_s <= 0:
            raise WorkerContractError('retention must be positive and finite')
        now_ns = time.time_ns() if now_ns is None else now_ns
        if type(now_ns) is not int or now_ns < 0:
            raise WorkerContractError('invalid retention clock')
        purged = []
        for row in self.journal.attempts():
            if row['state'] == 'CANDIDATE' and row['updated_ns'] + int(retention_s * 1e9) <= now_ns:
                contract = WorkerContract.from_dict(strict_json(row['contract_json']))
                self.purge(contract)
                purged.append(contract.attempt_id)
        return purged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Opt-in M2 brokered worker execution; candidates only')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--runtime-root', required=True)
    parser.add_argument('--journal', required=True)
    parser.add_argument('--run-id', '--trace-id', dest='run_id', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--approval', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--allow-local-worker-code', action='store_true')
    args = parser.parse_args(argv)
    try:
        plan = ExecutionPlan.from_dict(strict_json(Path(args.plan).read_text()))
        approval = FrozenPlan.from_dict(strict_json(Path(args.approval).read_text()))
        contract = WorkerContract.from_dict(strict_json(Path(args.contract).read_text()))
        journal = RuntimeJournal(args.journal, trace_id=args.run_id)
        runtime = FactoryRuntime(args.repo, args.runtime_root, journal,
                                 allow_local_worker_code=args.allow_local_worker_code)
        result = runtime.run(plan, approval, contract, Path(args.source).read_text())
        print(canonical(result.to_dict()))
        return 0 if result.status == 'CANDIDATE' else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(canonical({'status': 'blocked', 'error_type': type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
