"""Tests for SPEC-ENT-001: Enterprise Identity and Access Management.

Covers ENT1-R1 through ENT1-R8 using deterministic in-memory fixtures
and a manually advanced clock.
"""
from __future__ import annotations

import unittest

from residual.core import ContractError
from residual.iam import (
    ABACEvaluator,
    ABACPolicy,
    Condition,
    EventLog,
    JITManager,
    MFAManager,
    OIDCClient,
    Permission,
    Role,
    RoleRegistry,
    SAMLSettings,
    ServiceAccountManager,
    SessionManager,
    SessionPolicy,
    UserAttributes,
)
from residual.iam import abac, events, oidc, rbac, saml, service_accounts
from residual.iam.crypto import (
    jwt_encode,
    rsa_generate_keypair,
    rsa_pkcs1v15_sign_sha256,
    rsa_pkcs1v15_verify_sha256,
)

NOW = 1_700_000_000
IP = "203.0.113.7"
IP2 = "203.0.113.8"


class Clock:
    def __init__(self, start=NOW):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


# ---------------------------------------------------------------------------
# ENT1-R1: SAML 2.0 and OIDC
# ---------------------------------------------------------------------------

class TestSAML(unittest.TestCase):
    """Implements ENT1-R1 (SAML 2.0)."""

    def setUp(self):
        self.key = rsa_generate_keypair(1024)
        self.settings = SAMLSettings(
            idp_entity_id="http://www.okta.com/acme",
            idp_sso_url="https://acme.okta.com/app/x/sso/saml",
            sp_entity_id="residual-station",
            signature_key=self.key.public_key,
        )

    def _response(self, **kwargs):
        params = dict(
            issuer="http://www.okta.com/acme",
            audience="residual-station",
            name_id="alice@acme.com",
            not_before=NOW - 60,
            not_on_or_after=NOW + 300,
            attributes={"department": "engineering", "clearance_level": "3"},
            session_index="s1",
            authn_instant=NOW - 60,
            sign_key=self.key,
        )
        params.update(kwargs)
        return saml.build_response(**params)

    def test_parse_valid_response(self):
        identity = saml.parse_saml_response(self._response(), self.settings, now=NOW)
        self.assertEqual(identity.subject, "alice@acme.com")
        self.assertEqual(identity.attributes["department"], "engineering")
        self.assertEqual(identity.session_index, "s1")

    def test_tampered_response_rejected(self):
        xml = self._response().replace("alice@acme.com", "mallory@evil.com")
        with self.assertRaises(ContractError):
            saml.parse_saml_response(xml, self.settings, now=NOW)

    def test_unsigned_response_rejected_when_key_configured(self):
        xml = self._response(sign_key=None)
        with self.assertRaises(ContractError):
            saml.parse_saml_response(xml, self.settings, now=NOW)

    def test_expired_assertion_rejected(self):
        xml = self._response(not_before=NOW - 600, not_on_or_after=NOW - 300)
        with self.assertRaises(ContractError):
            saml.parse_saml_response(xml, self.settings, now=NOW)

    def test_not_yet_valid_rejected(self):
        xml = self._response(not_before=NOW + 600, not_on_or_after=NOW + 900)
        with self.assertRaises(ContractError):
            saml.parse_saml_response(xml, self.settings, now=NOW)

    def test_wrong_issuer_rejected(self):
        with self.assertRaises(ContractError):
            saml.parse_saml_response(self._response(issuer="urn:evil"), self.settings, now=NOW)

    def test_wrong_audience_rejected(self):
        with self.assertRaises(ContractError):
            saml.parse_saml_response(self._response(audience="other-sp"), self.settings, now=NOW)

    def test_malformed_xml_rejected(self):
        with self.assertRaises(ContractError):
            saml.parse_saml_response("<not-xml", self.settings, now=NOW)

    def test_dtd_and_entity_xml_rejected_before_saml_processing(self):
        xml = """<!DOCTYPE samlp:Response [
<!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
&xxe;
</samlp:Response>"""
        with self.assertRaises(ContractError):
            saml.parse_saml_response(xml, self.settings, now=NOW)

    def test_oversized_saml_response_rejected(self):
        with self.assertRaises(ContractError):
            saml.parse_saml_response(" " + ("x" * (saml.MAX_SAML_XML_BYTES + 1)),
                                     self.settings, now=NOW)


    def test_all_providers_have_presets_without_custom_config(self):
        for name in ("okta", "azure_ad", "ping", "auth0", "onelogin"):
            self.assertIn(name, saml.SAML_PROVIDERS)
            settings = saml.provider_settings(name, dict(
                idp_entity_id="idp", idp_sso_url="https://idp.example/sso",
                sp_entity_id="residual",
            ))
            self.assertIsInstance(settings, SAMLSettings)
        with self.assertRaises(ContractError):
            saml.provider_settings("unknown", dict(
                idp_entity_id="x", idp_sso_url="y", sp_entity_id="z"))


