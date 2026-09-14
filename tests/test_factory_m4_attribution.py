"""PR #66 review: verification infrastructure failure is not receipt blame."""
from dataclasses import replace
import unittest
from unittest.mock import patch
from residual.factory import m4_integrator as m4
from tests import test_factory_m4_integrator as fixtures


class M4AttributionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.M4IntegratorTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.receipt = self.f.issue('task1', 'R1', artifacts={'one.txt': b'one\n'}, index=1)
        self.plan = self.f.m4.integration_plan((self.receipt.receipt_hash,))


    def integrate(self, policy=None):
        return self.f.integrator.integrate(self.plan, policy=policy or self.f.policy(),
                                          station_identity=self.f.identity)


    def policy(self, code, **kwargs):
        original = self.f.policy()
        first = replace(original.commands[0], argv=(fixtures.sys.executable, '-c', code), **kwargs)
        return replace(original, commands=(first,) + original.commands[1:])


    def test_unavailable_executable_is_unknown_not_pass(self):
        policy = self.f.policy()
        first = replace(policy.commands[0], argv=('/residual-no-such-executable',))
        with self.assertRaises(m4.ProjectVerificationError) as caught:
            self.integrate(replace(policy, commands=(first,) + policy.commands[1:]))
        self.assertIsNone(caught.exception.offending_receipt_hash)
        self.assertFalse(any(e['event'] == 'M4ReceiptRevisionRequired' for e in self.f.events))
        checks = [e for e in self.f.events if e['event'] == 'M4ProjectVerification'][-1]['checks']
        self.assertEqual(checks[0]['status'], 'unknown')


    def test_unknown_multi_receipt_verification_never_bisects_or_blames(self):
        other = self.f.issue('task2', 'R2', artifacts={'two.txt': b'two'}, index=2)
        self.plan = self.f.m4.integration_plan((self.receipt.receipt_hash, other.receipt_hash))
        unknown = m4.VerificationResult('tests', 'full_test_suite', 'unknown', None, '0'*64, '0'*64)
        with patch.object(self.f.integrator, '_run_verification', return_value=(unknown,)):
            with patch.object(self.f.integrator, '_attribute_failure') as attribute:
                with self.assertRaises(m4.ProjectVerificationError) as caught:
                    self.integrate()
        attribute.assert_not_called()
        self.assertIsNone(caught.exception.offending_receipt_hash)
        self.assertFalse(any(e['event'] == 'M4ReceiptRevisionRequired' for e in self.f.events))


    def test_resource_or_signal_failure_is_not_candidate_attribution(self):
        for reason, rc in (('timeout', None), ('output_limit', -9), ('exit', -9)):
            with self.subTest(reason=reason, rc=rc):
                failed = m4.VerificationResult('tests', 'full_test_suite', 'fail', rc,
                                               '0'*64, '0'*64, reason)
                with patch.object(self.f.integrator, '_run_verification', return_value=(failed,)):
                    with patch.object(self.f.integrator, '_attribute_failure') as attribute:
                        with self.assertRaises(m4.ProjectVerificationError) as caught:
                            self.integrate()
                attribute.assert_not_called()
                self.assertIsNone(caught.exception.offending_receipt_hash)
        self.assertFalse(any(e['event'] == 'M4ReceiptRevisionRequired' for e in self.f.events))


    def test_preexisting_project_failure_does_not_blame_a_new_receipt(self):
        with self.assertRaises(m4.ProjectVerificationError) as caught:
            self.integrate(self.policy('raise SystemExit(1)'))
        self.assertIsNone(caught.exception.offending_receipt_hash)
        self.assertFalse(any(e['event'] == 'M4ReceiptRevisionRequired' for e in self.f.events))


    def test_unknown_counterfactual_is_not_false_and_cannot_select_receipt(self):
        other = self.f.issue('task2', 'R2', artifacts={'two.txt': b'two'}, index=2)
        for outcomes in ((None,), (True, None), (True, True, None)):
            with self.subTest(outcomes=outcomes):
                with patch.object(self.f.integrator, '_verify_subset', side_effect=outcomes):
                    offender = self.f.integrator._attribute_failure(
                        self.f.base, (self.receipt, other), self.f.policy())
                self.assertIsNone(offender)


    def test_unknown_singleton_recheck_never_returns_its_hash(self):
        with patch.object(self.f.integrator, '_verify_subset', side_effect=(True, None)) as verify:
            offender = self.f.integrator._attribute_failure(self.f.base, (self.receipt,), self.f.policy())
        self.assertIsNone(offender)
        self.assertEqual(verify.call_count, 2)


    def test_subset_with_unavailable_verifier_has_unknown_outcome(self):
        unknown = m4.VerificationResult('tests', 'full_test_suite', 'unknown', None, '0'*64, '0'*64)
        with patch.object(self.f.integrator, '_run_verification', return_value=(unknown,)):
            outcome = self.f.integrator._verify_subset(self.f.base, (self.receipt,), self.f.policy(), 'unknown')
        self.assertIsNone(outcome)


    def test_dependency_incomplete_subset_is_not_a_failed_candidate(self):
        child = replace(self.receipt, parent_receipts=('a'*64,))
        with patch.object(self.f.integrator, '_worktree') as worktree:
            outcome = self.f.integrator._verify_subset(self.f.base, (child,), self.f.policy(), 'missing')
        self.assertIsNone(outcome)
        worktree.assert_not_called()
