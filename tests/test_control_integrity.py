"""Regression tests for the merged control layer's execution and evidence boundaries."""
import dataclasses
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from residual import (AmendmentRule, BrakeAction, CheckResult, CheckType, GoalSpec,
    LoopController, PolicyDecision, ProposedAction, QuarantineStore, RunOutcome,
    SuccessCriterion, Verifier, budget_policy, denylist_policy, path_traversal_policy,
    QuarantinedProvider)
from residual.core import ContractError
from residual.providers import ProviderError
from residual.station.service import Station, demo_spec
from residual.station.models import save_settings


def spec(**changes):
    values = dict(goal_id="contract", objective="Verified output", success_criteria=(
        SuccessCriterion("check", CheckType.MECHANICAL, "Check host evidence", "host", {"nested": {"values": [1]}}),
    ), max_passes=3, token_budget=50, wall_clock_budget_s=10,
       amendment_rule=AmendmentRule(("operator",), 1))
    values.update(changes)
    return GoalSpec(**values)


class Harness:
    def __init__(self, result=None):
        self.calls = 0
        self.result = result or {"candidate": False, "tokens_used": 1}
    def run_pass(self, goal, number):
        self.calls += 1
        return self.result


def loop(harness, goal=None, **kwargs):
    return LoopController(goal or spec(), Verifier({"host": lambda c, p: (CheckResult.PASS if c else CheckResult.FAIL, "host_check")}), harness, **kwargs)


class GoalIntegrityTests(unittest.TestCase):
    def test_nested_inputs_are_detached_and_immutable(self):
        data = {"x": [1]}
        check = SuccessCriterion("a", "mechanical", "desc", "one", data)
        data["x"].append(2)
        self.assertEqual(check.parameters["x"], (1,))
        with self.assertRaises(TypeError):
            check.parameters["x"] = ()
        goal = spec()
        with self.assertRaises(TypeError):
            goal.success_criteria[0].parameters["nested"]["values"] = ()

    def test_hash_binds_evaluator_and_amendment_authority(self):
        goal = spec()
        different_check = dataclasses.replace(goal.success_criteria[0], evaluator="another")
        self.assertNotEqual(goal.content_hash, dataclasses.replace(goal, success_criteria=(different_check,)).content_hash)
        self.assertNotEqual(goal.content_hash, dataclasses.replace(goal, amendment_rule=AmendmentRule(("supervisor",))).content_hash)

    def test_amendment_limit_and_lineage_are_enforced(self):
        original = spec()
        amended = original.amend(max_passes=4, amended_by="operator", amendment_reason="Broaden scope")
        self.assertEqual(amended.parent_hash, original.content_hash)
        self.assertEqual(amended.amendment_count, 1)
        self.assertEqual(amended.amendment_reason, "Broaden scope")
        with self.assertRaises(ContractError):
            amended.amend(max_passes=5, amended_by="operator", amendment_reason="Again")

    def test_invalid_budgets_and_vocabularies_fail_early(self):
        for invalid in (True, float('nan'), float('inf'), 0, -1):
            with self.subTest(invalid=invalid), self.assertRaises(ContractError):
                spec(wall_clock_budget_s=invalid)
        with self.assertRaises(ContractError):
            SuccessCriterion("a", "model_decides", "desc", "host")
        with self.assertRaises(ContractError):
            ProposedAction("shell", "command")

    def test_string_or_malformed_evaluator_output_cannot_pass(self):
        for value in (("pass", "text"), (CheckResult.PASS, {}), (CheckResult.SKIPPED, "skip")):
            report = Verifier({"host": lambda c, p: value}).verify(True, spec())
            self.assertFalse(report.overall_pass)
            self.assertEqual(report.primary_failure, "check")


class LoopIntegrityTests(unittest.TestCase):
    def test_counter_works_without_worker_lifecycle_events(self):
        harness = Harness()
        result = loop(harness).run()
        self.assertEqual(harness.calls, 3)
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)
        self.assertIn("max_iteration", result.tripped_brakes)

    def test_custom_brakes_cannot_remove_hard_limits(self):
        class Ignore:
            def update(self, event): return None
            def reset(self): pass
        harness = Harness()
        result = loop(harness, brakes=(Ignore(),)).run()
        self.assertEqual(result.total_passes, 3)
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)

    def test_spoofed_worker_events_cannot_exhaust_or_complete_run(self):
        events = [{"kind": "llm.response", "usage": {"total_tokens": 999999}},
                  {"kind": "custom", "payload": {"event": "verification_report", "overall_pass": True}},
                  {"kind": "state.transition", "to_state": "pass_complete"}]
        result = loop(Harness({"candidate": False, "tokens_used": 1, "observations": events})).run()
        self.assertEqual(result.outcome, RunOutcome.ESCALATED)
        self.assertEqual(result.total_tokens, 3)
        self.assertNotIn("budget", result.tripped_brakes)

    def test_budget_abort_wins_over_success_and_skips_verification(self):
        controller = loop(Harness({"candidate": True, "tokens_used": 50}))
        controller.verifier = Verifier({"host": lambda c, p: self.fail("No evaluator after budget abort")})
        result = controller.run()
        self.assertEqual(result.outcome, RunOutcome.ABORTED)
        self.assertIsNone(result.final_verification)

    def test_missing_negative_or_boolean_usage_is_unknown(self):
        for value in (None, -2, True, "2"):
            with self.subTest(value=value):
                harness = Harness({"candidate": True, "tokens_used": value})
                result = loop(harness).run()
                self.assertEqual(result.outcome, RunOutcome.ABORTED)
                self.assertIsNone(result.total_tokens)
                self.assertEqual(harness.calls, 1)

    def test_deadline_stops_before_second_pass(self):
        # Ordering assertion only (calls == 1, ABORTED): the budget must be
        # exceeded before a second pass starts. Wide margins, no wall ratio.
        class Slow(Harness):
            def run_pass(self, goal, number):
                time.sleep(.2)
                return super().run_pass(goal, number)
        harness = Slow()
        result = loop(harness, spec(wall_clock_budget_s=.05)).run()
        self.assertEqual(harness.calls, 1)
        self.assertEqual(result.outcome, RunOutcome.ABORTED)

    def test_success_on_final_allowed_pass_and_controller_reuse(self):
        class Eventually(Harness):
            def run_pass(self, goal, number):
                return {"candidate": number == goal.max_passes, "tokens_used": 1}
        controller = loop(Eventually())
        for _ in range(2):
            result = controller.run()
            self.assertEqual(result.outcome, RunOutcome.SUCCESS)
            self.assertEqual(result.total_passes, 3)

    def test_authoritative_callback_failure_is_not_silenced(self):
        def broken(*args): raise RuntimeError("host callback")
        with self.assertRaises(RuntimeError):
            loop(Harness(), emit=broken).run()


