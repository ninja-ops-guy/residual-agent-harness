from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_v1_recovery_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_v1_recovery_evidence", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)

H = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
G = "d" * 40
T = "e" * 40


def sample():
    return {
        "schema": "residual.v1-recovery-evidence.v1",
        "execution_claim": "OBSERVED",
        "rc": {"commit": G, "tree": T, "artifact_sha256": H},
        "deployment_profile": {"sha256": H2, "approved": True},
        "objectives": {"rpo_seconds": 300, "rto_seconds": 900},
        "backup": {
            "backup_id": "backup-001",
            "manifest_sha256": H3,
            "encrypted": True,
            "key_reference": "kms://release/backup-key-v1",
            "created_at_utc": "2026-09-24T08:00:00Z",
            "readable_before_traffic_change": True,
            "components": [
                "database",
                "durable_outbox_journal",
                "evidence_receipt_store",
                "configuration_references",
            ],
        },
        "restore": {
            "backup_id": "backup-001",
            "started_at_utc": "2026-09-24T08:05:00Z",
            "completed_at_utc": "2026-09-24T08:10:00Z",
            "integrity_verified": True,
            "receipt_chain_verified": True,
            "startup_verified": True,
            "critical_reads_verified": True,
            "observed_rpo_seconds": 60,
            "observed_rto_seconds": 300,
        },
        "rollback": {
            "previous_artifact_sha256": "f" * 64,
            "procedure_verified": True,
            "data_integrity_verified": True,
            "authority_integrity_verified": True,
            "in_flight_policy_verified": True,
        },
        "evidence_index": {"sha256": "1" * 64, "immutable_copy_verified": True},
        "approval": {
            "qualification_lead": "human-reviewer",
            "approved": True,
            "approved_at_utc": "2026-09-24T08:15:00Z",
        },
    }


class RecoveryEvidenceTests(unittest.TestCase):
    def test_valid_bundle_passes(self):
        out = mod.validate_evidence(sample())
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["execution_claim"], "VALIDATION_ONLY")

    def test_missing_observed_execution_claim_blocks(self):
        x = sample()
        x["execution_claim"] = "NONE"
        with self.assertRaises(mod.EvidenceError):
            mod.validate_evidence(x)

    def test_restore_must_bind_backup(self):
        x = sample()
        x["restore"]["backup_id"] = "backup-other"
        self.assertEqual(mod.validate_evidence(x)["status"], "FAIL")

    def test_rpo_breach_fails(self):
        x = sample()
        x["restore"]["observed_rpo_seconds"] = 301
        self.assertEqual(mod.validate_evidence(x)["status"], "FAIL")

    def test_rto_breach_fails(self):
        x = sample()
        x["restore"]["observed_rto_seconds"] = 901
        self.assertEqual(mod.validate_evidence(x)["status"], "FAIL")

    def test_integrity_false_fails(self):
        x = sample()
        x["restore"]["receipt_chain_verified"] = False
        self.assertEqual(mod.validate_evidence(x)["status"], "FAIL")

    def test_unapproved_profile_blocks(self):
        x = sample()
        x["deployment_profile"]["approved"] = False
        with self.assertRaises(mod.EvidenceError):
            mod.validate_evidence(x)

    def test_secret_bearing_fields_are_rejected(self):
        x = sample()
        x["backup"]["api_token"] = "do-not-retain"
        with self.assertRaises(mod.EvidenceError):
            mod.validate_evidence(x)

    def test_timestamp_must_be_utc_z(self):
        x = sample()
        x["restore"]["completed_at_utc"] = "2026-09-24T08:10:00+00:00"
        with self.assertRaises(mod.EvidenceError):
            mod.validate_evidence(x)

    def test_required_components_fail_closed(self):
        x = sample()
        x["backup"]["components"].remove("durable_outbox_journal")
        self.assertEqual(mod.validate_evidence(x)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
