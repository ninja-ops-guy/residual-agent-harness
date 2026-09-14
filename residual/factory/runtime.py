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
    engine_name: str = 'brokered-python'
    engine_version: str = PROFILE

    def to_dict(self) -> dict[str, Any]:
        return {**vars(self), 'candidate': self.candidate.to_dict() if self.candidate else None}


class _ProcessControl:
    """Kill is independent of guard/journal locks; audit follows OS termination."""
    def __init__(self, process: subprocess.Popen):
        self.process = process
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise RuntimeUnavailable('pidfd-based process ownership is required')
        self.pidfd = os.pidfd_open(process.pid, 0)
        self._lock = threading.Lock()
        self.reason: tuple[str, str, dict] | None = None
        self.termination_requested = threading.Event()
        self.stopped = threading.Event()

    def kill(self, reason: tuple[str, str, dict] | None = None) -> None:
        # Mark termination intent before waiting on the process. The watchdog uses
        # this to avoid replacing a primary broker/contract violation with a
        # secondary lease-read failure while another thread is already terminating
        # the attempt.
        self.termination_requested.set()
        with self._lock:
            if reason is not None and self.reason is None:
                self.reason = reason
            if self.process.poll() is None:
                try:
                    signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=2)
            self.stopped.set()

    def close(self) -> None:
        with self._lock:
            if self.pidfd >= 0:
                os.close(self.pidfd)
                self.pidfd = -1