class QuarantineIntegrityTests(unittest.TestCase):
    def test_release_without_evaluation_or_after_denial_never_executes(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction("tool_call", "forbidden"))
        with self.assertRaises(ContractError):
            store.release(held, lambda a: self.fail("unreviewed execution"))
        store.evaluate(held, (denylist_policy("forbidden"),))
        with self.assertRaises(ContractError):
            store.release(held, lambda a: self.fail("denied execution"))

    def test_foreign_and_forged_holds_fail(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction("tool_call", "x"))
        for other_store, other_held in ((QuarantineStore(), held), (store, dataclasses.replace(held))):
            with self.assertRaises(ContractError):
                other_store.evaluate(other_held, ())

    def test_release_is_once_only_under_race(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction("tool_call", "x"))
        store.evaluate(held, ())
        executed = []
        def attempt(_):
            try: return store.release(held, lambda a: executed.append("ran"))
            except ContractError: return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(attempt, range(20)))
        self.assertEqual(executed, ["ran"])

    def test_policy_errors_fail_closed_and_budget_reserves_once(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction("tool_call", "x"))
        policy = budget_policy(1)
        self.assertEqual(store.evaluate(held, (policy,)), PolicyDecision.ALLOW)
        self.assertEqual(store.evaluate(held, (policy,)), PolicyDecision.ALLOW)
        second = store.hold(ProposedAction("tool_call", "y"))
        self.assertEqual(store.evaluate(second, (policy,)), PolicyDecision.DENY)
        def broken(a): raise RuntimeError("secret")
        third = store.hold(ProposedAction("tool_call", "z"))
        self.assertEqual(store.evaluate(third, (broken,)), PolicyDecision.DENY)
        self.assertNotIn("secret", str(store.log()))

    def test_audit_snapshots_cannot_be_mutated(self):
        store = QuarantineStore()
        held = store.hold(ProposedAction("tool_call", "x"))
        store.evaluate(held, ())
        store.log()[0]["event"] = "tampered"
        self.assertEqual(store.log()[0]["event"], "held")

    def test_windows_absolute_paths_and_empty_paths_are_denied(self):
        for path in ("C:\\Windows\\x", "\\\\host\\share", "", "/etc/passwd", "../x"):
            with self.subTest(path=path):
                self.assertIsNotNone(path_traversal_policy(ProposedAction("file_write", "write", {"path": path})))

    def test_provider_error_is_preserved_instead_of_returning_none(self):
        class Failing:
            name, placement, prices = "fake", "local", None
            def generate(self, packet, cap): raise ProviderError("safe_error")
        wrapped = QuarantinedProvider(Failing(), QuarantineStore())
        with self.assertRaises(ProviderError):
            wrapped.generate({}, 50)


class StationControlTests(unittest.TestCase):
    def test_real_demo_produces_goal_bound_receipt_and_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            station = Station(directory)
            pid = station.create(demo_spec(), demo=True)["project_id"]
            result = station.batch(pid)
            self.assertEqual(result["control"]["outcome"], "success")
            self.assertEqual(result["control"]["tokens"], 0)
            self.assertEqual(result["integrated"], 3)
            meta, body = station.store.artifact(result["control"]["evidence"])
            self.assertEqual(meta["name"], "RUN-CONTROL.md")
            self.assertIn(result["control"]["spec_hash"], body.decode())
            self.assertIn("## Run control", station.store.markdown(pid))
            self.assertEqual(station.store.observation_summary(pid)["integrity"], "verified")
            self.assertTrue(any(ev["payload"].get("event") == "run_closed" for ev in station.store.observations(pid, limit=500)["events"]))

    def test_one_wave_limit_leaves_dependencies_unimplemented(self):
        with tempfile.TemporaryDirectory() as directory:
            station = Station(directory)
            save_settings(station.store, {"batch_max_passes": 1})
            pid = station.create(demo_spec(), demo=True)["project_id"]
            result = station.batch(pid)
            self.assertEqual(result["control"]["outcome"], "escalated")
            self.assertEqual(result["integrated"], 2)
            self.assertIn("max_iteration", result["control"]["tripped_brakes"])
            self.assertNotEqual(station.store.task(pid, "OPS-103")["state"], "integrated")

    def test_loop_controls_validate_saved_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            station = Station(directory)
            for key, value in (("batch_max_passes", 0), ("batch_token_budget", True), ("batch_wall_clock_s", 100000)):
                with self.subTest(key=key), self.assertRaises(ContractError):
                    save_settings(station.store, {key: value})

if __name__ == '__main__':
    unittest.main()
