import importlib.util, os, tempfile, time, unittest
from pathlib import Path
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / 'demo' / 'cloud_gateway' / 'server.py'

class DemoGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['RESIDUAL_DEMO_DB'] = str(Path(self.tmp.name) / 'gateway.sqlite3')
        os.environ['FREELLMAPI_BASE_URL'] = 'https://freellm.invalid'
        os.environ['FREELLMAPI_ADMIN_EMAIL'] = 'demo@example.invalid'
        os.environ['FREELLMAPI_ADMIN_PASSWORD'] = 'not-a-real-secret'
        os.environ['TAILSCALE_OAUTH_CLIENT_ID'] = 'test'
        os.environ['TAILSCALE_OAUTH_CLIENT_SECRET'] = 'test'
        spec = importlib.util.spec_from_file_location('demo_gateway_under_test', MODULE)
        self.g = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.g)
        self.g.DB_PATH = Path(os.environ['RESIDUAL_DEMO_DB'])
        self.g.MAX_REQUESTS = 2; self.g.MAX_TOKENS = 300; self.g.MAX_OUTPUT = 200; self.g.TTL = 60
        self.g.MAX_ACTIVE_SESSIONS = 32; self.g.MAX_SESSIONS_PER_HOUR = 64

    def tearDown(self): self.tmp.cleanup()

    def test_session_mints_bounded_opaque_token_and_upstream_profile(self):
        with mock.patch.object(self.g, '_freellm_create_profile', return_value=(7, 'sk-cp-upstream-secret')), \
             mock.patch.object(self.g, '_tailscale_auth_key', return_value='tskey-auth-ephemeral'):
            out = self.g._new_session()
        self.assertTrue(out['token'].startswith('rdemo_'))
        self.assertNotIn('sk-cp-', repr(out))
        self.assertEqual(out['tailscaleAuthKey'], 'tskey-auth-ephemeral')
        row = self.g._db().execute('SELECT * FROM sessions WHERE token=?', (out['token'],)).fetchone()
        self.assertEqual(row['profile_key'], 'sk-cp-upstream-secret')
        self.assertEqual(row['requests_left'], 2)

    def test_budget_is_reserved_atomically(self):
        with mock.patch.object(self.g, '_freellm_create_profile', return_value=(7, 'sk-cp-secret')), \
             mock.patch.object(self.g, '_tailscale_auth_key', return_value='tskey-auth-x'):
            out = self.g._new_session()
        key, amount = self.g._reserve(out['token'], 180)
        self.assertEqual((key, amount), ('sk-cp-secret', 180))
        with self.assertRaises(PermissionError): self.g._reserve(out['token'], 180)

    def test_expired_session_revokes_profile(self):
        with mock.patch.object(self.g, '_freellm_create_profile', return_value=(9, 'sk-cp-secret')), \
             mock.patch.object(self.g, '_tailscale_auth_key', return_value='tskey-auth-x'):
            out = self.g._new_session()
        conn = self.g._db(); conn.execute('UPDATE sessions SET expires=? WHERE token=?', (int(time.time())-1, out['token'])); conn.commit(); conn.close()
        with mock.patch.object(self.g, '_freellm_delete_profile') as delete:
            with self.assertRaises(PermissionError): self.g._reserve(out['token'], 1)
            delete.assert_called_with(9)

    def test_session_creation_has_global_active_cap(self):
        self.g.MAX_ACTIVE_SESSIONS = 1
        with mock.patch.object(self.g, '_freellm_create_profile', return_value=(7, 'sk-cp-secret')) as create, \
             mock.patch.object(self.g, '_tailscale_auth_key', return_value='tskey-auth-x'):
            self.g._new_session()
            with self.assertRaises(self.g.DemoCapacityError):
                self.g._new_session()
        self.assertEqual(create.call_count, 1)

    def test_session_creation_has_hourly_issuance_cap(self):
        self.g.MAX_ACTIVE_SESSIONS = 99
        self.g.MAX_SESSIONS_PER_HOUR = 1
        with mock.patch.object(self.g, '_freellm_create_profile', return_value=(7, 'sk-cp-secret')) as create, \
             mock.patch.object(self.g, '_tailscale_auth_key', return_value='tskey-auth-x'):
            first = self.g._new_session()
            self.g._revoke(first['token'])
            with self.assertRaises(self.g.DemoCapacityError):
                self.g._new_session()
        self.assertEqual(create.call_count, 1)

    def test_gateway_database_is_private(self):
        conn = self.g._db(); conn.close()
        self.assertEqual(os.stat(self.g.DB_PATH).st_mode & 0o077, 0)

    def test_capacity_error_maps_to_http_429(self):
        with mock.patch.object(self.g, '_new_session', side_effect=self.g.DemoCapacityError('full')):
            code, body = self.g._route('POST', '/v1/demo/session', {}, b'')
        self.assertEqual(code, 429)
        self.assertIn('capacity', body['error']['message'].replace('full', 'capacity'))

if __name__ == '__main__': unittest.main()
