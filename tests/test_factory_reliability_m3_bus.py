from __future__ import annotations

import unittest

from residual.factory.evidence_receipts import EvidenceError, StationIdentity
from residual.factory.reliability_m3_bus import M3_BUS_FAULTS, aggregate_m3_bus_faults, run_m3_bus_fault


class M3EvidenceBusReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            StationIdentity.generate()
        except EvidenceError as exc:
            raise unittest.SkipTest(str(exc))

    def test_declared_fault_matrix_is_contained(self):
        report = aggregate_m3_bus_faults()
        self.assertEqual(report['faults'], len(M3_BUS_FAULTS))
        self.assertEqual(report['contained'], len(M3_BUS_FAULTS))
        self.assertEqual(report['fcr'], 1.0)
        self.assertTrue(all(x['injection_observed'] for x in report['trials']))
        self.assertTrue(all(x['detected'] for x in report['trials']))
        self.assertTrue(all(not x['trusted_handoff'] for x in report['trials']))

    def test_signature_tamper_is_rejected_at_consumption(self):
        trial = run_m3_bus_fault('receipt_signature_tamper')
        self.assertTrue(trial['stored_unverified_receipt'])
        self.assertTrue(trial['contained'])
        self.assertFalse(trial['trusted_handoff'])

    def test_artifact_corruption_is_detected(self):
        trial = run_m3_bus_fault('artifact_store_corruption')
        self.assertTrue(trial['contained'])

    def test_receipt_queue_is_append_only(self):
        trial = run_m3_bus_fault('receipt_queue_mutation')
        self.assertTrue(trial['contained'])

    def test_dependency_mismatch_is_rejected(self):
        trial = run_m3_bus_fault('dependency_receipt_mismatch')
        self.assertTrue(trial['contained'])

    def test_unknown_fault_fails_closed(self):
        with self.assertRaises(EvidenceError):
            run_m3_bus_fault('unknown')


if __name__ == '__main__':
    unittest.main()
