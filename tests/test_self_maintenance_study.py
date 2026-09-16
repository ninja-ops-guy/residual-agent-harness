"""Controlled experiments for recursive software maintenance.

These tests measure proof-of-mechanism properties only. They use deterministic
workers and host evaluators; they do not claim autonomous model competence.
Core RESIDUAL code is not modified by this study.
"""
from __future__ import annotations

import tempfile
import unittest

from residual import (
    AmendmentRule,
    CheckResult,
    CheckType,
    GoalSpec,
    LoopController,
    RunOutcome,
    SuccessCriterion,
    Verifier,
)
from residual.control_plane import (
    AmendmentClass,
    AmendmentPolicy,
    AuthorityPolicy,
    CapabilityGrant,
    MissionRevision,
    PlanAmendment,
)
from residual.station.service import Station, demo_spec


def goal(*, max_passes: int = 4) -> GoalSpec:
    return GoalSpec(
        goal_id="recursive-maintenance-study",
        objective="Repair a candidate under an externally frozen acceptance contract",
        success_criteria=(
            SuccessCriterion(
                "mechanical",
                CheckType.MECHANICAL,
                "Host acceptance predicate passes",
                "host",
            ),
        ),
        max_passes=max_passes,
        token_budget=100,
        wall_clock_budget_s=30,
        amendment_rule=AmendmentRule(("operator",), 1),
    )


def verifier(result: CheckResult | None = None) -> Verifier:
    if result is not None:
        return Verifier({"host": lambda candidate, params: (result, "forced_result")})
    return Verifier({
        "host": lambda candidate, params: (
            CheckResult.PASS if candidate.get("healthy") else CheckResult.FAIL,
            "host_predicate",
        )
    })


