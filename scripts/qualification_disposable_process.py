"""Test-only owned Python subprocess adapter; not a production runtime watchdog."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import threading
import time

from . import qualification_rc_supervision as sup


class OwnedPython:
    """Owns exactly the Popen it creates; never opens or signals an arbitrary PID.

    Blocking pipe reads occur only in a daemon transport thread. poll() uses
    Popen.poll and bounded queue draining, never waits for a child response.
    """
    def __init__(self, *, workspace, directory, role, mode, lifetime, cleanup_timeout):
        sup.moment(lifetime); sup.moment(cleanup_timeout)
        if not 0 < cleanup_timeout <= lifetime <= 60:
            raise ValueError('invalid_external_test_timeouts')
        if role not in ('observer','target','driver') or mode not in (
                'healthy','never_second','never','exit','wrong_identity','stale'):
            raise ValueError('invalid_fixture_role_or_mode')
        workspace, directory = Path(workspace).resolve(), Path(directory).resolve()
        directory.relative_to(workspace)
        if not directory.is_dir(): raise ValueError('fixture_directory_required')
        child = Path(__file__).resolve().parents[1]/'tests/fixtures/rc_disposable_child.py'
        self.token = secrets.token_hex(16)
        executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
        self.role, self.cleanup_timeout = role, cleanup_timeout
        self.config = directory/(role+'-'+self.token+'.json')
        self.stderr_path = directory/(role+'-'+self.token+'.stderr.log')
        self.command = [sys.executable,'-I','-B',str(child),'--role',role,'--mode',mode,
                        '--token',self.token,'--config',str(self.config),'--lifetime',str(lifetime)]
        self._stderr = self.stderr_path.open('xb')
        self._proc = None
        self._reader = None
        try:
            self._proc = subprocess.Popen(self.command, cwd=directory, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=self._stderr, shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.identity = sup.ProcessIdentity('local-test-host',self._proc.pid,self.token,
                                               executable_sha256)
            self.poll_calls = 0
            self._messages = queue.Queue(maxsize=4)
            self._transport_failed = threading.Event()
            self._hello = None
            self._outcomes = {}
            self._cleanup = None
            self._reader = threading.Thread(target=self._read, name='fixture-pipe-'+self.token, daemon=True)
            self._reader.start()
        except BaseException as original:
            # Ownership begins at successful spawn, not successful construction.
            # Keep the original exception and expose the owned handles if cleanup fails.
            try:
                cleanup = self._abort_initialization()
            except BaseException as cleanup_error:
                cleanup = {'errors':[{'stage':'cleanup_internal','type':type(cleanup_error).__name__}],
                           'rc_qualified':False}
            original.owned_process = self._proc
            original.owned_reader = self._reader
            original.owned_stderr = self._stderr
            original.owned_process_cleanup = cleanup
            if cleanup['errors']:
                original.add_note('owned subprocess initialization cleanup incomplete; see owned_process_cleanup')
            raise

    def _abort_initialization(self):
        errors = []
        def attempt(stage, action):
            try: return True, action()
            except BaseException as exc:
                errors.append({'stage':stage,'type':type(exc).__name__})
                return False, None
        proc, reader = self._proc, self._reader
        reaped, joined = proc is None, False
        if proc is not None:
            ok, code = attempt('poll', proc.poll)
            if ok:
                terminated = code is not None
                if not terminated: terminated, _ = attempt('terminate', proc.terminate)
                if terminated:
                    try:
                        proc.wait(timeout=self.cleanup_timeout)
                        reaped = True
                    except subprocess.TimeoutExpired:
                        killed, _ = attempt('kill_after_timeout', proc.kill)
                        if killed:
                            reaped, _ = attempt('wait_after_kill', lambda: proc.wait(timeout=self.cleanup_timeout))
                    except BaseException as exc:
                        errors.append({'stage':'wait','type':type(exc).__name__})
        # ident remains set after a started thread exits. Never join an unstarted thread.
        started = reader is not None and reader.ident is not None
        reader_alive = False
        if started:
            joined, _ = attempt('reader_join', lambda: reader.join(timeout=self.cleanup_timeout))
            reader_alive = reader.is_alive()
            joined = joined and not reader_alive
            if reader_alive: errors.append({'stage':'reader_join','type':'TimeoutError'})
        if proc is not None and proc.stdout is not None and not reader_alive:
            attempt('stdout_close', proc.stdout.close)
        attempt('stderr_close', self._stderr.close)
        return {'pid':proc.pid if proc is not None else None,'generation_token':self.token,
                'command':self.command,'reaped':reaped,'reader_started':started,
                'reader_joined':joined,'errors':errors,'rc_qualified':False}

    def _read(self):
        try:
            for _ in range(5):
                raw = self._proc.stdout.readline(65537)
                if not raw: return
                if len(raw) > 65536 or not raw.endswith(b'\n'):
                    raise ValueError('oversized_or_incomplete_fixture_frame')
                self._messages.put_nowait(raw)
            self._transport_failed.set()
        except Exception:
            self._transport_failed.set()

    def _drain(self):
        for _ in range(4):
            try: raw = self._messages.get_nowait()
            except queue.Empty: break
            try:
                value = json.loads(raw)
                if value.get('event') == 'hello':
                    sup.fields(value, ('event','pid','token','role'))
                    if self._hello is not None or value['role'] != self.role or type(value['pid']) is not int:
                        raise ValueError('invalid_hello')
                    sup.text(value['token'])
                    self._hello = value
                elif value.get('event') == 'outcome':
                    sup.fields(value, ('event','value'))
                    outcome = value['value']; sequence = outcome['sequence']
                    if type(sequence) is not int or sequence not in (0,1) or sequence in self._outcomes:
                        raise ValueError('invalid_fixture_sequence')
                    self._outcomes[sequence] = sup.frozen_copy(outcome)
                else: raise ValueError('invalid_fixture_message')
            except Exception:
                self._transport_failed.set()
        if self._transport_failed.is_set(): raise ValueError('fixture_transport_failed')

    def ready(self):
        self._drain()
        return self._hello is not None

    def poll(self, task=None):
        self.poll_calls += 1
        self._drain()
        identity = asdict(self.identity)
        if self._hello:
            identity.update(pid=self._hello['pid'], birth_token=self._hello['token'])
        state = 'exited' if self._proc.poll() is not None else 'alive'
        if self._hello is None: state = 'failed'
        result = {'identity':identity,'state':state}
        if self.role == 'driver':
            result['outcome'] = self._outcomes.get(task.sequence) if task is not None else None
        return sup.frozen_copy(result)

    def configure(self, tasks, target, driver):
        value = {'tasks':[asdict(t) for t in tasks], 'target':asdict(target),'driver':asdict(driver)}
        # Exclusive creation, before the child reads. Child retries incomplete JSON.
        with self.config.open('xb') as stream: stream.write(sup.canonical(value))

    def close(self):
        if self._cleanup is not None: return self._cleanup
        action = 'already_exited'
        if self._proc.poll() is None:
            action = 'terminate_owned_popen'
            self._proc.terminate()
        try:
            self._proc.wait(timeout=self.cleanup_timeout)
        except subprocess.TimeoutExpired:
            action = 'kill_owned_popen'
            self._proc.kill()
            self._proc.wait(timeout=self.cleanup_timeout)
        self._reader.join(timeout=self.cleanup_timeout)
        if self._reader.is_alive(): raise RuntimeError('fixture_pipe_reader_cleanup_timeout')
        self._proc.stdout.close(); self._stderr.close()
        self._cleanup = {'pid':self._proc.pid,'generation_token':self.token,'role':self.role,
                         'command':self.command,'action':action,'returncode':self._proc.returncode,
                         'reader_joined':True,'poll_calls':self.poll_calls,
                         'hello':self._hello,'expected_identity':asdict(self.identity),'rc_qualified':False}
        return self._cleanup


def wait_ready(handles, *, timeout, interval):
    sup.moment(timeout); sup.moment(interval)
    if not 0 < interval <= timeout: raise ValueError('invalid_external_startup_timeout')
    end = time.monotonic()+timeout
    while time.monotonic() < end:
        if all(handle.ready() for handle in handles): return
        time.sleep(interval)
    raise TimeoutError('fixture_startup_timeout')