class TestOIDC(unittest.TestCase):
    """Implements ENT1-R1 (OpenID Connect)."""

    ISSUER = "https://acme.okta.com/oauth2/default"
    CLIENT = "residual-station"

    def setUp(self):
        self.key = rsa_generate_keypair(1024)
        self.secret = b"test-hmac-secret"
        self.settings = oidc.provider_settings(
            "okta", issuer=self.ISSUER, client_id=self.CLIENT)

    def _client(self, provider):
        return OIDCClient(self.settings, provider)

    def _payload(self, **kwargs):
        payload = dict(
            iss=self.ISSUER, sub="alice@acme.com", aud=self.CLIENT,
            iat=NOW - 10, exp=NOW + 600, amr=["pwd", "mfa"],
            department="engineering",
        )
        payload.update(kwargs)
        return payload

    def test_rs256_token_accepted(self):
        token = jwt_encode(self._payload(), self.key, alg="RS256", headers={"kid": "k1"})
        identity = self._client({"k1": self.key.public_key}).authenticate(token, now=NOW)
        self.assertEqual(identity.subject, "alice@acme.com")
        self.assertEqual(identity.attributes["department"], "engineering")
        self.assertIn("mfa", identity.amr)

    def test_hs256_token_accepted(self):
        token = jwt_encode(self._payload(), self.secret, alg="HS256")
        identity = self._client(lambda kid: self.secret).authenticate(token, now=NOW)
        self.assertEqual(identity.subject, "alice@acme.com")

    def test_expired_token_rejected(self):
        token = jwt_encode(self._payload(exp=NOW - 120), self.secret)
        with self.assertRaises(ContractError):
            self._client(lambda kid: self.secret).authenticate(token, now=NOW)

    def test_bad_signature_rejected(self):
        token = jwt_encode(self._payload(), b"other-secret")
        with self.assertRaises(ContractError):
            self._client(lambda kid: self.secret).authenticate(token, now=NOW)

    def test_wrong_issuer_and_audience_rejected(self):
        with self.assertRaises(ContractError):
            token = jwt_encode(self._payload(iss="https://evil.example"), self.secret)
            self._client(lambda kid: self.secret).authenticate(token, now=NOW)
        with self.assertRaises(ContractError):
            token = jwt_encode(self._payload(aud="other-app"), self.secret)
            self._client(lambda kid: self.secret).authenticate(token, now=NOW)

    def test_nonce_enforced(self):
        token = jwt_encode(self._payload(nonce="n-1"), self.secret)
        client = self._client(lambda kid: self.secret)
        client.authenticate(token, now=NOW, nonce="n-1")
        with self.assertRaises(ContractError):
            client.authenticate(token, now=NOW, nonce="n-2")

    def test_alg_none_rejected(self):
        from residual.iam.crypto import b64url_encode
        import json
        header = b64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        body = b64url_encode(json.dumps(self._payload()).encode())
        with self.assertRaises(ContractError):
            self._client(lambda kid: self.secret).authenticate(f"{header}.{body}.", now=NOW)

    def test_all_oidc_providers_have_presets(self):
        for name in ("okta", "azure_ad", "ping", "auth0", "onelogin"):
            self.assertIn(name, oidc.OIDC_PROVIDERS)
            settings = oidc.provider_settings(name, issuer="https://idp.example", client_id="c")
            self.assertTrue(settings.jwks_url.startswith("https://idp.example"))
        with self.assertRaises(ContractError):
            oidc.provider_settings("unknown", issuer="x", client_id="c")


