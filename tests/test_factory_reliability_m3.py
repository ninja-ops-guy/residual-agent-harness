from __future__ import annotations

import unittest

from residual.factory.evidence_receipts import EvidenceError, StationIdentity
from residual.factory.reliability_m3 import M3_FAULTS, aggregate_m3_faults, run_m3_fault


class M3ReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            StationIdentity.generate()
        except EvidenceError as exc:
            raise unittest.SkipTest(str(exc))

    def test_all_declared_faults_are_cryptographically_contained(self):
        report = aggregate_m3_faults()
        self.assertEqual(report['faults'], len(M3_FAULTS))
        self.assertEqual(report['contained'], len(M3_FAULTS))
        self.assertEqual(report['fcr'], 1.0)
        self.assertTrue(all(x['injection_observed'] for x in report['trials']))
        self.assertTrue(all(not x['signature_verified'] for x in report['trials']))
        self.assertTrue(all(not x['trusted_handoff'] for x in report['trials']))

    def test_payload_tamper_changes_hash_but_preserved_signature_fails(self):
        trial = run_m3_fault('receipt_payload_tamper')
        self.assertNotEqual(trial['receipt_hash_before'], trial['receipt_hash_after'])
        self.assertFalse(trial['signature_verified'])
        self.assertTrue(trial['contained'])

    def test_verifier_revision_is_signature_bound(self):
        trial = run_m3_fault('verifier_revision_tamper')
        self.assertFalse(trial['signature_verified'])
        self.assertTrue(trial['contained'])

    def test_artifact_hash_is_signature_bound(self):
        trial = run_m3_fault('artifact_hash_tamper')
        self.assertFalse(trial['signature_verified'])
        self.assertTrue(trial['contained'])

    def test_wrong_station_key_cannot_validate_receipt(self):
        trial = run_m3_fault('wrong_station_key')
        self.assertFalse(trial['signature_verified'])
        self.assertTrue(trial['contained'])

    def test_unknown_fault_fails_closed(self):
        with self.assertRaises(EvidenceError):
            run_m3_fault('not-a-fault')


if __name__ == '__main__':
    unittest.main()
