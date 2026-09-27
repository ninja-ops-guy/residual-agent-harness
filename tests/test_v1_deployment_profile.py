import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_v1_deployment_profile",
    ROOT / "scripts" / "validate_v1_deployment_profile.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def local_profile():
    return {
        "schema": "residual.v1-deployment-profile.v1",
        "profile_id": "v1-local-prod",
        "profile_version": 1,
        "release": "v1.0.0",
        "decision_owner": "owner",
        "operations_owner": "ops",
        "approval_timestamp": "2026-09-24T07:00:00Z",
        "source_revision": "d796f36b75e730a0bab71bdba564206174393719",
        "network": {
            "station_exposure": "LOOPBACK_ONLY",
            "bind_addresses": ["127.0.0.1", "::1"],
            "reverse_proxy": {"mode": "NONE"},
            "tls_termination": "NONE_LOCAL_ONLY",
            "proxy_header_trust": "NONE",
            "certificate_policy": "NOT_APPLICABLE",
            "remote_workers": {"mode": "DISALLOWED"},
            "outbound_provider_access": {"mode": "DISALLOWED"},
        },
        "tenancy": {
            "operator_model": "SINGLE_TRUSTED_OPERATOR",
            "user_model": "LOCAL_OPERATOR_ONLY",
            "authorization_boundary": "local authenticated operator",
            "break_glass_authority": "NOT_SUPPORTED",
            "credential_custody": "local OS trust domain",
        },
        "runtime": {
            "operating_systems": ["Ubuntu 24.04"],
            "architectures": ["x86_64"],
            "python_versions": ["3.12"],
            "installation_artifact": "WHEEL",
            "filesystems": ["ext4"],
            "sqlite_version": "3.45.x",
            "sqlite_durability_mode": "WAL + qualified synchronous policy",
            "persistent_volume_semantics": "local durable filesystem",
            "multi_process_station": "DISALLOWED",
            "multi_host_shared_database": "DISALLOWED",
        },
        "objectives": {
            "availability_slo": "best-effort single-host v1",
            "max_operation_recovery_seconds": 300,
            "rpo_seconds": 300,
            "rto_seconds": 1800,
            "backup_frequency_seconds": 300,
            "backup_retention_seconds": 604800,
            "evidence_retention_seconds": 2592000,
            "log_retention_seconds": 604800,
            "log_disk_budget_bytes": 1073741824,
            "host_loss_claim": "RESTORE_ONLY",
            "regional_loss_claim": "NONE",
            "soak_seconds": 259200,
            "soak_environment": "approved clean v1 reference host",
        },
    }


class DeploymentProfileTests(unittest.TestCase):
    def test_local_profile_passes_and_classifies_scope(self):
        result = module.validate_profile(local_profile())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["gate_applicability"]["PR-G05"], "NOT_APPLICABLE_BY_SCOPE")
        self.assertEqual(result["gate_applicability"]["PR-G09"], "NOT_APPLICABLE_WITH_FAIL_CLOSED_ENFORCEMENT")
        self.assertEqual(result["gate_applicability"]["PR-G17"], "NOT_APPLICABLE_BY_SCOPE")
        self.assertEqual(result["gate_applicability"]["PR-G31"], "REQUIRED")
        self.assertRegex(result["profile_sha256"], r"^[0-9a-f]{64}$")

    def test_undecided_is_fail_closed(self):
        profile = local_profile()
        profile["objectives"]["rto_seconds"] = "UNDECIDED"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_non_loopback_requires_tls_and_certificate_policy(self):
        profile = local_profile()
        profile["network"]["station_exposure"] = "INTERNET_FACING"
        profile["network"]["bind_addresses"] = ["0.0.0.0"]
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_proxy_headers_require_declared_proxy(self):
        profile = local_profile()
        profile["network"]["proxy_header_trust"] = "X-Forwarded-For from 10.0.0.2"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_multi_user_requires_authorization_boundary(self):
        profile = local_profile()
        profile["tenancy"]["user_model"] = "SINGLE_TENANT_MULTI_USER"
        profile["tenancy"]["authorization_boundary"] = "NOT_APPLICABLE"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_failover_claim_requires_multi_host_support(self):
        profile = local_profile()
        profile["objectives"]["host_loss_claim"] = "FAILOVER"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_multi_host_database_requires_multi_process_station(self):
        profile = local_profile()
        profile["runtime"]["multi_host_shared_database"] = "SUPPORTED"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_secret_bearing_keys_are_rejected(self):
        profile = local_profile()
        profile["api_key"] = "do-not-store-this"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_profile_digest_is_deterministic(self):
        a = module.validate_profile(local_profile())["profile_sha256"]
        b = module.validate_profile(local_profile())["profile_sha256"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