class TestCrypto(unittest.TestCase):
    """Implements ENT1-R1 (signing primitives)."""

    def test_rsa_sign_verify_roundtrip(self):
        key = rsa_generate_keypair(1024)
        sig = rsa_pkcs1v15_sign_sha256(key, b"message")
        self.assertTrue(rsa_pkcs1v15_verify_sha256(key.public_key, b"message", sig))
        self.assertFalse(rsa_pkcs1v15_verify_sha256(key.public_key, b"other", sig))


# ---------------------------------------------------------------------------
# ENT1-R2: RBAC
# ---------------------------------------------------------------------------

class TestRBAC(unittest.TestCase):
    """Implements ENT1-R2."""

    def setUp(self):
        self.registry = RoleRegistry()
        self.registry.define_role(Role(
            "engineer",
            frozenset({
                Permission(rbac.PERMISSION_TASK_TYPE, "code_change"),
                Permission(rbac.PERMISSION_SWARM, "*"),
                Permission(rbac.PERMISSION_RECEIPT_VISIBILITY, "team"),
            }),
        ))
        self.registry.define_role(Role(
            "approver",
            frozenset({Permission(rbac.PERMISSION_HITL_APPROVAL)}),
        ))
        self.registry.define_role(Role(
            "platform_admin",
            frozenset({
                Permission(rbac.PERMISSION_MODULE_INSTALLATION),
                Permission(rbac.PERMISSION_POLICY_MODIFICATION),
            }),
        ))
        self.registry.assign("alice", "engineer")
        self.registry.assign("bob", "approver")

    def test_scoped_task_type_permission(self):
        self.assertTrue(self.registry.is_allowed("alice", rbac.PERMISSION_TASK_TYPE, "code_change"))
        self.assertFalse(self.registry.is_allowed("alice", rbac.PERMISSION_TASK_TYPE, "db_migration"))

    def test_wildcard_scope(self):
        self.assertTrue(self.registry.is_allowed("alice", rbac.PERMISSION_SWARM, "swarm-9"))

    def test_hitl_approval_only_for_approver(self):
        self.assertTrue(self.registry.is_allowed("bob", rbac.PERMISSION_HITL_APPROVAL))
        self.assertFalse(self.registry.is_allowed("alice", rbac.PERMISSION_HITL_APPROVAL))

    def test_receipt_visibility_scope(self):
        self.assertTrue(self.registry.is_allowed("alice", rbac.PERMISSION_RECEIPT_VISIBILITY, "team"))
        self.assertFalse(self.registry.is_allowed("alice", rbac.PERMISSION_RECEIPT_VISIBILITY, "org"))

    def test_module_and_policy_permissions(self):
        self.registry.assign("carol", "platform_admin")
        self.assertTrue(self.registry.is_allowed("carol", rbac.PERMISSION_MODULE_INSTALLATION))
        self.assertTrue(self.registry.is_allowed("carol", rbac.PERMISSION_POLICY_MODIFICATION))
        self.assertFalse(self.registry.is_allowed("alice", rbac.PERMISSION_MODULE_INSTALLATION))

    def test_unassign_removes_permission(self):
        self.registry.unassign("bob", "approver")
        self.assertFalse(self.registry.is_allowed("bob", rbac.PERMISSION_HITL_APPROVAL))

    def test_unknown_role_and_category_rejected(self):
        with self.assertRaises(ContractError):
            self.registry.assign("alice", "nonexistent")
        with self.assertRaises(ContractError):
            Permission("not_a_category")


