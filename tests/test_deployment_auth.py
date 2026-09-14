import asyncio
import json
import tempfile
import time
import unittest

from residual import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
from residual.core import canonical
from residual.hitl.gateway import HITLEscalationGateway, HITLStatus

try:
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from residual.hitl.auth import OIDCAuthenticator, AuthenticationError
    from aiohttp import web, ClientSession
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False


def goal():
    return GoalSpec('review-goal', 'Review a held change',
        (SuccessCriterion('check', CheckType.MECHANICAL, 'Check', 'host'),),
        1, 100, 30, AmendmentRule(('operator',)))


@unittest.skipUnless(HAS_AUTH, 'install the hitl extra')
class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key())), 'kid': 'test-key', 'alg': 'RS256'}

    def auth(self):
        return OIDCAuthenticator(issuer='https://identity.example.test/tenant', audience='residual-review', jwks={'keys':[self.jwk]})

    def token(self, **changes):
        claims = {'iss':'https://identity.example.test/tenant', 'aud':'residual-review', 'sub':'operator-123',
                  'iat':int(time.time())-1, 'exp':int(time.time())+120, 'roles':['operator'], 'scope':'residual:review'}
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm='RS256', headers={'kid':'test-key'})

    def test_signed_token_claims_fail_closed(self):
        auth = self.auth()
        self.assertEqual(auth.principal(self.token()).subject, 'operator-123')
        for claims in ({'iss':'https://identity.example.test'}, {'aud':'other'}, {'exp':0}, {'roles':['admin']},
                       {'iat':time.time()-2000}, {'scope':'read'}, {'sub':''}, {'exp':float('nan')}, {'roles':'operator'}):
            with self.subTest(claims=claims), self.assertRaises(AuthenticationError):
                auth.principal(self.token(**claims))
        with self.assertRaises(AuthenticationError):
            auth.principal(jwt.encode({'sub':'operator'}, 'wrong-secret-that-is-at-least-32-bytes', algorithm='HS256', headers={'kid':'test-key'}))
        auth._loaded_at -= 4000
        with self.assertRaises(AuthenticationError): auth.principal(self.token())

    def test_challenge_binding_audit_denial_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            auth = self.auth()
            gateway = HITLEscalationGateway(b'k'*32, directory, authenticate=auth)
            first = gateway.generate_challenge('task', {'command':'review-only'}, 'operator_required', goal())
            second = gateway.generate_challenge('other', {}, 'operator_required', goal())
            def intent(cid, sig, decision='approve'):
                return canonical({'access_token':self.token(), 'challenge_id':cid, 'challenge_signature':sig, 'decision':decision})
            wrong = gateway.verify_approval(second.challenge_id, intent(first.challenge_id,first.signature), 'operator', ('operator',))
            self.assertEqual(wrong, HITLStatus.DENIED)
            body = intent(first.challenge_id,first.signature)
            self.assertEqual(gateway.verify_approval(first.challenge_id, body, 'operator', ('operator',)), HITLStatus.APPROVED)
            self.assertEqual(gateway.verify_approval(first.challenge_id, body, 'operator', ('operator',)), HITLStatus.DENIED)
            again = HITLEscalationGateway(b'k'*32, directory, authenticate=auth)
            record = again.get_challenge(first.challenge_id)
            self.assertEqual(record['resolution']['subject'], 'operator-123')
            self.assertNotIn('access_token', canonical(record))
            denied = again.submit_decision(second.challenge_id, intent(second.challenge_id,second.signature,'deny'), 'operator', ('operator',), decision='deny')
            self.assertEqual(denied, (True,HITLStatus.DENIED))
            self.assertEqual(again.get_challenge(second.challenge_id)['status'], 'denied')
            self.assertEqual(again.list_challenges(('other',))['challenges'], [])

    def test_expiry_persisted_on_read(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = HITLEscalationGateway(b'k'*32, directory, validity_window_s=.001, authenticate=self.auth())
            challenge = gateway.generate_challenge('task', {}, 'review', goal())
            time.sleep(.003)
            self.assertEqual(gateway.get_challenge(challenge.challenge_id)['status'], 'expired')


@unittest.skipUnless(HAS_AUTH, 'install hitl extra')
class ReviewHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_http_review_security_and_decision(self):
        from residual.hitl.server import create_app
        import socket
        helper = AuthenticationTests(); AuthenticationTests.setUpClass()
        with tempfile.TemporaryDirectory() as directory:
            auth = helper.auth(); gateway = HITLEscalationGateway(b'k'*32, directory, authenticate=auth)
            challenge = gateway.generate_challenge('task', {'text':'<script>untrusted</script>'}, 'review', goal())
            sock = socket.socket(); sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
            origin = f'http://127.0.0.1:{port}'
            runner = web.AppRunner(create_app(gateway, auth, origin=origin), access_log=None)
            await runner.setup(); site = web.SockSite(runner,sock); await site.start()
            try:
                async with ClientSession() as client:
                    async with client.get(origin+'/api/challenges') as response: self.assertEqual(response.status,401)
                    headers = {'Authorization':'Bearer '+helper.token()}
                    async with client.get(origin+'/api/challenges',headers={**headers,'Origin':'https://evil.invalid'}) as response: self.assertEqual(response.status,403)
                    async with client.get(origin+'/api/challenges',headers=headers) as response:
                        self.assertEqual(response.status,200); self.assertEqual(len((await response.json())['challenges']),1)
                        self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
                    body = {'decision':'approve','role':'operator','challenge_signature':challenge.signature}
                    endpoint = origin+f'/api/challenges/{challenge.challenge_id}/decision'
                    async with client.post(endpoint,headers=headers,json=body) as response:
                        self.assertEqual(response.status,200); self.assertFalse((await response.json())['execution_resumed'])
                    async with client.post(endpoint,headers=headers,json=body) as response: self.assertEqual(response.status,409)
            finally: await runner.cleanup()
