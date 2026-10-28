"""Security boundaries exercised without external network or real credentials."""
import json
import logging
import threading
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from residual.core import ContractError
from residual.providers import ProviderError
from residual.station.mesh import MeshEnvelope, MeshIntegrityError, new_envelope
from residual.station.mesh_worker import MeshWorkerClient
from residual.station.service import Station


@pytest.mark.parametrize('url', [
    'https://station.example', 'https://station.example:443/prefix',
    'http://localhost:8000', 'http://127.0.0.1:8000', 'http://[::1]:8000',
])
def test_allowed(url):
    client = MeshWorkerClient(url, 'synthetic-secret', worker_id='worker')
    assert client.base == url.replace('localhost', '127.0.0.1')


@pytest.mark.parametrize('url', [
    'http://station.example', 'http://127.0.0.2', 'http://localhost.evil',
    'http://2130706433', 'http://[::ffff:127.0.0.1]', 'ftp://localhost',
    'https:///missing', 'https://', 'https://host:bad', 'https://host:65536',
    'http://localhost:0', 'http://[broken', 'http://localhost\n',
    ' https://host', 'https://host\\evil', 'https://user:synthetic-secret@host',
    'https://@host', 'https://host?synthetic-secret', 'https://host#synthetic-secret',
    'https://host?', 'https://host#',
])
def test_rejected_and_redacted(url):
    with pytest.raises(ContractError) as caught:
        MeshWorkerClient(url, 'synthetic-secret', worker_id='worker')
    assert 'synthetic-secret' not in str(caught.value)
    assert url not in str(caught.value)


@contextmanager
def endpoint(status=200, location=None):
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            seen.append((self.path, self.headers.get('Authorization')))
            self.send_response(status)
            if location:
                self.send_header('Location', location)
            self.end_headers()
            self.wfile.write(b'{}')
        do_POST = do_GET
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize('method', ['fetch', 'request'])
@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_redirect_never_receives_credentials(method, status):
    with endpoint() as (target, target_seen):
        with endpoint(status, target + '/synthetic-secret') as (source, seen):
            client = MeshWorkerClient(source, 'synthetic-secret', worker_id='worker')
            with pytest.raises((ProviderError, urllib.error.HTTPError)) as caught:
                getattr(client, method)('presence', {})
            assert 'synthetic-secret' not in str(caught.value)
            assert len(seen) == 1
            assert target_seen == []


@pytest.mark.parametrize('method', ['fetch', 'request'])
def test_environment_proxy_bypassed_and_localhost_pinned(monkeypatch, method):
    with endpoint() as (proxy, proxy_seen), endpoint() as (station, seen):
        for key in ['http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy']:
            monkeypatch.setenv(key, proxy)
        monkeypatch.setenv('no_proxy', '')
        monkeypatch.setenv('NO_PROXY', '')
        client = MeshWorkerClient(station.replace('127.0.0.1', 'localhost'),
                                  'synthetic-secret', worker_id='worker')
        assert getattr(client, method)('presence', {}) == {}
        assert seen[0][1] == 'Bearer synthetic-secret'
        assert proxy_seen == []


@pytest.mark.parametrize('artifact', [False, True])
def test_integrity_classification_and_redacted_telemetry(tmp_path, caplog, artifact):
    station = Station(tmp_path)
    raw = new_envelope(project_id='private-project', sender='private-worker',
                       recipient='private-recipient', generation=1, kind='message',
                       **({'artifact_ref': 'private-artifact'} if artifact else
                          {'payload': {'secret': 'synthetic-secret'}}))
    raw['payload_digest'] = '0' * 64
    with pytest.raises(MeshIntegrityError) as caught:
        MeshEnvelope.parse(raw)
    assert caught.value.code == 'MESH_PAYLOAD_DIGEST_MISMATCH'
    with caplog.at_level(logging.WARNING), pytest.raises(MeshIntegrityError):
        station.mesh.admit_message({'worker_id': 'private-worker'}, raw)
    with station.store.connect() as conn:
        rows = [dict(row) for row in conn.execute('SELECT * FROM mesh_dead_letters')]
    assert len(rows) == 1
    assert rows[0]['operation'] == 'message.integrity'
    assert rows[0]['reason'] == caught.value.code
    records = [r for r in caplog.records if r.getMessage() == 'mesh_integrity_failure']
    assert len(records) == 1
    assert records[0].event_code == caught.value.code
    assert records[0].outcome == 'rejected'
    serialized = json.dumps(rows) + repr(records[0].__dict__)
    for secret in ['private-project', 'private-worker', 'private-recipient',
                   'private-artifact', 'synthetic-secret', raw['payload_digest']]:
        assert secret not in serialized
    assert station.mesh.status()['message_count'] == 0


def test_malformed_digest_is_contract_error_not_integrity_event(tmp_path, caplog):
    raw = new_envelope(project_id='p', sender='w', recipient='all', generation=1,
                       kind='message', payload={'text': 'hello'})
    raw['payload_digest'] = 'not-a-digest'
    station = Station(tmp_path)
    with pytest.raises(ContractError) as caught:
        station.mesh.admit_message({'worker_id': 'w'}, raw)
    assert not isinstance(caught.value, MeshIntegrityError)
    assert not caplog.records


def test_authenticated_http_rejection_is_observable_and_redacted(tmp_path, caplog):
    import time
    from residual.station.server import Server
    from residual.station.service import demo_spec

    station = Station(tmp_path)
    pid = station.create(demo_spec(), demo=True)['project_id']
    enrolled = station.mesh.enroll({
        'worker_id': 'worker', 'host_id': 'host', 'adapter': 'openclaw',
        'adapter_version': '2026.6.1', 'project_ids': [pid],
        'capabilities': ['comms.read', 'comms.write'], 'topics': ['ops'],
        'expires_at': time.time() + 3600,
    }, allowed_capabilities=station.store.settings()['mesh_allowed_capabilities'])
    server = Server(('127.0.0.1', 0), station)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = MeshWorkerClient(f'http://127.0.0.1:{server.server_port}',
                                  enrolled['token'], worker_id='worker')
        raw = new_envelope(project_id=pid, sender='worker', recipient='all',
                           generation=1, kind='message', payload={'secret': 'private-payload'})
        raw['payload_digest'] = '0' * 64
        with caplog.at_level(logging.WARNING), pytest.raises(urllib.error.HTTPError) as caught:
            client.request('message', raw)
        error = caught.value
        try:
            assert error.code == 400
            body = error.read().decode()
            assert json.loads(body) == {'error': 'payload_digest does not match the payload'}
        finally:
            error.close()
        assert station.mesh.status()['dead_letter_count'] == 1
        assert station.mesh.status()['message_count'] == 0
        assert len([r for r in caplog.records if getattr(r, 'event_code', None)
                    == 'MESH_PAYLOAD_DIGEST_MISMATCH']) == 1
        for secret in [enrolled['token'], 'private-payload', pid]:
            assert secret not in body + caplog.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