# ---------------------------------------------------------------------------
# ENT1-R3: ABAC
# ---------------------------------------------------------------------------

class TestABAC(unittest.TestCase):
    """Implements ENT1-R3."""

    def setUp(self):
        self.attrs = UserAttributes(
            department="engineering", region="eu", clearance_level=3,
            employment_status="active", custom={"project": "apollo"},
        )
        self.evaluator = ABACEvaluator((
            ABACPolicy(
                "eng-eu-swarm", abac.ALLOW, rbac.PERMISSION_SWARM,
                conditions=(
                    Condition("department", "eq", "engineering"),
                    Condition("region", "in", ["eu", "us"]),
                    Condition("clearance_level", "gte", 2),
                    Condition("employment_status", "eq", "active"),
                ),
            ),
            ABACPolicy(
                "contractor-deny-install", abac.DENY, rbac.PERMISSION_MODULE_INSTALLATION,
                conditions=(Condition("employment_status", "eq", "contractor"),),
            ),
            ABACPolicy(
                "staff-install", abac.ALLOW, rbac.PERMISSION_MODULE_INSTALLATION,
                conditions=(Condition("employment_status", "eq", "active"),
                            Condition("clearance_level", "gte", 4)),
            ),
            ABACPolicy(
                "apollo-receipts", abac.ALLOW, rbac.PERMISSION_RECEIPT_VISIBILITY,
                conditions=(Condition("project", "eq", "apollo"),), scope="team",
            ),
        ))

    def test_all_core_attributes_evaluated(self):
        decision = self.evaluator.evaluate(self.attrs, rbac.PERMISSION_SWARM)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_allow, ("eng-eu-swarm",))

    def test_missing_attribute_fails_condition(self):
        attrs = UserAttributes(department="engineering")
        self.assertFalse(self.evaluator.evaluate(attrs, rbac.PERMISSION_SWARM).allowed)

    def test_deny_overrides_allow(self):
        attrs = UserAttributes(employment_status="contractor", clearance_level=5)
        decision = self.evaluator.evaluate(attrs, rbac.PERMISSION_MODULE_INSTALLATION)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.matched_deny, ("contractor-deny-install",))

    def test_clearance_threshold(self):
        self.assertFalse(self.evaluator.evaluate(self.attrs, rbac.PERMISSION_MODULE_INSTALLATION).allowed)
        senior = UserAttributes(employment_status="active", clearance_level=4)
        self.assertTrue(self.evaluator.evaluate(senior, rbac.PERMISSION_MODULE_INSTALLATION).allowed)

    def test_custom_attribute_from_idp(self):
        self.assertTrue(self.evaluator.evaluate(self.attrs, rbac.PERMISSION_RECEIPT_VISIBILITY, "team").allowed)
        other = UserAttributes(custom={"project": "zeus"})
        self.assertFalse(self.evaluator.evaluate(other, rbac.PERMISSION_RECEIPT_VISIBILITY, "team").allowed)

    def test_scope_mismatch_not_applied(self):
        self.assertFalse(
            self.evaluator.evaluate(self.attrs, rbac.PERMISSION_RECEIPT_VISIBILITY, "org").allowed)

    def test_from_idp_attributes(self):
        attrs = UserAttributes.from_idp({
            "department": "engineering", "region": "eu", "clearance_level": "3",
            "employment_status": "active", "project": "apollo",
        })
        self.assertEqual(attrs.clearance_level, 3)
        self.assertEqual(attrs.custom["project"], "apollo")
        self.assertTrue(self.evaluator.evaluate(attrs, rbac.PERMISSION_SWARM).allowed)


# ---------------------------------------------------------------------------
# ENT1-R4: Just-In-Time access
# ---------------------------------------------------------------------------

