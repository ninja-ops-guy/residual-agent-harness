from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

from residual.workbench import browser_worker
from residual.workbench.host_recovery import build_recovery_command


@unittest.skipUnless(os.name == 'posix', 'WebVM worker recovery uses POSIX process/filesystem semantics')
class WebVMWorkerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'; self.root.mkdir()
        self.mailbox = self.base / 'mailbox'; self.mailbox.mkdir()
        self.output = self.base / 'runs'; self.output.mkdir()
        self.repo_root = Path(__file__).resolve().parents[1]
        self.env = os.environ.copy()
        current = self.env.get('PYTHONPATH')
        self.env['PYTHONPATH'] = str(self.repo_root) + (os.pathsep + current if current else '')

    def paths(self, name: str):
        control = self.base / name
        control.mkdir()
        return (
            control / 'worker.pid',
            control / 'worker.fifo',
            control / 'worker.poison',
        )

    def run_worker_and_recovery(self, *, name: str, recovery_mission: str, active_value: str):
        pid_file, fifo, poison = self.paths(name)
        active = self.output / '.active'
        active.write_text(active_value, encoding='ascii')
        marker = 'RECOVERY_' + name.upper()
        command = build_recovery_command(
            pid_file=pid_file,
            fifo=fifo,
            poison_file=poison,
            active_lock=active,
            mission_id=recovery_mission,
            marker=marker,
        )
        python = shlex.quote(sys.executable)
        script = f"""
set -u
{python} -m residual.workbench.browser_worker \
  --fifo {shlex.quote(str(fifo))} \
  --pid-file {shlex.quote(str(pid_file))} \
  --poison-file {shlex.quote(str(poison))} \
  --mailbox {shlex.quote(str(self.mailbox))} \
  --root {shlex.quote(str(self.root))} \
  --output-root {shlex.quote(str(self.output))} &
residual_test_worker=$!
for residual_wait in {{1..100}}; do
  [ -f {shlex.quote(str(pid_file))} ] && break
  sleep 0.02
done
{command}
wait "$residual_test_worker" 2>/dev/null || true
"""
        result = subprocess.run(
            ['bash', '-c', script],
            cwd=self.repo_root,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'{marker}:0', result.stdout, result.stdout + result.stderr)
        self.assertTrue(poison.is_file(), 'durable timeout poison was not retained')
        self.assertFalse(pid_file.exists(), 'worker PID file survived successful recovery')
        self.assertFalse(fifo.exists(), 'worker FIFO survived successful recovery')
        return active, poison, pid_file, fifo

    def test_timeout_recovery_kills_worker_recovers_matching_lock_and_fences_restart(self):
        mission = 'm-' + 'a' * 32
        active, poison, pid_file, fifo = self.run_worker_and_recovery(
            name='matching', recovery_mission=mission, active_value=mission,
        )
        self.assertFalse(active.exists(), 'matching stale .active lock was not recovered')

        # A new process in the same guest/control generation must refuse to become
        # READY while the durable poison record exists. This models page/host
        # reinitialization without an explicit guest reset.
        restart = subprocess.run(
            [
                sys.executable, '-m', 'residual.workbench.browser_worker',
                '--fifo', str(fifo), '--pid-file', str(pid_file),
                '--poison-file', str(poison), '--mailbox', str(self.mailbox),
                '--root', str(self.root), '--output-root', str(self.output),
            ],
            cwd=self.repo_root,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        self.assertEqual(restart.returncode, 75, restart.stdout + restart.stderr)
        self.assertIn(browser_worker.POISONED, restart.stdout)
        self.assertNotIn(browser_worker.READY, restart.stdout)
        self.assertFalse(pid_file.exists())
        self.assertFalse(fifo.exists())

    def test_timeout_recovery_never_clears_another_missions_lock(self):
        timed_out = 'm-' + 'b' * 32
        other = 'm-' + 'c' * 32
        active, _, _, _ = self.run_worker_and_recovery(
            name='mismatch', recovery_mission=timed_out, active_value=other,
        )
        self.assertTrue(active.is_file(), 'recovery removed a different mission lock')
        self.assertEqual(active.read_text(encoding='ascii'), other)

    def test_recovery_command_rejects_untrusted_dynamic_fields(self):
        kwargs = {
            'pid_file': self.base / 'pid',
            'fifo': self.base / 'fifo',
            'poison_file': self.base / 'poison',
            'active_lock': self.output / '.active',
        }
        with self.assertRaises(ValueError):
            build_recovery_command(**kwargs, mission_id='bad;rm -rf /', marker='SAFE')
        with self.assertRaises(ValueError):
            build_recovery_command(**kwargs, mission_id=None, marker='BAD;echo injected')


if __name__ == '__main__':
    unittest.main()
