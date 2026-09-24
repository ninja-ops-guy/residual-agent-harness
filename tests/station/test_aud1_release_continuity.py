"""AUD-1 follow-up regressions: delayed request admission and stalled heartbeat.

Real loopback Station tests plus a controlled worker transport stall. No live
fleet, credentials, R4 state, tunnel changes, or physical-F6 qualification.
"""
from __future__ import annotations

import concurrent.futures
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from residual.providers import Reply, Usage

from residual.core import ContractError, canonical
from residual.station.server import Handler, Server
from residual.station.service import DEMO_FILES, Station, demo_spec
from residual.station.worker import WorkerAuthorityLost, WorkerClient
from residual.station.worker_access import WorkerAccessGate


class DelayedAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        self.pid = self.station.create(demo_spec(), demo=True)['project_id']
        self.station.triage(self.pid)
        self.http = Server(('127.0.0.1', 0), self.station)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.http.server_port}'
        self.token = self.post('/api/workers/access', {'enabled': True})['token']
        self.work = self.post('/api/worker/claim', {'project_id': self.pid, 'task_id': 'OPS-101', 'name': 'old-runner'}, self.token)['work']

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def post(self, route, data, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        else:
            headers['X-Station-Token'] = self.station.store.settings()['session_token']
        request = urllib.request.Request(self.url + route, canonical(data).encode(), headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    def assert_control_change_fences_body(self, route, data, *, rotate):
        before = self.station.store.task(self.pid, 'OPS-101')
        reached = threading.Event()
        release = threading.Event()
        body = Handler.body

        def delayed_body(handler):
            if handler.path == route:
                reached.set()  # do_POST has authenticated; body has not been read.
                if not release.wait(5):
                    raise AssertionError('test body barrier timed out')
            return body(handler)

        with patch.object(Handler, 'body', delayed_body):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                old = pool.submit(self.post, route, data, self.token)
                try:
                    self.assertTrue(reached.wait(3), 'request did not reach auth/body barrier')
                    self.post('/api/workers/access', {'enabled': rotate, 'rotate': rotate})
                finally:
                    release.set()
                with self.assertRaises(urllib.error.HTTPError) as error:
                    old.result(timeout=5)
                self.assertEqual(error.exception.code, 403)
        after = self.station.store.task(self.pid, 'OPS-101')
        self.assertEqual(after, before, 'a denied stale request mutated task state')

    def test_rotation_fences_heartbeat_authenticated_before_body(self):
        self.assert_control_change_fences_body('/api/worker/heartbeat', {
            'project_id': self.pid, 'task_id': 'OPS-101', 'lease': self.work['lease'],
        }, rotate=True)

    def test_rotation_fences_result_authenticated_before_body(self):
        self.assert_control_change_fences_body('/api/worker/result', {
            'project_id': self.pid, 'task_id': 'OPS-101', 'lease': self.work['lease'],
            'submission_id': 'delayed-result', 'response': {'files': DEMO_FILES['OPS-101']},
        }, rotate=True)

    def test_disable_fences_heartbeat_authenticated_before_body(self):
        self.assert_control_change_fences_body('/api/worker/heartbeat', {
            'project_id': self.pid, 'task_id': 'OPS-101', 'lease': self.work['lease'],
        }, rotate=False)


    def test_rotation_drains_admitted_results_without_serializing_projects(self):
        other_pid = self.station.create(demo_spec(), demo=True)['project_id']
        self.station.triage(other_pid)
        other_token = self.post('/api/workers/access', {'enabled': True})['token']
        other_work = self.post('/api/worker/claim', {
            'project_id': other_pid, 'task_id': 'OPS-101', 'name': 'second-runner',
        }, other_token)['work']
        entered = {self.pid: threading.Event(), other_pid: threading.Event()}
        release = threading.Event()
        original = self.station.finish

        def blocked_finish(work, response, usage=None):
            entered[work['project_id']].set()
            if not release.wait(5):
                raise AssertionError('result fixture did not drain')
            return original(work, response, usage)

        with patch.object(self.station, 'finish', blocked_finish):
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                results = []
                for pid, token, work in [(self.pid, self.token, self.work), (other_pid, other_token, other_work)]:
                    results.append(pool.submit(self.post, '/api/worker/result', {
                        'project_id': pid, 'task_id': 'OPS-101', 'lease': work['lease'],
                        'submission_id': 'inflight-' + pid, 'response': {'files': DEMO_FILES['OPS-101']},
                    }, token))
                try:
                    self.assertTrue(all(event.wait(3) for event in entered.values()), 'unrelated projects serialized')
                    rotation = pool.submit(self.post, '/api/workers/access', {'enabled': True, 'rotate': True})
                    gate = self.http._worker_gate
                    with gate._condition:
                        self.assertTrue(gate._condition.wait_for(lambda: gate._writers_waiting > 0, timeout=2))
                    self.assertFalse(rotation.done(), 'rotation acknowledged before admitted work drained')
                    release.set()
                    for future in results:
                        self.assertEqual(future.result(timeout=5)['state'], 'review_ready')
                    self.assertTrue(rotation.result(timeout=5)['enabled'])
                finally:
                    release.set()
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post('/api/worker/heartbeat', {
                'project_id': self.pid, 'task_id': 'OPS-101', 'lease': self.work['lease'],
            }, self.token)
        self.assertEqual(error.exception.code, 403)


class HeartbeatDeadlineTests(unittest.TestCase):
    def test_blocked_heartbeat_does_not_disable_authority_deadline(self):
        client = WorkerClient('http://127.0.0.1:1', 'fixture', heartbeat_interval=0.02, heartbeat_grace=0.10)
        entered = threading.Event()
        release = threading.Event()
        stop = threading.Event()

        def stalled_request(route, data):
            self.assertEqual(route, 'heartbeat')
            entered.set()
            release.wait(5)
            return {'ok': True}

        class Provider:
            def generate(self, packet, max_tokens):
                release.wait(5)
                return 'late output'

        client.request = stalled_request
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            running = pool.submit(client._generate_with_authority, Provider(), {}, 1, {}, stop)
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(WorkerAuthorityLost):
                    running.result(timeout=1)
            finally:
                stop.set()
                release.set()
                try:
                    running.result(timeout=3)
                except WorkerAuthorityLost:
                    pass


class AccessGateTests(unittest.TestCase):
    def test_parallel_operations_and_writer_preference(self):
        gate = WorkerAccessGate()
        active = [threading.Event(), threading.Event()]
        drain = threading.Event()
        changing = threading.Event()
        changed = threading.Event()
        later = threading.Event()
        order = []

        def reader(index):
            with gate.operation():
                active[index].set()
                if not drain.wait(5):
                    raise AssertionError('reader fixture did not drain')

        def writer():
            with gate.control():
                order.append('control')
                changing.set()
                if not changed.wait(5):
                    raise AssertionError('control fixture did not finish')

        def late_reader():
            with gate.operation():
                order.append('late-reader')
                later.set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            pending = [pool.submit(reader, 0), pool.submit(reader, 1)]
            try:
                self.assertTrue(all(e.wait(2) for e in active), 'worker requests serialized')
                pending.append(pool.submit(writer))
                with gate._condition:
                    self.assertTrue(gate._condition.wait_for(lambda: gate._writers_waiting == 1, timeout=2))
                pending.append(pool.submit(late_reader))
                self.assertFalse(changing.is_set(), 'control entered before admitted requests drained')
                drain.set()
                self.assertTrue(changing.wait(2))
                self.assertFalse(later.is_set(), 'new request passed an unfinished control change')
                changed.set()
                for future in pending:
                    future.result(timeout=3)
                self.assertEqual(order, ['control', 'late-reader'])
            finally:
                drain.set()
                changed.set()

    def test_failed_operation_and_control_release_barrier(self):
        gate = WorkerAccessGate()
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with gate.operation():
                raise RuntimeError('fixture')
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with gate.control():
                raise RuntimeError('fixture')
        with gate.operation():
            self.assertEqual(gate._readers, 1)
        self.assertEqual(gate._readers, 0)
        self.assertFalse(gate._writing)


class HeartbeatInputTests(unittest.TestCase):
    def test_nonfinite_and_boolean_heartbeat_windows_are_rejected(self):
        for interval, grace in [(float('nan'), 180), (60, float('nan')), (float('inf'), float('inf')),
                                (60, float('inf')), (True, 180), (1, False), (0, 1), (2, 1), ('60', 180)]:
            with self.subTest(interval=interval, grace=grace):
                with self.assertRaises(ContractError):
                    WorkerClient('http://127.0.0.1:1', 'fixture', interval, grace)

    def test_revocation_response_surrenders_without_waiting_full_grace(self):
        client = WorkerClient('http://127.0.0.1:1', 'fixture', 0.01, 30)
        release = threading.Event()
        stop = threading.Event()

        def revoked(route, data):
            raise urllib.error.HTTPError(client.base, 403, 'revoked', {}, None)

        class Provider:
            def generate(self, packet, max_tokens):
                release.wait(5)
                return 'late'

        client.request = revoked
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(client._generate_with_authority, Provider(), {}, 1, {}, stop)
            try:
                with self.assertRaises(WorkerAuthorityLost):
                    result.result(timeout=1)
            finally:
                stop.set()
                release.set()

    def test_malformed_acknowledgements_do_not_extend_authority(self):
        client = WorkerClient('http://127.0.0.1:1', 'fixture', 0.01, 0.08)
        release = threading.Event()
        stop = threading.Event()
        client.request = lambda route, data: {'ok': 'true'}

        class Provider:
            def generate(self, packet, max_tokens):
                release.wait(5)
                return 'late'

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(client._generate_with_authority, Provider(), {}, 1, {}, stop)
            try:
                with self.assertRaises(WorkerAuthorityLost):
                    result.result(timeout=1)
            finally:
                stop.set()
                release.set()

    def test_transient_failure_recovers_inside_window(self):
        client = WorkerClient('http://127.0.0.1:1', 'fixture', 0.01, 2)
        stop = threading.Event()
        recovered = threading.Event()
        calls = []

        def request(route, data):
            calls.append(route)
            if len(calls) == 1:
                raise OSError('temporary loss')
            recovered.set()
            return {'ok': True}

        class Provider:
            def generate(self, packet, max_tokens):
                if not recovered.wait(3):
                    raise AssertionError('recovery not reached')
                return 'valid candidate'

        client.request = request
        try:
            self.assertEqual(client._generate_with_authority(Provider(), {}, 1, {}, stop), 'valid candidate')
            self.assertGreaterEqual(len(calls), 2)
        finally:
            stop.set()


class BlackholeTransportTests(unittest.TestCase):
    def test_real_http_stall_surrenders_without_submitting_late_candidate(self):
        heartbeat_seen = threading.Event()
        release = threading.Event()
        results = []

        class Blackhole(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path.endswith('/claim'):
                    response = {'work': {'project_id': 'p-fixture', 'task_id': 't-fixture',
                                'lease': 'fixture-lease', 'packet': {}, 'allow_cloud': False}}
                elif self.path.endswith('/heartbeat'):
                    heartbeat_seen.set()
                    release.wait(5)
                    response = {'ok': True}
                else:
                    results.append(data)
                    response = {'task_id': 't-fixture', 'state': 'review_ready'}
                try:
                    raw = canonical(response).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class Provider:
            placement = 'local'
            model = 'fixture'

            def generate(self, packet, max_tokens):
                release.wait(5)
                return Reply('{"files":{}}', Usage())

            def wire_size(self, packet, max_tokens):
                return 0

        http = ThreadingHTTPServer(('127.0.0.1', 0), Blackhole)
        http.daemon_threads = True
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        client = WorkerClient(f'http://127.0.0.1:{http.server_port}', 'fixture', 0.02, 0.12)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                running = pool.submit(client.run_once, 'p-fixture', 'fixture-runner', Provider())
                try:
                    self.assertTrue(heartbeat_seen.wait(2))
                    with self.assertRaises(WorkerAuthorityLost):
                        running.result(timeout=1)
                finally:
                    release.set()
            self.assertEqual(results, [], 'late candidate was submitted after authority loss')
        finally:
            release.set()
            http.shutdown()
            http.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