class TestJIT(unittest.TestCase):
    """Implements ENT1-R4."""

    def setUp(self):
        self.clock = Clock()
        self.log = EventLog(self.clock)
        self.registry = RoleRegistry()
        self.jit = JITManager(self.registry, self.log, self.clock)
        self.jit.add_approver("manager")

    def _request(self, **kwargs):
        params = dict(scope="*", reason="incident fix", duration_seconds=3600)
        params.update(kwargs)
        return self.jit.request_elevation("alice", rbac.PERMISSION_HITL_APPROVAL, **params)

    def test_approved_elevation_grants_access(self):
        request = self._request(task_id="task-1")
        self.assertFalse(self.jit.is_elevated("alice", rbac.PERMISSION_HITL_APPROVAL))
        grant = self.jit.approve(request.request_id, "manager", IP)
        self.assertTrue(self.jit.is_elevated("alice", rbac.PERMISSION_HITL_APPROVAL))
        self.assertEqual(grant.approver_id, "manager")
        self.assertEqual(grant.expires_at, NOW + 3600)

    def test_elevation_expires_automatically(self):
        request = self._request()
        self.jit.approve(request.request_id, "manager", IP)
        self.clock.advance(3601)
        self.assertFalse(self.jit.is_elevated("alice", rbac.PERMISSION_HITL_APPROVAL))
        self.assertEqual(self.jit.active_grants("alice"), ())

    def test_elevation_is_observed_and_receipted(self):
        request = self._request()
        self.jit.approve(request.request_id, "manager", IP)
        obs = self.log.observations[-1]
        self.assertEqual(obs.event_type, events.EVENT_ELEVATION)
        self.assertEqual(obs.subject_id, "alice")
        self.assertEqual(obs.source_ip, IP)
        self.assertEqual(obs.details["approver"], "manager")
        self.assertEqual(len(self.log.receipts), len(self.log.observations))
        self.assertTrue(self.log.verify_chain())

    def test_approval_requires_designated_approver(self):
        request = self._request()
        with self.assertRaises(ContractError):
            self.jit.approve(request.request_id, "mallory", IP)
        obs = self.log.observations[-1]
        self.assertEqual(obs.event_type, events.EVENT_ACCESS_DENIED)
        self.assertEqual(obs.result, "deny")

    def test_approver_cannot_self_approve(self):
        self.jit.add_approver("alice")
        request = self._request()
        with self.assertRaises(ContractError):
            self.jit.approve(request.request_id, "alice", IP)

    def test_denial_is_observed(self):
        request = self._request()
        self.jit.deny(request.request_id, "manager", IP)
        self.assertEqual(self.log.observations[-1].result, "deny")

    def test_task_and_window_scoping(self):
        request = self.jit.request_elevation(
            "alice", rbac.PERMISSION_MODULE_INSTALLATION,
            scope="mod-x", reason="install fix", duration_seconds=60, task_id="task-2")
        self.jit.approve(request.request_id, "manager", IP)
        self.assertTrue(self.jit.is_elevated("alice", rbac.PERMISSION_MODULE_INSTALLATION, "mod-x"))
        self.assertFalse(self.jit.is_elevated("alice", rbac.PERMISSION_MODULE_INSTALLATION, "mod-y"))

    def test_duration_bounds(self):
        with self.assertRaises(ContractError):
            self._request(duration_seconds=0)
        with self.assertRaises(ContractError):
            self._request(duration_seconds=25 * 3600)

    def test_is_allowed_combines_rbac_and_jit(self):
        self.registry.define_role(Role("dev", frozenset({Permission(rbac.PERMISSION_TASK_TYPE, "build")})))
        self.registry.assign("alice", "dev")
        self.assertTrue(self.jit.is_allowed("alice", rbac.PERMISSION_TASK_TYPE, "build"))
        request = self._request()
        self.jit.approve(request.request_id, "manager", IP)
        self.assertTrue(self.jit.is_allowed("alice", rbac.PERMISSION_HITL_APPROVAL))


# ---------------------------------------------------------------------------
# ENT1-R5: Service accounts
# ---------------------------------------------------------------------------

