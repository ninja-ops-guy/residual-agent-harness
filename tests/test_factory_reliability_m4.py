from __future__ import annotations

import unittest

from residual.factory.evidence_receipts import EvidenceError, StationIdentity
from residual.factory.reliability_m4 import M4_FAULTS, aggregate_m4_faults, run_m4_fault


class M4ReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            StationIdentity.generate()
        except EvidenceError as exc:
            raise unittest.SkipTest(str(exc))

    def test_all_declared_m4_faults_are_contained(self):
        report = aggregate_m4_faults()
        self.assertEqual(report['faults'], len(M4_FAULTS))
        self.assertEqual(report['contained'], len(M4_FAULTS))
        self.assertEqual(report['fcr'], 1.0)
        self.assertTrue(all(x['injection_observed'] for x in report['trials']))
        self.assertTrue(all(x['detected'] for x in report['trials']))

    def test_permuted_receipts_produce_identical_output(self):
        trial = run_m4_fault('input_order_permutation')
        self.assertTrue(trial['contained'])
        self.assertTrue(trial['integration_receipt_issued'])

    def test_missing_parent_is_rejected(self):
        trial = run_m4_fault('missing_parent')
        self.assertTrue(trial['contained'])
        self.assertFalse(trial['integration_receipt_issued'])

    def test_true_conflict_cannot_publish_receipt(self):
        trial = run_m4_fault('true_overlap_conflict')
        self.assertTrue(trial['contained'])
        self.assertFalse(trial['integration_receipt_issued'])

    def test_verification_failure_attributes_offender_and_blocks_receipt(self):
        trial = run_m4_fault('verification_failure')
        self.assertTrue(trial['contained'])
        self.assertIsNotNone(trial['offending_receipt'])
        self.assertFalse(trial['integration_receipt_issued'])

    def test_unbound_human_resolution_is_rejected(self):
        self.assertTrue(run_m4_fault('invalid_human_resolution')['contained'])

    def test_integration_receipt_tamper_invalidates_signature(self):
        self.assertTrue(run_m4_fault('integration_receipt_tamper')['contained'])

    def test_unknown_fault_fails_closed(self):
        with self.assertRaises(EvidenceError):
            run_m4_fault('unknown')


if __name__ == '__main__':
    unittest.main()