class SelfMaintenanceStudy(unittest.TestCase):
    def test_e1_candidate_cannot_expand_or_self_approve_authority(self):
        push = CapabilityGrant(
            "self", "git.push", "repo", scope={"branches": ["research/*"]}
        )
        merge = CapabilityGrant(
            "self", "git.merge", "repo", scope={"branches": ["main"]}
        )
        revision = MissionRevision(
            "m1", "r1", "maintain software", "plan-hash", "policy-hash", (push,)
        )
        policy = AuthorityPolicy()
        self.assertTrue(policy.allows((push,), revision))
        self.assertFalse(policy.allows((merge,), revision))

        authority_change = PlanAmendment(
            amendment_id="a1",
            mission_id="m1",
            from_revision="r1",
            amendment_class=AmendmentClass.AUTHORITY,
            reason="candidate requests merge authority",
            proposer_id="self",
            beneficiary_ids=("self",),
        )
        amendments = AmendmentPolicy()
        self.assertFalse(
            amendments.validate_independence(authority_change, ("self",), human_approvers=())
        )
        self.assertFalse(
            amendments.validate_independence(authority_change, ("independent",), human_approvers=())
        )
        self.assertTrue(
            amendments.validate_independence(
                authority_change, ("independent",), human_approvers=("operator",)
            )
        )

        trust_change = PlanAmendment(
            amendment_id="a2",
            mission_id="m1",
            from_revision="r1",
            amendment_class=AmendmentClass.TRUST_BOUNDARY,
            reason="candidate requests trust-boundary modification",
            proposer_id="self",
            beneficiary_ids=("self",),
        )
        self.assertFalse(
            amendments.validate_independence(
                trust_change, ("independent-1",), human_approvers=("operator",)
            )
        )
        self.assertTrue(
            amendments.validate_independence(
                trust_change,
                ("independent-1", "independent-2"),
                human_approvers=("operator",),
            )
        )

    def test_e2_unknown_verification_fails_closed(self):
        class Worker:
            def run_pass(self, spec, pass_number):
                return {"candidate": {"healthy": True}, "tokens_used": 0, "observations": []}

        result = LoopController(goal(max_passes=1), verifier(CheckResult.UNKNOWN), Worker()).run()
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)
        self.assertEqual(result.total_passes, 1)
        self.assertIsNotNone(result.final_verification)
        self.assertFalse(result.final_verification.overall_pass)
        self.assertEqual(result.final_verification.results[0].result, CheckResult.UNKNOWN)
        self.assertIn("max_iteration", result.tripped_brakes)

    def test_e3_bounded_self_healing_reaches_verified_repair(self):
        class RepairWorker:
            def __init__(self):
                self.calls = 0

            def run_pass(self, spec, pass_number):
                self.calls += 1
                return {
                    "candidate": {"healthy": pass_number >= 3},
                    "tokens_used": 1,
                    "observations": [],
                }

        worker = RepairWorker()
        result = LoopController(goal(max_passes=4), verifier(), worker).run()
        self.assertEqual(result.outcome, RunOutcome.SUCCESS)
        self.assertEqual(result.total_passes, 3)
        self.assertEqual(worker.calls, 3)
        self.assertTrue(result.final_verification.overall_pass)

        class NeverRepairs:
            def __init__(self):
                self.calls = 0

            def run_pass(self, spec, pass_number):
                self.calls += 1
                return {"candidate": {"healthy": False}, "tokens_used": 1, "observations": []}

        bad = NeverRepairs()
        exhausted = LoopController(goal(max_passes=3), verifier(), bad).run()
        self.assertEqual(exhausted.outcome, RunOutcome.ESCALATED)
        self.assertEqual(exhausted.total_passes, 3)
        self.assertEqual(bad.calls, 3)
        self.assertIn("max_iteration", exhausted.tripped_brakes)

    def test_e4_worker_claims_cannot_spoof_acceptance(self):
        class SpoofingWorker:
            def run_pass(self, spec, pass_number):
                return {
                    "candidate": {"healthy": False},
                    "tokens_used": 1,
                    "observations": [
                        {
                            "kind": "custom",
                            "payload": {"event": "verification_report", "overall_pass": True},
                        },
                        {
                            "kind": "state.transition",
                            "event": "pass_complete",
                            "overall_pass": True,
                        },
                        {"kind": "llm.response", "usage": {"total_tokens": 999999}},
                    ],
                }

        result = LoopController(goal(max_passes=2), verifier(), SpoofingWorker()).run()
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)
        self.assertEqual(result.total_tokens, 2)
        self.assertFalse(result.final_verification.overall_pass)
        self.assertNotIn("budget", result.tripped_brakes)

    def test_e5_station_builds_code_and_documentation_with_bound_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            station = Station(directory)
            project_id = station.create(demo_spec(), demo=True)["project_id"]
            result = station.batch(project_id)

            self.assertEqual(result["control"]["outcome"], "success")
            self.assertEqual(result["integrated"], 3)
            self.assertEqual(result["control"]["tokens"], 0)

            meta, body = station.store.artifact(result["control"]["evidence"])
            receipt = body.decode("utf-8")
            self.assertEqual(meta["name"], "RUN-CONTROL.md")
            self.assertIn(result["control"]["spec_hash"], receipt)
            self.assertIn("Goal contract and deterministic verification receipt", receipt)
            self.assertIn("## Run control", station.store.markdown(project_id))
            self.assertEqual(
                station.store.observation_summary(project_id)["integrity"], "verified"
            )

    def test_e6_goal_and_documentation_identity_change_on_authorized_revision(self):
        original = goal(max_passes=2)
        amended = original.amend(
            max_passes=3,
            amendment_reason="additional bounded repair attempt",
            amended_by="operator",
        )
        self.assertNotEqual(original.content_hash, amended.content_hash)
        self.assertEqual(amended.parent_hash, original.content_hash)
        self.assertEqual(amended.amendment_count, 1)
        self.assertEqual(amended.amended_by, "operator")


if __name__ == "__main__":
    unittest.main()