class TestServiceAccounts(unittest.TestCase):
    """Implements ENT1-R5."""

    def setUp(self):
        self.clock = Clock()
        self.log = EventLog(self.clock)
        self.manager = ServiceAccountManager(self.log)

    def _create(self):
        return self.manager.create(
            "ci-bot", "alice",
            {Permission(rbac.PERMISSION_TASK_TYPE, "build")},
        )

    def test_scoped_permissions_enforced(self):
        account, _ = self._create()
        self.assertTrue(self.manager.authorize(account, rbac.PERMISSION_TASK_TYPE, "build", IP))
        self.assertFalse(self.manager.authorize(account, rbac.PERMISSION_TASK_TYPE, "deploy", IP))

    def test_never_admin(self):
        with self.assertRaises(ContractError):
            self.manager.create("evil-bot", "alice",
                                {Permission(rbac.PERMISSION_POLICY_MODIFICATION)})
        with self.assertRaises(ContractError):
            self.manager.create("evil-bot", "alice",
                                {Permission(rbac.PERMISSION_MODULE_INSTALLATION)})

    def test_credential_rotation_invalidates_old(self):
        account, old_credential = self._create()
        self.assertEqual(self.manager.authenticate(old_credential).account_id, account.account_id)
        rotated, new_credential = self.manager.rotate(account.account_id)
        self.assertEqual(rotated.credential_generation, 2)
        with self.assertRaises(ContractError):
            self.manager.authenticate(old_credential)
        self.assertEqual(self.manager.authenticate(new_credential).account_id, account.account_id)

    def test_every_action_is_observed(self):
        account, _ = self._create()
        self.manager.authorize(account, rbac.PERMISSION_TASK_TYPE, "build", IP)
        self.manager.authorize(account, rbac.PERMISSION_SWARM, "*", IP)
        self.assertEqual(len(self.log.observations), 2)
        self.assertEqual(self.log.observations[0].event_type, events.EVENT_SERVICE_ACTION)
        self.assertEqual(self.log.observations[1].result, "deny")

    def test_distinguishable_from_humans_in_receipts(self):
        account, _ = self._create()
        self.log.record(events.EVENT_LOGIN, "alice", IP, "allow")
        self.manager.authorize(account, rbac.PERMISSION_TASK_TYPE, "build", IP)
        human_receipt, service_receipt = self.log.receipts
        self.assertEqual(human_receipt.subject_type, events.SUBJECT_HUMAN)
        self.assertEqual(service_receipt.subject_type, events.SUBJECT_SERVICE)
        self.assertEqual(self.log.observations[-1].subject_type, events.SUBJECT_SERVICE)


# ---------------------------------------------------------------------------
# ENT1-R6: Observation and receipts of auth events
# ---------------------------------------------------------------------------

class TestAuthEvents(unittest.TestCase):
    """Implements ENT1-R6."""

    def setUp(self):
        self.clock = Clock()
        self.log = EventLog(self.clock)

    def test_event_fields(self):
        obs, receipt = self.log.record(events.EVENT_LOGIN, "alice", IP, "allow",
                                       details={"method": "oidc"})
        self.assertEqual(obs.subject_id, "alice")
        self.assertEqual(obs.timestamp, NOW)
        self.assertEqual(obs.source_ip, IP)
        self.assertEqual(obs.result, "allow")
        self.assertEqual(receipt.subject_id, "alice")

    def test_all_auth_event_types(self):
        for event in (events.EVENT_LOGIN, events.EVENT_LOGOUT, events.EVENT_TOKEN_REFRESH,
                      events.EVENT_ELEVATION, events.EVENT_ACCESS_DENIED):
            self.log.record(event, "alice", IP, "allow")
        self.assertEqual(len(self.log.observations), 5)
        self.assertEqual(len(self.log.receipts), 5)

    def test_denial_recorded(self):
        obs, _ = self.log.record(events.EVENT_ACCESS_DENIED, "mallory", IP, "deny")
        self.assertEqual(obs.result, "deny")

    def test_invalid_ip_and_event_rejected(self):
        with self.assertRaises(ContractError):
            self.log.record(events.EVENT_LOGIN, "alice", "not-an-ip", "allow")
        with self.assertRaises(ContractError):
            self.log.record("mystery", "alice", IP, "allow")

    def test_receipt_chain_integrity(self):
        for i in range(5):
            self.log.record(events.EVENT_LOGIN, "alice", IP, "allow")
        self.assertTrue(self.log.verify_chain())
        self.assertEqual(self.log.receipts[0].previous_hash, events.GENESIS_HASH)
        for prev, cur in zip(self.log.receipts, self.log.receipts[1:]):
            self.assertEqual(cur.previous_hash, prev.receipt_hash)


