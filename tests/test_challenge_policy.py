from __future__ import annotations

import unittest

from residual.challenge_policy import (
    ChallengeDisposition, ChallengePolicy, ChallengeRecord,
    ChallengeResolution, effective_disposition, validate_filing,
    validate_resolution,
)
from residual.core import ContractError


class ChallengePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy=ChallengePolicy(
            policy_id="m6-semantic-v1",
            eligible_challenger_roles=("reviewer","human"),
            allowed_grounds=("semantic","evidence","framing","authorization"),
            resolution_authority_roles=("human",),
            filing_window_events=100,
            allow_withdrawal=True,
        )
        self.record=ChallengeRecord(
            challenge_id="ch-1",target_node_id="node-a",
            policy_id="m6-semantic-v1",challenger_role="reviewer",
            ground="semantic",filed_event=20,
        )

    def test_challenge_filing_enforces_role_ground_and_window(self):
        validate_filing(self.policy,self.record,target_created_event=10)
        with self.assertRaisesRegex(ContractError,"eligible"):
            validate_filing(
                self.policy,
                ChallengeRecord("ch-2","node-a","m6-semantic-v1","planner","semantic",20),
                target_created_event=10,
            )
        with self.assertRaisesRegex(ContractError,"ground"):
            validate_filing(
                self.policy,
                ChallengeRecord("ch-3","node-a","m6-semantic-v1","reviewer","style",20),
                target_created_event=10,
            )
        with self.assertRaisesRegex(ContractError,"window"):
            validate_filing(
                self.policy,
                ChallengeRecord("ch-4","node-a","m6-semantic-v1","reviewer","semantic",200),
                target_created_event=10,
            )

    def test_resolution_requires_authority(self):
        with self.assertRaisesRegex(ContractError,"authority"):
            validate_resolution(
                self.policy,self.record,
                ChallengeResolution("ch-1","reviewer",ChallengeDisposition.REJECTED,30,"not supported"),
            )

    def test_withdrawal_is_policy_controlled(self):
        locked=ChallengePolicy(
            policy_id="locked",eligible_challenger_roles=("reviewer",),
            allowed_grounds=("semantic",),resolution_authority_roles=("human",),
            allow_withdrawal=False,
        )
        record=ChallengeRecord("ch","node","locked","reviewer","semantic",1)
        with self.assertRaisesRegex(ContractError,"withdrawal"):
            validate_resolution(
                locked,record,
                ChallengeResolution("ch","human",ChallengeDisposition.WITHDRAWN,2,"withdraw"),
            )

    def test_effective_disposition_uses_governed_resolution(self):
        resolution=ChallengeResolution(
            "ch-1","human",ChallengeDisposition.REJECTED,30,
            "challenge not sustained by evidence",
        )
        self.assertEqual(
            effective_disposition(self.policy,self.record,[resolution],at_event=40),
            ChallengeDisposition.REJECTED,
        )
        self.assertEqual(
            effective_disposition(self.policy,self.record,[],at_event=25),
            ChallengeDisposition.OPEN,
        )


if __name__=="__main__":
    unittest.main()
