#!/usr/bin/env python3
import json, os, secrets, sqlite3, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB_PATH = Path(os.getenv('RESIDUAL_DEMO_DB', '/tmp/residual-demo-gateway.sqlite3'))
ORIGIN = os.getenv('RESIDUAL_DEMO_ORIGIN', 'https://ninja-ops-guy.github.io')
TTL = int(os.getenv('RESIDUAL_DEMO_TTL_SECONDS', '900'))
MAX_REQUESTS = int(os.getenv('RESIDUAL_DEMO_MAX_REQUESTS', '8'))
MAX_TOKENS = int(os.getenv('RESIDUAL_DEMO_MAX_TOKENS', '4096'))
MAX_OUTPUT = int(os.getenv('RESIDUAL_DEMO_MAX_OUTPUT_TOKENS', '512'))
MAX_BODY_BYTES = int(os.getenv('RESIDUAL_DEMO_MAX_BODY_BYTES', '262144'))
MAX_UPSTREAM_BYTES = int(os.getenv('RESIDUAL_DEMO_MAX_UPSTREAM_BYTES', '2097152'))
MAX_ACTIVE_SESSIONS = int(os.getenv('RESIDUAL_DEMO_MAX_ACTIVE_SESSIONS', '32'))
MAX_SESSIONS_PER_HOUR = int(os.getenv('RESIDUAL_DEMO_MAX_SESSIONS_PER_HOUR', '64'))
FREELLM = os.environ.get('FREELLMAPI_BASE_URL', '').rstrip('/')
FREELLM_EMAIL = os.environ.get('FREELLMAPI_ADMIN_EMAIL', '')
FREELLM_PASSWORD = os.environ.get('FREELLMAPI_ADMIN_PASSWORD', '')
TS_CLIENT_ID = os.environ.get('TAILSCALE_OAUTH_CLIENT_ID', '')
TS_CLIENT_SECRET = os.environ.get('TAILSCALE_OAUTH_CLIENT_SECRET', '')
TS_TAG = os.getenv('TAILSCALE_DEMO_TAG', 'tag:residual-demo')
TS_TAILNET = os.getenv('TAILSCALE_TAILNET', '-')
ALLOWED_MODELS = {'auto', 'auto:fast', 'auto:smart'}
_lock = threading.Lock()


class DemoCapacityError(RuntimeError):
    pass


class RequestTooLarge(ValueError):
    pass