# ---------------------------------------------------------------------------
# ENT1-R7: MFA
# ---------------------------------------------------------------------------

class TestMFA(unittest.TestCase):
    """Implements ENT1-R7."""

    def setUp(self):
        self.clock = Clock()
        self.mfa = MFAManager(self.clock)
        self.secret = b"0123456789abcdef"

    def test_idp_delegated_mfa_via_amr(self):
        self.mfa.require_privileged("hitl_approval", "alice", amr=("pwd", "mfa"))

    def test_idp_delegated_mfa_via_saml_context(self):
        self.mfa.require_privileged(
            "policy_modification", "alice",
            authn_context="urn:oasis:names:tc:SAML:2.0:ac:classes:Multifactor")

    def test_local_totp_flow(self):
        from residual.iam.mfa import generate_totp, verify_totp
        code = generate_totp(self.secret, NOW)
        self.assertTrue(verify_totp(self.secret, code, NOW))
        self.assertFalse(verify_totp(self.secret, "000000" if code != "000000" else "111111", NOW))
        self.assertTrue(self.mfa.verify_local("alice", self.secret, code))
        self.mfa.require_privileged("module_installation", "alice")

    def test_privileged_actions_require_mfa_regardless_of_session_age(self):
        for action in ("hitl_approval", "policy_modification", "module_installation"):
            with self.assertRaises(ContractError):
                self.mfa.require_privileged(action, "alice")
        # Even long after login (session age), MFA is still required.
        self.clock.advance(3600)
        with self.assertRaises(ContractError):
            self.mfa.require_privileged("hitl_approval", "alice")

    def test_unknown_privileged_action_rejected(self):
        with self.assertRaises(ContractError):
            self.mfa.require_privileged("read_receipts", "alice", amr=("mfa",))


# ---------------------------------------------------------------------------
# ENT1-R8: Session management
# ---------------------------------------------------------------------------

