"""Disposable real-Station controls; no provider calls or public listeners."""
import contextlib
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from residual.core import ContractError
from residual.station import service, server


def cleanup_station(station):
    close = getattr(station, 'close', None)
    if close is not None:
        close(timeout=2)


class StationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'state'
        self.addCleanup(self.temp.cleanup)
        self.env = mock.patch.dict(os.environ, {
            'RESIDUAL_REMOTE_EXPOSURE': '', 'RESIDUAL_ALLOWED_HOSTS': '',
            'RESIDUAL_PUBLIC_URL': ''})
        self.env.start(); self.addCleanup(self.env.stop)

    def station(self, root=None):
        station = service.Station(root or self.root)
        self.addCleanup(cleanup_station, station)
        return station

    def test_real_station_denies_second_constructor_before_store(self):
        first = self.station()
        with mock.patch.object(service, 'Store', wraps=service.Store) as store:
            with self.assertRaises(ContractError):
                second = service.Station(self.root)
                cleanup_station(second)
            store.assert_not_called()
        self.assertEqual(first.store.list_projects(), [])

    def test_denied_constructor_preserves_settings_and_database(self):
        first = self.station()
        first.store.settings({'ownership_sentinel': 'unchanged'})
        before = hashlib.sha256(first.store.db.read_bytes()).hexdigest()
        with self.assertRaises(ContractError):
            second = service.Station(self.root)
            cleanup_station(second)
        self.assertEqual(first.store.settings()['ownership_sentinel'], 'unchanged')
        self.assertEqual(hashlib.sha256(first.store.db.read_bytes()).hexdigest(), before)

    def test_separate_real_station_directories_work(self):
        first = self.station(); other = self.station(Path(self.temp.name) / 'other')
        first.store.settings({'one': 1})
        self.assertNotIn('one', other.store.settings())

    def test_real_station_release_then_restart(self):
        first = self.station(); first.store.settings({'sentinel': 17})
        first.close()
        second = self.station()
        self.assertEqual(second.store.settings()['sentinel'], 17)
        first.close()  # idempotent old close cannot disturb the new owner
        with self.assertRaises(ContractError):
            service.Station(self.root)

    def test_failed_store_initialization_releases_owner(self):
        with mock.patch.object(service, 'Store', side_effect=RuntimeError('fixture')):
            with self.assertRaisesRegex(RuntimeError, 'fixture'):
                service.Station(self.root)
        self.station()

    def test_interrupted_initialization_releases_owner(self):
        with mock.patch.object(service, 'Store', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                service.Station(self.root)
        self.station()

    def test_closed_station_rejects_new_work(self):
        first = self.station(); first.close()
        with self.assertRaises(ContractError):
            first.create(service.demo_spec(), demo=True)
        with self.assertRaises(ContractError):
            first.launch('no', lambda progress: {})

    def test_active_job_retains_owner_on_close_timeout(self):
        first = self.station(); started = threading.Event(); release = threading.Event()
        def job(progress):
            started.set()
            if not release.wait(2): raise RuntimeError('fixture timed out')
            return {'observed': True}
        try:
            jid = first.launch('test', job)['job_id']
            self.assertTrue(started.wait(2))
            before = time.monotonic()
            with self.assertRaisesRegex(ContractError, 'ownership retained'):
                first.close(timeout=0.02)
            self.assertLess(time.monotonic() - before, 0.7)
            with self.assertRaises(ContractError): service.Station(self.root)
            with self.assertRaises(ContractError): first.create(service.demo_spec(), demo=True)
        finally:
            release.set()
            # Cleanup must not trust the close implementation under mutation.
            deadline = time.monotonic() + 3
            while first.active and time.monotonic() < deadline:
                time.sleep(0.005)
            first.close(timeout=2)
        self.assertEqual(first.store.jobs()[0]['state'], 'completed')
        self.station()

    def test_thread_start_failure_releases_reservation(self):
        first = self.station()
        with mock.patch.object(threading.Thread, 'start', side_effect=RuntimeError('thread denied')):
            with self.assertRaisesRegex(RuntimeError, 'thread denied'):
                first.launch('test', lambda progress: {})
        self.assertEqual(first.active, set())
        self.assertEqual(first.store.jobs()[0]['state'], 'failed')
        first.close(timeout=0)
        self.station()

    def test_close_cannot_release_server_lifetime(self):
        first = self.station(); http = server.Server(('127.0.0.1', 0), first)
        try:
            with self.assertRaisesRegex(ContractError, 'ownership retained'):
                first.close(timeout=0)
        finally: http.server_close()
        first.close(timeout=0); self.station()

    def test_server_constructor_failure_does_not_leak_reservation(self):
        first = self.station()
        with mock.patch.object(server.ThreadingHTTPServer, '__init__', side_effect=OSError('bind denied')):
            with self.assertRaises(OSError): server.Server(('127.0.0.1', 0), first)
        first.close(timeout=0)

    def test_constructor_nonloopback_rejected_before_os_bind(self):
        first = self.station()
        with mock.patch.object(server.ThreadingHTTPServer, '__init__') as bind:
            with self.assertRaises(ContractError):
                server.Server(('0.0.0.0', 0), first)
            bind.assert_not_called()

    def test_constructor_hostname_rejected_before_dns_or_bind(self):
        first = self.station()
        with mock.patch.object(server.ThreadingHTTPServer, '__init__') as bind:
            with self.assertRaises(ContractError): server.Server(('fixture.invalid', 0), first)
            bind.assert_not_called()

    def test_cli_rejects_exposure_before_station_mutation(self):
        with mock.patch.object(server, 'Station') as station, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit): server.main(['--host', '0.0.0.0', '--data', str(self.root)])
            station.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_loopback_constructor_positive_control(self):
        first = self.station(); http = server.Server(('127.0.0.1', 0), first)
        try:
            self.assertEqual(http.server_address[0], '127.0.0.1')
            self.assertGreater(http.server_port, 0)
        finally: http.server_close()

    def test_localhost_resolves_to_fixed_loopback_bind(self):
        first = self.station(); http = server.Server(('localhost', 0), first)
        try: self.assertEqual(http.server_address[0], '127.0.0.1')
        finally: http.server_close()

    def test_explicit_remote_policy_has_shared_boundary(self):
        first = self.station(); captured = []
        def intercepted(instance, address, handler):
            captured.append(address)
            instance.server_port = 8765
        with mock.patch.dict(os.environ, {'RESIDUAL_REMOTE_EXPOSURE': '1',
                'RESIDUAL_ALLOWED_HOSTS': 'station.example',
                'RESIDUAL_PUBLIC_URL': 'https://station.example'}), \
             mock.patch.object(server.ThreadingHTTPServer, '__init__', intercepted), \
             mock.patch.object(server.Server, '_register_legacy_worker_key'):
            http = server.Server(('0.0.0.0', 8765), first)
            self.assertTrue(http.secure_cookie)
            self.assertEqual(captured, [('0.0.0.0', 8765)])
            # No socket created: release synthetic server reservation directly.
            http._lifetime.cancel()

    def test_cli_bind_failure_closes_station(self):
        with mock.patch.object(server, 'Server', side_effect=OSError('bind denied')):
            with self.assertRaises(OSError): server.main(['--data', str(self.root)])
        self.station()

    def test_cli_serve_failure_closes_socket_and_station(self):
        with mock.patch.object(server.Server, 'serve_forever', side_effect=RuntimeError('serve failed')), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError): server.main(['--data', str(self.root), '--port', '0'])
        self.station()

    def test_context_manager_releases_after_exception(self):
        with self.assertRaises(RuntimeError):
            with service.Station(self.root): raise RuntimeError('expected')
        self.station()

    def test_real_demo_git_checks_review_and_export(self):
        first = self.station(); pid = first.create(service.demo_spec(), demo=True)['project_id']
        self.assertEqual(first.batch(pid)['integrated'], 3)
        self.assertEqual(first.metrics(pid)['calls'], 0)
        self.assertTrue(first.export(pid)['sha256'])

    def test_restart_recovers_task_without_reusing_stale_lease(self):
        first = self.station(); pid = first.create(service.demo_spec(), demo=True)['project_id']
        first.triage(pid); work = first.prepare(pid, 'local-runner', 'OPS-101'); first.close()
        second = self.station()
        self.assertEqual(second.store.task(pid, 'OPS-101')['state'], 'blocked')
        with self.assertRaises(ContractError): second.finish(work, {'files': service.DEMO_FILES['OPS-101']})

    def test_second_process_station_constructor_is_rejected(self):
        first = self.station()
        code = '''import sys
from residual.station.service import Station
from residual.core import ContractError
try:
 s=Station(sys.argv[1])
except ContractError:
 raise SystemExit(23)
else:
 if hasattr(s,'close'): s.close()
 raise SystemExit(0)
'''
        run = subprocess.run([sys.executable, '-c', code, str(self.root)],
                             capture_output=True, timeout=7, text=True)
        self.assertEqual(run.returncode, 23, run.stderr)

    def test_close_rejects_invalid_deadline(self):
        first = self.station()
        for value in (True, -1, float('nan'), float('inf'), '1'):
            with self.subTest(value=value), self.assertRaises(ValueError): first.close(value)
        self.assertEqual(first.store.list_projects(), [])

if __name__ == '__main__': unittest.main()
