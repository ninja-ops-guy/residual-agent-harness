"""Tests for the loop layer: goalspec, verifier, brakes, quarantine, loopcontroller."""
import time
import unittest

from residual import (
    AmendmentRule, BrakeAction, BudgetBrake, CheckResult, CheckType,
    CompletionBrake, GoalSpec, LoopController, MaxIterationBrake,
    NoProgressBrake, PolicyDecision, ProposedAction, QuarantineStore,
    RunOutcome, SuccessCriterion, Verifier,
    budget_policy, build_brakes, denylist_policy, path_traversal_policy,
)


def make_spec(**overrides):
    defaults = dict(
        goal_id="g1",
        objective="produce a verified artifact",
        success_criteria=(
            SuccessCriterion("mech1", CheckType.MECHANICAL, "file exists", "check_file"),
            SuccessCriterion("struct1", CheckType.STRUCTURAL, "has sections", "check_sections"),
            SuccessCriterion("judge1", CheckType.JUDGE, "quality review", "check_quality"),
        ),
        max_passes=5,
        token_budget=10_000,
        wall_clock_budget_s=60.0,
        amendment_rule=AmendmentRule(authorized_roles=("operator",)),
    )
    defaults.update(overrides)
    return GoalSpec(**defaults)


class TestGoalSpec(unittest.TestCase):
    def test_construction_enforces_ordering(self):
        with self.assertRaises(Exception):
            make_spec(success_criteria=(
                SuccessCriterion("j1", CheckType.JUDGE, "judge first", "check_quality"),
                SuccessCriterion("m1", CheckType.MECHANICAL, "mech after judge", "check_file"),
            ))

    def test_immutability(self):
        spec = make_spec()
        with self.assertRaises(Exception):
            spec.max_passes = 99

    def test_content_hash_stable(self):
        spec = make_spec()
        self.assertEqual(spec.content_hash, make_spec().content_hash)

    def test_amend_produces_new_instance(self):
        spec = make_spec()
        amended = spec.amend(max_passes=10, amendment_reason="need more passes", amended_by="operator")
        self.assertEqual(amended.max_passes, 10)
        self.assertEqual(spec.max_passes, 5)  # original unchanged
        self.assertNotEqual(spec.content_hash, amended.content_hash)
        self.assertEqual(amended.schema_version, "1.1.0")

    def test_amend_unauthorized_role_rejected(self):
        spec = make_spec()
        with self.assertRaises(Exception):
            spec.amend(max_passes=10, amendment_reason="x", amended_by="intruder")

    def test_amend_without_reason_rejected(self):
        spec = make_spec()
        with self.assertRaises(Exception):
            spec.amend(max_passes=10, amendment_reason="", amended_by="operator")


class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.evaluators = {
            "check_file": lambda c, p: (CheckResult.PASS, ""),
            "check_sections": lambda c, p: (CheckResult.PASS, ""),
            "check_quality": lambda c, p: (CheckResult.PASS, ""),
        }

    def test_all_pass(self):
        v = Verifier(self.evaluators)
        report = v.verify({}, make_spec())
        self.assertTrue(report.overall_pass)
        self.assertIsNone(report.primary_failure)

    def test_mechanical_failure_blocks_judge(self):
        evaluators = dict(self.evaluators)
        evaluators["check_file"] = lambda c, p: (CheckResult.FAIL, "missing")
        v = Verifier(evaluators)
        report = v.verify({}, make_spec())
        self.assertFalse(report.overall_pass)
        self.assertEqual(report.primary_failure, "mech1")
        # judge should be SKIPPED, not FAIL
        judge_result = [r for r in report.results if r.name == "judge1"][0]
        self.assertEqual(judge_result.result, CheckResult.SKIPPED)
        self.assertEqual(judge_result.reason, "prior_check_failed")

    def test_judge_unavailable_fails_closed(self):
        evaluators = {k: fn for k, fn in self.evaluators.items() if k != "check_quality"}
        v = Verifier(evaluators)
        report = v.verify({}, make_spec())
        self.assertFalse(report.overall_pass)
        judge_result = [r for r in report.results if r.name == "judge1"][0]
        self.assertEqual(judge_result.result, CheckResult.UNKNOWN)
        self.assertEqual(judge_result.reason, "judge_unavailable")

    def test_evaluator_exception_returns_unknown(self):
        def bad_eval(c, p):
            raise RuntimeError("boom")
        evaluators = dict(self.evaluators)
        evaluators["check_file"] = bad_eval
        v = Verifier(evaluators)
        report = v.verify({}, make_spec())
        self.assertFalse(report.overall_pass)
        mech = [r for r in report.results if r.name == "mech1"][0]
        self.assertEqual(mech.result, CheckResult.UNKNOWN)
        self.assertEqual(mech.reason, "check_error")

    def test_all_checks_evaluated_despite_early_failure(self):
        evaluators = dict(self.evaluators)
        evaluators["check_file"] = lambda c, p: (CheckResult.FAIL, "early fail")
        v = Verifier(evaluators)
        report = v.verify({}, make_spec())
        self.assertEqual(len(report.results), 3)  # all three evaluated

    def test_emits_per_check(self):
        events = []
        v = Verifier(self.evaluators)
        v.verify({}, make_spec(), emit=lambda kind, payload: events.append((kind, payload)))
        self.assertEqual(len(events), 3)
        self.assertTrue(all(k == "check_evaluated" for k, _ in events))