class TestSessions(unittest.TestCase):
    """Implements ENT1-R8."""

    def setUp(self):
        self.clock = Clock()
        self.log = EventLog(self.clock)
        self.policy = SessionPolicy(
            session_timeout=3600, idle_timeout=600, max_concurrent=2,
            allowed_networks=("203.0.113.0/24",),
        )
        self.manager = SessionManager(self.policy, self.log, self.clock)

    def test_create_and_validate(self):
        session = self.manager.create_session("alice", IP)
        self.assertEqual(self.manager.validate(session.session_id, IP).subject_id, "alice")

    def test_absolute_timeout(self):
        manager = SessionManager(
            SessionPolicy(session_timeout=3600, idle_timeout=3600, max_concurrent=2,
                          allowed_networks=("203.0.113.0/24",)),
            self.log, self.clock)
        session = manager.create_session("alice", IP)
        self.clock.advance(3599)
        manager.validate(session.session_id)
        self.clock.advance(2)
        with self.assertRaises(ContractError):
            manager.validate(session.session_id)

    def test_idle_timeout(self):
        session = self.manager.create_session("alice", IP)
        self.clock.advance(599)
        self.manager.touch(session.session_id, IP)
        self.clock.advance(599)
        self.manager.validate(session.session_id)
        self.clock.advance(601)
        with self.assertRaises(ContractError):
            self.manager.validate(session.session_id)

    def test_concurrent_session_limit(self):
        self.manager.create_session("alice", IP)
        self.manager.create_session("alice", IP2)
        with self.assertRaises(ContractError):
            self.manager.create_session("alice", IP)
        self.assertEqual(len(self.manager.active_sessions("alice")), 2)

    def test_ip_restriction(self):
        with self.assertRaises(ContractError):
            self.manager.create_session("alice", "198.51.100.9")
        obs = self.log.observations[-1]
        self.assertEqual(obs.event_type, events.EVENT_ACCESS_DENIED)
        self.assertEqual(obs.details["kind"], "ip_restriction")

    def test_session_bound_to_origin_ip(self):
        session = self.manager.create_session("alice", IP)
        with self.assertRaises(ContractError):
            self.manager.validate(session.session_id, IP2)

    def test_immediate_revocation_on_security_event(self):
        session = self.manager.create_session("alice", IP)
        self.manager.revoke(session.session_id, "credential leak detected")
        self.assertTrue(self.manager.is_revoked(session.session_id))
        with self.assertRaises(ContractError):
            self.manager.validate(session.session_id)
        obs = self.log.observations[-1]
        self.assertEqual(obs.event_type, events.EVENT_SESSION_REVOKED)
        self.assertEqual(obs.details["reason"], "credential leak detected")

    def test_revoke_all_sessions(self):
        self.manager.create_session("alice", IP)
        self.manager.create_session("alice", IP2)
        self.assertEqual(self.manager.revoke_all("alice", "account compromise"), 2)
        self.assertEqual(self.manager.active_sessions("alice"), ())

    def test_logout_observed(self):
        session = self.manager.create_session("alice", IP)
        self.manager.logout(session.session_id)
        self.assertEqual(self.log.observations[-1].event_type, events.EVENT_LOGOUT)
        with self.assertRaises(ContractError):
            self.manager.validate(session.session_id)

    def test_policy_validation(self):
        with self.assertRaises(ContractError):
            SessionPolicy(idle_timeout=100, session_timeout=50)
        with self.assertRaises(ContractError):
            SessionPolicy(allowed_networks=("not-a-cidr",))


# ---------------------------------------------------------------------------
# Cross-cutting: end-to-end login flow (ENT1-R1 + R6 + R8)
# ---------------------------------------------------------------------------

class TestEndToEndLogin(unittest.TestCase):
    """Implements ENT1-R1, ENT1-R6, ENT1-R8."""

    def test_oidc_login_creates_observed_session(self):
        clock = Clock()
        log = EventLog(clock)
        key = rsa_generate_keypair(1024)
        settings = oidc.provider_settings(
            "auth0", issuer="https://acme.auth0.com/", client_id="residual")
        client = OIDCClient(settings, {"k1": key.public_key})
        token = jwt_encode(
            {"iss": "https://acme.auth0.com/", "sub": "alice@acme.com",
             "aud": "residual", "iat": NOW, "exp": NOW + 300, "amr": ["mfa"]},
            key, alg="RS256", headers={"kid": "k1"})
        try:
            identity = client.authenticate(token, now=NOW)
            result = "allow"
        except ContractError:
            identity = None
            result = "deny"
        events.record_auth_event(log, events.EVENT_LOGIN, identity.subject if identity else "unknown",
                                 IP, result)
        self.assertEqual(result, "allow")
        manager = SessionManager(SessionPolicy(max_concurrent=5), log, clock)
        session = manager.create_session(identity.subject, IP, mfa_verified=("mfa" in identity.amr))
        self.assertTrue(session.mfa_verified)
        self.assertTrue(log.verify_chain())

    def test_failed_login_is_receipted(self):
        clock = Clock()
        log = EventLog(clock)
        events.record_auth_event(log, events.EVENT_ACCESS_DENIED, "mallory", IP, "deny",
                                 {"reason": "bad signature"})
        self.assertEqual(log.observations[0].result, "deny")
        self.assertTrue(log.verify_chain())


if __name__ == "__main__":
    unittest.main()
