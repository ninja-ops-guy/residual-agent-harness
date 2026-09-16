from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == 'posix' and Path('/proc').is_dir(), 'worker recovery requires Linux /proc')
class WebVMWorkerTimeoutRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = Path(__file__).resolve().parents[1]
        self.root = self.base / 'repo'; self.root.mkdir()
        self.mailbox = self.base / 'mailbox'; self.mailbox.mkdir()
        self.output = self.base / 'runs'; self.output.mkdir()
        self.fifo = self.base / 'worker.fifo'
        self.pid_file = self.base / 'worker.pid'
        self.poison = self.output / '.worker-poisoned'
        self.script = self.repo / 'demo/vm/terminate_worker.sh'
        (self.root / 'README.md').write_text('timeout recovery fixture\n', encoding='utf-8')
        self.children: list[subprocess.Popen] = []
        self.addCleanup(self.cleanup_children)

    def cleanup_children(self):
        for proc in self.children:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    def start_worker(self):
        proc = subprocess.Popen(
            [
                sys.executable, '-m', 'residual.workbench.browser_worker',
                '--fifo', str(self.fifo),
                '--pid-file', str(self.pid_file),
                '--mailbox', str(self.mailbox),
                '--root', str(self.root),
                '--output-root', str(self.output),
            ],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.children.append(proc)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.pid_file.exists() and self.fifo.exists():
                return proc
            if proc.poll() is not None:
                out, err = proc.communicate()
                self.fail(f'worker exited before ready: {proc.returncode}\nstdout={out}\nstderr={err}')
            time.sleep(0.02)
        self.fail('worker did not publish PID/FIFO')

    def recovery_env(self):
        env = os.environ.copy()
        env.update({
            'RESIDUAL_WORKER_PID_FILE': str(self.pid_file),
            'RESIDUAL_WORKER_FIFO': str(self.fifo),
            'RESIDUAL_WORKER_OUTPUT_ROOT': str(self.output),
            'RESIDUAL_WORKER_POISON_FILE': str(self.poison),
        })
        return env

    def recover(self, token: str, mission_id: str, launch_pid: str = ''):
        return subprocess.run(
            ['bash', str(self.script), token, mission_id, launch_pid],
            cwd=self.repo,
            env=self.recovery_env(),
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )

    def test_timeout_kills_verified_worker_and_clears_only_matching_lock(self):
        mission = 'm-' + 'a' * 32
        proc = self.start_worker()
        (self.output / '.active').write_text(mission + '\n', encoding='ascii')
        partial = self.output / mission
        partial.mkdir()
        (partial / 'partial-evidence.txt').write_text('retain me', encoding='utf-8')

        result = self.recover(mission, mission, str(proc.pid))
        proc.wait(timeout=5)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'RESIDUAL_WORKER_TERMINATED_{mission}:0', result.stdout)
        self.assertFalse(self.pid_file.exists())
        self.assertFalse(self.fifo.exists())
        self.assertFalse((self.output / '.active').exists())
        self.assertFalse(self.poison.exists())
        self.assertEqual((partial / 'partial-evidence.txt').read_text(encoding='utf-8'), 'retain me')

    def test_timeout_never_removes_another_missions_lock(self):
        mission = 'm-' + 'b' * 32
        other = 'm-' + 'c' * 32
        proc = self.start_worker()
        (self.output / '.active').write_text(other + '\n', encoding='ascii')

        result = self.recover(mission, mission, str(proc.pid))
        proc.wait(timeout=5)

        self.assertIn(f'RESIDUAL_WORKER_TERMINATED_{mission}:0', result.stdout)
        self.assertEqual((self.output / '.active').read_text(encoding='ascii').strip(), other)
        self.assertFalse(self.poison.exists())

    def test_startup_timeout_uses_shell_launch_pid_before_pid_file_is_available(self):
        proc = self.start_worker()
        # Simulate the host timing out before it observed the worker-owned PID file.
        self.pid_file.unlink()

        result = self.recover('startup', '', str(proc.pid))
        proc.wait(timeout=5)

        self.assertIn('RESIDUAL_WORKER_TERMINATED_startup:0', result.stdout)
        self.assertFalse(self.fifo.exists())
        self.assertFalse(self.poison.exists())

    def test_unverified_pid_is_not_signaled_and_poison_remains(self):
        mission = 'm-' + 'd' * 32
        sleeper = subprocess.Popen(['sleep', '60'])
        self.children.append(sleeper)
        self.pid_file.write_text(str(sleeper.pid) + '\n', encoding='ascii')
        (self.output / '.active').write_text(mission + '\n', encoding='ascii')

        result = self.recover(mission, mission, '')

        self.assertIn(f'RESIDUAL_WORKER_TERMINATED_{mission}:3', result.stdout)
        self.assertIsNone(sleeper.poll(), 'recovery killed an unverified process')
        self.assertTrue(self.poison.is_file(), 'uncertain recovery must remain durably poisoned')
        self.assertEqual((self.output / '.active').read_text(encoding='ascii').strip(), mission)


if __name__ == '__main__':
    unittest.main()
