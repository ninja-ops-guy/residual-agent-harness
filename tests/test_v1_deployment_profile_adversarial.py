"""Adversarial boundary tests for the v1 deployment profile validator."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_v1_deployment_profile.py"
SPEC = importlib.util.spec_from_file_location("validate_v1_deployment_profile", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)

MAIN = "d796f36b75e730a0bab71bdba564206174393719"

def local_profile():
    return {
        "schema": "residual.v1-deployment-profile.v1",
        "profile_id": "v1-local-prod",
        "profile_version": 1,
        "release": "v1.0.0",
        "decision_owner": "owner",
        "operations_owner": "ops",
        "approval_timestamp": "2026-09-24T07:00:00Z",
        "source_revision": MAIN,
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

def run_text(text):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "profile.json"
        path.write_text(text, encoding="utf-8")
        stream = io.StringIO()
        with mock.patch("sys.stdout", stream):
            code = module.main([str(path)])
        return code, json.loads(stream.getvalue())

class DeploymentProfileBoundaryTests(unittest.TestCase):
    def test_positive_control_still_passes(self):
        self.assertEqual(module.validate_profile(local_profile())["status"], "PASS")

    def test_whitespace_padded_undecided_owner_is_rejected(self):
        profile = local_profile()
        profile["decision_owner"] = "  UNDECIDED  "
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_unknown_top_level_field_is_rejected(self):
        profile = local_profile()
        profile["unreviewed_claim"] = True
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_unknown_nested_network_field_is_rejected(self):
        profile = local_profile()
        profile["network"]["unreviewed_network_claim"] = "present"
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_duplicate_owner_json_is_blocked(self):
        text = json.dumps(local_profile(), separators=(",", ":"))
        text = text.replace('"decision_owner":"owner"', '"decision_owner":"UNDECIDED","decision_owner":"owner"', 1)
        code, payload = run_text(text)
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "BLOCKED")

    def test_duplicate_exposure_json_is_blocked(self):
        text = json.dumps(local_profile(), separators=(",", ":"))
        text = text.replace('"station_exposure":"LOOPBACK_ONLY"', '"station_exposure":"INTERNET_FACING","station_exposure":"LOOPBACK_ONLY"', 1)
        code, payload = run_text(text)
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "BLOCKED")

    def test_nonstandard_json_constant_is_blocked(self):
        text = json.dumps(local_profile(), separators=(",", ":"))
        text = text.replace('"reverse_proxy":{"mode":"NONE"}', '"reverse_proxy":{"mode":"NONE","version":NaN}', 1)
        code, payload = run_text(text)
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "BLOCKED")

    def test_inactive_reverse_proxy_fields_cannot_hide_padded_undecided(self):
        profile = local_profile()
        profile["network"]["reverse_proxy"].update({
            "name": "  UNDECIDED  ",
            "version": "  UNDECIDED  ",
        })
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_disallowed_remote_worker_topology_cannot_hide_padded_undecided(self):
        profile = local_profile()
        profile["network"]["remote_workers"]["topology"] = "  UNDECIDED  "
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

    def test_disallowed_outbound_boundary_cannot_hide_padded_undecided(self):
        profile = local_profile()
        profile["network"]["outbound_provider_access"]["boundary"] = "  UNDECIDED  "
        with self.assertRaises(module.ProfileError):
            module.validate_profile(profile)

if __name__ == "__main__":
    unittest.main()