class TestBrakes(unittest.TestCase):
    def test_max_iteration_trips(self):
        spec = make_spec(max_passes=3)
        brake = MaxIterationBrake(spec)
        for _ in range(2):
            self.assertIsNone(brake.update({"kind": "state.transition", "to_state": "pass_complete"}))
        trip = brake.update({"kind": "state.transition", "to_state": "pass_complete"})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.brake_name, "max_iteration")
        self.assertEqual(trip.recommended_action, BrakeAction.ESCALATE)

    def test_budget_trips_on_tokens(self):
        spec = make_spec(token_budget=100)
        brake = BudgetBrake(spec)
        trip = brake.update({"kind": "llm.response", "usage": {"total_tokens": 150}})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.recommended_action, BrakeAction.ABORT)

    def test_no_progress_trips_on_repetition(self):
        brake = NoProgressBrake(threshold=3)
        ev = {"kind": "tool.invoked", "payload": {"tool": "search", "args": "('q',)", "kwargs": "{}"}}
        self.assertIsNone(brake.update(ev))
        self.assertIsNone(brake.update(ev))
        trip = brake.update(ev)
        self.assertIsNotNone(trip)
        self.assertEqual(trip.brake_name, "no_progress")

    def test_no_progress_resets_on_different_call(self):
        brake = NoProgressBrake(threshold=3)
        ev1 = {"kind": "tool.invoked", "payload": {"tool": "a", "args": "()", "kwargs": "{}"}}
        ev2 = {"kind": "tool.invoked", "payload": {"tool": "b", "args": "()", "kwargs": "{}"}}
        brake.update(ev1)
        brake.update(ev1)
        self.assertIsNone(brake.update(ev2))  # different call resets streak
        self.assertIsNone(brake.update(ev1))
        self.assertIsNone(brake.update(ev1))
        self.assertIsNotNone(brake.update(ev1))

    def test_completion_trips_on_pass(self):
        brake = CompletionBrake()
        self.assertIsNone(brake.update({"kind": "custom", "payload": {"event": "verification_report", "overall_pass": False}}))
        trip = brake.update({"kind": "custom", "payload": {"event": "verification_report", "overall_pass": True}})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.brake_name, "completion")

    def test_build_brakes_returns_four(self):
        brakes = build_brakes(make_spec())
        self.assertEqual(len(brakes), 4)


class TestQuarantine(unittest.TestCase):
    def test_hold_evaluate_release(self):
        store = QuarantineStore()
        action = ProposedAction(action_type="tool_call", name="search", arguments={"q": "test"})
        held = store.hold(action)
        self.assertEqual(held.fingerprint, action.fingerprint)
        decision = store.evaluate(held, ())
        self.assertEqual(decision, PolicyDecision.ALLOW)
        executed = store.release(held, lambda a: f"result_for_{a.name}")
        self.assertEqual(executed.result, "result_for_search")
        self.assertIsNone(executed.error)

    def test_release_captures_error(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction(action_type="tool_call", name="explode", arguments={}))
        store.evaluate(held, ())
        def boom(_):
            raise RuntimeError("kaput")
        executed = store.release(held, boom)
        self.assertEqual(executed.error, "RuntimeError")

    def test_denylist_policy(self):
        store = QuarantineStore()
        policy = denylist_policy("rm_rf", "exec_shell")
        held = store.hold(ProposedAction(action_type="tool_call", name="rm_rf", arguments={}))
        decision = store.evaluate(held, (policy,))
        self.assertEqual(decision, PolicyDecision.DENY)

    def test_path_traversal_policy(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction(action_type="file_write", name="write", arguments={"path": "../../etc/passwd"}))
        decision = store.evaluate(held, (path_traversal_policy,))
        self.assertEqual(decision, PolicyDecision.DENY)

    def test_budget_policy(self):
        store = QuarantineStore()
        policy = budget_policy(max_actions=2)
        a1 = store.hold(ProposedAction(action_type="tool_call", name="a", arguments={}))
        a2 = store.hold(ProposedAction(action_type="tool_call", name="b", arguments={}))
        a3 = store.hold(ProposedAction(action_type="tool_call", name="c", arguments={}))
        self.assertEqual(store.evaluate(a1, (policy,)), PolicyDecision.ALLOW)
        self.assertEqual(store.evaluate(a2, (policy,)), PolicyDecision.ALLOW)
        self.assertEqual(store.evaluate(a3, (policy,)), PolicyDecision.DENY)

    def test_log_is_append_only_and_queryable(self):
        store = QuarantineStore()
        action = ProposedAction(action_type="tool_call", name="x", arguments={})
        held = store.hold(action)
        store.evaluate(held, ())
        store.release(held, lambda a: "ok")
        log = store.log()
        self.assertEqual(len(log), 3)  # held, evaluated, executed
        self.assertEqual(len(store.query(action.fingerprint)), 3)

    def test_emit_on_deny(self):
        events = []
        store = QuarantineStore(emit=lambda kind, payload: events.append((kind, payload)))
        held = store.hold(ProposedAction(action_type="tool_call", name="forbidden", arguments={}))
        store.evaluate(held, (denylist_policy("forbidden"),))
        store.deny(held, reason="on denylist", policy_name="denylist_policy")
        self.assertEqual(events[0][0], "action_denied")
        self.assertEqual(events[0][1]["reason"], "on denylist")