class FactoryRuntime:
    def __init__(self, repository: str | Path, runtime_root: str | Path,
                 journal: RuntimeJournal, *, allow_local_worker_code: bool = False):
        if sys.platform != 'linux':
            raise RuntimeUnavailable('the brokered execution backend requires Linux')
        self.repository, self.root = Path(repository).absolute(), Path(runtime_root).absolute()
        self.journal = journal
        self.enabled = allow_local_worker_code is True
        self._lock = threading.Lock()
        self._active: dict[str, _ProcessControl] = {}

    def cancel(self, attempt_id: str) -> bool:
        with self._lock:
            control = self._active.get(attempt_id)
        if control is None:
            return False
        control.kill(('cancellation', 'operator_cancel', {'reason': 'local_operator'}))
        try:
            self.journal.revoke(attempt_id)  # serialize cancellation against candidate publication
        except JournalError:
            return False  # already terminal; do not claim a completed candidate was cancelled
        return True

    def _watch(self, control: _ProcessControl, contract: WorkerContract,
               started: float, done: threading.Event) -> None:
        memory_at = lease_at = 0.0
        while not done.wait(0.02):
            if control.termination_requested.is_set() or control.process.poll() is not None:
                return
            now = time.monotonic()
            reason = None
            if now - started >= contract.wall_clock_budget_s:
                reason = ('resource', 'wall_clock_budget_s', {'elapsed_s': now - started})
            elif now >= memory_at:
                memory_at = now + 1.0
                try:
                    fields = Path(f'/proc/{control.process.pid}/statm').read_text().split()
                    resident = int(fields[1]) * os.sysconf('SC_PAGE_SIZE')
                    if resident > contract.memory_limit_mb * 1024 * 1024:
                        reason = ('resource', 'memory_limit_mb', {'resident_bytes': resident})
                except (OSError, ValueError, IndexError):
                    if control.process.poll() is None:
                        reason = ('resource', 'memory_limit_mb', {'reason': 'rss_meter_unavailable'})
            if reason is None and now >= lease_at:
                lease_at = now + 0.2
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
                control.kill(reason)
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
        guard = AttemptGuard(contract, observe=self.journal.observe,
                             terminate=lambda: control.kill() if control is not None else None)
        state, reason, candidate = 'FAILED', 'launch_failed', None
        reaped = False
        journal_finished = False
        try:
            workspace.create()
            self.journal.observe({'event': 'RuntimeWorktreeCreated', 'attempt_id': contract.attempt_id,
                                  'input_commit': contract.input_commit, 'contract_hash': contract.contract_hash})
            guard.start()  # durable contract acknowledgement BEFORE Popen
            def before_io():
                guard.check_deadline()
                if control is not None and control.reason is not None:
                    guard.fail(*control.reason)
                if not self.journal.lease_is_current(contract):
                    guard.fail('lease', 'lease_generation', {'reason': 'fenced_before_io'})
            broker = SafeFileBroker(workspace, guard, before_io=before_io)
            started = time.monotonic()
            bootstrap = Path(__file__).with_name('_sandbox_child.py').resolve()
            process = subprocess.Popen(
                [sys.executable, '-I', '-S', str(bootstrap), str(contract.memory_limit_mb),
                 str(contract.wall_clock_budget_s), str(os.getpid())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'},
                cwd='/', close_fds=True, start_new_session=True, bufsize=0)
            control = _ProcessControl(process)
            # Start the watchdog before persistence/dispatch, not in the worker.
            watcher = threading.Thread(target=self._watch, args=(control, contract, started, done), daemon=True)
            watcher.start()
            with self._lock:
                self._active[contract.attempt_id] = control
            self.journal.started(contract, process.pid)
            complete = self._exchange(process, control, guard, broker, contract, source)
            reaped = process.poll() is not None
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
                control.kill()
                reaped = process.poll() is not None
            elif process is not None:
                # Bootstrap failure before a pidfd/control was available. No
                # worker source has been sent and no other reaper owns this PID.
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
                    stream.close()
            if state != 'CANDIDATE':
                workspace.discard()
            if not journal_finished:
                # If the durable store is unavailable this raises instead of
                # falsely claiming a persisted terminal record.
                self.journal.finish(contract, state, reason=reason, process_reaped=reaped,
                                    returncode=process.returncode if process else None, usage=guard.usage)
        return RuntimeResult(contract.attempt_id, state, contract.contract_hash, plan.graph_hash,
                             process.returncode if process else None, reaped, guard.usage, candidate, reason)

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
                            self.journal.observe({'event': 'RuntimeSandboxReady', 'attempt_id': contract.attempt_id,
                                                  'profile': PROFILE, 'contract_hash': contract.contract_hash})
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
                if process.poll() is not None and all(key.data == 'in' for key in selector.get_map().values()):
                    break
            process.wait(timeout=2)
        if incoming:
            guard.fail('tool', 'broker_protocol', {'reason': 'unterminated_frame'})
        return ready and completed

    def run_many(self, plan: ExecutionPlan, approval: FrozenPlan,
                 workers: list[tuple[WorkerContract, str]], *, capacity: int = 2) -> list[RuntimeResult]:
        if not workers:
            return []
        if type(capacity) is not int or capacity < 1 or capacity > 32:
            raise WorkerContractError('capacity must be between 1 and 32')
        with ThreadPoolExecutor(max_workers=min(capacity, len(workers))) as pool:
            futures = [pool.submit(self.run, plan, approval, contract, source) for contract, source in workers]
            return [future.result() for future in futures]

    def purge(self, contract: WorkerContract) -> None:
        workspace = ManagedWorktree(self.repository, self.root, contract)
        workspace.created = workspace.path.exists()
        workspace.discard()
        self.journal.mark_purged(contract.attempt_id)

    def purge_expired(self, *, retention_s: float = 3600) -> int:
        if retention_s < 0:
            raise WorkerContractError('retention_s must be non-negative')
        cutoff = time.time_ns() - int(retention_s * 1_000_000_000)
        purged = 0
        for row in self.journal.attempts():
            if row['state'] != 'CANDIDATE' or row['updated_ns'] > cutoff:
                continue
            contract = WorkerContract.from_dict(strict_json(row['contract_json']))
            self.purge(contract)
            purged += 1
        return purged


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return strict_json(path.read_text())
    except (OSError, UnicodeError, ValueError) as exc:
        raise RuntimeUnavailable('unable to load runtime input') from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run one approved Residual Factory worker')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--runtime-root', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--approval', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--journal', required=True)
    parser.add_argument('--trace-id', required=True)
    args = parser.parse_args(argv)
    plan = ExecutionPlan.from_dict(_load_json(Path(args.plan)))
    approval = FrozenPlan.from_dict(_load_json(Path(args.approval)))
    contract = WorkerContract.from_dict(_load_json(Path(args.contract)))
    source = Path(args.source).read_text()
    runtime = FactoryRuntime(args.repo, args.runtime_root,
                             RuntimeJournal(args.journal, trace_id=args.trace_id),
                             allow_local_worker_code=True)
    result = runtime.run(plan, approval, contract, source)
    print(canonical(result.to_dict()))
    return 0 if result.status == 'CANDIDATE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
