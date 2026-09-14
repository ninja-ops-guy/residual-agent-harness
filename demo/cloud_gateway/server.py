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
FREELLM = os.environ.get('FREELLMAPI_BASE_URL', '').rstrip('/')
FREELLM_EMAIL = os.environ.get('FREELLMAPI_ADMIN_EMAIL', '')
FREELLM_PASSWORD = os.environ.get('FREELLMAPI_ADMIN_PASSWORD', '')
TS_CLIENT_ID = os.environ.get('TAILSCALE_OAUTH_CLIENT_ID', '')
TS_CLIENT_SECRET = os.environ.get('TAILSCALE_OAUTH_CLIENT_SECRET', '')
TS_TAG = os.getenv('TAILSCALE_DEMO_TAG', 'tag:residual-demo')
TS_TAILNET = os.getenv('TAILSCALE_TAILNET', '-')
ALLOWED_MODELS = {'auto', 'auto:fast', 'auto:smart'}
_lock = threading.Lock()


def _db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
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
        raw = r.read()
        return r.status, dict(r.headers), json.loads(raw or b'{}')


def _form(url, body, headers=None, timeout=20):
    data = urllib.parse.urlencode(body).encode()
    hdr = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    if headers: hdr.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b'{}')


def _freellm_admin_token():
    _, _, out = _json(f'{FREELLM}/api/auth/login', 'POST', {'email': FREELLM_EMAIL, 'password': FREELLM_PASSWORD})
    return out['token']


def _freellm_create_profile(name):
    token = _freellm_admin_token()
    _, _, out = _json(f'{FREELLM}/api/client-profiles', 'POST', {'name': name, 'systemPrompt': 'RESIDUAL public demo session. Follow the user task, return concise text, and do not claim verification authority.'}, {'Authorization': f'Bearer {token}'})
    return int(out['id']), out['key']


def _freellm_delete_profile(profile_id):
    try:
        token = _freellm_admin_token()
        _json(f'{FREELLM}/api/client-profiles/{profile_id}', 'DELETE', headers={'Authorization': f'Bearer {token}'})
    except Exception:
        pass


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
    token = 'rdemo_' + secrets.token_urlsafe(32)
    profile_id, profile_key = _freellm_create_profile('residual-demo-' + token[-8:])
    try:
        ts_key = _tailscale_auth_key()
    except Exception:
        _freellm_delete_profile(profile_id)
        raise
    now = int(time.time())
    with _lock:
        conn = _db(); conn.execute(
            'INSERT INTO sessions(token,created,expires,requests_left,tokens_left,profile_id,profile_key) VALUES(?,?,?,?,?,?,?)',
            (token, now, now + TTL, MAX_REQUESTS, MAX_TOKENS, profile_id, profile_key)); conn.commit(); conn.close()
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


class Handler(BaseHTTPRequestHandler):
    server_version = 'ResidualDemoGateway/1.0'
    def _cors(self):
        origin = self.headers.get('Origin')
        if origin == ORIGIN:
            self.send_header('Access-Control-Allow-Origin', origin); self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Cache-Control', 'no-store')
    def _send(self, code, obj):
        raw = json.dumps(obj, separators=(',', ':')).encode(); self.send_response(code); self._cors(); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def _body(self):
        n = int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def _token(self):
        auth = self.headers.get('Authorization',''); return auth[7:] if auth.startswith('Bearer ') else ''
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path == '/health': return self._send(200, {'ok': True, 'configured': bool(FREELLM and TS_CLIENT_ID)})
        return self._send(404, {'error':'not found'})
    def do_POST(self):
        try:
            if self.path == '/v1/demo/session': return self._send(201, _new_session())
            if self.path == '/v1/chat/completions':
                body = self._body(); model = body.get('model','auto:fast')
                if model not in ALLOWED_MODELS: return self._send(400, {'error': {'message':'model not allowed'}})
                key, reserved = _reserve(self._token(), body.get('max_tokens', body.get('max_completion_tokens', 256)))
                body['model'] = model; body['max_tokens'] = min(reserved, MAX_OUTPUT); body.pop('max_completion_tokens', None)
                _, _, out = _json(f'{FREELLM}/v1/chat/completions', 'POST', body, {'Authorization': f'Bearer {key}'}, timeout=45)
                return self._send(200, out)
            return self._send(404, {'error':'not found'})
        except PermissionError as e: return self._send(401, {'error': {'message': str(e)}})
        except Exception as e: return self._send(503, {'error': {'message':'demo cloud unavailable', 'detail': type(e).__name__}})
    def do_DELETE(self):
        if self.path != '/v1/demo/session': return self._send(404, {'error':'not found'})
        _revoke(self._token()); return self._send(200, {'revoked': True})
    def log_message(self, fmt, *args): pass


def main():
    host = os.getenv('HOST','0.0.0.0'); port = int(os.getenv('PORT','8080'))
    _db().close(); ThreadingHTTPServer((host, port), Handler).serve_forever()

if __name__ == '__main__': main()