class FakeHarness:
    """Simulates a harness pass for LoopController tests."""

    def __init__(self, outcomes):
        self._outcomes = outcomes  # list of (candidate, tokens, observations)
        self._idx = 0

    def run_pass(self, spec, pass_number):
        candidate, tokens, observations = self._outcomes[min(self._idx, len(self._outcomes) - 1)]
        self._idx += 1
        return {"candidate": candidate, "tokens_used": tokens, "observations": observations}


class TestLoopController(unittest.TestCase):
    def _make_controller(self, harness, spec=None, emit=None):
        evaluators = {
            "check_file": lambda c, p: (CheckResult.PASS if c.get("file_ok") else CheckResult.FAIL, ""),
            "check_sections": lambda c, p: (CheckResult.PASS if c.get("sections_ok") else CheckResult.FAIL, ""),
            "check_quality": lambda c, p: (CheckResult.PASS if c.get("quality_ok") else CheckResult.FAIL, ""),
        }
        return LoopController(
            spec=spec or make_spec(),
            verifier=Verifier(evaluators),
            harness=harness,
            emit=emit,
        )

    def test_success_on_first_pass(self):
        harness = FakeHarness([
            ({"file_ok": True, "sections_ok": True, "quality_ok": True}, 500, []),
        ])
        result = self._make_controller(harness).run()
        self.assertEqual(result.outcome, RunOutcome.SUCCESS)
        self.assertEqual(result.total_passes, 1)

    def test_eventual_success(self):
        harness = FakeHarness([
            ({"file_ok": False, "sections_ok": True, "quality_ok": True}, 400, []),
            ({"file_ok": True, "sections_ok": True, "quality_ok": True}, 300, []),
        ])
        result = self._make_controller(harness).run()
        self.assertEqual(result.outcome, RunOutcome.SUCCESS)
        self.assertEqual(result.total_passes, 2)

    def test_max_iterations_escalates(self):
        bad_candidate = {"file_ok": False, "sections_ok": False, "quality_ok": False}
        harness = FakeHarness([(bad_candidate, 100, [])] * 10)
        spec = make_spec(max_passes=3)
        result = self._make_controller(harness, spec=spec).run()
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)
        self.assertIn("max_iteration", result.tripped_brakes)

    def test_token_budget_aborts(self):
        bad_candidate = {"file_ok": False, "sections_ok": False, "quality_ok": False}
        harness = FakeHarness([
            (bad_candidate, 6000, [{"kind": "llm.response", "usage": {"total_tokens": 6000}}]),
        ])
        spec = make_spec(token_budget=5000)
        result = self._make_controller(harness, spec=spec).run()
        self.assertEqual(result.outcome, RunOutcome.ABORTED)
        self.assertIn("budget", result.tripped_brakes)

    def test_no_progress_escalates(self):
        bad_candidate = {"file_ok": False, "sections_ok": False, "quality_ok": False}
        obs = [{"kind": "tool.invoked", "payload": {"tool": "loop", "args": "()", "kwargs": "{}"}}]
        harness = FakeHarness([(bad_candidate, 50, obs)] * 10)
        result = self._make_controller(harness).run()
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)
        self.assertIn("no_progress", result.tripped_brakes)

    def test_emits_run_lifecycle(self):
        events = []
        harness = FakeHarness([
            ({"file_ok": True, "sections_ok": True, "quality_ok": True}, 100, []),
        ])
        result = self._make_controller(harness, emit=lambda k, p: events.append((k, p))).run()
        kinds = [k for k, _ in events]
        self.assertIn("checkpoint", kinds)       # run_opened + run_closed
        self.assertIn("state.transition", kinds) # pass transitions
        self.assertIn("custom", kinds)           # verification_report + brake_decision
        self.assertEqual(kinds.count("checkpoint"), 2)

    def test_run_result_fields(self):
        harness = FakeHarness([
            ({"file_ok": True, "sections_ok": True, "quality_ok": True}, 750, []),
        ])
        result = self._make_controller(harness).run()
        self.assertEqual(result.total_tokens, 750)
        self.assertEqual(result.total_passes, 1)
        self.assertTrue(result.wall_clock_s >= 0)
        self.assertTrue(result.spec_hash)


if __name__ == "__main__":
    unittest.main()