def _diag(stage, exc):
    msg = str(exc).replace('\n', ' ')[:240]
    print(f'[residual-demo] stage={stage} error={type(exc).__name__} detail={msg}', flush=True)


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        conn.close()
        raise
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS sessions(
      token TEXT PRIMARY KEY, created INTEGER NOT NULL, expires INTEGER NOT NULL,
      requests_left INTEGER NOT NULL, tokens_left INTEGER NOT NULL,
      profile_id INTEGER NOT NULL, profile_key TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
    )''')
    return conn


def _json(url, method='GET', body=None, headers=None, timeout=20):
    data = None if body is None else json.dumps(body).encode()
    hdr = {'Accept': 'application/json'}
    if body is not None: hdr['Content-Type'] = 'application/json'
    if headers: hdr.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(MAX_UPSTREAM_BYTES + 1)
        if len(raw) > MAX_UPSTREAM_BYTES:
            raise RuntimeError('upstream response exceeds configured limit')
        return r.status, dict(r.headers), json.loads(raw or b'{}')


def _form(url, body, headers=None, timeout=20):
    data = urllib.parse.urlencode(body).encode()
    hdr = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    if headers: hdr.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(MAX_UPSTREAM_BYTES + 1)
        if len(raw) > MAX_UPSTREAM_BYTES:
            raise RuntimeError('upstream response exceeds configured limit')
        return json.loads(raw or b'{}')


def _freellm_admin_token():
    _, _, out = _json(f'{FREELLM}/api/auth/login', 'POST', {'email': FREELLM_EMAIL, 'password': FREELLM_PASSWORD})
    return out['token']


def _freellm_create_profile(name):
    token = _freellm_admin_token()
    _, _, out = _json(f'{FREELLM}/api/client-profiles', 'POST', {'name': name, 'systemPrompt': None}, {'Authorization': f'Bearer {token}'})
    return int(out['id']), out['key']


def _freellm_delete_profile(profile_id):
    try:
        token = _freellm_admin_token()
        _json(f'{FREELLM}/api/client-profiles/{profile_id}', 'DELETE', headers={'Authorization': f'Bearer {token}'})
    except Exception as e:
        _diag('freellm_profile_cleanup', e)


def _tailscale_auth_key():
    oauth = _form('https://api.tailscale.com/api/v2/oauth/token', {
        'client_id': TS_CLIENT_ID, 'client_secret': TS_CLIENT_SECRET,
        'grant_type': 'client_credentials', 'scope': 'auth_keys', 'tags': TS_TAG,
    })['access_token']
    payload = {'capabilities': {'devices': {'create': {
        'reusable': False, 'ephemeral': True, 'preauthorized': True, 'tags': [TS_TAG]
    }}}, 'expirySeconds': min(TTL, 3600), 'description': 'residual-demo'}
    _, _, out = _json(f'https://api.tailscale.com/api/v2/tailnet/{urllib.parse.quote(TS_TAILNET, safe="-")}/keys', 'POST', payload, {'Authorization': f'Bearer {oauth}'})
    return out['key']


def _cleanup_expired():
    now = int(time.time())
    with _lock:
        conn = _db()
        rows = conn.execute('SELECT profile_id FROM sessions WHERE revoked=0 AND expires<=?', (now,)).fetchall()
        conn.execute('UPDATE sessions SET revoked=1 WHERE revoked=0 AND expires<=?', (now,))
        conn.commit(); conn.close()
    for row in rows: _freellm_delete_profile(row['profile_id'])


def _new_session():
    if not all([FREELLM, FREELLM_EMAIL, FREELLM_PASSWORD, TS_CLIENT_ID, TS_CLIENT_SECRET]):
        raise RuntimeError('gateway is not fully configured')
    _cleanup_expired()
    now = int(time.time())
    # Session creation is the public resource-allocation boundary. Serialize
    # issuance so concurrent callers cannot race around the global caps.
    with _lock:
        conn = _db()
        active = conn.execute(
            'SELECT COUNT(*) FROM sessions WHERE revoked=0 AND expires>?',
            (now,),
        ).fetchone()[0]
        recent = conn.execute(
            'SELECT COUNT(*) FROM sessions WHERE created>=?',
            (now - 3600,),
        ).fetchone()[0]
        conn.close()
        if active >= MAX_ACTIVE_SESSIONS or recent >= MAX_SESSIONS_PER_HOUR:
            raise DemoCapacityError('demo session capacity reached; retry later')

        token = 'rdemo_' + secrets.token_urlsafe(32)
        try:
            profile_id, profile_key = _freellm_create_profile('residual-demo-' + token[-8:])
        except Exception as e:
            _diag('freellm_profile_create', e)
            raise
        try:
            ts_key = _tailscale_auth_key()
        except Exception as e:
            _diag('tailscale_auth_key', e)
            _freellm_delete_profile(profile_id)
            raise
        try:
            conn = _db()
            conn.execute(
                'INSERT INTO sessions(token,created,expires,requests_left,tokens_left,profile_id,profile_key) VALUES(?,?,?,?,?,?,?)',
                (token, now, now + TTL, MAX_REQUESTS, MAX_TOKENS, profile_id, profile_key),
            )
            conn.commit(); conn.close()
        except Exception as e:
            _diag('session_store', e)
            _freellm_delete_profile(profile_id)
            raise
    print('[residual-demo] stage=session_create status=ok', flush=True)
    return {'token': token, 'expiresAt': now + TTL, 'requests': MAX_REQUESTS, 'tokenBudget': MAX_TOKENS, 'tailscaleAuthKey': ts_key, 'model': 'auto:fast'}


def _reserve(token, requested):
    _cleanup_expired(); now = int(time.time())
    with _lock:
        conn = _db(); conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM sessions WHERE token=?', (token,)).fetchone()
        if not row or row['revoked'] or row['expires'] <= now:
            conn.rollback(); conn.close(); raise PermissionError('session expired or invalid')
        amount = max(1, min(int(requested), MAX_OUTPUT))
        if row['requests_left'] <= 0 or row['tokens_left'] < amount:
            conn.rollback(); conn.close(); raise PermissionError('session budget exhausted')
        conn.execute('UPDATE sessions SET requests_left=requests_left-1,tokens_left=tokens_left-? WHERE token=?', (amount, token))
        conn.commit(); conn.close(); return row['profile_key'], amount


def _revoke(token):
    with _lock:
        conn = _db(); row = conn.execute('SELECT profile_id FROM sessions WHERE token=?', (token,)).fetchone()
        if row: conn.execute('UPDATE sessions SET revoked=1 WHERE token=?', (token,)); conn.commit()
        conn.close()
    if row: _freellm_delete_profile(row['profile_id'])


def _route(method, path, headers, body):
    if method == 'OPTIONS': return 204, None
    if method == 'GET':
        if path == '/health':
            return 200, {'ok': True, 'configured': bool(FREELLM and FREELLM_EMAIL and FREELLM_PASSWORD and TS_CLIENT_ID and TS_CLIENT_SECRET)}
        return 404, {'error': 'not found'}
    if method == 'POST':
        try:
            if path == '/v1/demo/session': return 201, _new_session()
            if path == '/v1/chat/completions':
                payload = json.loads(body or b'{}')
                model = payload.get('model', 'auto:fast')
                if model not in ALLOWED_MODELS: return 400, {'error': {'message': 'model not allowed'}}
                auth = headers.get('authorization', '')
                token = auth[7:] if auth.startswith('Bearer ') else ''
                key, reserved = _reserve(token, payload.get('max_tokens', payload.get('max_completion_tokens', 256)))
                payload['model'] = model; payload['max_tokens'] = min(reserved, MAX_OUTPUT); payload.pop('max_completion_tokens', None)
                _, _, out = _json(f'{FREELLM}/v1/chat/completions', 'POST', payload, {'Authorization': f'Bearer {key}'}, timeout=45)
                return 200, out
            return 404, {'error': 'not found'}
        except PermissionError as e: return 401, {'error': {'message': str(e)}}
        except DemoCapacityError as e: return 429, {'error': {'message': str(e)}}
        except Exception as e:
            _diag('request', e)
            return 503, {'error': {'message': 'demo cloud unavailable', 'detail': type(e).__name__}}
    if method == 'DELETE':
        if path != '/v1/demo/session': return 404, {'error': 'not found'}
        auth = headers.get('authorization', '')
        _revoke(auth[7:] if auth.startswith('Bearer ') else '')
        return 200, {'revoked': True}
    return 405, {'error': 'method not allowed'}


class ASGIApp:
    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http': return
        chunks = []
        total = 0
        too_large = False
        while True:
            event = await receive()
            if event['type'] != 'http.request': continue
            chunk = event.get('body', b'')
            total += len(chunk)
            if total > MAX_BODY_BYTES:
                too_large = True
            elif not too_large:
                chunks.append(chunk)
            if not event.get('more_body'): break
        headers = {k.decode().lower(): v.decode() for k, v in scope.get('headers', [])}
        path = scope.get('path') or '/'
        if too_large:
            code, obj = 413, {'error': {'message': 'request body too large'}}
        else:
            code, obj = _route(scope.get('method', 'GET').upper(), path, headers, b''.join(chunks))
        origin = headers.get('origin')
        out_headers = [(b'content-type', b'application/json'), (b'cache-control', b'no-store'),
                       (b'x-content-type-options', b'nosniff'),
                       (b'referrer-policy', b'no-referrer'),
                       (b'content-security-policy', b"default-src 'none'; frame-ancestors 'none'"),
                       (b'x-frame-options', b'DENY'),
                       (b'access-control-allow-headers', b'Authorization, Content-Type'),
                       (b'access-control-allow-methods', b'GET, POST, DELETE, OPTIONS')]
        if origin == ORIGIN:
            out_headers += [(b'access-control-allow-origin', origin.encode()), (b'vary', b'Origin')]
        raw = b'' if obj is None else json.dumps(obj, separators=(',', ':')).encode()
        out_headers.append((b'content-length', str(len(raw)).encode()))
        await send({'type': 'http.response.start', 'status': code, 'headers': out_headers})
        await send({'type': 'http.response.body', 'body': raw})

app = ASGIApp()


class Handler(BaseHTTPRequestHandler):
    server_version = 'ResidualDemoGateway/1.0'
    def _cors(self):
        origin = self.headers.get('Origin')
        if origin == ORIGIN:
            self.send_header('Access-Control-Allow-Origin', origin); self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
        self.send_header('X-Frame-Options', 'DENY')
    def _send(self, code, obj):
        raw = b'' if obj is None else json.dumps(obj, separators=(',', ':')).encode(); self.send_response(code); self._cors(); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def _body(self):
        try:
            n = int(self.headers.get('Content-Length','0'))
        except ValueError as exc:
            raise RequestTooLarge('invalid content length') from exc
        if n < 0 or n > MAX_BODY_BYTES:
            raise RequestTooLarge('request body too large')
        return self.rfile.read(n)
    def _dispatch(self, method):
        headers = {k.lower(): v for k, v in self.headers.items()}
        try:
            body = self._body() if method == 'POST' else b''
            code, obj = _route(method, urllib.parse.urlsplit(self.path).path, headers, body)
        except RequestTooLarge as e:
            code, obj = 413, {'error': {'message': str(e)}}
        self._send(code, obj)
    def do_OPTIONS(self): self._dispatch('OPTIONS')
    def do_GET(self): self._dispatch('GET')
    def do_POST(self): self._dispatch('POST')
    def do_DELETE(self): self._dispatch('DELETE')
    def log_message(self, fmt, *args): pass


def main():
    host = os.getenv('HOST','0.0.0.0'); port = int(os.getenv('PORT','8080'))
    _db().close(); ThreadingHTTPServer((host, port), Handler).serve_forever()

if __name__ == '__main__': main()
